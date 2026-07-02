import datetime
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List

def get_most_recent_trading_day() -> str:
    now = datetime.datetime.now()
    # If weekend, go back to Friday
    if now.weekday() == 5: # Saturday
        now -= datetime.timedelta(days=1)
    elif now.weekday() == 6: # Sunday
        now -= datetime.timedelta(days=2)
    return now.strftime("%Y-%m-%d")

def query_db_stock_names(codes: List[str]) -> Dict[str, str]:
    """Batch query stock Chinese names from the shared market database."""
    from src.config.paths import get_market_db_path
    import sqlite3

    results = {}
    market_db = get_market_db_path()
    # Also check legacy stocks_default.db for backward compatibility during migration
    from src.config.paths import get_runtime_root
    legacy_db = get_runtime_root() / "stocks_default.db"
    for db_path in [market_db, legacy_db]:
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in codes)
                cursor.execute(f"SELECT code, name FROM stock_meta WHERE code IN ({placeholders})", codes)
                for code, name in cursor.fetchall():
                    if code not in results:
                        results[code] = name
                conn.close()
            except Exception:
                pass
        if len(results) == len(codes):
            break  # All found, no need to check legacy DB
    return results

def fetch_tencent_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    """Fetch real-time quotes from Tencent API, resolved against local DB metadata for stability.

    Name resolution priority (local-first):
      1. Watchlist.name in tenant DB — THS sync already populates this, always up-to-date
      2. stock_meta.name in shared DB — populated by initialize_history_data.py
      3. Live API response (fields[1]) — lightweight fallback for unknown stocks
    Close-price resolution:
      kline_daily in shared DB — used as fallback price when network is unavailable
    """
    from src.config.paths import active_tenant_var, get_runtime_root, get_market_db_path
    import sqlite3

    # 1. Resolve metadata (names and last close prices) from local DB
    tenant = active_tenant_var.get() or "default"
    tenant_db = get_runtime_root() / f"stocks_{tenant}.db"
    # Market data (stock_meta, kline_daily) lives in shared stocks_market.db
    market_db = get_market_db_path()
    # Backward-compat: also check stocks_default.db during migration period
    legacy_db = get_runtime_root() / "stocks_default.db"

    local_names = {}
    local_prices = {}

    # Priority 1: Query Watchlist.name from the tenant DB (THS sync stores correct names here)
    if tenant_db.exists():
        try:
            conn = sqlite3.connect(str(tenant_db))
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in symbols)
            cursor.execute(
                f"SELECT code, name FROM Watchlist WHERE code IN ({placeholders}) AND name IS NOT NULL AND name != ''",
                symbols
            )
            for code, name in cursor.fetchall():
                local_names[code] = name
            conn.close()
        except Exception:
            pass

    # Priority 2: Query stock_meta + kline_daily from shared market DB (then legacy fallback)
    for db_path in [market_db, legacy_db]:
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            # Fill missing names from stock_meta
            missing = [s for s in symbols if s not in local_names]
            if missing:
                placeholders = ",".join("?" for _ in missing)
                cursor.execute(
                    f"SELECT code, name FROM stock_meta WHERE code IN ({placeholders})",
                    missing
                )
                for code, name in cursor.fetchall():
                    if code not in local_names and name:
                        local_names[code] = name
            # Query last close prices from daily kline
            for code in symbols:
                if code in local_prices:
                    continue
                cursor.execute("SELECT close FROM kline_daily WHERE code = ? ORDER BY date DESC LIMIT 1", (code,))
                row = cursor.fetchone()
                if row:
                    local_prices[code] = float(row[0])
            conn.close()
        except Exception:
            pass
        # If all data found, skip legacy DB
        if all(s in local_names for s in symbols) and all(s in local_prices for s in symbols):
            break


    # 2. Call light-weight online API for current price and percentage change
    query_parts = []
    for s in symbols:
        bare_code = s.split(".")[0].strip()
        if not bare_code or not bare_code.isdigit():
            continue
        prefix = "sh" if bare_code.startswith("6") or bare_code.startswith("9") or bare_code.startswith("5") else "sz"
        query_parts.append(f"{prefix}{bare_code}")
    
    url = f"https://qt.gtimg.cn/q={','.join(query_parts)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("gbk", errors="ignore")
        
        results = []
        for line in content.split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            parts = line.split("=")
            val = parts[1].strip('"')
            fields = val.split("~")
            if len(fields) < 6:
                continue
            try:
                change_val = float(fields[32])
            except ValueError:
                change_val = 0.0
            
            code = fields[2]
            name = local_names.get(code) or fields[1]
            
            results.append({
                "code": code,
                "name": name,
                "price": float(fields[3]),
                "change": change_val,
                "sparkline": [10, 15, 12, 18, 14, 22, 22 + change_val * 2]
            })
        return results
    except Exception:
        # 3. Fallback: network error, return metadata and last close prices from local DB
        results = []
        for code in symbols:
            name = local_names.get(code) or f"代码 {code}"
            price = local_prices.get(code) or 0.0
            results.append({
                "code": code,
                "name": name,
                "price": price,
                "change": 0.0,
                "sparkline": [10, 10, 10, 10, 10, 10, 10]
            })
        return results

