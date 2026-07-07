# -*- coding: utf-8 -*-
import json
import logging
import asyncio
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

class MultiTenantEventDispatcher:
    """AOP Event Dispatcher that listens to XueqiuWatcher data fetch events,
    switches active tenant contexts (active_tenant_var), performs delta checks (diffs),
    persists logs/snapshots to individual tenant workspaces, and triggers notifications.
    """

    def __init__(self, config_provider, watcher=None) -> None:
        self.config_provider = config_provider
        self.watcher = watcher
        self.session = requests.Session()

    def handle_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """Entrypoint called by the event emitter."""
        def log_exception(t):
            try:
                t.result()
            except Exception as e:
                import traceback
                print(f"[EventDispatcher ERROR] Task failed: {e}")
                traceback.print_exc()

        if event_name == "xueqiu:combo_fetched":
            t = asyncio.create_task(self._process_combo(event_data))
            t.add_done_callback(log_exception)
        elif event_name == "xueqiu:influencer_fetched":
            t = asyncio.create_task(self._process_influencer(event_data))
            t.add_done_callback(log_exception)

    async def _process_combo(self, event_data: Dict[str, Any]) -> None:
        combo_id = event_data["combo_id"]
        rebalancings = event_data["data"]
        monitoring_tenants = event_data["monitoring_tenants"]
        if not rebalancings:
            return

        from src.config.paths import active_tenant_var

        # 1. Initialize combo history for tenants that don't have it yet
        for tenant, name in monitoring_tenants:
            cfg = self.config_provider.get_tenant_xueqiu_config(tenant)
            if not cfg:
                continue
            data_dir = cfg["data_dir"]
            logs_path = data_dir / "xueqiu_rebalancing_logs.json"
            
            has_logs = False
            if logs_path.exists():
                try:
                    existing_logs = json.loads(logs_path.read_text(encoding="utf-8")) or []
                    has_logs = any(r.get("combo_id") == combo_id for r in existing_logs if isinstance(r, dict))
                except Exception:
                    pass

            if not has_logs:
                logger.info("[EventDispatcher] Initializing history for tenant %s combo %s (%s)", tenant, name, combo_id)
                await self._initialize_combo_history(tenant, combo_id, name, cfg)

        # 2. Distribute rebalancing results and send notifications
        for tenant, name in monitoring_tenants:
            cfg = self.config_provider.get_tenant_xueqiu_config(tenant)
            if not cfg:
                continue

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

                for item in rebalancings:
                    updated_at = item.get("updated_at")
                    stock_code = item.get("stock_symbol")
                    push_key = f"{name}_{stock_code}_{updated_at}"

                    if push_key not in pushed_records:
                        pushed_records[push_key] = True
                        
                        # Deliver notification
                        await self._notify_feishu(feishu_webhook, name, combo_id, item)

                        # Write to local logs
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
                            logger.error("[EventDispatcher] Failed to save rebalancing logs for tenant %s: %s", tenant, le)

                        await asyncio.sleep(1)

                try:
                    pushed_path.write_text(json.dumps({today: pushed_records}, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception as e:
                    logger.error("[EventDispatcher] Failed to save pushed records for tenant %s: %s", tenant, e)

            finally:
                active_tenant_var.reset(token)

    async def _process_influencer(self, event_data: Dict[str, Any]) -> None:
        uid = event_data["uid"]
        stocks = event_data["data"]
        monitoring_tenants = event_data["monitoring_tenants"]
        if not stocks and not isinstance(stocks, list):
            return

        from src.config.paths import active_tenant_var

        # 1. Initialize watchlist snapshot for tenants that don't have it yet
        for tenant, name in monitoring_tenants:
            cfg = self.config_provider.get_tenant_xueqiu_config(tenant)
            if not cfg:
                continue
            data_dir = cfg["data_dir"]
            snapshots_path = data_dir / "xueqiu_watchlist_snapshots.json"
            
            has_snapshot = False
            if snapshots_path.exists():
                try:
                    snapshots = json.loads(snapshots_path.read_text(encoding="utf-8")) or {}
                    has_snapshot = uid in snapshots
                except Exception:
                    pass

            if not has_snapshot:
                logger.info("[EventDispatcher] Initializing watchlist snapshot for tenant %s influencer %s (%s)", tenant, name, uid)
                await self._initialize_influencer_watchlist(tenant, uid, name, cfg, stocks)

        # 2. Process changes, write logs, and trigger notifications
        for tenant, name in monitoring_tenants:
            cfg = self.config_provider.get_tenant_xueqiu_config(tenant)
            if not cfg:
                continue

            token = active_tenant_var.set(tenant)
            try:
                data_dir = cfg["data_dir"]
                feishu_webhook = cfg["feishu_webhook"]
                snapshots_path = data_dir / "xueqiu_watchlist_snapshots.json"
                
                snapshots = {}
                if snapshots_path.exists():
                    try:
                        snapshots = json.loads(snapshots_path.read_text(encoding="utf-8")) or {}
                    except Exception:
                        pass

                current_snapshot = {s["symbol"]: s["name"] for s in stocks if isinstance(s, dict) and s.get("symbol")}

                if uid not in snapshots:
                    snapshots[uid] = current_snapshot
                    try:
                        snapshots_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass
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
                            logger.error("[EventDispatcher] Failed to save watchlist rebalancing logs for tenant %s: %s", tenant, le)

                snapshots[uid] = current_snapshot
                try:
                    snapshots_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception as e:
                    logger.error("[EventDispatcher] Failed to save watchlist snapshots for tenant %s: %s", tenant, e)

            finally:
                active_tenant_var.reset(token)

    async def _initialize_combo_history(self, tenant: str, combo_id: str, combo_name: str, cfg: Dict[str, Any]) -> None:
        if not self.watcher:
            return
        tokens = cfg["xq_tokens"]
        if not tokens:
            from src.platforms.xueqiu_watcher import DEFAULT_XQ_TOKENS
            tokens = DEFAULT_XQ_TOKENS
        
        from src.config.paths import active_tenant_var
        token = active_tenant_var.set(tenant)
        try:
            await asyncio.to_thread(
                self.watcher.initialize_combo_history, combo_id, combo_name, tokens, cfg["data_dir"]
            )
        finally:
            active_tenant_var.reset(token)

    async def _initialize_influencer_watchlist(self, tenant: str, uid: str, name: str, cfg: Dict[str, Any], current_stocks: List[Dict[str, Any]]) -> None:
        from src.config.paths import active_tenant_var
        token = active_tenant_var.set(tenant)
        try:
            data_dir = cfg["data_dir"]
            snapshots_path = data_dir / "xueqiu_watchlist_snapshots.json"
            current_snapshot = {s["symbol"]: s["name"] for s in current_stocks if isinstance(s, dict) and s.get("symbol")}
            snapshots = {}
            if snapshots_path.exists():
                try:
                    snapshots = json.loads(snapshots_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    pass
            snapshots[uid] = current_snapshot
            snapshots_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding="utf-8")
        finally:
            active_tenant_var.reset(token)

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

        try:
            await asyncio.to_thread(
                requests.post,
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=10,
                verify=False
            )
        except Exception as e:
            logger.error("[EventDispatcher] Failed to send Feishu notification: %s", e)

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
            logger.error("[EventDispatcher] Failed to send influencer change notification: %s", e)
