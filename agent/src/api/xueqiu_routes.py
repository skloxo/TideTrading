# -*- coding: utf-8 -*-
import sys
import json
import os
import logging
import random
import time
import requests
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Global cache for Xueqiu combos
XUEQIU_COMBOS_CACHE = {}  # tenant -> (mtime, time, details)
XUEQIU_QR_SESSIONS = {}
_xueqiu_watcher = None


class XueqiuSettingsResponse(BaseModel):
    """Xueqiu portfolio monitoring settings."""
    enabled: bool = False
    feishu_webhook: str = ""
    combos: Dict[str, str] = Field(default_factory=dict)
    xq_tokens: List[str] = Field(default_factory=list)
    watch_uids: Dict[str, str] = Field(default_factory=dict)
    token_expired: bool = False


class UpdateXueqiuSettingsRequest(BaseModel):
    """Request payload to update Xueqiu monitoring settings."""
    enabled: bool
    feishu_webhook: str = ""
    combos: Dict[str, str] = Field(default_factory=dict)
    xq_tokens: List[str] = Field(default_factory=list)
    watch_uids: Dict[str, str] = Field(default_factory=dict)


class TestXueqiuWebhookRequest(BaseModel):
    """Request payload to test Xueqiu Feishu Webhook."""
    webhook_url: str


class ConfirmQRCodeRequest(BaseModel):
    """Request payload to confirm Xueqiu QR code scan login."""
    qrcode_id: str
    token: str


def _get_xueqiu_watcher():
    global _xueqiu_watcher
    if _xueqiu_watcher is None:
        from src.platforms.xueqiu_watcher import XueqiuWatcher
        from src.platforms.event_dispatcher import MultiTenantEventDispatcher
        _xueqiu_watcher = XueqiuWatcher()
        dispatcher = MultiTenantEventDispatcher(
            config_provider=_xueqiu_watcher.config_provider,
            watcher=_xueqiu_watcher
        )
        _xueqiu_watcher.add_event_listener(dispatcher.handle_event)
    return _xueqiu_watcher


def initialize_new_combos_task(added_combos: dict, xq_tokens: list, data_dir):
    """Background task to query and populate historical rebalancing logs for newly added combos."""
    if not added_combos:
        return
    watcher = _get_xueqiu_watcher()
    if not watcher:
        return
        
    tokens = [t.strip() for t in xq_tokens if t.strip()]
    if not tokens:
        from src.platforms.xueqiu_watcher import DEFAULT_XQ_TOKENS
        tokens = DEFAULT_XQ_TOKENS
        
    for name, cid in added_combos.items():
        try:
            logger.info("Background initializing history for combo %s (%s)", name, cid)
            watcher.initialize_combo_history(cid, name, tokens, data_dir)
        except Exception as e:
            logger.error("Failed to initialize combo history in background for %s: %s", cid, e)


def initialize_new_influencers_task(added_influencers: dict, xq_tokens: list, data_dir):
    """Background task to query and save initial watchlist snapshot for newly added influencers."""
    if not added_influencers:
        return
    watcher = _get_xueqiu_watcher()
    if not watcher:
        return
    tokens = [t.strip() for t in xq_tokens if t.strip()]
    if not tokens:
        from src.platforms.xueqiu_watcher import DEFAULT_XQ_TOKENS
        tokens = DEFAULT_XQ_TOKENS
    for name, uid in added_influencers.items():
        try:
            logger.info("Background initializing watchlist snapshot for influencer %s (%s)", name, uid)
            watcher.initialize_influencer_watchlist(uid, name, tokens, data_dir)
        except Exception as e:
            logger.error("Failed to initialize watchlist snapshot in background for %s: %s", uid, e)


