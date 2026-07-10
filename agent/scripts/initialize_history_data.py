# -*- coding: utf-8 -*-
"""
Initialize and backfill historical A-share stock data into the tenant-specific stocks_<tenant>.db.
Establishes the core tables (including kline_daily, kline_weekly, and stock_meta) and fetches historical data.
Supports both free data sources (AkShare, mootdx) and premium source (Tushare).
"""

import os
import sys
import argparse
import sqlite3
import logging
import time
import socket
import hashlib
import random
import secrets
import threading
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np
import akshare as ak
from fake_useragent import UserAgent

# Set default socket timeout to prevent indefinite hangs in AkShare requests
socket.setdefaulttimeout(15.0)

# Add agent root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.paths import get_runtime_root

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("history_initializer")

# ==================== Eastmoney Anti-bot Patch ====================
original_request = None
ua = UserAgent()

class AuthCache:
    def __init__(self):
        self.data = None
        self.expire_at = 0
        self.lock = threading.Lock()
        self.ttl = 20

_cache = AuthCache()

class PatchSign:
    def __init__(self):
        self.patched = False

    def set_patch(self, patched):
        self.patched = patched

    def is_patched(self):
        return self.patched

_patch_sign = PatchSign()

def _get_nid(user_agent):
    now = time.time()
    if _cache.data and now < _cache.expire_at:
        return _cache.data
    with _cache.lock:
        try:
            def generate_uuid_md5():
                unique_id = str(uuid.uuid4())
                md5_hash = hashlib.md5(unique_id.encode('utf-8')).hexdigest()
                return md5_hash

            def generate_st_nvi():
                HASH_LENGTH = 4
                def generate_random_string(length=21):
                    charset = "useandom-26T198340PX75pxJACKVERYMINDBUSHWOLF_GQZbfghjklqvwyzrict"
                    return ''.join(secrets.choice(charset) for _ in range(length))

                def sha256(input_str):
                    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()

                random_str = generate_random_string()
                hash_prefix = sha256(random_str)[:HASH_LENGTH]
                return random_str + hash_prefix

            url = "https://anonflow2.eastmoney.com/backend/api/webreport"
            screen_resolution = random.choice(['1920X1080', '2560X1440', '3840X2160'])
            payload = json.dumps({
                "osPlatform": "Windows",
                "sourceType": "WEB",
                "osversion": "Windows 10.0",
                "language": "zh-CN",
                "timezone": "Asia/Shanghai",
                "webDeviceInfo": {
                    "screenResolution": screen_resolution,
                    "userAgent": user_agent,
                    "canvasKey": generate_uuid_md5(),
                    "webglKey": generate_uuid_md5(),
                    "fontKey": generate_uuid_md5(),
                    "audioKey": generate_uuid_md5()
                }
            })
            headers = {
                'Cookie': f'st_nvi={generate_st_nvi()}',
                'Content-Type': 'application/json'
            }
            import requests
            response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            nid = data['data']['nid']

            _cache.data = nid
            _cache.expire_at = now + _cache.ttl
            return nid
        except Exception as e:
            logger.warning(f"Failed to get Eastmoney NID token: {e}")
            _cache.data = None
            _cache.expire_at = now + 300
            return None

def eastmoney_patch():
    global original_request
    if _patch_sign.is_patched():
        return

    import requests
    original_request = requests.Session.request

    def patched_request(self, method, url, **kwargs):
        is_target = any(
            d in (url or "")
            for d in [
                "fund.eastmoney.com",
                "push2.eastmoney.com",
                "push2his.eastmoney.com",
            ]
        )
        if not is_target:
            return original_request(self, method, url, **kwargs)
        user_agent = ua.random
        headers = kwargs.get("headers", {})
        headers["User-Agent"] = user_agent
        nid = _get_nid(user_agent)
        if nid:
            headers["Cookie"] = f"nid18={nid}"
        kwargs["headers"] = headers
        # Random sleep to prevent anti-bot blocking
        sleep_time = random.uniform(1, 3)
        time.sleep(sleep_time)
        return original_request(self, method, url, **kwargs)

    requests.Session.request = patched_request
    _patch_sign.set_patch(True)
    logger.info("Eastmoney requests patch applied successfully.")

# Apply Eastmoney patch immediately
eastmoney_patch()

# ==================================================================

