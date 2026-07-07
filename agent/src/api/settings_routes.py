import importlib.util
import json
import os
import sys as _sys
import hashlib
import secrets
import hmac
import asyncio
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field

# Agent root (agent/) — resolved from this file's location (agent/src/api/).
_AGENT_DIR = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models (defined locally -- NO shared modules, per maintainer rule)
# ---------------------------------------------------------------------------

class AdminElevateRequest(BaseModel):
    username: str
    password: str


class AdminChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TenantKeyItem(BaseModel):
    """Tenant key definition."""
    key: str
    tenant_id: str
    name: str
    created_at: str
    is_active: bool


class CreateTenantKeyRequest(BaseModel):
    """Request payload to create a tenant key."""
    name: str = Field(..., min_length=1)


class UpdateTenantKeyRequest(BaseModel):
    """Request payload to update a tenant key."""
    name: Optional[str] = None
    is_active: Optional[bool] = None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt, hash_val = encoded.split('$', 3)
        assert algorithm == 'pbkdf2_sha256'
        iterations = int(iterations)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return key.hex() == hash_val
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Pydantic models (defined locally -- NO shared modules, per maintainer rule)
# ---------------------------------------------------------------------------


class LLMProviderOption(BaseModel):
    """Supported LLM provider metadata for the settings UI."""

    name: str
    label: str
    api_key_env: Optional[str] = None
    base_url_env: str
    default_model: str
    default_base_url: str
    api_key_required: bool = True
    auth_type: str = "api_key"
    login_command: Optional[str] = None


class LLMSettingsResponse(BaseModel):
    """Current LLM runtime settings."""

    provider: str
    model_name: str
    base_url: str
    api_key_env: Optional[str] = None
    api_key_configured: bool
    api_key_hint: Optional[str] = None
    api_key_required: bool
    temperature: float
    timeout_seconds: int
    max_retries: int
    reasoning_effort: str
    sse_timeout_seconds: int
    env_path: str
    providers: List[LLMProviderOption]


class UpdateLLMSettingsRequest(BaseModel):
    """Update LLM settings persisted to agent/.env."""

    provider: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1)
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    clear_api_key: bool = False
    temperature: float = 0.0
    timeout_seconds: int = Field(120, ge=1, le=3600)
    max_retries: int = Field(2, ge=0, le=20)
    reasoning_effort: Optional[str] = None


class DataSourceSettingsResponse(BaseModel):
    """Current data source credential settings."""

    tushare_token_configured: bool
    tushare_token_hint: Optional[str] = None
    baostock_supported: bool
    baostock_installed: bool
    baostock_message: str
    env_path: str


class UpdateDataSourceSettingsRequest(BaseModel):
    """Update project-local data source credentials."""

    tushare_token: Optional[str] = None
    clear_tushare_token: bool = False


# ---------------------------------------------------------------------------
# Provider metadata (settings-exclusive)
# ---------------------------------------------------------------------------

LLM_PROVIDER_CONFIG_PATH = _AGENT_DIR / "src" / "providers" / "llm_providers.json"


def _load_llm_providers() -> List[LLMProviderOption]:
    """Load provider metadata from JSON so additions stay data-driven."""
    try:
        raw = json.loads(LLM_PROVIDER_CONFIG_PATH.read_text(encoding="utf-8"))
        providers = [LLMProviderOption(**item) for item in raw]
    except Exception as exc:
        raise RuntimeError(f"Failed to load LLM provider config: {LLM_PROVIDER_CONFIG_PATH}") from exc

    seen: set[str] = set()
    for provider in providers:
        if provider.name in seen:
            raise RuntimeError(f"Duplicate LLM provider name: {provider.name}")
        seen.add(provider.name)
    if not providers:
        raise RuntimeError("LLM provider config must not be empty")
    return providers


LLM_PROVIDERS = _load_llm_providers()
LLM_PROVIDER_BY_NAME = {provider.name: provider for provider in LLM_PROVIDERS}
LLM_REASONING_EFFORTS = {"", "low", "medium", "high", "max"}
LLM_API_KEY_PLACEHOLDERS = {"", "sk-or-v1-your-key-here", "sk-xxx", "xxx", "gsk_xxx"}
TUSHARE_TOKEN_PLACEHOLDERS = {"", "your-tushare-token"}


