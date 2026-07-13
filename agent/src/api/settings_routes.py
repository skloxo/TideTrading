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
    is_custom: Optional[bool] = None
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
    use_default: bool = False


class DataSourceSettingsResponse(BaseModel):
    """Current data source credential settings."""

    tushare_token_configured: bool
    tushare_token_hint: Optional[str] = None
    iwencai_key_configured: bool = False
    iwencai_key_hint: Optional[str] = None
    fred_api_key_configured: bool = False
    fred_api_key_hint: Optional[str] = None
    baostock_supported: bool
    baostock_installed: bool
    baostock_message: str
    env_path: str
    ths_cookie_configured: bool
    ths_cookie_hint: Optional[str] = None
    is_custom: Optional[bool] = None


class ProfileResponse(BaseModel):
    """User Profile Response."""
    role: str
    tenant_id: str
    name: Optional[str] = None
    is_local: bool
    is_tenant: bool = False   # Has a valid tenant Bearer Token
    is_admin: bool = False    # Has a valid admin session token


class FeatureFlagsResponse(BaseModel):
    """Current feature flag state."""

    shell_tools_enabled: bool
    scheduler_enabled: bool
    session_runtime_enabled: bool
    env_path: str


class AgentConfigTextResponse(BaseModel):
    """Raw YAML agent configuration response."""
    yaml_content: str
    config_path: str


class UpdateAgentConfigRequest(BaseModel):
    """Payload to update raw agent configuration."""
    yaml_content: str


class UpdateDataSourceSettingsRequest(BaseModel):
    """Update project-local data source credentials."""

    tushare_token: Optional[str] = None
    clear_tushare_token: bool = False
    iwencai_key: Optional[str] = None
    clear_iwencai_key: bool = False
    fred_api_key: Optional[str] = None
    clear_fred_api_key: bool = False
    ths_cookie: Optional[str] = None
    clear_ths_cookie: bool = False
    use_default: bool = False


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
IWENCAI_KEY_PLACEHOLDERS = {"", "your-iwencai-key"}
FRED_API_KEY_PLACEHOLDERS = {"", "your-fred-api-key"}
THS_COOKIE_PLACEHOLDERS = {"", "your-ths-cookie"}


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


def _delete_env_values(path: Path, keys_to_delete: List[str]) -> None:
    """Delete keys from a dotenv file."""
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    to_delete_set = set(keys_to_delete)
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in to_delete_set:
            continue
        new_lines.append(line)
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _baostock_supported() -> bool:
    """Check whether the project has a BaoStock loader implementation."""
    host = _host()
    if host is not None and getattr(host, "_baostock_supported", None) is not _baostock_supported:
        return host._baostock_supported()
    agent_dir = host.AGENT_DIR if host is not None else _AGENT_DIR
    loader_dir = agent_dir / "backtest" / "loaders"
    return any((loader_dir / name).exists() for name in ("baostock.py", "baostock_loader.py"))


def _baostock_installed() -> bool:
    """Check whether the optional BaoStock package is importable."""
    host = _host()
    if host is not None and getattr(host, "_baostock_installed", None) is not _baostock_installed:
        return host._baostock_installed()
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


def mask_api_keys(key: str) -> str:
    if not key:
        return ""
    key = key.strip()
    return key[:4] + "***" + key[-4:] if len(key) > 8 else "***"

def _build_llm_settings_response(
    values: Optional[Dict[str, str]] = None,
    is_public: bool = False,
) -> LLMSettingsResponse:
    """Build the public settings payload from dotenv values."""
    host = _host()
    from src.config.paths import active_tenant_var, get_runtime_root
    tenant = active_tenant_var.get()

    is_custom = True
    if tenant != "default":
        tenant_env = get_runtime_root() / ".env"
        if not tenant_env.exists():
            is_custom = False
        else:
            tenant_vals = host._read_env_values(tenant_env)
            is_custom = "LANGCHAIN_PROVIDER" in tenant_vals

    if tenant != "default":
        if is_custom:
            env_values = values if values is not None else tenant_vals
        else:
            env_values = {}
    else:
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
        is_custom=is_custom,
        providers=LLM_PROVIDERS,
    )