# Table SQL definitions
CREATE_TABLES_SQL = {
    "trade_calendar": """
        CREATE TABLE IF NOT EXISTS trade_calendar (
            date TEXT PRIMARY KEY,
            is_open INTEGER NOT NULL
        );
    """,
    "kline_daily": """
        CREATE TABLE IF NOT EXISTS kline_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            amount REAL,
            pct_chg REAL,
            ma5 REAL,
            ma10 REAL,
            ma20 REAL,
            UNIQUE(code, date)
        );
    """,
    "kline_weekly": """
        CREATE TABLE IF NOT EXISTS kline_weekly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            amount REAL,
            pct_chg REAL,
            ma5 REAL,
            ma10 REAL,
            ma20 REAL,
            UNIQUE(code, date)
        );
    """,
    "stock_meta": """
        CREATE TABLE IF NOT EXISTS stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            list_date TEXT
        );
    """,
    "stock_valuation": """
        CREATE TABLE IF NOT EXISTS stock_valuation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            pe REAL,
            pb REAL,
            ps REAL,
            dv REAL, -- Dividend yield (%)
            market_cap REAL,
            float_market_cap REAL,
            UNIQUE(code, date)
        );
    """,
    "theme_mapping": """
        CREATE TABLE IF NOT EXISTS theme_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            theme_type TEXT NOT NULL, -- 'industry' or 'concept'
            theme_name TEXT NOT NULL,
            UNIQUE(code, theme_type, theme_name)
        );
    """,
    "capital_flow": """
        CREATE TABLE IF NOT EXISTS capital_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            main_net_inflow REAL,
            retail_net_inflow REAL,
            inflow_5d REAL,
            inflow_10d REAL,
            UNIQUE(code, date)
        );
    """,
    "margin_trading": """
        CREATE TABLE IF NOT EXISTS margin_trading (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            margin_balance REAL,
            margin_buy REAL,
            short_balance REAL,
            short_sell REAL,
            margin_short_balance REAL,
            UNIQUE(code, date)
        );
    """,
    "company_profile": """
        CREATE TABLE IF NOT EXISTS company_profile (
            code TEXT PRIMARY KEY,
            full_name TEXT,
            english_name TEXT,
            chairman TEXT,
            secretary TEXT,
            registered_capital REAL,
            employees INTEGER,
            main_business TEXT,
            business_scope TEXT,
            province TEXT,
            city TEXT,
            address TEXT,
            phone TEXT,
            website TEXT,
            listing_date TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """,
    "financial_income": """
        CREATE TABLE IF NOT EXISTS financial_income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            period TEXT NOT NULL,
            report_type TEXT,
            revenue REAL,
            gross_profit REAL,
            op_profit REAL,
            net_profit REAL,
            net_profit_excl REAL,
            eps REAL,
            yoy_revenue REAL,
            yoy_profit REAL,
            UNIQUE(code, period)
        );
    """,
    "financial_balance": """
        CREATE TABLE IF NOT EXISTS financial_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            period TEXT NOT NULL,
            total_assets REAL,
            total_liab REAL,
            equity REAL,
            cash REAL,
            receivable REAL,
            inventory REAL,
            fixed_assets REAL,
            UNIQUE(code, period)
        );
    """,
    "financial_cashflow": """
        CREATE TABLE IF NOT EXISTS financial_cashflow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            period TEXT NOT NULL,
            op_cashflow REAL,
            inv_cashflow REAL,
            fin_cashflow REAL,
            net_cashflow REAL,
            free_cashflow REAL,
            UNIQUE(code, period)
        );
    """,
    "financial_indicator": """
        CREATE TABLE IF NOT EXISTS financial_indicator (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            period TEXT NOT NULL,
            roe REAL,
            roa REAL,
            gross_margin REAL,
            net_margin REAL,
            debt_ratio REAL,
            current_ratio REAL,
            quick_ratio REAL,
            asset_turnover REAL,
            eps REAL,
            bvps REAL,
            UNIQUE(code, period)
        );
    """,
    "top10_shareholders": """
        CREATE TABLE IF NOT EXISTS top10_shareholders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            period TEXT NOT NULL,
            rank INTEGER NOT NULL,
            holder_name TEXT,
            hold_shares REAL,
            hold_ratio REAL,
            holder_type TEXT,
            change_type TEXT,
            UNIQUE(code, period, rank)
        );
    """,
    "dividend_records": """
        CREATE TABLE IF NOT EXISTS dividend_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            announce_date TEXT,
            record_date TEXT,
            ex_div_date TEXT,
            div_per_share REAL,
            bonus_share_ratio REAL,
            allotment_ratio REAL,
            allotment_price REAL,
            UNIQUE(code, ex_div_date)
        );
    """,
    "longhu_records": """
        CREATE TABLE IF NOT EXISTS longhu_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            date TEXT NOT NULL,
            reason TEXT,
            net_buy REAL,
            buy_amount REAL,
            sell_amount REAL,
            top_buyer_1 TEXT,
            top_buyer_2 TEXT,
            top_seller_1 TEXT,
            top_seller_2 TEXT,
            UNIQUE(code, date)
        );
    """,
    "limit_up_records": """
        CREATE TABLE IF NOT EXISTS limit_up_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            date TEXT NOT NULL,
            board_count INTEGER,
            open_count INTEGER,
            limit_time TEXT,
            last_open_time TEXT,
            turnover_rate REAL,
            free_float_mv REAL,
            reason TEXT,
            UNIQUE(code, date)
        );
    """,
    "north_bound_flow": """
        CREATE TABLE IF NOT EXISTS north_bound_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            hold_shares REAL,
            hold_ratio REAL,
            hold_mv REAL,
            net_buy REAL,
            UNIQUE(code, date)
        );
    """,
    "block_trade": """
        CREATE TABLE IF NOT EXISTS block_trade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            date TEXT NOT NULL,
            price REAL,
            volume REAL,
            amount REAL,
            buyer TEXT,
            seller TEXT,
            discount_pct REAL,
            UNIQUE(code, date, buyer, seller)
        );
    """
}

