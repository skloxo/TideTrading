# -*- coding: utf-8 -*-
import asyncio
import random
import time
import json
import logging
import datetime
import urllib3
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

# Disable requests ssl warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"

USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.15",
    "Mozilla/5.0 (Linux; Android 14; SM-G9980) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi K70) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; vivo X100) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 YaBrowser/24.7.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Edg/128.0.0.0",
    "Mozilla/5.0 (Linux; Android 12; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36"
]

# System fallback tokens
DEFAULT_XQ_TOKENS = [
    "aa7bc8450a0b0f41073434348f321cdb08c7790d",
    "b9696defb7a32f1ad38bfaab4555508ca2f5ed33"
]

class XueqiuWatcher:
    """Background watcher for Xueqiu portfolio rebalancing events."""

    def __init__(self, check_interval_seconds: int = 300) -> None:
        self.check_interval_seconds = check_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stopping = False
        self.session = requests.Session()

    def start(self) -> None:
        """Start the background watcher loop."""
        if self._task is not None and not self._task.done():
            return
        self._stopping = False
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run_loop(), name="xueqiu-watcher")
        logger.info("[XueqiuWatcher] Background watcher started.")

    async def stop(self) -> None:
        """Stop the background watcher loop."""
        if self._task is None:
            return
        self._stopping = True
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("[XueqiuWatcher] Background watcher stopped.")

    async def _run_loop(self) -> None:
        """Main loop executing periodically."""
        while not self._stopping:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("[XueqiuWatcher] Error in watcher tick: %s", e)
            
            if self._stopping:
                break
            await asyncio.sleep(self.check_interval_seconds)

    async def tick(self) -> None:
        """Perform a single check across all active tenants.
        
        This check uses a Shared Cache Pool and de-duplicates queries across all active tenants,
        while performing cooperative Cookie rotation to distribute network request load.
        """
        from src.config.paths import active_tenant_var, get_data_dir
        
        # 1. Load active tenants and configurations
        tenants = ["default"]
        try:
            from api_server import _load_tenant_keys
            for k in _load_tenant_keys():
                if k.get("is_active", True):
                    tenants.append(k["tenant_id"])
        except Exception as e:
            logger.error("[XueqiuWatcher] Failed to load tenants: %s", e)

        tenant_configs = {}
        for tenant in tenants:
            token = active_tenant_var.set(tenant)
            try:
                data_dir = get_data_dir()
                config_path = data_dir / "xueqiu_monitor.json"
                if config_path.exists():
                    try:
                        config = json.loads(config_path.read_text(encoding="utf-8"))
                        if config.get("enabled", False):
                            tenant_configs[tenant] = {
                                "combos": config.get("combos", {}) or {},
                                "watch_uids": config.get("watch_uids", {}) or {},
                                "xq_tokens": [t.strip() for t in config.get("xq_tokens", []) if t.strip()],
                                "feishu_webhook": config.get("feishu_webhook", "").strip(),
                                "data_dir": data_dir
                            }
                    except Exception as ce:
                        logger.error("[XueqiuWatcher] Failed to parse config for tenant %s: %s", tenant, ce)
            except Exception as e:
                logger.error("[XueqiuWatcher] Error loading config context for tenant %s: %s", tenant, e)
            finally:
                active_tenant_var.reset(token)

        if not tenant_configs:
            logger.info("[XueqiuWatcher] No active tenants have Xueqiu monitoring enabled.")
            return

        # 2. Build unique mappings (combo/uid -> tenants)
        combo_to_tenants = {}
        uid_to_tenants = {}

        for tenant, cfg in tenant_configs.items():
            for name, combo_id in cfg["combos"].items():
                combo_id = combo_id.strip()
                if not combo_id:
                    continue
                if combo_id not in combo_to_tenants:
                    combo_to_tenants[combo_id] = []
                combo_to_tenants[combo_id].append((tenant, name))

            for name, uid in cfg["watch_uids"].items():
                uid = uid.strip()
                if not uid:
                    continue
                if uid not in uid_to_tenants:
                    uid_to_tenants[uid] = []
                uid_to_tenants[uid].append((tenant, name))

        # 3. Gather cooperative token lists and rotation indices
        if not hasattr(self, "_combo_rotation_indices"):
            self._combo_rotation_indices = {}
        if not hasattr(self, "_uid_rotation_indices"):
            self._uid_rotation_indices = {}

        # 4. Perform single-queries with cooperative cookie rotation
        shared_combo_results = {}
        for combo_id, monitoring_tenants in combo_to_tenants.items():
            if self._stopping:
                break

            # Gather cookies
            cookies = []
            for tenant, _ in monitoring_tenants:
                cookies.extend(tenant_configs[tenant]["xq_tokens"])
            seen = set()
            unique_cookies = [x for x in cookies if not (x in seen or seen.add(x))]
            if not unique_cookies:
                unique_cookies = DEFAULT_XQ_TOKENS

            # Rotate cookie choice
            idx = self._combo_rotation_indices.get(combo_id, 0)
            selected_token = unique_cookies[idx % len(unique_cookies)]
            self._combo_rotation_indices[combo_id] = (idx + 1) % len(unique_cookies)

            # Move selected token to front
            rotated_cookies = [selected_token] + [t for t in unique_cookies if t != selected_token]

            # Auto-prepopulate logs for any tenant that doesn't have logs yet for this combo
            for tenant, name in monitoring_tenants:
                t_token = active_tenant_var.set(tenant)
                try:
                    t_data_dir = tenant_configs[tenant]["data_dir"]
                    logs_path = t_data_dir / "xueqiu_rebalancing_logs.json"
                    has_logs = False
                    if logs_path.exists():
                        try:
                            existing_logs = json.loads(logs_path.read_text(encoding="utf-8")) or []
                            has_logs = any(r.get("combo_id") == combo_id for r in existing_logs if isinstance(r, dict))
                        except Exception:
                            pass
                    if not has_logs:
                        logger.info("[XueqiuWatcher] Auto-prepopulating history for tenant %s combo %s (%s)", tenant, name, combo_id)
                        await asyncio.to_thread(
                            self.initialize_combo_history, combo_id, name, rotated_cookies, t_data_dir
                        )
                except Exception as e:
                    logger.error("[XueqiuWatcher] Failed to auto-prepopulate history for %s under tenant %s: %s", combo_id, tenant, e)
                finally:
                    active_tenant_var.reset(t_token)

            # Determine alert route (which tenant context and webhook to use for expired token notifications)
            alert_webhook = None
            alert_data_dir = None
            for tenant, _ in monitoring_tenants:
                if selected_token in tenant_configs[tenant]["xq_tokens"]:
                    alert_webhook = tenant_configs[tenant]["feishu_webhook"]
                    alert_data_dir = tenant_configs[tenant]["data_dir"]
                    break
            if not alert_webhook:
                first_tenant = monitoring_tenants[0][0]
                alert_webhook = tenant_configs[first_tenant]["feishu_webhook"]
                alert_data_dir = tenant_configs[first_tenant]["data_dir"]

            # Query online
            rebalancings = await asyncio.to_thread(
                self._query_combo, combo_id, rotated_cookies, alert_webhook, alert_data_dir
            )
            shared_combo_results[combo_id] = rebalancings

        shared_uid_results = {}
        for uid, monitoring_tenants in uid_to_tenants.items():
            if self._stopping:
                break

            # Gather cookies
            cookies = []
            for tenant, _ in monitoring_tenants:
                cookies.extend(tenant_configs[tenant]["xq_tokens"])
            seen = set()
            unique_cookies = [x for x in cookies if not (x in seen or seen.add(x))]
            if not unique_cookies:
                unique_cookies = DEFAULT_XQ_TOKENS

            idx = self._uid_rotation_indices.get(uid, 0)
            selected_token = unique_cookies[idx % len(unique_cookies)]
            self._uid_rotation_indices[uid] = (idx + 1) % len(unique_cookies)

            rotated_cookies = [selected_token] + [t for t in unique_cookies if t != selected_token]

            # Auto-initialize watchlist snapshot for any tenant that doesn't have it yet
            for tenant, name in monitoring_tenants:
                t_token = active_tenant_var.set(tenant)
                try:
                    t_data_dir = tenant_configs[tenant]["data_dir"]
                    snapshots_path = t_data_dir / "xueqiu_watchlist_snapshots.json"
                    has_snapshot = False
                    if snapshots_path.exists():
                        try:
                            snapshots = json.loads(snapshots_path.read_text(encoding="utf-8")) or {}
                            has_snapshot = uid in snapshots
                        except Exception:
                            pass
                    if not has_snapshot:
                        logger.info("[XueqiuWatcher] Initializing watchlist snapshot for tenant %s influencer %s (%s)", tenant, name, uid)
                        await asyncio.to_thread(
                            self.initialize_influencer_watchlist, uid, name, rotated_cookies, t_data_dir
                        )
                except Exception as e:
                    logger.error("[XueqiuWatcher] Failed to initialize watchlist snapshot for %s under tenant %s: %s", uid, tenant, e)
                finally:
                    active_tenant_var.reset(t_token)

            # Query online
            stocks = await asyncio.to_thread(
                self._query_influencer_watchlist, uid, rotated_cookies
            )
            shared_uid_results[uid] = stocks

        # 5. Distribute results privately to each tenant
        for tenant, cfg in tenant_configs.items():
            if self._stopping:
                break

            token = active_tenant_var.set(tenant)
            try:
                data_dir = cfg["data_dir"]
                feishu_webhook = cfg["feishu_webhook"]
                pushed_path = data_dir / "xueqiu_pushed_records.json"
                pushed_records = {}
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                if pushed_path.exists():
                    try:
                        pushed_data = json.loads(pushed_path.read_text(encoding="utf-8"))
                        if today in pushed_data:
                            pushed_records = pushed_data[today]
                    except Exception:
                        pass

                # Process combos
                for name, combo_id in cfg["combos"].items():
                    rebalancings = shared_combo_results.get(combo_id)
                    if not rebalancings:
                        continue

                    for item in rebalancings:
                        updated_at = item.get("updated_at")
                        stock_code = item.get("stock_symbol")
                        push_key = f"{name}_{stock_code}_{updated_at}"

                        if push_key not in pushed_records:
                            pushed_records[push_key] = True
                            await self._notify_feishu(feishu_webhook, name, combo_id, item)

                            # Save log item locally for Web UI
                            try:
                                logs_path = data_dir / "xueqiu_rebalancing_logs.json"
                                logs = []
                                if logs_path.exists():
                                    try:
                                        logs = json.loads(logs_path.read_text(encoding="utf-8"))
                                    except Exception:
                                        pass
                                log_item = {
                                    "combo_name": name,
                                    "combo_id": combo_id,
                                    **item
                                }
                                logs.insert(0, log_item)
                                logs = logs[:500]
                                logs_path.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")
                            except Exception as le:
                                logger.error("[XueqiuWatcher] Failed to save rebalancing logs for tenant %s: %s", tenant, le)

                            await asyncio.sleep(1)

                try:
                    pushed_path.write_text(json.dumps({today: pushed_records}, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception as e:
                    logger.error("[XueqiuWatcher] Failed to save pushed records for tenant %s: %s", tenant, e)

                # Process influencers (watch_uids)
                if cfg["watch_uids"]:
                    snapshots_path = data_dir / "xueqiu_watchlist_snapshots.json"
                    snapshots = {}
                    if snapshots_path.exists():
                        try:
                            snapshots = json.loads(snapshots_path.read_text(encoding="utf-8")) or {}
                        except Exception:
                            pass

                    for name, uid in cfg["watch_uids"].items():
                        stocks = shared_uid_results.get(uid)
                        if not stocks and not isinstance(stocks, list):
                            continue

                        current_snapshot = {s["symbol"]: s["name"] for s in stocks if isinstance(s, dict) and s.get("symbol")}

                        if uid not in snapshots:
                            snapshots[uid] = current_snapshot
                            continue

                        old_snapshot = snapshots[uid] or {}

                        added = [s for s in stocks if isinstance(s, dict) and s.get("symbol") and s["symbol"] not in old_snapshot]
                        removed = [{"symbol": sym, "name": name_val} for sym, name_val in old_snapshot.items() if sym not in current_snapshot]

                        has_changes = False
                        if added or removed:
                            logs_path = data_dir / "xueqiu_rebalancing_logs.json"
                            logs = []
                            if logs_path.exists():
                                try:
                                    logs = json.loads(logs_path.read_text(encoding="utf-8")) or []
                                except Exception:
                                    pass

                            current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            for s in added:
                                operation = "新增自选"
                                await self._notify_influencer_change(feishu_webhook, name, uid, operation, s["name"], s["symbol"])
                                log_item = {
                                    "combo_name": f"{name}的自选股",
                                    "combo_id": uid,
                                    "stock_symbol": s["symbol"],
                                    "stock_name": s["name"],
                                    "operation": operation,
                                    "trade_time": current_time_str,
                                    "price": "--",
                                    "current_weight": 0.0,
                                    "prev_weight": 0.0,
                                    "position_change": 0.0
                                }
                                logs.insert(0, log_item)
                                has_changes = True

                            for s in removed:
                                operation = "移出自选"
                                await self._notify_influencer_change(feishu_webhook, name, uid, operation, s["name"], s["symbol"])
                                log_item = {
                                    "combo_name": f"{name}的自选股",
                                    "combo_id": uid,
                                    "stock_symbol": s["symbol"],
                                    "stock_name": s["name"],
                                    "operation": operation,
                                    "trade_time": current_time_str,
                                    "price": "--",
                                    "current_weight": 0.0,
                                    "prev_weight": 0.0,
                                    "position_change": 0.0
                                }
                                logs.insert(0, log_item)
                                has_changes = True

                            if has_changes:
                                try:
                                    logs = logs[:500]
                                    logs_path.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")
                                except Exception as le:
                                    logger.error("[XueqiuWatcher] Failed to save watchlist rebalancing logs for tenant %s: %s", tenant, le)

                        snapshots[uid] = current_snapshot

                    try:
                        snapshots_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding="utf-8")
                    except Exception as e:
                        logger.error("[XueqiuWatcher] Failed to save watchlist snapshots for tenant %s: %s", tenant, e)

            except Exception as te:
                logger.error("[XueqiuWatcher] Error distributing results for tenant %s: %s", tenant, te)
            finally:
                active_tenant_var.reset(token)

    def _get_headers(self, token: str, combo_id: str = None) -> Dict[str, str]:
        """Generate random request headers with token cookie."""
        ua = random.choice(USER_AGENT_POOL)
        cookie_header = token if ("xq_a_token=" in token or ";" in token) else f"xq_a_token={token};"
        referer = f"https://xueqiu.com/P/{combo_id}" if combo_id else "https://xueqiu.com/"
        return {
            "User-Agent": ua,
            "Cookie": cookie_header,
            "Accept": "application/json; text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": referer,
            "Origin": "https://xueqiu.com"
        }

    def _query_combo(self, combo_id: str, tokens: List[str], feishu_webhook: str = None, data_dir = None) -> List[Dict[str, Any]]:
        """Query combination rebalancing history from Xueqiu."""
        timestamp = int(time.time() * 1000)
        url = f"https://xueqiu.com/cubes/rebalancing/history.json?cube_symbol={combo_id}&count=20&page=1&_={timestamp}"
        
        max_retries = 3
        for retry in range(max_retries):
            if self._stopping:
                return []
            
            token = tokens[retry % len(tokens)]
            headers = self._get_headers(token, combo_id)
            
            try:
                response = self.session.get(url, headers=headers, timeout=15, verify=False)
                
                if response.status_code == 429:
                    logger.warning("[XueqiuWatcher] 429 rate limit hit for combo %s. Retrying after delay...", combo_id)
                    time.sleep(5 * (retry + 1))
                    continue
                elif response.status_code in (400, 401, 403):
                    logger.warning("[XueqiuWatcher] Token expired or invalid (HTTP %d): %s****", response.status_code, token[:10])
                    if feishu_webhook and data_dir:
                        self._send_expiration_alert(token, data_dir, feishu_webhook)
                    continue
                elif response.status_code != 200:
                    logger.warning("[XueqiuWatcher] HTTP %d when querying combo %s", response.status_code, combo_id)
                    continue
                
                res_json = response.json()
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                valid_statuses = {"success", "pending", "待处理", "成功"}
                
                raw_list = res_json.get("list", [])
                matching_records = []
                
                for rebal in raw_list:
                    if rebal.get("status") not in valid_statuses:
                        continue
                    
                    # Convert updated_at to format time
                    dt = datetime.datetime.fromtimestamp(rebal["updated_at"] / 1000.0)
                    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    
                    if dt_str.startswith(today):
                        # Extract stock adjustments
                        histories = rebal.get("rebalancing_histories", [])
                        for hist in histories:
                            current_weight = float(hist.get("weight", 0) or 0)
                            prev_weight = float(hist.get("prev_weight_adjusted", 0) or 0)
                            
                            if current_weight == 0 and prev_weight > 0:
                                operation = "卖出"
                            elif prev_weight == 0 and current_weight > 0:
                                operation = "买入"
                            elif current_weight > prev_weight:
                                operation = "加仓"
                            elif current_weight < prev_weight and current_weight > 0:
                                operation = "减仓"
                            else:
                                operation = "调仓"
                                
                            position_change = round(current_weight - prev_weight, 2)
                            
                            matching_records.append({
                                "updated_at": rebal["updated_at"],
                                "trade_time": dt_str,
                                "operation": operation,
                                "stock_symbol": hist["stock_symbol"],
                                "stock_name": hist["stock_name"],
                                "price": hist.get("price", "") or "待成交",
                                "current_weight": current_weight,
                                "prev_weight": prev_weight,
                                "position_change": position_change
                            })
                            
                return matching_records
                
            except Exception as e:
                logger.error("[XueqiuWatcher] Request error querying combo %s (attempt %d/%d): %s", combo_id, retry+1, max_retries, e)
                time.sleep(2 * (retry + 1))
                
        return []

    def initialize_combo_history(self, combo_id: str, combo_name: str, tokens: List[str], data_dir) -> List[Dict[str, Any]]:
        """Fetch the last 5 pages of rebalancings of a combo (historical) and merge them into logs."""
        raw_list = []
        max_pages = 5
        
        for page in range(1, max_pages + 1):
            timestamp = int(time.time() * 1000)
            url = f"https://xueqiu.com/cubes/rebalancing/history.json?cube_symbol={combo_id}&count=20&page={page}&_={timestamp}"
            
            page_fetched = False
            max_retries = 3
            for retry in range(max_retries):
                token = tokens[retry % len(tokens)]
                headers = self._get_headers(token, combo_id)
                try:
                    response = self.session.get(url, headers=headers, timeout=15, verify=False)
                    if response.status_code == 200:
                        res_json = response.json()
                        page_list = res_json.get("list", []) or []
                        raw_list.extend(page_list)
                        page_fetched = True
                        
                        max_page_val = res_json.get("max_page", 1)
                        if page >= max_page_val or not page_list:
                            break
                        break
                    elif response.status_code == 429:
                        time.sleep(2 * (retry + 1))
                except Exception as e:
                    logger.error("[XueqiuWatcher] Failed to fetch history page %d (attempt %d): %s", page, retry+1, e)
                    time.sleep(1)
                    
            if not page_fetched or not raw_list:
                break
                
            time.sleep(0.5)
            
        if not raw_list:
            return []
            
        valid_statuses = {"success", "pending", "待处理", "成功"}
        matching_records = []
        for rebal in raw_list:
            if rebal.get("status") not in valid_statuses:
                continue
            
            # Convert updated_at to format time
            dt = datetime.datetime.fromtimestamp(rebal["updated_at"] / 1000.0)
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            
            histories = rebal.get("rebalancing_histories", []) or []
            for hist in histories:
                current_weight = float(hist.get("weight", 0) or 0)
                prev_weight = float(hist.get("prev_weight_adjusted", 0) or 0)
                
                if current_weight == 0 and prev_weight > 0:
                    operation = "卖出"
                elif prev_weight == 0 and current_weight > 0:
                    operation = "买入"
                elif current_weight > prev_weight:
                    operation = "加仓"
                elif current_weight < prev_weight and current_weight > 0:
                    operation = "减仓"
                else:
                    operation = "调仓"
                    
                position_change = round(current_weight - prev_weight, 2)
                matching_records.append({
                    "combo_name": combo_name,
                    "combo_id": combo_id,
                    "updated_at": rebal["updated_at"],
                    "trade_time": dt_str,
                    "operation": operation,
                    "stock_symbol": hist["stock_symbol"],
                    "stock_name": hist["stock_name"],
                    "price": hist.get("price", "") or "待成交",
                    "current_weight": current_weight,
                    "prev_weight": prev_weight,
                    "position_change": position_change
                })
                
        if matching_records:
            try:
                logs_path = data_dir / "xueqiu_rebalancing_logs.json"
                existing_logs = []
                if logs_path.exists():
                    try:
                        existing_logs = json.loads(logs_path.read_text(encoding="utf-8")) or []
                    except Exception:
                        pass
                
                # Deduplicate records by checking combo_id, stock_symbol and updated_at
                existing_keys = {
                    f"{r.get('combo_id')}_{r.get('stock_symbol')}_{r.get('updated_at')}"
                    for r in existing_logs if isinstance(r, dict)
                }
                
                new_added = []
                for rec in matching_records:
                    key = f"{rec['combo_id']}_{rec['stock_symbol']}_{rec['updated_at']}"
                    if key not in existing_keys:
                        new_added.append(rec)
                        existing_keys.add(key)
                        
                if new_added:
                    # Sort new records chronologically so they are inserted in order
                    new_added.sort(key=lambda x: x["updated_at"])
                    # Insert at the beginning of the logs list
                    for rec in new_added:
                        existing_logs.insert(0, rec)
                    # Limit log count
                    existing_logs = existing_logs[:500]
                    logs_path.write_text(json.dumps(existing_logs, indent=2, ensure_ascii=False), encoding="utf-8")
                    logger.info("[XueqiuWatcher] Initialized combo %s with %d historical records", combo_id, len(new_added))
            except Exception as le:
                logger.error("[XueqiuWatcher] Failed to merge initialized history: %s", le)
                
        return matching_records

    def _send_expiration_alert(self, token: str, data_dir, feishu_webhook: str) -> None:
        """Alert the user when a Xueqiu token is detected as expired/invalid (synchronous)."""
        if not feishu_webhook:
            return
            
        alert_path = data_dir / "xueqiu_alert_status.json"
        now = time.time()
        
        # Debounce alerts to once every 12 hours per token
        alert_status = {}
        if alert_path.exists():
            try:
                alert_status = json.loads(alert_path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass
                
        last_alert_time = alert_status.get(token, 0)
        if now - last_alert_time < 12 * 3600:
            return
            
        try:
            headers = {"Content-Type": "application/json"}
            card = {
                "msg_type": "interactive",
                "card": {
                    "config": {"wide_screen_mode": True},
                    "header": {
                        "template": "orange",
                        "title": {"tag": "plain_text", "content": "⚠️ 雪球监控登录凭证过期告警"}
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": (
                                    f"**告警原因**：系统检测到您的雪球 `xq_a_token` 凭证已失效。\n"
                                    f"**影响范围**：系统将暂时无法自动抓取调仓和自选股异动通知。\n"
                                    f"**受损凭证片段**：`{token[:8]}***{token[-8:] if len(token) > 8 else ''}`\n\n"
                                    f"**如何恢复**：\n"
                                    f"1. 请在电脑浏览器登录 [雪球网](https://xueqiu.com/)。\n"
                                    f"2. 按 F12 打开开发者工具 -> Application(应用) -> Cookies -> 双击复制 `xq_a_token` 的值。\n"
                                    f"3. 访问您的系统面板并在主页配置中重新添加该 Token。"
                                )
                            }
                        }
                    ]
                }
            }
            requests.post(feishu_webhook, json=card, headers=headers, timeout=10, verify=False)
            
            # Save alert timestamp
            alert_status[token] = now
            alert_path.write_text(json.dumps(alert_status, indent=2), encoding="utf-8")
            logger.warning("[XueqiuWatcher] Expired token alert sent to Feishu webhook successfully.")
        except Exception as e:
            logger.error("[XueqiuWatcher] Failed to send expired token alert to Feishu: %s", e)
    def _query_influencer_watchlist(self, uid: str, tokens: List[str]) -> List[Dict[str, Any]]:
        """Query target influencer's watchlist from Xueqiu."""
        timestamp = int(time.time() * 1000)
        url = f"https://stock.xueqiu.com/v5/stock/portfolio/stock/list.json?uid={uid}&category=1&size=200&pid=-120"
        
        max_retries = 3
        for retry in range(max_retries):
            if self._stopping:
                return []
            
            token = tokens[retry % len(tokens)]
            headers = self._get_headers(token)
            
            try:
                response = self.session.get(url, headers=headers, timeout=15, verify=False)
                if response.status_code == 200:
                    data = response.json().get("data", {}) or {}
                    return data.get("stocks", []) or []
                elif response.status_code in (400, 401, 403):
                    logger.warning("[XueqiuWatcher] Expiration/Forbidden in watchlist query (HTTP %d)", response.status_code)
                    continue
                elif response.status_code == 429:
                    time.sleep(2 * (retry + 1))
            except Exception as e:
                logger.error("[XueqiuWatcher] Watchlist request error for user %s: %s", uid, e)
                time.sleep(1)
                
        return []

    async def _notify_influencer_change(self, webhook_url: str, influencer_name: str, uid: str, operation: str, stock_name: str, stock_symbol: str) -> None:
        """Deliver influencer watchlist change notification to Feishu Webhook."""
        if not webhook_url:
            return
            
        color = "green" if "新增" in operation else "red"
        title = f"📢 大 V 自选股异动：{influencer_name} {operation}"
        
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": color,
                    "title": {"tag": "plain_text", "content": title}
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**大 V 名称**：{influencer_name} ({uid})\n"
                                f"**异动标的**：{stock_name} ({stock_symbol})\n"
                                f"**异动操作**：【{operation}】\n"
                                f"**监控发现时间**：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        }
                    }
                ]
            }
        }
        
        try:
            headers = {"Content-Type": "application/json"}
            await asyncio.to_thread(
                requests.post, webhook_url, json=card, headers=headers, timeout=10, verify=False
            )
        except Exception as e:
            logger.error("[XueqiuWatcher] Failed to send influencer change notification: %s", e)

    def initialize_influencer_watchlist(self, uid: str, name: str, tokens: List[str], data_dir) -> None:
        """Fetch the initial watchlist of an influencer and save it to snapshots to prevent false change alerts."""
        stocks = self._query_influencer_watchlist(uid, tokens)
        if not stocks and not isinstance(stocks, list):
            return
            
        current_snapshot = {s["symbol"]: s["name"] for s in stocks if isinstance(s, dict) and s.get("symbol")}
        
        try:
            snapshots_path = data_dir / "xueqiu_watchlist_snapshots.json"
            snapshots = {}
            if snapshots_path.exists():
                try:
                    snapshots = json.loads(snapshots_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    pass
            snapshots[uid] = current_snapshot
            snapshots_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("[XueqiuWatcher] Initialized watchlist snapshot for influencer %s (%s) with %d stocks", name, uid, len(current_snapshot))
        except Exception as e:
            logger.error("[XueqiuWatcher] Failed to initialize watchlist snapshot for %s: %s", uid, e)


    async def _notify_feishu(self, webhook_url: str, combo_name: str, combo_id: str, item: Dict[str, Any]) -> None:
        """Deliver a premium interactive card message to a Feishu Webhook."""
        if not webhook_url:
            return

        operation = item["operation"]
        stock_name = item["stock_name"]
        stock_code = item["stock_symbol"]
        current_weight = item["current_weight"]
        prev_weight = item["prev_weight"]
        position_change = item["position_change"]
        price = item["price"]
        trade_time = item["trade_time"]

        # Color code header template
        if operation in {"买入", "加仓"}:
            template_color = "green"
        elif operation in {"卖出", "减仓"}:
            template_color = "red"
        else:
            template_color = "orange"

        card_json = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔔 雪球组合调仓提醒 - {combo_name}"
                },
                "template": template_color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**组合名称：** [{combo_name}](https://xueqiu.com/P/{combo_id})\n"
                            f"**操作方向：** **{operation}**\n"
                            f"**标的信息：** [{stock_name}({stock_code})](https://xueqiu.com/S/{stock_code})\n"
                            f"**仓位变化：** **{prev_weight}%** ➡️ **{current_weight}%** (变化: {position_change:+.2f}%)\n"
                            f"**成交价格：** {price}\n"
                            f"**调仓时间：** {trade_time}"
                        )
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "🔍 查看组合"
                            },
                            "type": "primary",
                            "url": f"https://xueqiu.com/P/{combo_id}"
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "📈 查看个股"
                            },
                            "type": "default",
                            "url": f"https://xueqiu.com/S/{stock_code}"
                        }
                    ]
                }
            ]
        }

        payload = {
            "msg_type": "interactive",
            "card": card_json
        }

        # Run webhook request in thread to avoid blocking loop
        await asyncio.to_thread(self._send_webhook, webhook_url, payload)

    def _send_webhook(self, url: str, payload: Dict[str, Any]) -> None:
        """Send POST request to Feishu Webhook."""
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=10
            )
            if response.status_code != 200:
                logger.error("[XueqiuWatcher] Feishu Webhook returned HTTP %d: %s", response.status_code, response.text)
        except Exception as e:
            logger.error("[XueqiuWatcher] Failed to send notification to Feishu Webhook: %s", e)

    async def test_webhook(self, webhook_url: str) -> bool:
        """Send a test interactive card to verify the webhook configuration."""
        card_json = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🔔 雪球组合监控 - Webhook 测试成功"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "**您的飞书群聊机器人 Webhook 配置成功！**\n\n"
                            f"**测试标的：** [臻镭科技(SH688270)](https://xueqiu.com/S/SH688270)\n"
                            f"**测试组合：** [演示组合](https://xueqiu.com/P/ZH123456)\n"
                            f"**测试时间：** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            "当有真实的调仓事件触发时，系统会第一时间以本样式将调仓详情推送至您的群聊。"
                        )
                    }
                }
            ]
        }

        payload = {
            "msg_type": "interactive",
            "card": card_json
        }

        try:
            res = await asyncio.to_thread(
                requests.post,
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return res.status_code == 200
        except Exception as e:
            logger.error("[XueqiuWatcher] Webhook test failed: %s", e)
            return False