# ---------------------------------------------------------------------------
# Host access helpers (late-binding for test monkeypatch compat)
# ---------------------------------------------------------------------------


def _host():
    """Return the ``api_server`` module for late-access attribute reads.

    Tests monkeypatch ``ENV_PATH``, ``ENV_EXAMPLE_PATH``, ``_baostock_supported``
    and ``_baostock_installed`` directly on the ``api_server`` module; every
    function that reads these symbols goes through ``_host()`` so monkeypatched
    values take effect.
    """
    return _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")


# ---------------------------------------------------------------------------
# Settings-exclusive helpers
# ---------------------------------------------------------------------------


def _baostock_supported() -> bool:
    """Check whether the project has a BaoStock loader implementation."""
    host = _host()
    agent_dir = host.AGENT_DIR if host is not None else _AGENT_DIR
    loader_dir = agent_dir / "backtest" / "loaders"
    return any((loader_dir / name).exists() for name in ("baostock.py", "baostock_loader.py"))


def _baostock_installed() -> bool:
    """Check whether the optional BaoStock package is importable."""
    return importlib.util.find_spec("baostock") is not None


def _read_settings_env_values() -> Dict[str, str]:
    """Read settings without creating agent/.env.

    Prefer the user's active agent/.env.  If it does not exist yet, fall back
    to agent/.env.example for display defaults only.
    """
    host = _host()
    env_path = host.ENV_PATH
    env_example_path = host.ENV_EXAMPLE_PATH
    read_env = host._read_env_values
    if env_path.exists():
        return read_env(env_path)
    if env_example_path.exists():
        return read_env(env_example_path)
    return {}


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _build_llm_settings_response(
    values: Optional[Dict[str, str]] = None,
) -> LLMSettingsResponse:
    """Build the public settings payload from dotenv values."""
    host = _host()
    env_values = values if values is not None else _read_settings_env_values()
    provider_name = env_values.get("LANGCHAIN_PROVIDER", "openai").strip().lower()
    provider = LLM_PROVIDER_BY_NAME.get(provider_name, LLM_PROVIDER_BY_NAME["openai"])
    api_key = env_values.get(provider.api_key_env or "", "") if provider.api_key_env else ""
    api_key_configured = host._is_configured_secret(api_key, LLM_API_KEY_PLACEHOLDERS)
    api_key_hint = None
    if provider.auth_type == "oauth":
        try:
            from src.providers.openai_codex import get_openai_codex_login_status

            token = get_openai_codex_login_status()
        except Exception:
            token = None
        api_key_configured = bool(token)
        api_key_hint = None
    return LLMSettingsResponse(
        provider=provider.name,
        model_name=env_values.get("LANGCHAIN_MODEL_NAME", provider.default_model),
        base_url=env_values.get(provider.base_url_env, provider.default_base_url),
        api_key_env=provider.api_key_env,
        api_key_configured=api_key_configured,
        api_key_hint=api_key_hint,
        api_key_required=provider.api_key_required,
        temperature=host._coerce_float(env_values.get("LANGCHAIN_TEMPERATURE", "0.0"), 0.0),
        timeout_seconds=host._coerce_int(env_values.get("TIMEOUT_SECONDS", "120"), 120),
        max_retries=host._coerce_int(env_values.get("MAX_RETRIES", "2"), 2),
        reasoning_effort=env_values.get("LANGCHAIN_REASONING_EFFORT", "").strip().lower(),
        sse_timeout_seconds=host._coerce_int(env_values.get("VIBE_TRADING_SSE_TIMEOUT", "90"), 90),
        env_path=host._project_relative_path(host.ENV_PATH),
        providers=LLM_PROVIDERS,
    )


def _build_data_source_settings_response(
    values: Optional[Dict[str, str]] = None,
) -> DataSourceSettingsResponse:
    """Build the public data source settings payload."""
    host = _host()
    env_values = values if values is not None else _read_settings_env_values()
    token = env_values.get("TUSHARE_TOKEN", "")
    token_configured = host._is_configured_secret(token, TUSHARE_TOKEN_PLACEHOLDERS)
    # Late-access baostock helpers for monkeypatch compat.
    baostock_sup = getattr(host, "_baostock_supported", _baostock_supported)
    baostock_ins = getattr(host, "_baostock_installed", _baostock_installed)
    supported = baostock_sup()
    installed = baostock_ins()
    if supported:
        baostock_message = "BaoStock loader is available."
    elif installed:
        baostock_message = "BaoStock package is installed, but this project has no BaoStock loader."
    else:
        baostock_message = "No BaoStock loader is registered in this project."
    return DataSourceSettingsResponse(
        tushare_token_configured=token_configured,
        tushare_token_hint=None,
        baostock_supported=supported,
        baostock_installed=installed,
        baostock_message=baostock_message,
        env_path=host._project_relative_path(host.ENV_PATH),
    )