# Index Creation SQL
CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_kline_daily_code_date ON kline_daily(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_kline_weekly_code_date ON kline_weekly(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_stock_meta_code ON stock_meta(code);",
    "CREATE INDEX IF NOT EXISTS idx_valuation_code_date ON stock_valuation(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_theme_code ON theme_mapping(code);",
    "CREATE INDEX IF NOT EXISTS idx_theme_name ON theme_mapping(theme_name);",
    "CREATE INDEX IF NOT EXISTS idx_capital_flow_code_date ON capital_flow(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_margin_code_date ON margin_trading(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_fin_income_code ON financial_income(code, period);",
    "CREATE INDEX IF NOT EXISTS idx_fin_balance_code ON financial_balance(code, period);",
    "CREATE INDEX IF NOT EXISTS idx_fin_cashflow_code ON financial_cashflow(code, period);",
    "CREATE INDEX IF NOT EXISTS idx_fin_indicator_code ON financial_indicator(code, period);",
    "CREATE INDEX IF NOT EXISTS idx_top10_holder_code ON top10_shareholders(code, period);",
    "CREATE INDEX IF NOT EXISTS idx_dividend_code ON dividend_records(code);",
    "CREATE INDEX IF NOT EXISTS idx_longhu_code_date ON longhu_records(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_longhu_date ON longhu_records(date);",
    "CREATE INDEX IF NOT EXISTS idx_limitup_code_date ON limit_up_records(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_limitup_date ON limit_up_records(date);",
    "CREATE INDEX IF NOT EXISTS idx_northbound_code_date ON north_bound_flow(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_blocktrade_code_date ON block_trade(code, date);",
]

def init_db(db_path: str):
    """Initialize the database and create tables and indexes."""
    logger.info(f"Initializing database at: {db_path}")
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable WAL mode for concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create tables
    for table_name, sql in CREATE_TABLES_SQL.items():
        logger.info(f"Creating table {table_name}...")
        cursor.execute(sql)
        
    # Create indexes
    for sql in CREATE_INDEXES_SQL:
        cursor.execute(sql)
        
    conn.commit()
    conn.close()
    logger.info("Database initialization completed successfully.")

def fetch_with_retry(func, *args, max_retries=3, delay=2.0, **kwargs):
    """Wrapper to execute a fetching function with retries and exponential backoff."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            wait_time = delay * (2 ** attempt)
            func_name = getattr(func, '__name__', str(func))
            logger.warning(f"Error executing {func_name} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    raise last_exc

def get_market_prefix(code: str) -> str:
    """Return 'sh' or 'sz' or 'bj' based on stock code prefix."""
    if code.startswith(('60', '68', '90', '58')):
        return 'sh'
    elif code.startswith(('00', '30', '20', '08')):
        return 'sz'
    elif code.startswith(('43', '83', '87', '88', '92')):
        return 'bj'
    return 'sh'

def to_ts_code(code: str) -> str:
    """Convert 6-digit stock code to Tushare format."""
    if code.startswith(('60', '68', '90', '58')):
        return f"{code}.SH"
    elif code.startswith(('00', '30', '20', '08')):
        return f"{code}.SZ"
    elif code.startswith(('43', '83', '87', '88', '92')):
        return f"{code}.BJ"
    return code

def backfill_trade_calendar(db_path: str, start_date: str, end_date: str):
    """Backfill trade calendar from AkShare."""
    logger.info("Backfilling trade calendar...")
    try:
        df = fetch_with_retry(ak.tool_trade_date_hist_sina)
        if df is not None and not df.empty:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Format dates and filter
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
            filtered_df = df[(df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)]
            
            records = [(row['trade_date'], 1) for _, row in filtered_df.iterrows()]
            
            cursor.executemany(
                "INSERT OR IGNORE INTO trade_calendar (date, is_open) VALUES (?, ?)",
                records
            )
            conn.commit()
            conn.close()
            logger.info(f"Successfully backfilled {len(records)} trading dates.")
        else:
            logger.error("Failed to fetch trade calendar: Empty DataFrame returned.")
    except Exception as e:
        logger.error(f"Failed to backfill trade calendar: {e}")

def get_active_stocks(db_path: str = None) -> List[Dict[str, str]]:
    """
    Get all active A-share stocks. Uses a multi-source fallback chain:
      0. TDX local file (tdx_a_shares.json) — parsed from local 通达信 software, zero network needed
      1. mootdx TCP (direct server IP, avoids auto-discovery ping failure in Docker)
      2. AKShare SH + SZ spot APIs (separate endpoints)
      3. AKShare stock_info_a_code_name (needs SZSE access)
      4. Extract from local theme_mapping table (guaranteed fallback if market data available)
    """
    logger.info("Fetching active A-share stock list (multi-source fallback)...")

    # Source 0: TDX local file (pre-generated from local 通达信/同花顺 software)
    # This file contains 5156 A-shares parsed from shs.tnf + szs.tnf — no network required.
    # File is generated by: scripts/update_tdx_stock_list.py
    try:
        import json as _json
        from src.config.paths import _get_active_runtime_dir
        _tdx_candidates = [
            _get_active_runtime_dir() / "tdx_a_shares.json",
            Path(__file__).parent.parent / "data" / "tdx_a_shares.json",
        ]
        for _tdx_path in _tdx_candidates:
            if _tdx_path.exists():
                with open(_tdx_path, 'r', encoding='utf-8') as _f:
                    _tdx_data = _json.load(_f)
                _stocks = _tdx_data.get('stocks', [])
                if len(_stocks) > 1000:
                    logger.info(f"[Source 0 TDX] Loaded {len(_stocks)} A-shares from local TDX file: {_tdx_path}")
                    return [{'code': s['code'], 'name': s['name']} for s in _stocks]
    except Exception as _e:
        logger.debug(f"TDX local file source failed: {_e}")

    # Source 1: mootdx with direct server IP (avoids factory() auto-discovery)
    MOOTDX_SERVERS = [
        ('119.147.212.81', 7709),
        ('121.14.110.194', 7709),
        ('114.80.149.11',  7709),
        ('202.108.253.130', 7709),
    ]
    for server_ip, server_port in MOOTDX_SERVERS:
        try:
            from mootdx.quotes import StdQuotes
            client = StdQuotes(server=server_ip, port=server_port, timeout=10)
            stocks = []
            for market_id in [0, 1]:  # 0=SZ, 1=SH
                try:
                    count = client.count(market=market_id)
                    if not count or count < 100:
                        continue
                    for start in range(0, min(count, 10000), 1000):
                        items = client.stocks(market=market_id, offset=start, count=1000)
                        if items is not None:
                            for item in items:
                                code = str(item.get('code', '')).strip().zfill(6)
                                name = str(item.get('name', '')).strip()
                                if code and name and code.isdigit():
                                    stocks.append({'code': code, 'name': name})
                except Exception:
                    pass
            client.close()
            if len(stocks) > 100:
                seen = set()
                unique = []
                for s in stocks:
                    if s['code'] not in seen:
                        seen.add(s['code'])
                        unique.append(s)
                logger.info(f"mootdx ({server_ip}): Found {len(unique)} A-share stocks.")
                return unique
        except Exception as e:
            logger.debug(f"mootdx {server_ip} failed: {e}")
    logger.warning("All mootdx servers failed, trying HTTP sources...")



    # Source 2: AKShare SH + SZ spot (separate endpoints, avoid szse.cn)
    try:
        stocks = []
        for fn_name in ['stock_sh_a_spot_em', 'stock_sz_a_spot_em']:
            try:
                fn = getattr(ak, fn_name, None)
                if fn is None:
                    continue
                df = fetch_with_retry(fn)
                if df is not None and not df.empty:
                    code_col = '代码' if '代码' in df.columns else df.columns[0]
                    name_col = '名称' if '名称' in df.columns else df.columns[1]
                    for _, row in df.iterrows():
                        code = str(row[code_col]).strip().zfill(6)
                        name = str(row[name_col]).strip()
                        if code.isdigit():
                            stocks.append({'code': code, 'name': name})
            except Exception as ex:
                logger.debug(f"AKShare {fn_name} failed: {ex}")
        if len(stocks) > 100:
            seen = set()
            unique = [s for s in stocks if s['code'] not in seen and not seen.add(s['code'])]  # type: ignore[func-returns-value]
            logger.info(f"AKShare SH+SZ: Found {len(unique)} A-share stocks.")
            return unique
    except Exception as e:
        logger.debug(f"AKShare SH+SZ source failed: {e}")

    # Source 3: AKShare combined (may timeout in Docker due to szse.cn block)
    try:
        df = fetch_with_retry(ak.stock_info_a_code_name)
        if df is not None and not df.empty and len(df) > 100:
            stocks = [
                {'code': str(row['code']).strip().zfill(6), 'name': str(row['name']).strip()}
                for _, row in df.iterrows()
            ]
            logger.info(f"AKShare combined: Found {len(stocks)} A-share stocks.")
            return stocks
    except Exception as e:
        logger.debug(f"AKShare combined source failed: {e}")

    # Source 4: Extract unique codes from local theme_mapping DB (guaranteed fallback)
    if db_path and os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT DISTINCT code FROM theme_mapping WHERE LENGTH(code)=6 ORDER BY code"
            ).fetchall()
            conn.close()
            if rows:
                # Get names from stock_meta if available
                conn2 = sqlite3.connect(db_path)
                meta = {r[0]: r[1] for r in conn2.execute("SELECT code, name FROM stock_meta").fetchall()}
                conn2.close()
                stocks = [{'code': r[0], 'name': meta.get(r[0], f'股票{r[0]}')} for r in rows]
                logger.info(f"DB theme_mapping fallback: Found {len(stocks)} unique stock codes.")
                return stocks
        except Exception as e:
            logger.error(f"DB fallback failed: {e}")

    logger.error("All stock list sources exhausted. Cannot get full market list.")
    return []





def calculate_ma(df: pd.DataFrame, window: int) -> pd.Series:
    """Calculate moving average."""
    if len(df) < window:
        return pd.Series(index=df.index, dtype=np.float64)
    return df['close'].rolling(window=window).mean()

def get_sync_dates(db_path: str, code: str, default_start_date: str) -> Tuple[str, bool]:
    """
    Check database for existing records of this stock to support incremental backfilling.
    Returns:
        - start_date to fetch from.
        - boolean indicating if daily and weekly are already fully synced.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check kline_daily
    cursor.execute("SELECT MAX(date) FROM kline_daily WHERE code = ?", (code,))
    row_daily = cursor.fetchone()
    max_daily = row_daily[0] if row_daily and row_daily[0] else None
    
    # Check kline_weekly
    cursor.execute("SELECT MAX(date) FROM kline_weekly WHERE code = ?", (code,))
    row_weekly = cursor.fetchone()
    max_weekly = row_weekly[0] if row_weekly and row_weekly[0] else None
    
    conn.close()
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if max_daily and max_weekly:
        latest_sync = min(max_daily, max_weekly)
        if latest_sync >= today_str:
            return today_str, True
            
        # Overlap by 30 calendar days (~20 trading days) to ensure rolling MA (ma20) compiles correctly
        latest_dt = datetime.strptime(latest_sync, '%Y-%m-%d')
        start_dt = max(latest_dt - timedelta(days=30), datetime.strptime(default_start_date, '%Y-%m-%d'))
        return start_dt.strftime('%Y-%m-%d'), False
        
    return default_start_date, False

def fetch_kline_akshare(code: str, start_date: str, end_date: str, period: str) -> Optional[pd.DataFrame]:
    """Fetch daily or weekly K-lines via AkShare."""
    start_str = start_date.replace('-', '')
    end_str = end_date.replace('-', '')
    period_str = "daily" if period == 'D' else "weekly"
    try:
        df = fetch_with_retry(
            ak.stock_zh_a_hist,
            symbol=code,
            period=period_str,
            start_date=start_str,
            end_date=end_str,
            adjust="qfq"
        )
        if df is not None and not df.empty:
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_chg'
            })
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
            df = df.sort_values('trade_date').reset_index(drop=True)
            return df
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch {period} K-line via AkShare: {e}")
    return None

