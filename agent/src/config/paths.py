"""Path helpers for agent-level structured config."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import contextvars

_DEFAULT_FILENAMES = ("agent.json", "agent.yaml", "agent.yml")

active_tenant_var = contextvars.ContextVar("active_tenant", default="default")
env_overrides_var = contextvars.ContextVar("env_overrides", default=None)


in_tenant_env_lookup = contextvars.ContextVar("in_tenant_env_lookup", default=False)


@lru_cache(maxsize=128)
def _read_tenant_env_file(env_path: Path, mtime: float) -> dict[str, str]:
    """Read active KEY=value entries from a dotenv file, cached by path and modification time."""
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    try:
        content = env_path.read_text(encoding="utf-8")
        for raw in content.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            if key:
                val = val.strip()
                if " #" in val:
                    val = val.split(" #", 1)[0].rstrip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in {"'", '"'}:
                    val = val[1:-1]
                values[key] = val.strip()
    except Exception:
        pass
    return values


def get_tenant_env_values(tenant: str) -> dict[str, str]:
    """Retrieve settings from the tenant-specific .env file."""
    if tenant == "default":
        return {}
    # Use standard tenant path structure derived from home
    tenant_dir = _get_active_runtime_dir() / "tenants" / tenant
    env_path = tenant_dir / ".env"
    if not env_path.exists():
        return {}
    try:
        mtime = env_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    return _read_tenant_env_file(env_path, mtime)


_NOT_FOUND = object()


def _get_tenant_env(key: str) -> object:
    """Retrieve the value of an environment variable under the active tenant context."""
    if in_tenant_env_lookup.get():
        return _NOT_FOUND
        
    token = in_tenant_env_lookup.set(True)
    try:
        # 1. Check in-memory overrides for the current task/request
        overrides = env_overrides_var.get()
        if overrides is not None and key in overrides:
            return overrides[key]
        
        # 2. Check cached tenant-specific .env file
        tenant = active_tenant_var.get()
        if tenant != "default":
            vals = get_tenant_env_values(tenant)
            if key in vals:
                return vals[key]
    finally:
        in_tenant_env_lookup.reset(token)
            
    return _NOT_FOUND


# Monkeypatch os.getenv and os.environ
import os
from functools import lru_cache

_orig_getenv = os.getenv


def tenant_getenv(key: str, default: str | None = None) -> str | None:
    # Support both prefixes (TT_ and VIBE_TRADING_)
    mapped_keys = [key]
    if key.startswith("VIBE_TRADING_"):
        mapped_keys.insert(0, key.replace("VIBE_TRADING_", "TT_", 1))
    elif key.startswith("TT_"):
        mapped_keys.append(key.replace("TT_", "VIBE_TRADING_", 1))

    for k in mapped_keys:
        val = _get_tenant_env(k)
        if val is not _NOT_FOUND:
            return val  # type: ignore

    for k in mapped_keys:
        val = _orig_getenv(k, _NOT_FOUND)
        if val is not _NOT_FOUND:
            return val  # type: ignore

    return default


os.getenv = tenant_getenv


_orig_getitem = os.environ.__class__.__getitem__
_orig_get = os.environ.__class__.get
_orig_contains = os.environ.__class__.__contains__
_orig_iter = os.environ.__class__.__iter__
_orig_len = os.environ.__class__.__len__
_orig_copy = os.environ.__class__.copy
_orig_pop = os.environ.__class__.pop
_orig_delitem = os.environ.__class__.__delitem__


def tenant_getitem(self, key: str) -> str:
    mapped_keys = [key]
    if key.startswith("VIBE_TRADING_"):
        mapped_keys.insert(0, key.replace("VIBE_TRADING_", "TT_", 1))
    elif key.startswith("TT_"):
        mapped_keys.append(key.replace("TT_", "VIBE_TRADING_", 1))

    for k in mapped_keys:
        val = _get_tenant_env(k)
        if val is not _NOT_FOUND:
            return val  # type: ignore

    for k in mapped_keys:
        try:
            return _orig_getitem(self, k)
        except KeyError:
            continue
            
    raise KeyError(key)


def tenant_get(self, key: str, default: str | None = None) -> str | None:
    mapped_keys = [key]
    if key.startswith("VIBE_TRADING_"):
        mapped_keys.insert(0, key.replace("VIBE_TRADING_", "TT_", 1))
    elif key.startswith("TT_"):
        mapped_keys.append(key.replace("TT_", "VIBE_TRADING_", 1))

    for k in mapped_keys:
        val = _get_tenant_env(k)
        if val is not _NOT_FOUND:
            return val  # type: ignore

    for k in mapped_keys:
        val = _orig_get(self, k, _NOT_FOUND)
        if val is not _NOT_FOUND:
            return val  # type: ignore

    return default


def tenant_contains(self, key: str) -> bool:
    mapped_keys = [key]
    if key.startswith("VIBE_TRADING_"):
        mapped_keys.insert(0, key.replace("VIBE_TRADING_", "TT_", 1))
    elif key.startswith("TT_"):
        mapped_keys.append(key.replace("TT_", "VIBE_TRADING_", 1))

    for k in mapped_keys:
        val = _get_tenant_env(k)
        if val is not _NOT_FOUND:
            return True
        if _orig_contains(self, k):
            return True
    return False


def tenant_iter(self):
    tenant = active_tenant_var.get()
    overrides = env_overrides_var.get()
    
    extra_keys = set()
    if overrides:
        extra_keys.update(overrides.keys())
    if tenant != "default":
        extra_keys.update(get_tenant_env_values(tenant).keys())
        
    if extra_keys:
        all_keys = set(_orig_iter(self)) | extra_keys
        return iter(all_keys)
    return _orig_iter(self)


def tenant_len(self) -> int:
    tenant = active_tenant_var.get()
    overrides = env_overrides_var.get()
    
    extra_keys = set()
    if overrides:
        extra_keys.update(overrides.keys())
    if tenant != "default":
        extra_keys.update(get_tenant_env_values(tenant).keys())
        
    if extra_keys:
        all_keys = set(_orig_iter(self)) | extra_keys
        return len(all_keys)
    return _orig_len(self)


def tenant_copy(self) -> dict[str, str]:
    return {k: self[k] for k in self}


_SENTINEL = object()

def tenant_pop(self, key, default=_SENTINEL):
    val = self.get(key, _NOT_FOUND)
    if val is not _NOT_FOUND:
        try:
            _orig_delitem(self, key)
        except KeyError:
            pass
        overrides = env_overrides_var.get()
        if overrides and key in overrides:
            overrides.pop(key, None)
        return val
    if default is not _SENTINEL:
        return default
    raise KeyError(key)


def tenant_delitem(self, key):
    try:
        _orig_delitem(self, key)
    except KeyError:
        pass
    overrides = env_overrides_var.get()
    if overrides and key in overrides:
        overrides.pop(key, None)


os.environ.__class__.__getitem__ = tenant_getitem
os.environ.__class__.get = tenant_get
os.environ.__class__.__contains__ = tenant_contains
os.environ.__class__.__iter__ = tenant_iter
os.environ.__class__.__len__ = tenant_len
os.environ.__class__.copy = tenant_copy
os.environ.__class__.pop = tenant_pop
os.environ.__class__.__delitem__ = tenant_delitem


def _get_active_runtime_dir() -> Path:
    import os
    if "PYTEST_CURRENT_TEST" in os.environ:
        return Path.home() / ".vibe-trading-cnx"
    old_dir = Path.home() / ".vibe-trading-cnx"
    old_upstream = Path.home() / ".vibe-trading"
    new_dir = Path.home() / ".tide-trading"
    
    if not new_dir.exists():
        if old_dir.exists():
            try:
                new_dir.symlink_to(old_dir)
            except Exception:
                return old_dir
        elif old_upstream.exists():
            try:
                new_dir.symlink_to(old_upstream)
            except Exception:
                return old_upstream
    return new_dir

def get_runtime_root(config_path: Path | None = None) -> Path:
    """Return the runtime root directory for user-level agent state.

    Args:
        config_path: Optional explicit config file path. When provided, the
            runtime root is derived from that file's parent directory.

    Returns:
        The directory containing the explicit structured config file when one
        is provided, otherwise the default ``~/.tide-trading`` runtime root,
        or a tenant-specific root under ``~/.tide-trading/tenants/<tenant>``.
    """
    if config_path is not None:
        return config_path.expanduser().parent
    tenant = active_tenant_var.get()
    base = _get_active_runtime_dir()
    if tenant == "default":
        return base
    return base / "tenants" / tenant


def get_market_db_path() -> Path:
    """Return the path to the SHARED public market database (stocks_market.db).

    This database contains all public A-share market data shared across ALL tenants:
      - kline_daily, kline_weekly (historical price/volume)
      - stock_meta, company_profile, theme_mapping, trade_calendar (reference data)
      - financial_* (fundamentals)
      - capital_flow, stock_valuation, margin_trading, north_bound_flow (capital)
      - longhu_records, limit_up_records (sentiment)
      - intraday_1min, intraday_5min (intraday cache, watched stocks only)

    There is ONE instance of this file regardless of how many tenants exist.
    Always lives under the default runtime root (~/.vibe-trading-cnx/).
    """
    base = _get_active_runtime_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / "stocks_market.db"


def get_tenant_db_path(tenant_id: str | None = None) -> Path:
    """Return the path to the PRIVATE per-tenant database.

    This database contains only user-private data:
      - Watchlist (self-selected stocks + metadata)
      - AlertRules (price/indicator alert rules)
      - positions (future: position records)

    Each tenant has their own independent copy.
    """
    tid = tenant_id or active_tenant_var.get() or "default"
    if tid == "default":
        root = _get_active_runtime_dir()
    else:
        root = _get_active_runtime_dir() / "tenants" / tid
    root.mkdir(parents=True, exist_ok=True)
    return root / f"stocks_{tid}.db"



def get_config_candidates(config_path: Path | None = None) -> list[Path]:
    """Return supported config path candidates in lookup order.

    Returns:
        Candidate config paths ordered by lookup priority. When an explicit
        config path is provided, only that path is returned.
    """
    if config_path is not None:
        return [config_path.expanduser()]
    root = get_runtime_root()
    return [root / filename for filename in _DEFAULT_FILENAMES]


def get_config_path(config_path: Path | None = None) -> Path:
    """Return the active config file path.

    Prefers the first existing candidate. If an explicit path is provided,
    returns that path directly. If no candidate exists yet, returns the
    recommended default JSON path.

    Args:
        config_path: Optional explicit config file path.

    Returns:
        The selected config file path for the current runtime context.
    """
    candidates = get_config_candidates(config_path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def get_data_dir(config_path: Path | None = None) -> Path:
    """Return and create the runtime data directory derived from config path.

    Args:
        config_path: Optional explicit config file path.

    Returns:
        The directory containing the active config file. The directory is
        created when it does not already exist.
    """
    data_dir = get_config_path(config_path).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_sessions_dir() -> Path:
    """Return the sessions directory for the active tenant."""
    tenant = active_tenant_var.get()
    if tenant == "default":
        return Path(__file__).resolve().parents[2] / "sessions"
    return get_runtime_root() / "sessions"


def get_runs_dir() -> Path:
    """Return the runs directory for the active tenant."""
    tenant = active_tenant_var.get()
    if tenant == "default":
        return Path(__file__).resolve().parents[2] / "runs"
    return get_runtime_root() / "runs"


def get_uploads_dir() -> Path:
    """Return the uploads directory for the active tenant."""
    tenant = active_tenant_var.get()
    if tenant == "default":
        return Path(__file__).resolve().parents[2] / "uploads"
    return get_runtime_root() / "uploads"


def get_workspace_path() -> Path:
    """Return the workspace path for channel state data.

    For channel adapters that need to persist state (e.g. conversation
    references, auth tokens), this returns ``~/.tide-trading/workspace``.
    """
    p = get_runtime_root() / "workspace"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_research_ledger_path() -> Path:
    """Return the path to the research ledger database."""
    base = _get_active_runtime_dir()
    return base / "research-ledger" / "ledger.sqlite"


def get_research_protocols_dir() -> Path:
    """Return the path to the research protocols directory."""
    base = _get_active_runtime_dir()
    return base / "research-protocols"


def get_artifacts_dir() -> Path:
    """Return the path to the artifacts directory."""
    base = _get_active_runtime_dir()
    return base / "artifacts"


def get_feishu_channels_config_path() -> Path:
    """Return the path to the Feishu channels configuration file."""
    base = _get_active_runtime_dir()
    return base / "feishu_channels.json"


def get_shadow_accounts_dir() -> Path:
    """Return the path to the shadow accounts directory."""
    base = _get_active_runtime_dir()
    return base / "shadow_accounts"


def get_shadow_runs_dir() -> Path:
    """Return the path to the shadow runs directory."""
    base = _get_active_runtime_dir()
    return base / "shadow_runs"


def get_shadow_reports_dir() -> Path:
    """Return the path to the shadow reports directory."""
    base = _get_active_runtime_dir()
    return base / "shadow_reports"


def get_user_skills_dir() -> Path:
    """Return the path to the user skills directory."""
    base = _get_active_runtime_dir()
    return base / "skills" / "user"


def get_hypotheses_path() -> Path:
    """Return the path to the hypotheses registry file."""
    base = _get_active_runtime_dir()
    return base / "hypotheses.json"


def get_pairing_path() -> Path:
    """Return the path to the pairing configuration file."""
    base = _get_active_runtime_dir()
    return base / "pairing.json"


def get_connector_settings_path(connector_name: str) -> Path:
    """Return the path to the settings file for a specific broker connector."""
    base = _get_active_runtime_dir()
    return base / f"{connector_name}.json"