def _sync_runtime_env(provider: LLMProviderOption, updates: Dict[str, str]) -> None:
    """Apply saved LLM settings to the running API process."""
    host = _host()
    for key, value in updates.items():
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)

    if provider.api_key_env:
        key_value = os.environ.get(provider.api_key_env, "")
        if host._is_configured_secret(key_value, LLM_API_KEY_PLACEHOLDERS):
            os.environ["OPENAI_API_KEY"] = key_value
        else:
            os.environ.pop("OPENAI_API_KEY", None)
    elif provider.auth_type == "oauth":
        os.environ.pop("OPENAI_API_KEY", None)
    else:
        os.environ["OPENAI_API_KEY"] = "ollama"

    base_url = os.environ.get(provider.base_url_env, "")
    if base_url:
        os.environ["OPENAI_API_BASE"] = base_url
        os.environ["OPENAI_BASE_URL"] = base_url
    else:
        os.environ.pop("OPENAI_API_BASE", None)
        os.environ.pop("OPENAI_BASE_URL", None)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

AuthDep = Callable[..., Awaitable[Any] | Any]


def register_settings_routes(
    app: FastAPI,
    require_local_or_auth: AuthDep | None = None,
    require_settings_write_auth: AuthDep | None = None,
) -> None:
    """Mount the settings routes onto ``app``."""
    host = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")

    if host is None:
        raise RuntimeError(
            "register_settings_routes: api_server module not in sys.modules; "
            "ensure api_server is imported before calling this function"
        )

    if require_auth is None:
        require_auth = host.require_auth
    require_local_or_auth = getattr(host, "require_local_or_auth", require_auth)
    if require_settings_write_auth is None:
        require_settings_write_auth = getattr(host, "require_settings_write_auth", require_auth)
    require_admin = getattr(host, "require_admin", require_auth)

    # --- Routes ---

    @app.get(
        "/settings/llm",
        response_model=LLMSettingsResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_llm_settings():
        """Return project-local LLM settings for the Web UI."""
        return _build_llm_settings_response()

    @app.put(
        "/settings/llm",
        response_model=LLMSettingsResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_llm_settings(payload: UpdateLLMSettingsRequest):
        """Persist project-local LLM settings and update the running process."""
        host_ref = _host()
        provider_name = payload.provider.strip().lower()
        provider = LLM_PROVIDER_BY_NAME.get(provider_name)
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported LLM provider"
            )

        model_name = payload.model_name.strip()
        if not model_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Model name is required"
            )

        if payload.temperature < 0 or payload.temperature > 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temperature must be between 0 and 2",
            )

        reasoning_effort = (payload.reasoning_effort or "").strip().lower()
        if reasoning_effort not in LLM_REASONING_EFFORTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reasoning effort must be low, medium, high, or max",
            )

        current_values = _read_settings_env_values()
        base_url = (
            payload.base_url if payload.base_url is not None else provider.default_base_url
        ).strip()
        if provider.auth_type == "oauth":
            try:
                from src.providers.openai_codex import validate_codex_base_url

                base_url = validate_codex_base_url(base_url)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                ) from exc
        updates: Dict[str, str] = {
            "LANGCHAIN_PROVIDER": provider.name,
            "LANGCHAIN_MODEL_NAME": model_name,
            provider.base_url_env: base_url,
            "LANGCHAIN_TEMPERATURE": str(payload.temperature),
            "TIMEOUT_SECONDS": str(payload.timeout_seconds),
            "MAX_RETRIES": str(payload.max_retries),
        }
        if reasoning_effort or "LANGCHAIN_REASONING_EFFORT" in current_values:
            updates["LANGCHAIN_REASONING_EFFORT"] = reasoning_effort

        if provider.api_key_env:
            if payload.clear_api_key:
                updates[provider.api_key_env] = ""
            elif payload.api_key is not None and payload.api_key.strip():
                api_key = payload.api_key.strip()
                updates[provider.api_key_env] = (
                    api_key
                    if host_ref._is_configured_secret(api_key, LLM_API_KEY_PLACEHOLDERS)
                    else ""
                )
            elif provider.api_key_env in current_values and host_ref._is_configured_secret(
                current_values[provider.api_key_env],
                LLM_API_KEY_PLACEHOLDERS,
            ):
                updates[provider.api_key_env] = current_values[provider.api_key_env]
        elif payload.clear_api_key:
            os.environ.pop("OPENAI_API_KEY", None)

        host_ref._write_env_values(host_ref.ENV_PATH, updates)
        _sync_runtime_env(provider, updates)
        return _build_llm_settings_response(host_ref._read_env_values(host_ref.ENV_PATH))

    @app.get(
        "/settings/data-sources",
        response_model=DataSourceSettingsResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_data_source_settings():
        """Return project-local data source credentials for the Web UI."""
        return _build_data_source_settings_response()

    @app.put(
        "/settings/data-sources",
        response_model=DataSourceSettingsResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_data_source_settings(payload: UpdateDataSourceSettingsRequest):
        """Persist project-local data source credentials and update the running process."""
        host_ref = _host()
        current_values = _read_settings_env_values()
        updates: Dict[str, str] = {}

        if payload.clear_tushare_token:
            updates["TUSHARE_TOKEN"] = ""
        elif payload.tushare_token is not None and payload.tushare_token.strip():
            updates["TUSHARE_TOKEN"] = payload.tushare_token.strip()
        elif "TUSHARE_TOKEN" in current_values:
            updates["TUSHARE_TOKEN"] = current_values["TUSHARE_TOKEN"]

        if updates:
            host_ref._write_env_values(host_ref.ENV_PATH, updates)
            token = updates.get("TUSHARE_TOKEN", "").strip()
            if host_ref._is_configured_secret(token, TUSHARE_TOKEN_PLACEHOLDERS):
                os.environ["TUSHARE_TOKEN"] = token
            else:
                os.environ.pop("TUSHARE_TOKEN", None)

        return _build_data_source_settings_response(
            host_ref._read_env_values(host_ref.ENV_PATH)
        )

    # --- Custom THS Cookie Test/Sync Endpoints ---

    @app.post("/settings/ths/test", dependencies=[Depends(require_settings_write_auth)])
    async def test_ths_cookie(payload: Dict[str, str]):
        cookie = payload.get("cookie", "").strip()
        if not cookie:
            raise HTTPException(status_code=400, detail="Cookie cannot be empty")
        from src.market.ths_sync import ThsSyncManager, ThsSyncService
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        
        loop = asyncio.get_running_loop()
        manager = ThsSyncManager(tenant_id=tenant)
        res = await loop.run_in_executor(None, manager.test_connection, cookie)
        
        if res.get("success"):
            ThsSyncService()._failure_counts[tenant] = 0
            
        return res

    @app.post("/settings/ths/sync", dependencies=[Depends(require_settings_write_auth)])
    async def manual_ths_sync(request: Request):
        """手动立即触发当前租户的同花顺自选股同步。"""
        from src.market.ths_sync import ThsSyncService
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        service = ThsSyncService()
        result = await service.manual_sync_tenant(tenant)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "同步失败"))
        return result

    # --- Admin Elevation & Password Change Endpoints ---

    @app.post("/settings/admin-elevate")
    async def admin_elevate(payload: AdminElevateRequest):
        """Elevate request to admin status using username and password."""
        if payload.username != "admin":
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
        
        from src.config.paths import get_tenant_db_path
        import sqlite3
        db_path = get_tenant_db_path("default")
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM admin_auth WHERE username = 'admin'")
            row = cursor.fetchone()
            conn.close()
        except Exception as e:
            logger.error("Database query failed: %s", e)
            raise HTTPException(status_code=500, detail="数据库查询失败")
            
        if not row:
            raise HTTPException(status_code=500, detail="管理员账户未初始化")
            
        pwd_hash = row[0]
        if not verify_password(payload.password, pwd_hash):
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
            
        token = secrets.token_hex(32)
        host = _host()
        host._ADMIN_SESSION_TOKENS.add(token)
        return {"status": "success", "admin_token": token}

    @app.post("/settings/admin-change-password")
    async def admin_change_password(request: Request, payload: AdminChangePasswordRequest):
        """Change admin password."""
        host = _host()
        if not host._is_request_admin(request):
            raise HTTPException(status_code=403, detail="管理员权限不足")
        
        from src.config.paths import get_tenant_db_path
        import sqlite3
        db_path = get_tenant_db_path("default")
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM admin_auth WHERE username = 'admin'")
            row = cursor.fetchone()
        except Exception as e:
            logger.error("Database query failed: %s", e)
            raise HTTPException(status_code=500, detail="数据库查询失败")
            
        if not row:
            if conn:
                conn.close()
            raise HTTPException(status_code=500, detail="管理员账户未初始化")
            
        pwd_hash = row[0]
        if not verify_password(payload.old_password, pwd_hash):
            conn.close()
            raise HTTPException(status_code=400, detail="原密码不正确")
            
        try:
            new_hash = hash_password(payload.new_password)
            cursor.execute("UPDATE admin_auth SET password_hash = ? WHERE username = 'admin'", (new_hash,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Database update failed: %s", e)
            raise HTTPException(status_code=500, detail="数据库更新失败")
            
        return {"status": "success", "detail": "密码修改成功"}

    @app.post("/settings/admin-deelevate")
    async def admin_deelevate(request: Request):
        """Remove admin elevation token."""
        host = _host()
        token = request.headers.get("x-admin-token")
        if token and token in host._ADMIN_SESSION_TOKENS:
            host._ADMIN_SESSION_TOKENS.remove(token)
        return {"status": "success"}

    # --- Multi-tenant Keys CRUD Endpoints ---

    @app.get(
        "/admin/tenants/keys",
        response_model=List[TenantKeyItem],
        dependencies=[Depends(require_admin)],
    )
    async def get_tenant_keys():
        """List all configured tenant API keys."""
        host = _host()
        keys = host._load_tenant_keys()
        return [TenantKeyItem(**k) for k in keys]

    @app.post(
        "/admin/tenants/keys",
        response_model=TenantKeyItem,
        dependencies=[Depends(require_admin)],
    )
    async def create_tenant_key(payload: CreateTenantKeyRequest):
        """Generate a new tenant API key and setup workspace."""
        import secrets
        import datetime
        host = _host()
        
        raw_key = "vibe_t_" + secrets.token_hex(16)
        tenant_id = "tenant_" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12]
        
        keys = host._load_tenant_keys()
        new_key = {
            "key": raw_key,
            "tenant_id": tenant_id,
            "name": payload.name.strip(),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "is_active": True,
        }
        keys.append(new_key)
        host._save_tenant_keys(keys)
        
        tenant_dir = host._get_active_runtime_dir() / "tenants" / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return TenantKeyItem(**new_key)

    @app.put(
        "/admin/tenants/keys/{tenant_id}",
        response_model=TenantKeyItem,
        dependencies=[Depends(require_admin)],
    )
    async def update_tenant_key(tenant_id: str, payload: UpdateTenantKeyRequest):
        """Update status or name of an existing tenant key."""
        host = _host()
        keys = host._load_tenant_keys()
        matched = None
        for k in keys:
            if k["tenant_id"] == tenant_id:
                matched = k
                break
        if not matched:
            raise HTTPException(status_code=404, detail="Tenant key not found")
        
        if payload.name is not None:
            matched["name"] = payload.name.strip()
        if payload.is_active is not None:
            matched["is_active"] = payload.is_active
            
        host._save_tenant_keys(keys)
        return TenantKeyItem(**matched)

    @app.delete(
        "/admin/tenants/keys/{tenant_id}",
        dependencies=[Depends(require_admin)],
    )
    async def delete_tenant_key(tenant_id: str):
        """Delete a tenant key (invalidating it instantly)."""
        host = _host()
        keys = host._load_tenant_keys()
        filtered_keys = [k for k in keys if k["tenant_id"] != tenant_id]
        if len(filtered_keys) == len(keys):
            raise HTTPException(status_code=404, detail="Tenant key not found")
        host._save_tenant_keys(filtered_keys)
        return {"status": "success"}