def fetch_kline_mootdx(code: str, start_date: str, end_date: str, period: str) -> Optional[pd.DataFrame]:
    """Fallback: Fetch daily or weekly K-lines via mootdx (direct TCP connect to TongDaXin)."""
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market="std")
    except Exception as e:
        logger.error(f"Failed to initialize mootdx client: {e}")
        return None

    interval_code = 4 if period == 'D' else 5 # 4: daily, 5: weekly
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end_dt - start_dt).days
    
    if period == 'D':
        expected_bars = int(days * 5 / 7) + 50
    else:
        expected_bars = int(days / 7) + 10

    chunks = []
    start_page = 0
    page_size = 800

    try:
        while len(chunks) * page_size < expected_bars:
            df = client.bars(symbol=code, frequency=interval_code, start=start_page * page_size, offset=page_size)
            if df is not None and not df.empty:
                df['trade_date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                chunks.append(df)
                
                earliest_date = df['trade_date'].min()
                if earliest_date <= start_date or len(df) < page_size:
                    break
            else:
                break
            start_page += 1

        if not chunks:
            return None

        combined_df = pd.concat(chunks, ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['trade_date'])
        combined_df = combined_df[(combined_df['trade_date'] >= start_date) & (combined_df['trade_date'] <= end_date)]
        
        # Normalize columns to standard naming
        combined_df = combined_df.rename(columns={'vol': 'volume'})
        combined_df['volume'] = pd.to_numeric(combined_df['volume'], errors="coerce")
        combined_df['close'] = pd.to_numeric(combined_df['close'], errors="coerce")
        combined_df['open'] = pd.to_numeric(combined_df['open'], errors="coerce")
        combined_df['high'] = pd.to_numeric(combined_df['high'], errors="coerce")
        combined_df['low'] = pd.to_numeric(combined_df['low'], errors="coerce")
        combined_df['amount'] = pd.to_numeric(combined_df.get('amount', 0.0), errors="coerce")
        
        combined_df = combined_df.sort_values('trade_date').reset_index(drop=True)
        
        # Calculate pct_chg
        combined_df['pct_chg'] = combined_df['close'].pct_change() * 100
        combined_df['pct_chg'] = combined_df['pct_chg'].fillna(0.0).round(2)
        
        return combined_df
    except Exception as e:
        logger.error(f"[{code}] Failed to fetch {period} K-line via mootdx: {e}")
        return None

def fetch_kline_with_fallback(code: str, start_date: str, end_date: str, period: str) -> Optional[pd.DataFrame]:
    """Fetch daily or weekly K-lines with sliding fallback logic (AkShare -> mootdx/TDX)."""
    # 1. Try AkShare
    df = fetch_kline_akshare(code, start_date, end_date, period)
    if df is not None and not df.empty:
        return df
        
    # 2. Try mootdx/TDX Fallback
    logger.warning(f"[{code}] AkShare failed. Sliding fallback to mootdx (pytdx connection)...")
    df = fetch_kline_mootdx(code, start_date, end_date, period)
    if df is not None and not df.empty:
        return df
        
    return None

def get_preceding_history(db_path: str, code: str, start_date: str, table_name: str, limit: int = 30) -> pd.DataFrame:
    """Load the last N records before start_date from the database."""
    conn = sqlite3.connect(db_path)
    query = f"""
        SELECT date, open, high, low, close, volume, amount, pct_chg 
        FROM {table_name} 
        WHERE code = ? AND date < ? 
        ORDER BY date DESC LIMIT ?
    """
    try:
        df = pd.read_sql_query(query, conn, params=(code, start_date, limit))
        conn.close()
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)
            return df
    except Exception as e:
        logger.warning(f"Failed to fetch preceding history from {table_name}: {e}")
    return pd.DataFrame()

