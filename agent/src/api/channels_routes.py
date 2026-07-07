import os
import json
import hmac
import hashlib
import secrets
import time
import logging
import traceback
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, Query
from pydantic import BaseModel, Field
from src.config.paths import _get_active_runtime_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models (defined locally -- NO shared modules, per maintainer rule)
# ---------------------------------------------------------------------------

class ChannelPairingCommandRequest(BaseModel):
    """Pairing command payload for IM channel sender pairing."""

    channel: str
    command: str


class FeishuChannelResponse(BaseModel):
    """Detailed information for a single Feishu channel."""
    id: str
    name: str
    app_id: str
    app_secret_configured: bool
    allowed_users: str
    allow_all_users: bool
    enabled: bool


class CreateFeishuChannelRequest(BaseModel):
    """Payload to create a new Feishu channel."""
    name: str
    app_id: str
    app_secret: str
    allowed_users: Optional[str] = ""
    allow_all_users: bool = False
    enabled: bool = True


class UpdateFeishuChannelRequest(BaseModel):
    """Payload to update an existing Feishu channel."""
    name: str
    app_id: str
    app_secret: Optional[str] = None
    allowed_users: Optional[str] = ""
    allow_all_users: bool = False
    enabled: bool = True


class WechatChannelResponse(BaseModel):
    """Detailed information for a single WeChat channel."""
    id: str
    name: str
    mode: str = "ilink"
    enabled: bool
    ilink_bot_token: Optional[str] = ""
    ilink_base_url: Optional[str] = ""
    ilink_bot_id: Optional[str] = ""
    ilink_user_id: Optional[str] = ""


class CreateWechatChannelRequest(BaseModel):
    """Payload to create a new WeChat channel."""
    name: str
    mode: str = "ilink"
    enabled: bool = True
    ilink_bot_token: Optional[str] = ""
    ilink_base_url: Optional[str] = ""
    ilink_bot_id: Optional[str] = ""
    ilink_user_id: Optional[str] = ""


class UpdateWechatChannelRequest(BaseModel):
    """Payload to update an existing WeChat channel."""
    name: str
    mode: str = "ilink"
    enabled: bool = True
    ilink_bot_token: Optional[str] = None
    ilink_base_url: Optional[str] = None
    ilink_bot_id: Optional[str] = None
    ilink_user_id: Optional[str] = None


FEISHU_SECRET_PLACEHOLDERS: set[str] = {"", "your-feishu-app-secret"}
FEISHU_CHANNELS_JSON = Path(__file__).resolve().parents[3] / "sessions" / "feishu_channels.json"
WECHAT_CHANNELS_JSON = _get_active_runtime_dir() / "wechat_channels.json"

def _get_feishu_channels_json_path() -> Path:
    from src.config.paths import active_tenant_var
    tenant = active_tenant_var.get()
    if tenant == "default":
        return Path(__file__).resolve().parents[3] / "sessions" / "feishu_channels.json"
    return _get_active_runtime_dir() / "feishu_channels.json"

def _load_feishu_channels() -> list[dict[str, Any]]:
    """Load Feishu channels from the persistent JSON file. Handles legacy migration."""
    channels = []
    path = _get_feishu_channels_json_path()
    if path.exists():
        try:
            channels = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to read %s: %s", path, e)
    return channels

def _save_feishu_channels(channels: list[dict[str, Any]]) -> None:
    """Save Feishu channels to the persistent JSON file."""
    path = _get_feishu_channels_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(channels, indent=2, ensure_ascii=False), encoding="utf-8")

def _get_wechat_channels_json_path() -> Path:
    """Get path to the WeChat channels persistent JSON file based on active tenant."""
    from src.config.paths import active_tenant_var
    tenant = active_tenant_var.get()
    if tenant == "default":
        return WECHAT_CHANNELS_JSON
    return _get_active_runtime_dir() / "wechat_channels.json"

def _load_wechat_channels() -> list[dict[str, Any]]:
    """Load WeChat channels from the persistent JSON file."""
    channels = []
    path = _get_wechat_channels_json_path()
    if path.exists():
        try:
            channels = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to read %s: %s", path, e)
    return channels