def _build_data_source_settings_response(
    values: Optional[Dict[str, str]] = None,
    is_public: bool = False,
) -> DataSourceSettingsResponse:
    """Build the public data source settings payload."""
    host = _host()
    from src.config.paths import active_tenant_var, get_runtime_root
    tenant = active_tenant_var.get()

    is_custom = True
    tenant_vals = {}
    if tenant != "default":
        tenant_env = get_runtime_root() / ".env"
        if not tenant_env.exists():
            is_custom = False
        else:
            tenant_vals = host._read_env_values(tenant_env)
            is_custom = any(k in tenant_vals for k in ["TUSHARE_TOKEN", "FRED_API_KEY", "VIBE_TRADING_IWENCAI_KEY", "THS_COOKIE"])

    if tenant != "default":
        if is_custom:
            env_values = values if values is not None else tenant_vals
        else:
            env_values = {}
    else:
        env_values = values if values is not None else _read_settings_env_values()

    token = env_values.get("TUSHARE_TOKEN", "")
    token_configured = host._is_configured_secret(token, TUSHARE_TOKEN_PLACEHOLDERS)
    iwencai_key = env_values.get("VIBE_TRADING_IWENCAI_KEY", "")
    iwencai_key_configured = host._is_configured_secret(iwencai_key, IWENCAI_KEY_PLACEHOLDERS)
    fred_key = env_values.get("FRED_API_KEY", "")
    fred_api_key_configured = host._is_configured_secret(fred_key, FRED_API_KEY_PLACEHOLDERS)
    ths_cookie = env_values.get("THS_COOKIE", "")
    ths_cookie_configured = host._is_configured_secret(ths_cookie, THS_COOKIE_PLACEHOLDERS)
    supported = _baostock_supported()
    installed = _baostock_installed()
    if supported:
        baostock_message = "BaoStock loader is available."
    elif installed:
        baostock_message = (
            "BaoStock package is installed, but this project has no BaoStock loader."
        )
    else:
        baostock_message = "No BaoStock loader is registered in this project."

    tushare_token_hint = None
    iwencai_key_hint = None
    fred_api_key_hint = None
    ths_cookie_hint = None

    return DataSourceSettingsResponse(
        tushare_token_configured=token_configured,
        tushare_token_hint=tushare_token_hint,
        iwencai_key_configured=iwencai_key_configured,
        iwencai_key_hint=iwencai_key_hint,
        fred_api_key_configured=fred_api_key_configured,
        fred_api_key_hint=fred_api_key_hint,
        baostock_supported=supported,
        baostock_installed=installed,
        baostock_message=baostock_message,
        env_path=host._project_relative_path(host.ENV_PATH),
        ths_cookie_configured=ths_cookie_configured,
        ths_cookie_hint=ths_cookie_hint,
        is_custom=is_custom,
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

    require_auth = host.require_auth
    if require_local_or_auth is None:
        require_local_or_auth = getattr(host, "require_local_or_auth", require_auth)
    if require_settings_write_auth is None:
        require_settings_write_auth = getattr(host, "require_settings_write_auth", require_auth)
    require_admin = getattr(host, "require_admin", require_auth)
    require_event_stream_auth = getattr(host, "require_event_stream_auth", require_auth)

    # --- Routes ---

    @app.get(
        "/settings/llm",
        response_model=LLMSettingsResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_llm_settings(request: Request):
        """Return project-local LLM settings for the Web UI."""
        host_ref = _host()
        is_public = not (host_ref._is_request_admin(request) or host_ref._is_local_or_lan_client(request))
        return _build_llm_settings_response(is_public=is_public)

    @app.put(
        "/settings/llm",
        response_model=LLMSettingsResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_llm_settings(request: Request, payload: UpdateLLMSettingsRequest):
        """Persist project-local LLM settings and update the running process."""
        host_ref = _host()
        is_public = not (host_ref._is_request_admin(request) or host_ref._is_local_or_lan_client(request))
        
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        if payload.use_default:
            if tenant != "default":
                LLM_KEYS_TO_CLEAN = [
                    "LANGCHAIN_PROVIDER",
                    "LANGCHAIN_MODEL_NAME",
                    "LANGCHAIN_TEMPERATURE",
                    "TIMEOUT_SECONDS",
                    "MAX_RETRIES",
                    "LANGCHAIN_REASONING_EFFORT",
                    "OPENAI_API_KEY",
                    "OPENAI_BASE_URL",
                    "OPENROUTER_API_KEY",
                    "OPENROUTER_BASE_URL",
                    "GEMINI_API_KEY",
                    "GEMINI_BASE_URL",
                    "ANTHROPIC_API_KEY",
                    "ANTHROPIC_BASE_URL",
                    "DEEPSEEK_API_KEY",
                    "DEEPSEEK_BASE_URL",
                    "QWEN_API_KEY",
                    "QWEN_BASE_URL",
                    "OLLAMA_BASE_URL",
                ]
                _delete_env_values(host_ref.ENV_PATH, LLM_KEYS_TO_CLEAN)
                for key in LLM_KEYS_TO_CLEAN:
                    os.environ.pop(key, None)
                return _build_llm_settings_response(is_public=is_public)
            else:
                raise HTTPException(status_code=400, detail="Admin cannot revert to global default")

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
                if api_key == "********":
                    if provider.api_key_env in current_values:
                        updates[provider.api_key_env] = current_values[provider.api_key_env]
                else:
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
        return _build_llm_settings_response(host_ref._read_env_values(host_ref.ENV_PATH), is_public=is_public)

    @app.get(
        "/settings/data-sources",
        response_model=DataSourceSettingsResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_data_source_settings(request: Request):
        """Return project-local data source credentials for the Web UI."""
        host_ref = _host()
        is_public = not (host_ref._is_request_admin(request) or host_ref._is_local_or_lan_client(request))
        return _build_data_source_settings_response(is_public=is_public)

    @app.put(
        "/settings/data-sources",
        response_model=DataSourceSettingsResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_data_source_settings(request: Request, payload: UpdateDataSourceSettingsRequest):
        """Persist project-local data source credentials and update the running process."""
        host_ref = _host()
        is_public = not (host_ref._is_request_admin(request) or host_ref._is_local_or_lan_client(request))
        
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        if payload.use_default:
            if tenant != "default":
                DS_KEYS_TO_CLEAN = ["TUSHARE_TOKEN", "FRED_API_KEY", "VIBE_TRADING_IWENCAI_KEY", "THS_COOKIE"]
                _delete_env_values(host_ref.ENV_PATH, DS_KEYS_TO_CLEAN)
                for key in DS_KEYS_TO_CLEAN:
                    os.environ.pop(key, None)
                return _build_data_source_settings_response(is_public=is_public)
            else:
                raise HTTPException(status_code=400, detail="Admin cannot revert to global default")

        current_values = _read_settings_env_values()
        updates: Dict[str, str] = {}

        # Tushare Token
        if payload.clear_tushare_token:
            updates["TUSHARE_TOKEN"] = ""
        elif payload.tushare_token is not None and payload.tushare_token.strip():
            val = payload.tushare_token.strip()
            if val == "********":
                if "TUSHARE_TOKEN" in current_values:
                    updates["TUSHARE_TOKEN"] = current_values["TUSHARE_TOKEN"]
            else:
                updates["TUSHARE_TOKEN"] = val
        elif "TUSHARE_TOKEN" in current_values:
            updates["TUSHARE_TOKEN"] = current_values["TUSHARE_TOKEN"]

        # Iwencai Key
        if payload.clear_iwencai_key:
            updates["VIBE_TRADING_IWENCAI_KEY"] = ""
        elif payload.iwencai_key is not None and payload.iwencai_key.strip():
            val = payload.iwencai_key.strip()
            if val == "********":
                if "VIBE_TRADING_IWENCAI_KEY" in current_values:
                    updates["VIBE_TRADING_IWENCAI_KEY"] = current_values["VIBE_TRADING_IWENCAI_KEY"]
            else:
                updates["VIBE_TRADING_IWENCAI_KEY"] = val
        elif "VIBE_TRADING_IWENCAI_KEY" in current_values:
            updates["VIBE_TRADING_IWENCAI_KEY"] = current_values["VIBE_TRADING_IWENCAI_KEY"]

        # Fred API Key
        if payload.clear_fred_api_key:
            updates["FRED_API_KEY"] = ""
        elif payload.fred_api_key is not None and payload.fred_api_key.strip():
            val = payload.fred_api_key.strip()
            if val == "********":
                if "FRED_API_KEY" in current_values:
                    updates["FRED_API_KEY"] = current_values["FRED_API_KEY"]
            else:
                updates["FRED_API_KEY"] = val
        elif "FRED_API_KEY" in current_values:
            updates["FRED_API_KEY"] = current_values["FRED_API_KEY"]

        # THS Cookie
        if payload.clear_ths_cookie:
            updates["THS_COOKIE"] = ""
        elif payload.ths_cookie is not None and payload.ths_cookie.strip():
            val = payload.ths_cookie.strip()
            if val == "********":
                if "THS_COOKIE" in current_values:
                    updates["THS_COOKIE"] = current_values["THS_COOKIE"]
            else:
                updates["THS_COOKIE"] = val
        elif "THS_COOKIE" in current_values:
            updates["THS_COOKIE"] = current_values["THS_COOKIE"]

        if updates:
            host_ref._write_env_values(host_ref.ENV_PATH, updates)
            if "TUSHARE_TOKEN" in updates:
                token = updates.get("TUSHARE_TOKEN", "").strip()
                if host_ref._is_configured_secret(token, TUSHARE_TOKEN_PLACEHOLDERS):
                    os.environ["TUSHARE_TOKEN"] = token
                else:
                    os.environ.pop("TUSHARE_TOKEN", None)
            if "VIBE_TRADING_IWENCAI_KEY" in updates:
                iwencai = updates.get("VIBE_TRADING_IWENCAI_KEY", "").strip()
                if host_ref._is_configured_secret(iwencai, IWENCAI_KEY_PLACEHOLDERS):
                    os.environ["VIBE_TRADING_IWENCAI_KEY"] = iwencai
                else:
                    os.environ.pop("VIBE_TRADING_IWENCAI_KEY", None)
            if "FRED_API_KEY" in updates:
                fred = updates.get("FRED_API_KEY", "").strip()
                if host_ref._is_configured_secret(fred, FRED_API_KEY_PLACEHOLDERS):
                    os.environ["FRED_API_KEY"] = fred
                else:
                    os.environ.pop("FRED_API_KEY", None)
            if "THS_COOKIE" in updates:
                cookie = updates.get("THS_COOKIE", "").strip()
                if host_ref._is_configured_secret(cookie, THS_COOKIE_PLACEHOLDERS):
                    os.environ["THS_COOKIE"] = cookie
                else:
                    os.environ.pop("THS_COOKIE", None)

        return _build_data_source_settings_response(
            host_ref._read_env_values(host_ref.ENV_PATH),
            is_public=is_public
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

    @app.post(
        "/settings/register",
        response_model=TenantKeyItem,
    )
    async def register_tenant(payload: CreateTenantKeyRequest):
        """Public tenant self-registration endpoint."""
        import secrets
        import datetime
        import re
        host = _host()
        
        name = payload.name.strip()
        # 1. 验证格式与长度 (2-20字符，中英文、数字、下划线、减号、空格)
        if not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9_\-\s]{2,20}$", name):
            raise HTTPException(
                status_code=400,
                detail="Nickname must be 2-20 characters, containing only letters, numbers, Chinese, spaces, dashes or underscores."
            )
            
        # 2. 查重
        keys = host._load_tenant_keys()
        normalized_name = name.lower()
        for k in keys:
            if k["name"].strip().lower() == normalized_name:
                raise HTTPException(status_code=400, detail="Tenant name already exists")
                
        # 3. 生成密钥与 tenant_id
        raw_key = "tide_t_" + secrets.token_hex(16)
        tenant_id = "tenant_" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12]
        
        new_key = {
            "key": raw_key,
            "tenant_id": tenant_id,
            "name": name,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "is_active": True,
        }
        keys.append(new_key)
        host._save_tenant_keys(keys)
        
        # 4. 创建隔离目录
        tenant_dir = host._get_active_runtime_dir() / "tenants" / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化专属的配置说明文件
        env_file = tenant_dir / ".env"
        if not env_file.exists():
            env_file.write_text(f"# Created for tenant: {name}\n", encoding="utf-8")
            
        return TenantKeyItem(**new_key)

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
        has_default = any(k.get("tenant_id") == "default" for k in keys)
        if not has_default:
            default_item = {
                "key": "default",
                "tenant_id": "default",
                "name": "默认租户 (default)",
                "created_at": "2026-06-23T00:00:00Z",
                "is_active": True
            }
            return [TenantKeyItem(**default_item)] + [TenantKeyItem(**k) for k in keys]
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
        
        raw_key = "tide_t_" + secrets.token_hex(16)
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
        if tenant_id == "default":
            raise HTTPException(status_code=400, detail="Cannot modify default tenant properties")
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
        try:
            from src.api.channels_routes import _reload_platform_manager
            await _reload_platform_manager()
        except Exception as e:
            logger.error("Failed to reload platform manager after updating tenant: %s", e)
        return TenantKeyItem(**matched)

    @app.delete(
        "/admin/tenants/keys/{tenant_id}",
        dependencies=[Depends(require_admin)],
    )
    async def delete_tenant_key(tenant_id: str):
        """Delete a tenant key (invalidating it instantly)."""
        if tenant_id == "default":
            raise HTTPException(status_code=400, detail="Cannot delete default tenant")
        host = _host()
        keys = host._load_tenant_keys()
        filtered_keys = [k for k in keys if k["tenant_id"] != tenant_id]
        if len(filtered_keys) == len(keys):
            raise HTTPException(status_code=404, detail="Tenant key not found")
        host._save_tenant_keys(filtered_keys)
        try:
            from src.api.channels_routes import _reload_platform_manager
            await _reload_platform_manager()
        except Exception as e:
            logger.error("Failed to reload platform manager after deleting tenant: %s", e)
        return {"status": "success"}

    # --- Extended settings & dashboard routes ---

    @app.get(
        "/settings/profile",
        response_model=ProfileResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_settings_profile(request: Request):
        """Return login identity and active workspace/tenant info."""
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get() or "default"
        host_ref = _host()

        # --- Admin status: valid admin session token in header ---
        admin_elevated = host_ref._is_request_admin(request)

        # --- Tenant status: check if Bearer token resolves to a tenant key ---
        is_tenant = False
        tenant_name: Optional[str] = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            admin_keys = host_ref._configured_api_keys()
            tenant_keys_list = host_ref._load_tenant_keys()
            tenant_key_values = [k["key"] for k in tenant_keys_list if k.get("is_active", True)]
            is_admin_key = any(__import__("hmac").compare_digest(token, k) for k in admin_keys)
            is_tenant = bool(token) and (is_admin_key or token in tenant_key_values)
            if is_tenant and tenant != "default":
                for item in tenant_keys_list:
                    if item.get("tenant_id") == tenant:
                        tenant_name = item.get("name")
                        break

        # --- Role derivation ---
        if is_tenant:
            role = "tenant"
            name = tenant_name or tenant
        elif admin_elevated:
            role = "admin"
            name = "Admin"
        else:
            role = "guest"
            name = "Guest"

        return ProfileResponse(
            role=role,
            tenant_id=tenant,
            name=name,
            is_local=host_ref._is_local_or_lan_client(request),
            is_tenant=is_tenant,
            is_admin=admin_elevated,
        )

    @app.get(
        "/settings/dashboard-layout",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_dashboard_layout():
        """Load dashboard layout configuration for the active tenant."""
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        host_ref = _host()
        layout_path = host_ref.AGENT_DIR / "runs" / f"dashboard_layout_{tenant}.json"
        if layout_path.exists():
            try:
                with open(layout_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to read dashboard layout for tenant %s: %s", tenant, e)
        return {}

    @app.put(
        "/settings/dashboard-layout",
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_dashboard_layout(payload: dict):
        """Save dashboard layout configuration for the active tenant."""
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        host_ref = _host()
        layout_path = host_ref.AGENT_DIR / "runs" / f"dashboard_layout_{tenant}.json"
        try:
            os.makedirs(layout_path.parent, exist_ok=True)
            with open(layout_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return {"status": "success"}
        except Exception as e:
            logger.error("Failed to save dashboard layout for tenant %s: %s", tenant, e)
            raise HTTPException(status_code=500, detail=f"Failed to save layout: {e}")

    @app.get(
        "/settings/dashboard/graph",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_dashboard_graph():
        """Load ECharts relation graph topology for the active tenant."""
        from src.config.paths import active_tenant_var
        from src.swarm.simulation_graph import SimulationGraphManager
        tenant = active_tenant_var.get()
        try:
            manager = SimulationGraphManager(tenant)
            return manager.load()
        except Exception as e:
            logger.error("Failed to load dashboard graph for tenant %s: %s", tenant, e)
            return {"nodes": [], "links": []}

    @app.get(
        "/settings/dashboard/react-logs",
        dependencies=[Depends(require_event_stream_auth)],
    )
    async def get_dashboard_react_logs(request: Request, stream: bool = True):
        """Get ReACT logs for the active tenant. Supports optional SSE streaming."""
        from src.config.paths import active_tenant_var
        tenant = active_tenant_var.get()
        host_ref = _host()
        log_path = host_ref.AGENT_DIR / "runs" / f"agent_log_{tenant}.jsonl"

        if not stream:
            logs = []
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                logs.append(json.loads(line.strip()))
                except Exception as e:
                    logger.warning("Failed to read ReACT logs array for tenant %s: %s", tenant, e)
            return logs

        # SSE Streaming mode
        from fastapi.responses import StreamingResponse
        import asyncio

        async def event_generator():
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                yield f"data: {line.strip()}\n\n"
                except Exception:
                    pass
            
            last_size = log_path.stat().st_size if log_path.exists() else 0
            while True:
                if await request.is_disconnected():
                    break
                if log_path.exists():
                    curr_size = log_path.stat().st_size
                    if curr_size > last_size:
                        try:
                            with open(log_path, "r", encoding="utf-8") as f:
                                f.seek(last_size)
                                for line in f:
                                    if line.strip():
                                        yield f"data: {line.strip()}\n\n"
                            last_size = curr_size
                        except Exception:
                            pass
                await asyncio.sleep(1)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post(
        "/settings/dashboard/agent-chat",
        dependencies=[Depends(require_auth)],
    )
    async def dashboard_agent_chat(payload: dict):
        """Direct NLP chat with specific Swarm Agent presets."""
        agent_id = payload.get("agent_id", "")
        message = payload.get("message", "")
        if not agent_id or not message:
            raise HTTPException(status_code=400, detail="agent_id and message are required")

        AGENT_PERSONAS = {
            "yuzi": "你是游资·游侠，热衷于超短线交易和炒作题材（如低空经济、AI算力）。你言辞犀利、行动迅速，极度关注涨停板 and 资金流入。请用大字报风格和黑客终端语气分析万丰奥威或其它股票，必须包含具体的阻力位、买入点 and 游资博弈心理。",
            "beixiang": "你是北向资金（机构投资者代表），倾向于长线价值投资与宏观配置。你行事稳健，注重筹码分布、基本面估值以及ETF异动，用理性、专业、机构视角的语气来分析市场和个股的估值水平及资金安全垫。",
            "SwarmConductor": "你是多智能体投研管线的指挥官（SwarmConductor），负责汇总技术面、基本面 and 风控面的辩论共识。用全面、不偏不倚的分析语气，客观权衡板块题材机会与回撤风险，给出综合结论。"
        }

        persona = AGENT_PERSONAS.get(agent_id, AGENT_PERSONAS["SwarmConductor"])
        
        from src.providers.chat import ChatLLM
        try:
            llm = ChatLLM()
            messages = [
                {"role": "system", "content": persona},
                {"role": "user", "content": message}
            ]
            response = llm.chat(messages)
            return {"response": response.content or "(无回复)"}
        except Exception as e:
            logger.error("Agent chat failed: %s", e)
            raise HTTPException(status_code=500, detail=f"LLM chat call failed: {e}")

    @app.get(
        "/settings/dashboard/market-data",
        dependencies=[Depends(require_local_or_auth)],
    )
    def get_dashboard_market_data():
        """Load real-time market data (watchlist, sectors, longhubang, limitup) for A-shares."""
        from src.swarm.market_board import (
            fetch_tencent_quotes,
            fetch_eastmoney_sectors,
            fetch_eastmoney_longhu,
            fetch_eastmoney_limitup,
            fetch_dynamic_yuzi,
            fetch_dynamic_portfolio,
            fetch_dynamic_kol_and_alerts,
            fetch_dynamic_lattice
        )
        from src.config.paths import active_tenant_var, get_runtime_root
        import sqlite3
        
        tenant = active_tenant_var.get() or "default"
        db_path = get_runtime_root() / f"stocks_{tenant}.db"
        
        watchlist_symbols = []
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Watchlist'")
                if cursor.fetchone():
                    cursor.execute("SELECT code FROM Watchlist")
                    watchlist_symbols = [row["code"] for row in cursor.fetchall()]
                conn.close()
            except Exception as e:
                logger.error("Failed to query Watchlist from DB: %s", e)
                
        if watchlist_symbols:
            cleaned_symbols = [s.split(".")[0].strip() for s in watchlist_symbols]
            cleaned_symbols = list(filter(None, dict.fromkeys(cleaned_symbols)))
        else:
            cleaned_symbols = ["300750", "600519", "002594", "301550", "601398"]

        try:
            watchlist = fetch_tencent_quotes(cleaned_symbols)
            sectors = fetch_eastmoney_sectors()
            longhu = fetch_eastmoney_longhu()
            limitup = fetch_eastmoney_limitup()
            
            yuzi = fetch_dynamic_yuzi()
            portfolio_data = fetch_dynamic_portfolio(tenant)
            kol_and_alerts = fetch_dynamic_kol_and_alerts(cleaned_symbols)
            lattice = fetch_dynamic_lattice()
            
            sentiment_score = 50
            up_count = sum(1 for s in sectors if s["change"] > 0)
            if sectors:
                sentiment_score = int((up_count / len(sectors)) * 100)
                
            return {
                "watchlist": watchlist,
                "sectors": sectors,
                "longhu": longhu,
                "limitup": limitup,
                "yuzi": yuzi,
                "portfolio": portfolio_data.get("positions", []),
                "netAsset": portfolio_data.get("netAsset", 0.0),
                "kol": kol_and_alerts.get("opinions", []),
                "alerts": kol_and_alerts.get("alerts", []),
                "lattice": lattice,
                "sentiment": {
                    "score": sentiment_score,
                    "description": "多头偏强" if sentiment_score > 60 else "空头偏强" if sentiment_score < 40 else "震荡平衡"
                }
            }
        except Exception as e:
            logger.error("Failed to load dashboard market data: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(
        "/settings/feature-flags",
        response_model=FeatureFlagsResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_feature_flags():
        """Return current feature flag state."""
        host_ref = _host()
        try:
            from src.api.scheduled_routes import _scheduled_research_scheduler_enabled
            scheduler_enabled = _scheduled_research_scheduler_enabled()
        except ImportError:
            scheduler_enabled = True

        shell_enabled = host_ref._env_shell_tools_enabled() if hasattr(host_ref, "_env_shell_tools_enabled") else False
        
        return FeatureFlagsResponse(
            shell_tools_enabled=shell_enabled,
            scheduler_enabled=scheduler_enabled,
            session_runtime_enabled=os.getenv("ENABLE_SESSION_RUNTIME", "true").lower() == "true",
            env_path=host_ref._project_relative_path(host_ref.ENV_PATH) if hasattr(host_ref, "_project_relative_path") else host_ref.ENV_PATH,
        )

    @app.get(
        "/settings/agent-config",
        response_model=AgentConfigTextResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_agent_config():
        """Read the raw agent.yaml config content."""
        from src.config.paths import get_config_path
        path = get_config_path()
        content = ""
        if path.exists():
            content = path.read_text(encoding="utf-8")
        else:
            content = """# TideTrading Agent Configuration File
# Configure global settings, MCP servers, and IM channels here.

# MCP Servers configurations:
# mcp_servers:
#   weather:
#     type: stdio
#     command: npx
#     args: ["-y", "@modelcontextprotocol/server-weather"]

# IM Channels configurations:
# channels:
#   send_progress: true
#   reply_timeout_s: 600
#   telegram:
#     enabled: false
#     token: "YOUR_TELEGRAM_BOT_TOKEN"
#     allow_from: ["YOUR_CHAT_ID"]
#   feishu:
#     enabled: false
#     app_id: "YOUR_FEISHU_APP_ID"
#     app_secret: "YOUR_FEISHU_APP_SECRET"
#   weixin:
#     enabled: false
#     token: "YOUR_WECHAT_ILINK_TOKEN"
"""
        return AgentConfigTextResponse(
            yaml_content=content,
            config_path=str(path),
        )

    @app.put(
        "/settings/agent-config",
        response_model=AgentConfigTextResponse,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_agent_config(payload: UpdateAgentConfigRequest):
        """Write the raw agent.yaml config content and reload runtime."""
        import yaml
        from src.config.paths import get_config_path
        from src.config.schema import AgentConfig
        
        try:
            parsed = yaml.safe_load(payload.yaml_content) or {}
            if not isinstance(parsed, dict):
                raise ValueError("YAML root must be an object")
            AgentConfig.model_validate(parsed)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration format: {e}")
        
        path = get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload.yaml_content, encoding="utf-8")
        
        import sys
        host_ref = _host()
        if host_ref and getattr(host_ref, "_channel_runtime", None) is not None:
            try:
                logger.info("Config changed, reloading channel runtime...")
                await host_ref._channel_runtime.stop()
                host_ref._channel_runtime = None
                host_ref._get_channel_runtime()
                if os.getenv("VIBE_TRADING_CHANNELS_AUTO_START", "").strip().lower() in {"1", "true", "yes"}:
                    await host_ref._start_channel_runtime()
            except Exception as ex:
                logger.exception("Failed to restart channel runtime after config update: %s", ex)
                
        return AgentConfigTextResponse(
            yaml_content=payload.yaml_content,
            config_path=str(path),
        )

    @app.get(
        "/settings/agent-config/json",
        response_model=dict,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_agent_config_json():
        """Read the agent.yaml config as a JSON object."""
        import yaml
        from src.config.paths import get_config_path
        path = get_config_path()
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                parsed = yaml.safe_load(content) or {}
                if not isinstance(parsed, dict):
                    parsed = {}
                return parsed
            except Exception as e:
                logger.error("Failed to parse agent.yaml: %s", e)
                return {}
        return {}

    @app.put(
        "/settings/agent-config/json",
        response_model=dict,
        dependencies=[Depends(require_settings_write_auth)],
    )
    async def update_agent_config_json(payload: dict):
        """Write the agent.yaml config from a JSON object and reload runtime."""
        import yaml
        from src.config.paths import get_config_path
        from src.config.schema import AgentConfig
        
        try:
            AgentConfig.model_validate(payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration format: {e}")
            
        path = get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        
        yaml_content = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        path.write_text(yaml_content, encoding="utf-8")
        
        import sys
        host_ref = _host()
        if host_ref and getattr(host_ref, "_channel_runtime", None) is not None:
            try:
                logger.info("Config changed via JSON API, reloading channel runtime...")
                await host_ref._channel_runtime.stop()
                host_ref._channel_runtime = None
                host_ref._get_channel_runtime()
                if os.getenv("VIBE_TRADING_CHANNELS_AUTO_START", "").strip().lower() in {"1", "true", "yes"}:
                    await host_ref._start_channel_runtime()
            except Exception as ex:
                logger.exception("Failed to restart channel runtime after JSON config update: %s", ex)
                
        return payload