def backfill_kline(db_path: str, code: str, start_date: str, end_date: str):
    """Fetch and store daily & weekly K-lines for a stock code."""
    for period, table_name in [('D', 'kline_daily'), ('W', 'kline_weekly')]:
        try:
            df = fetch_kline_with_fallback(code, start_date, end_date, period)
            if df is not None and not df.empty:
                # Load preceding 30 days of history from database to ensure MAs are calculated correctly
                hist_df = get_preceding_history(db_path, code, start_date, table_name, limit=30)
                if not hist_df.empty:
                    df_new = df[df['trade_date'] > hist_df['date'].max()].copy()
                    if not df_new.empty:
                        hist_df = hist_df.rename(columns={'date': 'trade_date'})
                        combined = pd.concat([hist_df, df_new], ignore_index=True)
                        combined['ma5'] = calculate_ma(combined, 5)
                        combined['ma10'] = calculate_ma(combined, 10)
                        combined['ma20'] = calculate_ma(combined, 20)
                        df = combined[combined['trade_date'] >= start_date].copy()
                    else:
                        df = pd.DataFrame()
                else:
                    df['ma5'] = calculate_ma(df, 5)
                    df['ma10'] = calculate_ma(df, 10)
                    df['ma20'] = calculate_ma(df, 20)

                if df.empty:
                    continue

                records = []
                for _, row in df.iterrows():
                    records.append((
                        code,
                        row['trade_date'],
                        float(row['open']),
                        float(row['high']),
                        float(row['low']),
                        float(row['close']),
                        float(row['volume']),
                        float(row['amount']) if 'amount' in row else 0.0,
                        float(row['pct_chg']) if 'pct_chg' in row else 0.0,
                        float(row['ma5']) if not pd.isna(row['ma5']) else None,
                        float(row['ma10']) if not pd.isna(row['ma10']) else None,
                        float(row['ma20']) if not pd.isna(row['ma20']) else None
                    ))
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.executemany(
                    f"""
                    INSERT OR REPLACE INTO {table_name} 
                    (code, date, open, high, low, close, volume, amount, pct_chg, ma5, ma10, ma20)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    records
                )
                conn.commit()
                conn.close()
                logger.info(f"[{code}] Backfilled {len(records)} K-lines into {table_name}.")
        except Exception as e:
            logger.error(f"[{code}] Failed backfilling {period} K-line: {e}")

def fetch_listing_date(code: str) -> Optional[str]:
    """Fetch listing date directly from Eastmoney API, bypassing buggy AkShare wrapper."""
    try:
        import requests
        market_code = 1 if code.startswith("6") else 0
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "fltt": "2",
            "invt": "2",
            "fields": "f189",
            "secid": f"{market_code}.{code}",
        }
        # Using fetch_with_retry for HTTP requests
        r = fetch_with_retry(requests.get, url, params=params, timeout=10)
        data = r.json()
        if data and "data" in data and data["data"] and "f189" in data["data"]:
            val = str(data["data"]["f189"]).strip()
            if len(val) == 8 and val.isdigit():
                return f"{val[:4]}-{val[4:6]}-{val[6:]}"
            return val
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch listing date directly: {e}")
    return None

_cached_spot_df = None

def backfill_valuation(db_path: str, code: str, start_date: str, end_date: str, ts_pro: Optional[Any] = None):
    """Backfill valuation indicators using Tushare or free AkShare spot data."""
    global _cached_spot_df
    if ts_pro is not None:
        try:
            ts_code = to_ts_code(code)
            ts_start = start_date.replace('-', '')
            ts_end = end_date.replace('-', '')
            df = fetch_with_retry(
                ts_pro.daily_basic,
                ts_code=ts_code,
                start_date=ts_start,
                end_date=ts_end,
                fields='trade_date,pe,pb,ps,dv,total_mv,float_mv'
            )
            if df is not None and not df.empty:
                records = []
                for _, row in df.iterrows():
                    trade_date = pd.to_datetime(row['trade_date']).strftime('%Y-%m-%d')
                    records.append((
                        code,
                        trade_date,
                        float(row['pe']) if row['pe'] is not None else None,
                        float(row['pb']) if row['pb'] is not None else None,
                        float(row['ps']) if row['ps'] is not None else None,
                        float(row['dv']) if row['dv'] is not None else None,
                        float(row['total_mv']) * 10000.0 if row['total_mv'] is not None else None,
                        float(row['float_mv']) * 10000.0 if row['float_mv'] is not None else None
                    ))
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO stock_valuation 
                    (code, date, pe, pb, ps, dv, market_cap, float_market_cap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    records
                )
                conn.commit()
                conn.close()
                logger.info(f"[{code}] Backfilled {len(records)} valuation records via Tushare.")
                return
        except Exception as e:
            logger.warning(f"[{code}] Tushare valuation backfill failed: {e}. Falling back to AkShare spot.")

    # Free Fallback: Fetch current spot valuation and store for today
    try:
        if _cached_spot_df is None:
            logger.info("Fetching and caching full A-share spot data for valuation fallback...")
            _cached_spot_df = fetch_with_retry(ak.stock_zh_a_spot_em)
        df = _cached_spot_df
        if df is not None and not df.empty:
            row = df[df['代码'] == code]
            if not row.empty:
                row = row.iloc[0]
                today_str = datetime.now().strftime('%Y-%m-%d')
                pe = float(row['市盈率-动态']) if '市盈率-动态' in row and not pd.isna(row['市盈率-动态']) else None
                pb = float(row['市净率']) if '市净率' in row and not pd.isna(row['市净率']) else None
                market_cap = float(row['总市值']) if '总市值' in row and not pd.isna(row['总市值']) else None
                float_market_cap = float(row['流通市值']) if '流通市值' in row and not pd.isna(row['流通市值']) else None
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO stock_valuation 
                    (code, date, pe, pb, ps, dv, market_cap, float_market_cap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (code, today_str, pe, pb, None, None, market_cap, float_market_cap)
                )
                conn.commit()
                conn.close()
                logger.info(f"[{code}] Saved current spot valuation to database (cached).")
    except Exception as e:
        logger.error(f"Failed to fetch free spot valuation for {code}: {e}")

def backfill_capital_flow(db_path: str, code: str, start_date: str, end_date: str):
    """Backfill historical capital flow using AkShare."""
    try:
        market = get_market_prefix(code)
        df = fetch_with_retry(ak.stock_individual_fund_flow, stock=code, market=market)
        if df is not None and not df.empty:
            df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
            filtered_df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]
            
            records = []
            for _, row in filtered_df.iterrows():
                main_net = float(row['主力净流入-净额']) if '主力净流入-净额' in row else 0.0
                retail_net = 0.0
                if '个人净流入-净额' in row:
                    retail_net = float(row['个人净流入-净额'])
                elif '散户净流入-净额' in row:
                    retail_net = float(row['散户净流入-净额'])
                
                inflow_5d = float(row['主力净流入-5日净额']) if '主力净流入-5日净额' in row else None
                inflow_10d = float(row['主力净流入-10日净额']) if '主力净流入-10日净额' in row else None
                
                records.append((
                    code,
                    row['日期'],
                    main_net,
                    retail_net,
                    inflow_5d,
                    inflow_10d
                ))
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO capital_flow 
                (code, date, main_net_inflow, retail_net_inflow, inflow_5d, inflow_10d)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                records
            )
            conn.commit()
            conn.close()
            logger.info(f"[{code}] Backfilled {len(records)} capital flow records.")
    except Exception as e:
        logger.error(f"Failed to fetch capital flow for {code}: {e}")

def backfill_margin_trading(db_path: str, code: str, start_date: str, end_date: str, ts_pro: Optional[Any] = None):
    """Backfill margin trading details using Tushare (if configured)."""
    if ts_pro is not None:
        try:
            ts_code = to_ts_code(code)
            ts_start = start_date.replace('-', '')
            ts_end = end_date.replace('-', '')
            df = fetch_with_retry(
                ts_pro.margin_detail,
                ts_code=ts_code,
                start_date=ts_start,
                end_date=ts_end
            )
            if df is not None and not df.empty:
                records = []
                for _, row in df.iterrows():
                    trade_date = pd.to_datetime(row['trade_date']).strftime('%Y-%m-%d')
                    records.append((
                        code,
                        trade_date,
                        float(row['rzye']) if 'rzye' in row and row['rzye'] is not None else 0.0,
                        float(row['rzmre']) if 'rzmre' in row and row['rzmre'] is not None else 0.0,
                        float(row['rqye']) if 'rqye' in row and row['rqye'] is not None else 0.0,
                        float(row['rqmcl']) if 'rqmcl' in row and row['rqmcl'] is not None else 0.0,
                        float(row['rzrqye']) if 'rzrqye' in row and row['rzrqye'] is not None else 0.0
                    ))
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO margin_trading 
                    (code, date, margin_balance, margin_buy, short_balance, short_sell, margin_short_balance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    records
                )
                conn.commit()
                conn.close()
                logger.info(f"[{code}] Backfilled {len(records)} margin trading records via Tushare.")
                return
        except Exception as e:
            logger.warning(f"[{code}] Tushare margin trading backfill failed: {e}.")
            
    logger.info(f"[{code}] Margin trading history skipped (requires TUSHARE_TOKEN).")

def backfill_all_theme_mappings(db_path: str):
    """
    Fetch all industries once, constituents mapping, and update theme_mapping & stock_meta.
    """
    logger.info("Starting optimized global industry theme mapping...")
    try:
        industries_df = fetch_with_retry(ak.stock_board_industry_name_em)
        if industries_df is None or industries_df.empty:
            logger.error("Failed to fetch industry list from Eastmoney.")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        total_industries = len(industries_df)
        for idx, row in industries_df.iterrows():
            ind_name = row['板块名称']
            logger.info(f"[{idx + 1}/{total_industries}] Fetching constituents for industry: {ind_name}")
            try:
                const_df = fetch_with_retry(ak.stock_board_industry_cons_em, symbol=ind_name)
                if const_df is not None and not const_df.empty:
                    records = []
                    for _, stock_row in const_df.iterrows():
                        stock_code = str(stock_row['代码']).strip().zfill(6)
                        records.append((stock_code, 'industry', ind_name))
                    
                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO theme_mapping (code, theme_type, theme_name)
                        VALUES (?, ?, ?)
                        """,
                        records
                    )
                    
                    # Update stock_meta table with industry
                    for stock_code, _, ind in records:
                        cursor.execute(
                            "UPDATE stock_meta SET industry = ? WHERE code = ?",
                            (ind, stock_code)
                        )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Failed to fetch constituents for industry {ind_name}: {e}")
            time.sleep(0.3)
            
        conn.close()
        logger.info("Global industry theme mapping completed successfully.")
    except Exception as e:
        logger.error(f"Failed to run global theme mapping: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# NEW DATA FETCH FUNCTIONS (Phase 1 P0/P1 expansion)
# ─────────────────────────────────────────────────────────────────────────────

def backfill_company_profile(db_path: str, code: str) -> None:
    """Fetch and store company profile from AKShare (东财个股信息)."""
    try:
        df = fetch_with_retry(ak.stock_individual_info_em, symbol=code)
        if df is None or df.empty:
            return
        info = {row['item']: row['value'] for _, row in df.iterrows()}
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT OR REPLACE INTO company_profile
               (code, full_name, chairman, employees, main_business, province, listing_date, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                code,
                info.get('股票简称') or info.get('公司名称'),
                info.get('法人代表') or info.get('董事长'),
                int(str(info.get('员工人数', 0)).replace(',', '') or 0) if info.get('员工人数') else None,
                info.get('主营业务') or info.get('经营范围'),
                info.get('所属省份') or info.get('省份'),
                info.get('上市时间'),
            )
        )
        conn.commit()
        conn.close()
        logger.info(f"[{code}] Company profile saved.")
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch company profile: {e}")