def _save_wechat_channels(channels: list[dict[str, Any]]) -> None:
    """Save WeChat channels to the persistent JSON file."""
    path = _get_wechat_channels_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(channels, indent=2, ensure_ascii=False), encoding="utf-8")

_platform_manager = None
active_transient_logins: dict[str, dict] = {}
active_ilink_logins: dict[str, dict] = {}

async def _reload_platform_manager() -> None:
    """Stop the running platform manager and start it with the latest active channel adapters."""
    global _platform_manager
    import sys
    host = sys.modules.get("api_server") or sys.modules.get("agent.api_server")
    session_service = host._get_session_service()
    logger.warning("[Platform] Reloading platform manager (session_service=%s)...", session_service is not None)
    if session_service:
        try:
            if _platform_manager:
                await _platform_manager.stop()
            
            from src.platforms import PlatformManager, FeishuAdapter, WechatAdapter
            _platform_manager = PlatformManager(session_service, tenant_id="default")
            
            tenants = ["default"]
            try:
                for k in host._load_tenant_keys():
                    if k.get("is_active", True):
                        tenants.append(k["tenant_id"])
            except Exception as e:
                logger.error("Failed to load tenant keys during platform reload: %s", e)

            from src.config.paths import active_tenant_var
            original_tenant = active_tenant_var.get()
            
            registered_count = 0
            try:
                for t in tenants:
                    active_tenant_var.set(t)
                    
                    # 1. Load Feishu channels
                    channels = _load_feishu_channels()
                    for chan in channels:
                        if chan.get("enabled", True):
                            adapter = FeishuAdapter(
                                channel_id=chan["id"],
                                name=chan["name"],
                                app_id=chan["app_id"],
                                app_secret=chan["app_secret"],
                                allowed_users=chan.get("allowed_users", ""),
                                allow_all_users=chan.get("allow_all_users", False),
                                tenant_id=t,
                            )
                            _platform_manager.register_adapter(adapter)
                            registered_count += 1

                    # 2. Load WeChat channels
                    wechat_chans = _load_wechat_channels()
                    for wchan in wechat_chans:
                        if wchan.get("enabled", True):
                            w_adapter = WechatAdapter(
                                channel_id=wchan["id"],
                                name=wchan["name"],
                                ilink_bot_token=wchan.get("ilink_bot_token", ""),
                                ilink_base_url=wchan.get("ilink_base_url", ""),
                                ilink_bot_id=wchan.get("ilink_bot_id", ""),
                                ilink_user_id=wchan.get("ilink_user_id", ""),
                                tenant_id=t,
                            )
                            _platform_manager.register_adapter(w_adapter)
                            registered_count += 1
            finally:
                active_tenant_var.set(original_tenant)

            logger.warning(f"[Platform] Registered {registered_count} adapter(s) across all active tenants. Starting...")
            await _platform_manager.start()
            logger.warning(f"[Platform] Platform manager started successfully.")
        except Exception as e:
            logger.exception("Failed to reload platform manager: %s", e)



# ---------------------------------------------------------------------------
# Lifecycle helpers (module-level, access host state via sys.modules)
# ---------------------------------------------------------------------------


async def _start_channel_runtime():
    """Start the IM channel runtime."""
    import sys as _sys

    host = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")
    runtime = host._get_channel_runtime()
    await runtime.start(start_manager=True)
    return runtime


async def _stop_channel_runtime() -> None:
    """Stop the IM channel runtime if it was initialized."""
    import sys as _sys

    host = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")
    if host._channel_runtime is None:
        return
    await host._channel_runtime.stop()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

AuthDep = Callable[..., Awaitable[Any] | Any]