def register_xueqiu_routes(app: FastAPI) -> None:
    """Mount the Xueqiu monitoring routes onto ``app``."""
    host = sys.modules.get("api_server") or sys.modules.get("agent.api_server")
    if host is None:
        raise RuntimeError("register_xueqiu_routes: api_server not imported")

    require_auth = host.require_auth
    require_local_or_auth = getattr(host, "require_local_or_auth", require_auth)
    require_settings_write_auth = getattr(host, "require_settings_write_auth", require_auth)

    @app.get(
        "/settings/xueqiu",
        response_model=XueqiuSettingsResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_xueqiu_settings():
        """Return Xueqiu portfolio monitoring settings for the Web UI."""
        from src.config.paths import get_data_dir
        data_dir = get_data_dir()
        path = data_dir / "xueqiu_monitor.json"
        if not path.exists():
            return XueqiuSettingsResponse()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            
            # Check token expiration status in alert_status
            token_expired = False
            alert_path = data_dir / "xueqiu_alert_status.json"
            if alert_path.exists():
                try:
                    alert_status = json.loads(alert_path.read_text(encoding="utf-8")) or {}
                    # If any of the configured xq_tokens is in alert_status, mark as expired
                    for token in data.get("xq_tokens", []):
                        if token in alert_status:
                            token_expired = True
                            break
                except Exception:
                    pass
                    
            data["token_expired"] = token_expired
            return XueqiuSettingsResponse(**data)
        except Exception as e:
            logger.error("Failed to load Xueqiu settings: %s", e)
            return XueqiuSettingsResponse()

    @app.put(
        "/settings/xueqiu",
        response_model=XueqiuSettingsResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_xueqiu_settings(payload: UpdateXueqiuSettingsRequest, background_tasks: BackgroundTasks):
        """Persist Xueqiu portfolio monitoring settings."""
        from src.config.paths import get_data_dir
        data_dir = get_data_dir()
        path = data_dir / "xueqiu_monitor.json"
        
        # Detect new combos
        old_combos = {}
        old_watch_uids = {}
        if path.exists():
            try:
                old_data = json.loads(path.read_text(encoding="utf-8"))
                old_combos = old_data.get("combos", {})
                old_watch_uids = old_data.get("watch_uids", {})
            except Exception:
                pass
                
        # Detect combos and influencers that need history/snapshot initialization
        logs_path = data_dir / "xueqiu_rebalancing_logs.json"
        existing_combo_ids = set()
        if logs_path.exists():
            try:
                existing_logs = json.loads(logs_path.read_text(encoding="utf-8")) or []
                existing_combo_ids = {r.get("combo_id") for r in existing_logs if isinstance(r, dict) and r.get("combo_id")}
            except Exception:
                pass
                
        new_combos = payload.combos or {}
        added_combos = {}
        for name, cid in new_combos.items():
            if cid not in old_combos.values() or cid not in existing_combo_ids:
                added_combos[name] = cid

        snapshots_path = data_dir / "xueqiu_watchlist_snapshots.json"
        existing_watch_uids = set()
        if snapshots_path.exists():
            try:
                existing_snaps = json.loads(snapshots_path.read_text(encoding="utf-8")) or {}
                existing_watch_uids = set(existing_snaps.keys())
            except Exception:
                pass
                
        new_watch_uids = payload.watch_uids or {}
        added_influencers = {}
        for name, uid in new_watch_uids.items():
            if uid not in old_watch_uids.values() or uid not in existing_watch_uids:
                added_influencers[name] = uid
        
        data = {
            "enabled": payload.enabled,
            "feishu_webhook": payload.feishu_webhook,
            "combos": payload.combos,
            "xq_tokens": payload.xq_tokens,
            "watch_uids": payload.watch_uids,
        }
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            
            # Clear alert status for newly updated tokens
            alert_path = data_dir / "xueqiu_alert_status.json"
            if alert_path.exists():
                try:
                    alert_path.unlink()
                except Exception:
                    pass
        except Exception as e:
            logger.error("Failed to save Xueqiu settings: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")
            
        if added_combos:
            background_tasks.add_task(initialize_new_combos_task, added_combos, payload.xq_tokens, data_dir)
            
        if added_influencers:
            background_tasks.add_task(initialize_new_influencers_task, added_influencers, payload.xq_tokens, data_dir)
            
        return XueqiuSettingsResponse(**data)

    @app.post(
        "/settings/xueqiu/test",
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def test_xueqiu_webhook(payload: TestXueqiuWebhookRequest):
        """Send a test interactive card to verify the Feishu Webhook configuration."""
        watcher = _get_xueqiu_watcher()
        success = await watcher.test_webhook(payload.webhook_url)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to deliver test card. Please check the Webhook URL.")
        return {"status": "success"}

    @app.get(
        "/settings/xueqiu/logs",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_xueqiu_logs():
        """Return Xueqiu portfolio rebalancing logs for the Web UI."""
        from src.config.paths import get_data_dir
        path = get_data_dir() / "xueqiu_rebalancing_logs.json"
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to load Xueqiu logs: %s", e)
            return []

    @app.get(
        "/settings/xueqiu/inject",
    )
    async def inject_xueqiu_token(token: str, redirect: bool = False, key: str = None):
        """Directly inject a Xueqiu token from a bookmarklet or script."""
        from fastapi.responses import RedirectResponse
        from src.config.paths import active_tenant_var
        
        if key:
            load_keys = getattr(host, "_load_tenant_keys", None)
            if load_keys:
                keys_list = load_keys()
                for k in keys_list:
                    if k.get("key") == key:
                        active_tenant_var.set(k["tenant_id"])
                        break
                    
        token = token.strip()
        if not token:
            raise HTTPException(status_code=400, detail="Token cannot be empty")
            
        from src.config.paths import get_data_dir
        data_dir = get_data_dir()
        path = data_dir / "xueqiu_monitor.json"
        
        data = {"enabled": False, "feishu_webhook": "", "combos": {}, "xq_tokens": []}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
                
        tokens = data.get("xq_tokens", [])
        if token not in tokens:
            tokens.append(token)
            data["xq_tokens"] = tokens
            try:
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.error("Failed to inject token: %s", e)
                raise HTTPException(status_code=500, detail=f"Failed to inject token: {e}")
                
        if redirect:
            return RedirectResponse(url="/xueqiu")

        # Return JSON with CORS headers to bypass browser restrictions silently
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
        return Response(
            content=json.dumps({"status": "success"}),
            media_type="application/json",
            headers=headers
        )

    @app.get(
        "/settings/xueqiu/combos/details",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_xueqiu_combos_details():
        """Fetch current quote and holding details for all monitored portfolios of this tenant."""
        from src.config.paths import get_data_dir
        from src.platforms.xueqiu_watcher import USER_AGENT_POOL, DEFAULT_XQ_TOKENS
        
        data_dir = get_data_dir()
        config_path = data_dir / "xueqiu_monitor.json"
        
        if not config_path.exists():
            return []
            
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to read config: %s", e)
            return []
            
        combos = config.get("combos", {})
        if not combos:
            return []
            
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        mtime = config_path.stat().st_mtime if config_path.exists() else 0
        current_time = time.time()
        
        if tenant in XUEQIU_COMBOS_CACHE:
            cached_mtime, cached_time, cached_details = XUEQIU_COMBOS_CACHE[tenant]
            if cached_mtime == mtime and (current_time - cached_time < 300):
                logger.info("Serving xueqiu combo details from cache for tenant: %s", tenant)
                return cached_details
            
        xq_tokens = [t.strip() for t in config.get("xq_tokens", []) if t.strip()]
        if not xq_tokens:
            xq_tokens = DEFAULT_XQ_TOKENS
            
        if not hasattr(app.state, "xueqiu_global_details_cache"):
            app.state.xueqiu_global_details_cache = {}
        details = []

        def fetch_single(name: str, symbol: str):
            curr_time = time.time()
            # 1. Try global shared cache first (valid for 5 minutes)
            cached = app.state.xueqiu_global_details_cache.get(symbol)
            if cached:
                cached_time, cached_data = cached
                if curr_time - cached_time < 300:
                    logger.info("[XueqiuDetails] Shared Cache hit for symbol %s", symbol)
                    result = dict(cached_data)
                    result["name"] = name
                    return result

            url = f"https://xueqiu.com/cubes/show.json?symbol={symbol}"
            for retry in range(3):
                token = xq_tokens[retry % len(xq_tokens)]
                ua = random.choice(USER_AGENT_POOL)
                cookie_header = token if ("xq_a_token=" in token or ";" in token) else f"xq_a_token={token};"
                headers = {
                    "User-Agent": ua,
                    "Cookie": cookie_header,
                    "Accept": "application/json; text/plain, */*",
                    "Referer": f"https://xueqiu.com/P/{symbol}",
                }
                try:
                    r = requests.get(url, headers=headers, verify=False, timeout=8)
                    if r.status_code == 200:
                        data = r.json()
                        
                        # Extract holdings
                        view_rb = data.get("view_rebalancing")
                        holdings_list = []
                        
                        if view_rb is not None:
                            raw_holdings = view_rb.get("holdings", []) or []
                            for h in raw_holdings:
                                holdings_list.append({
                                    "stock_name": h.get("stock_name", ""),
                                    "stock_symbol": h.get("stock_symbol", ""),
                                    "weight": h.get("weight", 0.0)
                                })
                        else:
                            # Fallback to current.json endpoint for holdings
                            fallback_url = f"https://xueqiu.com/cubes/rebalancing/current.json?cube_symbol={symbol}"
                            try:
                                fallback_r = requests.get(fallback_url, headers=headers, verify=False, timeout=8)
                                if fallback_r.status_code == 200:
                                    fallback_data = fallback_r.json()
                                    last_success = fallback_data.get("last_success_rb", {})
                                    raw_holdings = last_success.get("holdings", []) or []
                                    for h in raw_holdings:
                                        holdings_list.append({
                                            "stock_name": h.get("stock_name", ""),
                                            "stock_symbol": h.get("stock_symbol", ""),
                                            "weight": h.get("weight", 0.0)
                                        })
                                else:
                                    return {
                                        "name": name,
                                        "symbol": symbol,
                                        "net_value": None,
                                        "total_gain": None,
                                        "daily_gain": None,
                                        "monthly_gain": None,
                                        "error": f"获取持仓失败 (API返回状态码: {fallback_r.status_code})"
                                    }
                            except Exception as e:
                                logger.error("Fallback error fetching current.json for %s: %s", symbol, e)
                                return {
                                    "name": name,
                                    "symbol": symbol,
                                    "net_value": None,
                                    "total_gain": None,
                                    "daily_gain": None,
                                    "monthly_gain": None,
                                    "error": f"获取持仓失败 (网络或解析异常: {e})"
                                }
                            
                        # Extract quote details with a fallback to nav_daily/all.json if they are None
                        net_val = data.get("net_value")
                        total_g = data.get("total_gain")
                        daily_g = data.get("daily_gain")
                        monthly_g = data.get("monthly_gain")
                        
                        if net_val is None or total_g is None or daily_g is None or monthly_g is None:
                            nav_url = f"https://xueqiu.com/cubes/nav_daily/all.json?cube_symbol={symbol}"
                            try:
                                nav_r = requests.get(nav_url, headers=headers, verify=False, timeout=8)
                                if nav_r.status_code == 200:
                                    nav_data = nav_r.json()
                                    portfolio_item = None
                                    for item in nav_data:
                                        if isinstance(item, dict) and item.get("symbol") == symbol:
                                            portfolio_item = item
                                            break
                                    
                                    if portfolio_item:
                                        points = portfolio_item.get("list", []) or []
                                        if len(points) >= 1:
                                            latest = points[-1]
                                            if net_val is None:
                                                net_val = latest.get("value")
                                            if total_g is None:
                                                total_g = latest.get("percent")
                                            if daily_g is None and len(points) >= 2:
                                                prev = points[-2]
                                                if latest.get("value") and prev.get("value"):
                                                    daily_g = (latest["value"] - prev["value"]) / prev["value"] * 100
                                            if monthly_g is None:
                                                latest_time = latest.get("time")
                                                if latest_time:
                                                    target_time = latest_time - 30 * 86400 * 1000
                                                    closest_point = None
                                                    min_diff = float('inf')
                                                    for p in points:
                                                        p_time = p.get("time")
                                                        if p_time:
                                                            diff = abs(p_time - target_time)
                                                            if diff < min_diff:
                                                                min_diff = diff
                                                                closest_point = p
                                                    if closest_point and closest_point.get("value") and latest.get("value"):
                                                        if closest_point != latest:
                                                            monthly_g = (latest["value"] - closest_point["value"]) / closest_point["value"] * 100
                            except Exception as nav_e:
                                logger.error("Fallback error fetching nav_daily for %s: %s", symbol, nav_e)
                                
                        res = {
                            "name": name,
                            "symbol": symbol,
                            "net_value": net_val,
                            "total_gain": total_g,
                            "daily_gain": daily_g,
                            "monthly_gain": monthly_g,
                            "holdings": holdings_list
                        }
                        app.state.xueqiu_global_details_cache[symbol] = (curr_time, res)
                        return res
                    elif r.status_code == 429:
                        continue
                except Exception as e:
                    logger.error("Error fetching detail for %s: %s", symbol, e)

            return {
                "name": name,
                "symbol": symbol,
                "error": "Failed to fetch data from Xueqiu"
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(combos), 5)) as executor:
            futures = {executor.submit(fetch_single, name, symbol): (name, symbol) for name, symbol in combos.items()}
            for future in concurrent.futures.as_completed(futures):
                try:
                    res = future.result()
                    details.append(res)
                except Exception as e:
                    name, symbol = futures[future]
                    logger.error("Failed to fetch concurrent details for %s: %s", symbol, e)
                    details.append({
                        "name": name,
                        "symbol": symbol,
                        "error": f"Failed to fetch concurrently: {e}"
                    })
                
        details.sort(key=lambda x: x.get("name", ""))
        XUEQIU_COMBOS_CACHE[tenant] = (mtime, current_time, details)
        return details

    @app.get(
        "/settings/xueqiu/qrcode",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_xueqiu_qrcode(request: Request):
        """Generate a unique QR code session for simulated Xueqiu OAuth-style login."""
        import uuid
        
        qrcode_id = str(uuid.uuid4())
        XUEQIU_QR_SESSIONS[qrcode_id] = {
            "status": "waiting",
            "token": None,
            "created_at": time.time()
        }
        
        base_url = str(request.base_url)
        if not base_url.endswith("/"):
            base_url += "/"
        auth_url = f"{base_url}xueqiu/auth?id={qrcode_id}"
        
        return {
            "qrcode_id": qrcode_id,
            "auth_url": auth_url
        }

    @app.get(
        "/settings/xueqiu/qrcode/status",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_xueqiu_qrcode_status(id: str):
        """Poll QR code status and automatically inject token upon success."""
        session = XUEQIU_QR_SESSIONS.get(id)
        if not session:
            return {"status": "expired"}
            
        status = session["status"]
        if status == "confirmed" and session.get("token"):
            token = session["token"]
            
            from src.config.paths import get_data_dir
            data_dir = get_data_dir()
            path = data_dir / "xueqiu_monitor.json"
            
            data = {"enabled": False, "feishu_webhook": "", "combos": {}, "xq_tokens": []}
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
                    
            tokens = data.get("xq_tokens", [])
            if token not in tokens:
                tokens.append(token)
                data["xq_tokens"] = tokens
                try:
                    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception as e:
                    logger.error("Failed to auto-save token from QR code: %s", e)
                    
            XUEQIU_QR_SESSIONS.pop(id, None)
            return {"status": "confirmed", "token": token}
            
        return {"status": status}

    @app.post(
        "/settings/xueqiu/qrcode/confirm",
    )
    async def confirm_xueqiu_qrcode(payload: ConfirmQRCodeRequest):
        """Simulate user scans QR code and confirms login, sending token."""
        qrcode_id = payload.qrcode_id
        token = payload.token.strip()
        if not token:
            raise HTTPException(status_code=400, detail="Token cannot be empty")
            
        session = XUEQIU_QR_SESSIONS.get(qrcode_id)
        if not session:
            raise HTTPException(status_code=404, detail="QR code session not found or expired")
            
        session["status"] = "confirmed"
        session["token"] = token
        return {"status": "success"}

    @app.post(
        "/settings/xueqiu/qrcode/scan",
    )
    async def scan_xueqiu_qrcode(id: str = Query(...)):
        """Simulate scan event (status becomes 'scanned')."""
        session = XUEQIU_QR_SESSIONS.get(id)
        if not session:
            raise HTTPException(status_code=404, detail="QR code session not found or expired")
            
        session["status"] = "scanned"
        return {"status": "success"}