def backfill_financial_indicator(db_path: str, code: str) -> None:
    """Fetch core financial indicators (ROE/ROA/margins) from AKShare."""
    try:
        df = fetch_with_retry(ak.stock_financial_analysis_indicator, symbol=code)
        if df is None or df.empty:
            return
        conn = sqlite3.connect(db_path)
        records = []
        for _, row in df.iterrows():
            period = str(row.get('日期', '')).strip()[:10]
            if not period:
                continue
            records.append((
                code, period,
                _safe_float(row.get('加权净资产收益率(%)')),
                _safe_float(row.get('总资产净利润率(%)')),
                _safe_float(row.get('销售毛利率(%)')),
                _safe_float(row.get('销售净利率(%)')),
                _safe_float(row.get('资产负债率(%)')),
                _safe_float(row.get('流动比率')),
                _safe_float(row.get('速动比率')),
                _safe_float(row.get('总资产周转率(次)')),
                _safe_float(row.get('基本每股收益(元)')),
                _safe_float(row.get('每股净资产(元)')),
            ))
        conn.executemany(
            """INSERT OR REPLACE INTO financial_indicator
               (code, period, roe, roa, gross_margin, net_margin,
                debt_ratio, current_ratio, quick_ratio, asset_turnover, eps, bvps)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            records
        )
        conn.commit()
        conn.close()
        logger.info(f"[{code}] Financial indicators: {len(records)} periods saved.")
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch financial indicators: {e}")


def backfill_dividends(db_path: str, code: str) -> None:
    """Fetch dividend history from AKShare (CNINFO source)."""
    try:
        df = fetch_with_retry(ak.stock_dividend_cninfo, symbol=code)
        if df is None or df.empty:
            return
        conn = sqlite3.connect(db_path)
        records = []
        for _, row in df.iterrows():
            ex_date = str(row.get('除权除息日', '') or row.get('股权登记日', '')).strip()[:10]
            if not ex_date or ex_date == 'nan':
                continue
            records.append((
                code,
                str(row.get('公告日期', '')).strip()[:10],
                str(row.get('股权登记日', '')).strip()[:10],
                ex_date,
                _safe_float(row.get('每股派息(税前)(元)') or row.get('每股现金红利(元)')),
                _safe_float(row.get('每股送股(股)')),
                _safe_float(row.get('每股转增(股)')),
                _safe_float(row.get('配股价格(元)')),
            ))
        conn.executemany(
            """INSERT OR IGNORE INTO dividend_records
               (code, announce_date, record_date, ex_div_date,
                div_per_share, bonus_share_ratio, allotment_ratio, allotment_price)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            records
        )
        conn.commit()
        conn.close()
        logger.info(f"[{code}] Dividends: {len(records)} records saved.")
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch dividend records: {e}")