def register_channels_routes(
    app: FastAPI,
    require_auth: AuthDep | None = None,
) -> None:
    """Mount the channel routes onto ``app``.

    Resolves ``require_auth`` from the host ``api_server`` module via
    ``sys.modules`` when not passed explicitly.
    """
    # Resolve host dependencies via sys.modules fallback
    import sys as _sys
    import asyncio

    host = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")

    if host is None:
        raise RuntimeError(
            "register_channels_routes: api_server module not in sys.modules; "
            "ensure api_server is imported before calling this function"
        )

    if require_auth is None:
        require_auth = host.require_auth

    require_local_or_auth = getattr(host, "require_local_or_auth", require_auth)
    require_settings_write_auth = getattr(host, "require_settings_write_auth", require_auth)

    # Late-access closure for monkeypatch compatibility
    def _get_channel_runtime():
        """Late-access _get_channel_runtime for test monkeypatch compat."""
        h = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")
        return h._get_channel_runtime()

    # --- Routes ---

    @app.get("/channels/status", dependencies=[Depends(require_auth)])
    async def channels_status():
        """Return IM channel runtime and adapter status."""
        runtime = _get_channel_runtime()
        return runtime.status()

    @app.post("/channels/start", dependencies=[Depends(require_auth)])
    async def channels_start():
        """Start configured IM channel adapters."""
        runtime = await _start_channel_runtime()
        return {"status": "started", **runtime.status()}

    @app.post("/channels/stop", dependencies=[Depends(require_auth)])
    async def channels_stop():
        """Stop configured IM channel adapters."""
        runtime = _get_channel_runtime()
        await runtime.stop()
        return {"status": "stopped", **runtime.status()}

    @app.post("/channels/pairing/command", dependencies=[Depends(require_auth)])
    async def channels_pairing_command(payload: ChannelPairingCommandRequest):
        """Run a pairing command against the shared pairing store."""
        from src.channels.pairing import handle_pairing_command

        return {
            "channel": payload.channel,
            "reply": handle_pairing_command(payload.channel, payload.command),
        }

    # --- Custom Feishu / WeChat CRUD Routes ---

    @app.get(
        "/settings/platforms/feishu/channels",
        response_model=List[FeishuChannelResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def list_feishu_channels():
        """Return all Feishu channels configuration."""
        channels = _load_feishu_channels()
        return [
            FeishuChannelResponse(
                id=c["id"],
                name=c["name"],
                app_id=c["app_id"],
                app_secret_configured=bool(c.get("app_secret")) and c.get("app_secret") not in FEISHU_SECRET_PLACEHOLDERS,
                allowed_users=c.get("allowed_users", ""),
                allow_all_users=c.get("allow_all_users", False),
                enabled=c.get("enabled", True),
            )
            for c in channels
        ]

    @app.post(
        "/settings/platforms/feishu/channels",
        response_model=FeishuChannelResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def create_feishu_channel(payload: CreateFeishuChannelRequest):
        """Add a new Feishu channel configuration."""
        import secrets
        channels = _load_feishu_channels()
        
        new_id = f"chan_{secrets.token_hex(4)}"
        new_channel = {
            "id": new_id,
            "name": payload.name.strip() or f"飞书通道_{new_id[:4]}",
            "app_id": payload.app_id.strip(),
            "app_secret": payload.app_secret.strip(),
            "allowed_users": payload.allowed_users.strip(),
            "allow_all_users": payload.allow_all_users,
            "enabled": payload.enabled,
        }
        
        channels.append(new_channel)
        _save_feishu_channels(channels)
        
        await _reload_platform_manager()
        
        return FeishuChannelResponse(
            id=new_channel["id"],
            name=new_channel["name"],
            app_id=new_channel["app_id"],
            app_secret_configured=bool(new_channel["app_secret"]) and new_channel["app_secret"] not in FEISHU_SECRET_PLACEHOLDERS,
            allowed_users=new_channel["allowed_users"],
            allow_all_users=new_channel["allow_all_users"],
            enabled=new_channel["enabled"],
        )

    @app.put(
        "/settings/platforms/feishu/channels/{channel_id}",
        response_model=FeishuChannelResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_feishu_channel(channel_id: str, payload: UpdateFeishuChannelRequest):
        """Update an existing Feishu channel configuration."""
        channels = _load_feishu_channels()
        target_idx = None
        for idx, c in enumerate(channels):
            if c["id"] == channel_id:
                target_idx = idx
                break
                
        if target_idx is None:
            raise HTTPException(status_code=404, detail="Feishu channel not found")
            
        c = channels[target_idx]
        c["name"] = payload.name.strip()
        c["app_id"] = payload.app_id.strip()
        c["allowed_users"] = payload.allowed_users.strip()
        c["allow_all_users"] = payload.allow_all_users
        c["enabled"] = payload.enabled
        
        if payload.app_secret is not None:
            app_secret = payload.app_secret.strip()
            if app_secret and app_secret not in FEISHU_SECRET_PLACEHOLDERS:
                c["app_secret"] = app_secret
            elif app_secret == "":
                c["app_secret"] = ""
                
        _save_feishu_channels(channels)
        
        await _reload_platform_manager()
        
        return FeishuChannelResponse(
            id=c["id"],
            name=c["name"],
            app_id=c["app_id"],
            app_secret_configured=bool(c["app_secret"]) and c["app_secret"] not in FEISHU_SECRET_PLACEHOLDERS,
            allowed_users=c["allowed_users"],
            allow_all_users=c["allow_all_users"],
            enabled=c["enabled"],
        )

    @app.delete(
        "/settings/platforms/feishu/channels/{channel_id}",
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def delete_feishu_channel(channel_id: str):
        """Delete a Feishu channel configuration."""
        channels = _load_feishu_channels()
        initial_len = len(channels)
        channels = [c for c in channels if c["id"] != channel_id]
        
        if len(channels) == initial_len:
            raise HTTPException(status_code=404, detail="Feishu channel not found")
            
        _save_feishu_channels(channels)
        
        await _reload_platform_manager()
        
        return {"status": "success"}

    @app.get(
        "/settings/platforms/wechat/channels",
        response_model=List[WechatChannelResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def list_wechat_channels():
        """Return all WeChat channels configuration."""
        channels = _load_wechat_channels()
        return [
            WechatChannelResponse(
                id=c["id"],
                name=c["name"],
                mode="ilink",
                enabled=c.get("enabled", True),
                ilink_bot_token=c.get("ilink_bot_token", ""),
                ilink_base_url=c.get("ilink_base_url", ""),
                ilink_bot_id=c.get("ilink_bot_id", ""),
                ilink_user_id=c.get("ilink_user_id", ""),
            )
            for c in channels
        ]

    @app.post(
        "/settings/platforms/wechat/channels",
        response_model=WechatChannelResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def create_wechat_channel(payload: CreateWechatChannelRequest):
        """Add a new WeChat channel configuration."""
        import secrets
        channels = _load_wechat_channels()
        
        new_id = f"chan_{secrets.token_hex(4)}"
        new_channel = {
            "id": new_id,
            "name": payload.name.strip() or f"微信通道_{new_id[:4]}",
            "mode": "ilink",
            "enabled": payload.enabled,
            "ilink_bot_token": (payload.ilink_bot_token or "").strip(),
            "ilink_base_url": (payload.ilink_base_url or "https://ilinkai.weixin.qq.com").strip(),
            "ilink_bot_id": (payload.ilink_bot_id or "").strip(),
            "ilink_user_id": (payload.ilink_user_id or "").strip(),
        }
        
        channels.append(new_channel)
        _save_wechat_channels(channels)
        
        await _reload_platform_manager()
        
        if payload.enabled and new_channel["ilink_user_id"]:
            from src.config.paths import active_tenant_var
            tid = active_tenant_var.get() or "default"
            adapter_key = f"wechat_{tid}_{new_channel['id']}"
            if _platform_manager and adapter_key in _platform_manager._adapters:
                adapter = _platform_manager._adapters[adapter_key]
                welcome_msg = "你好，我是量化金融研究助手，我已经成功接收到您的消息并连接成功。"
                
                async def _send_welcome():
                    try:
                        for _ in range(5):
                            if adapter._last_context_tokens.get(new_channel["ilink_user_id"]):
                                break
                            await asyncio.sleep(2.0)
                        else:
                            logger.warning(f"[WeChat iLink] No context token found for {new_channel['ilink_user_id']} after waiting, trying send_message anyway.")
                        await adapter.send_message(new_channel["ilink_user_id"], welcome_msg)
                        logger.warning(f"[WeChat iLink] Sent proactive welcome message to {new_channel['ilink_user_id']}")
                    except Exception as ex:
                        logger.error(f"[WeChat iLink] Failed to send welcome message: {type(ex).__name__}: {ex}\n{traceback.format_exc()}")
                        
                asyncio.create_task(_send_welcome())
        
        return WechatChannelResponse(
            id=new_channel["id"],
            name=new_channel["name"],
            mode="ilink",
            enabled=new_channel["enabled"],
            ilink_bot_token=new_channel["ilink_bot_token"],
            ilink_base_url=new_channel["ilink_base_url"],
            ilink_bot_id=new_channel["ilink_bot_id"],
            ilink_user_id=new_channel["ilink_user_id"],
        )

    @app.put(
        "/settings/platforms/wechat/channels/{channel_id}",
        response_model=WechatChannelResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_wechat_channel(channel_id: str, payload: UpdateWechatChannelRequest):
        """Update an existing WeChat channel configuration."""
        channels = _load_wechat_channels()
        target_idx = None
        for idx, c in enumerate(channels):
            if c["id"] == channel_id:
                target_idx = idx
                break
                
        if target_idx is None:
            raise HTTPException(status_code=404, detail="WeChat channel not found")
            
        c = channels[target_idx]
        c["name"] = payload.name.strip()
        c["mode"] = "ilink"
        c["enabled"] = payload.enabled
        
        old_token = c.get("ilink_bot_token", "")
        old_user_id = c.get("ilink_user_id", "")
        old_enabled = c.get("enabled", False)

        if payload.ilink_bot_token is not None:
            c["ilink_bot_token"] = payload.ilink_bot_token.strip()
        if payload.ilink_base_url is not None:
            c["ilink_base_url"] = payload.ilink_base_url.strip() or "https://ilinkai.weixin.qq.com"
        if payload.ilink_bot_id is not None:
            c["ilink_bot_id"] = payload.ilink_bot_id.strip()
        if payload.ilink_user_id is not None:
            c["ilink_user_id"] = payload.ilink_user_id.strip()
                
        _save_wechat_channels(channels)
        
        await _reload_platform_manager()

        token_changed = (payload.ilink_bot_token is not None and payload.ilink_bot_token.strip() != old_token)
        user_id_changed = (payload.ilink_user_id is not None and payload.ilink_user_id.strip() != old_user_id)
        enabled_changed = (payload.enabled != old_enabled)

        if c["enabled"] and c["ilink_user_id"] and (token_changed or user_id_changed or (enabled_changed and c["enabled"])):
            from src.config.paths import active_tenant_var
            tid = active_tenant_var.get() or "default"
            adapter_key = f"wechat_{tid}_{c['id']}"
            if _platform_manager and adapter_key in _platform_manager._adapters:
                adapter = _platform_manager._adapters[adapter_key]
                welcome_msg = "你好，我是量化金融研究助手，我已经成功接收到您的消息并连接成功。"
                
                async def _send_welcome():
                    try:
                        for _ in range(5):
                            if adapter._last_context_tokens.get(c["ilink_user_id"]):
                                break
                            await asyncio.sleep(2.0)
                        else:
                            logger.warning(f"[WeChat iLink] No context token found for {c['ilink_user_id']} after waiting, trying send_message anyway.")
                        await adapter.send_message(c["ilink_user_id"], welcome_msg)
                        logger.warning(f"[WeChat iLink] Sent proactive welcome message to {c['ilink_user_id']}")
                    except Exception as ex:
                        logger.error(f"[WeChat iLink] Failed to send welcome message: {type(ex).__name__}: {ex}\n{traceback.format_exc()}")
                        
                asyncio.create_task(_send_welcome())
        
        return WechatChannelResponse(
            id=c["id"],
            name=c["name"],
            mode="ilink",
            enabled=c["enabled"],
            ilink_bot_token=c.get("ilink_bot_token", ""),
            ilink_base_url=c.get("ilink_base_url", ""),
            ilink_bot_id=c.get("ilink_bot_id", ""),
            ilink_user_id=c.get("ilink_user_id", ""),
        )

    @app.delete(
        "/settings/platforms/wechat/channels/{channel_id}",
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def delete_wechat_channel(channel_id: str):
        """Delete a WeChat channel configuration."""
        channels = _load_wechat_channels()
        initial_len = len(channels)
        channels = [c for c in channels if c["id"] != channel_id]
        
        if len(channels) == initial_len:
            raise HTTPException(status_code=404, detail="WeChat channel not found")
            
        _save_wechat_channels(channels)
        
        await _reload_platform_manager()
        
        return {"status": "success"}

    @app.get(
        "/settings/platforms/wechat/transient/qrcode",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_wechat_transient_qrcode(mode: str = "ilink"):
        """Fetch WeChat login QR code transiently without requiring an existing channel."""
        import secrets
        import time
        import httpx
        import urllib.parse

        temp_id = f"temp_{secrets.token_hex(8)}"

        if mode == "ilink":
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        "https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3",
                        json={"local_token_list": []},
                        timeout=10,
                    )
                    res.raise_for_status()
                    data = res.json()
                qrcode = data.get("qrcode")
                qrcode_img_content = data.get("qrcode_img_content")
                if qrcode and qrcode_img_content:
                    active_transient_logins[temp_id] = {
                        "qrcode": qrcode,
                        "qrcode_url": qrcode_img_content,
                        "started_at": time.time(),
                        "api_base_url": "https://ilinkai.weixin.qq.com",
                        "mode": "ilink",
                    }
                    qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote_plus(qrcode_img_content)}"
                    return {"status": "waiting", "qrcode": qr_image_url, "temp_id": temp_id}
                else:
                    raise HTTPException(status_code=500, detail="微信 iLink 官方网关返回空数据，请稍后重试。")
            except Exception as e:
                logger.exception("Failed to fetch official iLink QR code")
                raise HTTPException(status_code=500, detail=f"获取微信官方 iLink 二维码失败: {e}")

        raise HTTPException(status_code=400, detail="Unsupported mode")

    @app.get(
        "/settings/platforms/wechat/transient/status",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_wechat_transient_status(temp_id: str):
        """Fetch WeChat login status transiently."""
        login_context = active_transient_logins.get(temp_id)
        if not login_context:
            return {"status": "waiting"}

        mode = login_context.get("mode")
        if mode == "ilink":
            qrcode = login_context["qrcode"]
            api_base_url = login_context.get("api_base_url", "https://ilinkai.weixin.qq.com")

            import httpx
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    res = await client.get(
                        f"{api_base_url}/ilink/bot/get_qrcode_status?qrcode={qrcode}",
                    )
                    res.raise_for_status()
                    data = res.json()
            except Exception as e:
                logger.warning("Failed to poll official iLink QR status: %s", e)
                return {"status": "waiting"}

            try:
                status = data.get("status")
                if status == "scaned_but_redirect" and data.get("redirect_host"):
                    new_host = f"https://{data.get('redirect_host')}"
                    login_context["api_base_url"] = new_host
                    return {"status": "scanned"}
                elif status == "wait":
                    return {"status": "waiting"}
                elif status == "scaned":
                    return {"status": "scanned"}
                elif status == "expired":
                    return {"status": "expired"}
                elif status in ("confirmed", "binded_redirect"):
                    bot_token = data.get("bot_token")
                    baseurl = data.get("baseurl") or api_base_url
                    ilink_bot_id = data.get("ilink_bot_id")
                    ilink_user_id = data.get("ilink_user_id")

                    active_transient_logins.pop(temp_id, None)

                    return {
                        "status": "success",
                        "bot_token": bot_token,
                        "baseurl": baseurl,
                        "ilink_bot_id": ilink_bot_id,
                        "ilink_user_id": ilink_user_id,
                    }
            except Exception as e:
                logger.warning("Failed to process official iLink QR status data: %s", e)
                return {"status": "waiting"}

        return {"status": "waiting"}

    @app.get(
        "/settings/platforms/wechat/channels/{channel_id}/qrcode",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_wechat_channel_qrcode(channel_id: str):
        """Fetch WeChat login QR code from the iLink official gateway."""
        channels = _load_wechat_channels()
        channel = next((c for c in channels if c["id"] == channel_id), None)
        if not channel:
            raise HTTPException(status_code=404, detail="微信通道不存在")
            
        import httpx
        
        token = channel.get("ilink_bot_token", "").strip()
        local_tokens = [token] if token else []
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3",
                    json={"local_token_list": local_tokens},
                    timeout=10,
                )
                res.raise_for_status()
                data = res.json()
            qrcode = data.get("qrcode")
            qrcode_img_content = data.get("qrcode_img_content")
            if qrcode and qrcode_img_content:
                active_ilink_logins[channel_id] = {
                    "qrcode": qrcode,
                    "qrcode_url": qrcode_img_content,
                    "started_at": time.time(),
                    "api_base_url": "https://ilinkai.weixin.qq.com",
                }
                import urllib.parse
                qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote_plus(qrcode_img_content)}"
                return {"status": "waiting", "qrcode": qr_image_url}
            else:
                raise HTTPException(status_code=500, detail="微信 iLink 官方网关返回空数据，请稍后重试。")
        except Exception as e:
            logger.exception("Failed to fetch official iLink QR code")
            raise HTTPException(status_code=500, detail=f"获取微信官方 iLink 二维码失败: {e}")

    @app.get(
        "/settings/platforms/wechat/channels/{channel_id}/status",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_wechat_channel_status(channel_id: str):
        """Fetch WeChat login status from the iLink official gateway."""
        channels = _load_wechat_channels()
        channel = next((c for c in channels if c["id"] == channel_id), None)
        if not channel:
            raise HTTPException(status_code=404, detail="WeChat channel not found")
            
        login_context = active_ilink_logins.get(channel_id)
        if not login_context:
            return {"status": "waiting"}
            
        qrcode = login_context["qrcode"]
        api_base_url = login_context.get("api_base_url", "https://ilinkai.weixin.qq.com")
        
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(
                    f"{api_base_url}/ilink/bot/get_qrcode_status?qrcode={qrcode}",
                )
                res.raise_for_status()
                data = res.json()
        except Exception as e:
            logger.warning("Failed to poll official iLink QR status: %s", e)
            return {"status": "waiting"}

        try:
            status = data.get("status")
            if status == "scaned_but_redirect" and data.get("redirect_host"):
                new_host = f"https://{data.get('redirect_host')}"
                login_context["api_base_url"] = new_host
                return {"status": "scanned"}
            elif status == "wait":
                return {"status": "waiting"}
            elif status == "scaned":
                return {"status": "scanned"}
            elif status == "expired":
                return {"status": "expired"}
            elif status in ("confirmed", "binded_redirect"):
                bot_token = data.get("bot_token")
                baseurl = data.get("baseurl") or api_base_url
                ilink_bot_id = data.get("ilink_bot_id")
                ilink_user_id = data.get("ilink_user_id")
                
                for c in channels:
                    if c["id"] == channel_id:
                        if bot_token:
                            c["ilink_bot_token"] = bot_token
                        if baseurl:
                            c["ilink_base_url"] = baseurl
                        if ilink_bot_id:
                            c["ilink_bot_id"] = ilink_bot_id
                        if ilink_user_id:
                            c["ilink_user_id"] = ilink_user_id
                        c["enabled"] = True
                        break
                _save_wechat_channels(channels)
                active_ilink_logins.pop(channel_id, None)
                
                await _reload_platform_manager()
                
                if ilink_user_id:
                    from src.config.paths import active_tenant_var
                    tid = active_tenant_var.get() or "default"
                    adapter_key = f"wechat_{tid}_{channel_id}"
                    if _platform_manager and adapter_key in _platform_manager._adapters:
                        adapter = _platform_manager._adapters[adapter_key]
                        welcome_msg = "你好，我是量化金融研究助手，我已经成功接收到您的消息并连接成功。"
                        
                        async def _send_welcome():
                            try:
                                for _ in range(5):
                                    if adapter._last_context_tokens.get(ilink_user_id):
                                        break
                                    await asyncio.sleep(2.0)
                                else:
                                    logger.warning(f"[WeChat iLink] No context token found for {ilink_user_id} after waiting, trying send_message anyway.")
                                await adapter.send_message(ilink_user_id, welcome_msg)
                                logger.warning(f"[WeChat iLink] Sent proactive welcome message to {ilink_user_id}")
                            except Exception as ex:
                                logger.error(f"[WeChat iLink] Failed to send welcome message: {type(ex).__name__}: {ex}\n{traceback.format_exc()}")
                                
                        asyncio.create_task(_send_welcome())
                
                return {"status": "success"}
        except Exception as e:
            logger.warning("Failed to process official iLink QR status data: %s", e)
            return {"status": "waiting"}

        return {"status": "waiting"}