def fetch_eastmoney_sectors() -> List[Dict[str, Any]]:
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fields=f12,f14,f2,f3,f62&fid=f62&fs=m:90+t:2+f:!50"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        diff = data.get("data", {}).get("diff", [])
        results = []
        for d in diff:
            flow_val = float(d.get("f62", 0)) / 100000000.0 # in 100M
            results.append({
                "name": d.get("f14", ""),
                "flow": round(flow_val, 2),
                "change": float(d.get("f3", 0)),
                "sparkline": [10, 15, 8, 20, 25, 45, 45 + float(d.get("f3", 0)) * 2]
            })
        return results
    except Exception:
        return [
            {"name": "低空经济", "flow": 38.4, "change": 4.82, "sparkline": [10, 15, 8, 20, 25, 45, 60]},
            {"name": "AI算力", "flow": 29.1, "change": 3.15, "sparkline": [12, 10, 18, 14, 22, 30, 42]},
            {"name": "华为概念", "flow": 15.6, "change": 2.78, "sparkline": [5, 12, 9, 15, 20, 18, 28]},
            {"name": "半导体", "flow": 8.5, "change": 0.42, "sparkline": [15, 12, 16, 14, 18, 15, 19]},
            {"name": "生物医药", "flow": -18.2, "change": -2.10, "sparkline": [30, 25, 28, 18, 12, 15, 10]}
        ]

def fetch_eastmoney_longhu() -> List[Dict[str, Any]]:
    today = get_most_recent_trading_day()
    url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=BILLBOARD_NET_AMT&sortTypes=-1&pageSize=10&pageNumber=1&reportName=RPT_DAILY_BILLBOARD_DETAILNEW&columns=ALL&filter=(TRADE_DATE%3D%27{today}%27)"
    
    fallback_list = [
        {"code": "301550", "name": "万丰奥威", "reason": "三日涨幅达20%", "netAmount": 18500, "instBuyCount": 2, "yuziSeat": "中信证券西安朱雀大街"},
        {"code": "601138", "name": "工业富联", "reason": "日涨幅偏离值达7%", "netAmount": 12400, "instBuyCount": 3, "yuziSeat": "国泰君安上海分公司"},
        {"code": "000063", "name": "中兴通讯", "reason": "日涨幅偏离值达7%", "netAmount": 8900, "instBuyCount": 1, "yuziSeat": "东方财富拉萨团结路"},
        {"code": "300496", "name": "中科创达", "reason": "日跌幅偏离值达-7%", "netAmount": -4200, "instBuyCount": 0, "yuziSeat": "申万宏源上海分公司"}
    ]
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        diff = data.get("result", {}).get("data", [])
        if not diff:
            url_latest = "https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=TRADE_DATE%2CBILLBOARD_NET_AMT&sortTypes=-1%2C-1&pageSize=10&pageNumber=1&reportName=RPT_DAILY_BILLBOARD_DETAILNEW&columns=ALL"
            req_latest = urllib.request.Request(url_latest, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_latest, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            diff = data.get("result", {}).get("data", [])
            
        results = []
        for d in diff[:5]:
            net_amt = float(d.get("BILLBOARD_NET_AMT", 0)) / 10000.0 # to 10K
            results.append({
                "code": d.get("SECURITY_CODE", ""),
                "name": d.get("SECURITY_NAME_ABBR", ""),
                "reason": d.get("EXPLANATION", ""),
                "netAmount": round(net_amt, 2),
                "instBuyCount": int(d.get("ORGAN_BUY_NUM", 0)),
                "yuziSeat": d.get("MAX_BUY_ACTNAME", "") or "暂无著名席位"
            })
        
        # Batch query names from local DB to ensure consistency
        codes = [r["code"] for r in results]
        db_names = query_db_stock_names(codes)
        for r in results:
            if r["code"] in db_names:
                r["name"] = db_names[r["code"]]
        return results
    except Exception:
        codes = [r["code"] for r in fallback_list]
        db_names = query_db_stock_names(codes)
        for r in fallback_list:
            if r["code"] in db_names:
                r["name"] = db_names[r["code"]]
        return fallback_list

def fetch_eastmoney_limitup() -> List[Dict[str, Any]]:
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=LIMIT_UP_TIME&sortTypes=1&pageSize=10&pageNumber=1&reportName=RPT_LTPU_FREEZEDET&columns=ALL"
    fallback_list = [
        {"code": "000021", "name": "深科技", "price": 18.52, "change": 10.01, "time": "09:35:12", "count": 2},
        {"code": "603083", "name": "剑桥科技", "price": 42.15, "change": 10.00, "time": "09:42:05", "count": 1},
        {"code": "300502", "name": "新易盛", "price": 78.40, "change": 20.00, "time": "10:15:30", "count": 3},
        {"code": "600745", "name": "闻泰科技", "price": 38.65, "change": 9.99, "time": "11:22:15", "count": 1}
    ]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        diff = data.get("result", {}).get("data", [])
        results = []
        for d in diff[:5]:
            results.append({
                "code": d.get("SECURITY_CODE", ""),
                "name": d.get("SECURITY_NAME_ABBR", ""),
                "price": float(d.get("LATEST_PRICE", 0)),
                "change": float(d.get("CHANGE_RATE", 0)),
                "time": d.get("FIRST_LIMIT_UP_TIME", "")[-8:],
                "count": int(d.get("CONTINUOUS_PLATES_NUM", 1))
            })
        
        # Batch query names from local DB to ensure consistency
        codes = [r["code"] for r in results]
        db_names = query_db_stock_names(codes)
        for r in results:
            if r["code"] in db_names:
                r["name"] = db_names[r["code"]]
        return results
    except Exception:
        codes = [r["code"] for r in fallback_list]
        db_names = query_db_stock_names(codes)
        for r in fallback_list:
            if r["code"] in db_names:
                r["name"] = db_names[r["code"]]
        return fallback_list