def backfill_top10_shareholders(db_path: str, code: str) -> None:
    """Fetch top-10 float shareholders from AKShare (东财)."""
    try:
        df = fetch_with_retry(ak.stock_gdfx_free_top_10_em, symbol=code)
        if df is None or df.empty:
            return
        conn = sqlite3.connect(db_path)
        records = []
        for _, row in df.iterrows():
            period = str(row.get('报告期', '')).strip()[:10]
            rank = int(row.get('名次', 0) or 0)
            if not period or rank == 0:
                continue
            records.append((
                code, period, rank,
                str(row.get('股东名称', '')).strip(),
                _safe_float(row.get('持股数量')),
                _safe_float(row.get('持股比例')),
                str(row.get('股东性质', '') or '').strip(),
                str(row.get('增减', '') or '').strip(),
            ))
        conn.executemany(
            """INSERT OR REPLACE INTO top10_shareholders
               (code, period, rank, holder_name, hold_shares, hold_ratio, holder_type, change_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            records
        )
        conn.commit()
        conn.close()
        logger.info(f"[{code}] Top-10 shareholders: {len(records)} records saved.")
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch top-10 shareholders: {e}")


def backfill_longhu_for_stock(db_path: str, code: str, start_date: str, end_date: str) -> None:
    """Fetch dragon-tiger board (龙虎榜) history for a specific stock."""
    try:
        df = fetch_with_retry(
            ak.stock_lhb_stock_statistic_um,
            symbol=code,
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', '')
        )
        if df is None or df.empty:
            return
        conn = sqlite3.connect(db_path)
        records = []
        for _, row in df.iterrows():
            date_str = str(row.get('上榜日期', '') or row.get('日期', '')).strip()[:10]
            if not date_str or date_str == 'nan':
                continue
            records.append((
                code,
                str(row.get('股票名称', '') or '').strip(),
                date_str,
                str(row.get('上榜原因', '') or '').strip(),
                _safe_float(row.get('净买入额')),
                _safe_float(row.get('买入额')),
                _safe_float(row.get('卖出额')),
                str(row.get('买方机构1', '') or '').strip(),
                str(row.get('买方机构2', '') or '').strip(),
                str(row.get('卖方机构1', '') or '').strip(),
                str(row.get('卖方机构2', '') or '').strip(),
            ))
        conn.executemany(
            """INSERT OR REPLACE INTO longhu_records
               (code, name, date, reason, net_buy, buy_amount, sell_amount,
                top_buyer_1, top_buyer_2, top_seller_1, top_seller_2)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            records
        )
        conn.commit()
        conn.close()
        if records:
            logger.info(f"[{code}] Longhu records: {len(records)} entries saved.")
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch longhu records: {e}")


def backfill_limit_up_by_date_range(db_path: str, start_date: str, end_date: str) -> None:
    """Backfill daily limit-up board data across a date range (全市场按日期抓取)."""
    try:
        import akshare as ak
        conn = sqlite3.connect(db_path)
        # Iterate over trading days in range
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        # Only fetch last 90 days (API often has limits on historical data)
        cutoff_dt = end_dt - timedelta(days=90)
        actual_start = max(start_dt, cutoff_dt)
        current = actual_start
        total_saved = 0
        while current <= end_dt:
            date_str = current.strftime('%Y%m%d')
            try:
                df = ak.stock_zt_pool_em(date=date_str)
                if df is not None and not df.empty:
                    records = []
                    for _, row in df.iterrows():
                        code = str(row.get('代码', '') or '').strip().zfill(6)
                        if not code or not code.isdigit():
                            continue
                        records.append((
                            code,
                            str(row.get('名称', '') or '').strip(),
                            current.strftime('%Y-%m-%d'),
                            int(row.get('连板数', 1) or 1),
                            int(row.get('打开次数', 0) or 0),
                            str(row.get('涨停时间', '') or '').strip(),
                            str(row.get('最后封板时间', '') or '').strip(),
                            _safe_float(row.get('换手率')),
                            _safe_float(row.get('流通市值')),
                            str(row.get('涨停原因类别', '') or row.get('原因类别', '') or '').strip(),
                        ))
                    if records:
                        conn.executemany(
                            """INSERT OR IGNORE INTO limit_up_records
                               (code, name, date, board_count, open_count,
                                limit_time, last_open_time, turnover_rate, free_float_mv, reason)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            records
                        )
                        conn.commit()
                        total_saved += len(records)
            except Exception:
                pass  # Skip days with no data or API errors
            current += timedelta(days=1)
            time.sleep(0.2)
        conn.close()
        logger.info(f"Limit-up records backfill complete: {total_saved} rows saved.")
    except Exception as e:
        logger.error(f"Failed to backfill limit-up records: {e}")


def backfill_north_bound(db_path: str, code: str, start_date: str, end_date: str) -> None:
    """Fetch northbound (沪深股通) capital flow for a specific stock."""
    try:
        df = fetch_with_retry(ak.stock_hsgt_hist_em, symbol=code)
        if df is None or df.empty:
            return
        conn = sqlite3.connect(db_path)
        records = []
        for _, row in df.iterrows():
            date_str = str(row.get('日期', '')).strip()[:10]
            if not date_str or date_str < start_date or date_str > end_date:
                continue
            records.append((
                code, date_str,
                _safe_float(row.get('持股数量')),
                _safe_float(row.get('持股比例')),
                _safe_float(row.get('持股市值')),
                _safe_float(row.get('当日增减')),
            ))
        conn.executemany(
            """INSERT OR REPLACE INTO north_bound_flow
               (code, date, hold_shares, hold_ratio, hold_mv, net_buy)
               VALUES (?, ?, ?, ?, ?, ?)""",
            records
        )
        conn.commit()
        conn.close()
        if records:
            logger.info(f"[{code}] Northbound flow: {len(records)} records saved.")
    except Exception as e:
        logger.warning(f"[{code}] Failed to fetch northbound flow: {e}")


def _safe_float(val) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    try:
        if val is None or str(val).strip() in ('', 'nan', 'None', '-', '--'):
            return None
        return float(str(val).replace(',', '').replace('%', '').strip())
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    default_years = int(os.getenv("BACKFILL_YEARS", "5"))
    
    parser = argparse.ArgumentParser(description="Initialize and backfill A-share historical data.")
    parser.add_argument("--code", type=str, help="Comma-separated stock codes to backfill (e.g., 600519,000001).")
    parser.add_argument("--all", action="store_true", help="Backfill all active A-share stocks.")
    parser.add_argument("--years", type=int, default=default_years, help=f"Number of years of history to backfill (default: {default_years}).")
    parser.add_argument("--db", type=str, help="Custom path to the SQLite database.")
    parser.add_argument("--tenant", type=str, default="default", help="Tenant ID to initialize database for (default: default).")
    parser.add_argument("--skip-kline", action="store_true", help="Skip K-line backfill (faster run for metadata-only update).")
    parser.add_argument("--fundamentals", action="store_true", help="Also backfill financial indicators, dividends, shareholders.")
    parser.add_argument("--sentiment", action="store_true", help="Also backfill longhu, limit-up, northbound flow.")
    
    args = parser.parse_args()
    
    if args.db:
        db_path = args.db
    else:
        tenant = args.tenant
        from src.config.paths import active_tenant_var, get_market_db_path
        active_tenant_var.set(tenant)
        # All market data (K-line, fundamentals, capital flow, etc.) goes to the SHARED
        # public market database (stocks_market.db), NOT the per-tenant database.
        # The per-tenant database only stores Watchlist, AlertRules, and user-private data.
        db_path = str(get_market_db_path())
        logger.info(f"[Architecture] Writing market data to shared DB: {db_path}")

    init_db(db_path)

    
    # 1. Backfill Trade Calendar
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=args.years * 365)).strftime('%Y-%m-%d')
    logger.info(f"Backfill Date Range: {start_date} to {end_date}")
    
    backfill_trade_calendar(db_path, start_date, end_date)
    
    # 2. Check Tushare Token
    ts_token = os.getenv("TUSHARE_TOKEN", "").strip()
    ts_pro = None
    if ts_token and ts_token not in ("your-tushare-token", ""):
        try:
            import tushare as ts
            ts.set_token(ts_token)
            ts_pro = ts.pro_api()
            logger.info("Tushare Token successfully loaded. Premium data backfill enabled.")
        except Exception as e:
            logger.warning(f"Failed to initialize Tushare with provided token: {e}. Falling back to free sources.")
    else:
        logger.info("No TUSHARE_TOKEN configured. Using free data sources only.")

    # 3. Resolve Stock Codes
    if args.all:
        stocks = get_active_stocks(db_path=db_path)
        if not stocks:
            logger.error("Could not fetch active stocks list from any source. Exiting.")
            sys.exit(1)
        logger.info(f"Running backfill for ALL {len(stocks)} A-share stocks. This may take a long time!")
    elif args.code:
        codes = [c.strip().zfill(6) for c in args.code.split(",")]
        stocks = [{"code": c, "name": f"Stock {c}"} for c in codes]
    else:
        logger.info("No stock codes specified. Defaulting to benchmark stocks: 600519 (Kweichow Moutai) and 000001 (Ping An Bank)")
        stocks = [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000001", "name": "平安银行"}
        ]
        
    # 4. Loop and Backfill K-line, Valuation, Capital Flow, Margin Trading
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for idx, stock in enumerate(stocks):
        code = stock["code"]
        name = stock["name"]
        logger.info(f"[{idx + 1}/{len(stocks)}] Starting backfill for {code} ({name})...")
        
        # Write/Update stock_meta name first
        cursor.execute(
            "INSERT OR IGNORE INTO stock_meta (code, name) VALUES (?, ?)",
            (code, name)
        )
        cursor.execute(
            "UPDATE stock_meta SET name = ? WHERE code = ?",
            (name, code)
        )
        conn.commit()
        
        # Check Incremental/Resumable sync dates
        adjusted_start, is_synced = get_sync_dates(db_path, code, start_date)
        if is_synced:
            logger.info(f"[{code}] Already fully synced up to today. Skipping K-line backfill.")
        else:
            logger.info(f"[{code}] Backfilling K-lines from {adjusted_start} to {end_date}...")
            backfill_kline(db_path, code, adjusted_start, end_date)
            
            # Fetch and store listing date on-demand if missing
            cursor.execute("SELECT list_date FROM stock_meta WHERE code = ?", (code,))
            meta_row = cursor.fetchone()
            if not meta_row or not meta_row[0]:
                list_date = fetch_listing_date(code)
                if list_date:
                    cursor.execute(
                        "UPDATE stock_meta SET list_date = ? WHERE code = ?",
                        (list_date, code)
                    )
                    conn.commit()
                    logger.info(f"[{code}] Listing date updated: {list_date}")
        
        # Valuation, Capital Flow, Margin
        if not args.skip_kline:
            backfill_valuation(db_path, code, adjusted_start, end_date, ts_pro)
            backfill_capital_flow(db_path, code, adjusted_start, end_date)
            backfill_margin_trading(db_path, code, adjusted_start, end_date, ts_pro)

        # Company profile (always run - fast, low-rate-limit risk)
        backfill_company_profile(db_path, code)

        # Fundamentals: financial indicators, dividends, shareholders
        if args.fundamentals:
            logger.info(f"[{code}] Fetching fundamentals (indicators/dividends/shareholders)...")
            backfill_financial_indicator(db_path, code)
            backfill_dividends(db_path, code)
            backfill_top10_shareholders(db_path, code)

        # Sentiment: longhu, northbound
        if args.sentiment:
            logger.info(f"[{code}] Fetching sentiment data (longhu/northbound)...")
            backfill_longhu_for_stock(db_path, code, adjusted_start, end_date)
            backfill_north_bound(db_path, code, adjusted_start, end_date)

        time.sleep(0.3)
        
    conn.close()

    # 5. Backfill Theme Mapping (Optimized Global Run)
    backfill_all_theme_mappings(db_path)

    # 6. Sentiment: Limit-up board history (全市场按日期，不按股票)
    if args.sentiment:
        logger.info("Backfilling limit-up board history (last 90 days)...")
        backfill_limit_up_by_date_range(db_path, start_date, end_date)

    logger.info("All backfill tasks completed successfully!")

if __name__ == "__main__":
    main()
