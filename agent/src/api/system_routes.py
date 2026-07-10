import os
import re
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

_AGENT_DIR = Path(__file__).resolve().parent.parent.parent
_changelog_cache = {
    "zh": {"mtime": 0, "data": []},
    "en": {"mtime": 0, "data": []}
}

def _parse_readme_changelog(filepath: Path, max_entries: int = 5) -> list:
    if not filepath.exists():
        return []
    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        in_changelog = False
        entries = []
        current_entry = None
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## 📰 最新动态") or stripped.startswith("## 最新动态"):
                in_changelog = True
                continue
            elif in_changelog and stripped.startswith("## "):
                break
            elif in_changelog and stripped.startswith("---"):
                if entries:
                    break
            
            if in_changelog:
                m = re.match(r'^\s*[-\*]\s+\*\*(\d{4}-\d{2}-\d{2})\*\*\s+🚀\s+\*\*(v[\d\.]+)\s*—\s*(.*?)\*\*：?', line)
                if m:
                    if len(entries) >= max_entries:
                        break
                    date_str, ver_str, title_str = m.groups()
                    current_entry = {
                        "v": ver_str,
                        "date": date_str,
                        "title": title_str.strip(),
                        "body": []
                    }
                    entries.append(current_entry)
                elif current_entry is not None:
                    if line.strip():
                        subbed = re.sub(r'^\s*[-\*]\s+', '', line).rstrip()
                        cleaned_line = f"* {subbed}"
                        current_entry["body"].append(cleaned_line)
        
        formatted_entries = []
        for entry in entries:
            body_text = "\n".join(entry["body"])
            formatted_entries.append({
                "v": entry["v"],
                "date": entry["date"],
                "title": entry["title"],
                "body": body_text
            })
        return formatted_entries
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Failed to parse changelog from %s: %s", filepath, e)
        return []


# ---------------------------------------------------------------------------
# Pydantic models (defined locally -- NO shared modules, per maintainer rule)
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check payload."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Server timestamp")


class MonitorStatsResponse(BaseModel):
    """Service monitoring statistics."""
    active_tenants: List[Dict[str, Any]] = Field(default_factory=list)
    total_sessions: int
    total_runs: int
    memory_usage_mb: float
    services: Dict[str, Any] = Field(default_factory=dict)


class LogEntry(BaseModel):
    """Single log entry details."""
    timestamp: str
    level: str
    logger: str
    message: str


# ---------------------------------------------------------------------------
# Process termination
# ---------------------------------------------------------------------------


def _terminate_current_process() -> None:
    """Stop the current API process after the response has been sent."""
    time.sleep(0.25)
    os.kill(os.getpid(), signal.SIGTERM)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_system_routes(
    app: FastAPI,
    app_version: str | None = None,
) -> None:
    """Mount the system routes onto ``app``.

    Resolves ``_security``, ``_require_shutdown_authorization``, and
    ``APP_VERSION`` from the host ``api_server`` module via ``sys.modules``
    when not passed explicitly.
    """
    # Resolve host dependencies via sys.modules fallback
    import sys as _sys

    host = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")

    if host is None:
        raise RuntimeError(
            "register_system_routes: api_server module not in sys.modules; "
            "ensure api_server is imported before calling this function"
        )

    _security = host._security
    _require_shutdown_authorization = host._require_shutdown_authorization
    _app_version = app_version if app_version is not None else host.APP_VERSION
    require_admin = getattr(host, "require_admin", host.require_auth)

    def _get_terminate_process():
        """Late-access _terminate_current_process for test monkeypatch compat."""
        h = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")
        if h is not None:
            fn = getattr(h, "_terminate_current_process", None)
            if fn is not None:
                return fn
        return _terminate_current_process

    # --- Routes ---

    @app.get(
        "/admin/monitor/stats",
        response_model=MonitorStatsResponse,
        dependencies=[Depends(require_admin)],
    )
    async def get_monitor_stats():
        """Get service metrics, database runs, sessions, and active tenants."""
        # 1. Active tenants
        keys = host._load_tenant_keys()
        active_tenants = [
            {
                "tenant_id": k.get("tenant_id"),
                "name": k.get("name"),
                "created_at": k.get("created_at"),
                "is_active": k.get("is_active", True)
            }
            for k in keys
        ]
        
        # 2. Total sessions
        total_sessions = 0
        sessions_dir = getattr(host, "SESSIONS_DIR", None)
        if sessions_dir is None:
            try:
                sessions_dir = host._get_sessions_dir()
            except AttributeError:
                sessions_dir = None
        if sessions_dir and sessions_dir.exists():
            try:
                total_sessions = sum(1 for d in sessions_dir.iterdir() if d.is_dir())
            except Exception:
                pass
                
        # 3. Total runs
        total_runs = 0
        runs_dir = getattr(host, "RUNS_DIR", None)
        if runs_dir is None:
            try:
                runs_dir = host._get_runs_dir()
            except AttributeError:
                runs_dir = None
        if runs_dir and runs_dir.exists():
            try:
                total_runs = sum(1 for d in runs_dir.iterdir() if d.is_dir())
            except Exception:
                pass
                
        # 4. Memory usage
        memory_usage_mb = 0.0
        try:
            if os.path.exists("/proc/self/status"):
                with open("/proc/self/status", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                memory_usage_mb = float(parts[1]) / 1024.0
                                break
        except Exception:
            pass

        # 5. Service status info
        services_info = {}
        
        # 5.1 Data Maintenance
        try:
            from src.market.close_maintenance import CloseDataMaintenanceService
            from src.config.paths import get_market_db_path
            import sqlite3
            
            db_path = get_market_db_path()
            db_size_mb = 0.0
            if db_path.exists():
                db_size_mb = db_path.stat().st_size / (1024.0 * 1024.0)
                
            historical_range = "未开始"
            today_status = "待维护"
            total_stocks = 0
            # Per-dimension health metrics
            kline_rows = 0
            valuation_rows = 0
            capital_flow_rows = 0
            theme_rows = 0
            financial_rows = 0
            kline_last_date = None
            meta_coverage_pct = 0
            health_alerts: list = []
            
            if db_path.exists():
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM stock_meta")
                    total_stocks = cur.fetchone()[0]

                    cur.execute("SELECT COUNT(*) FROM kline_daily")
                    kline_rows = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM stock_valuation")
                    valuation_rows = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM capital_flow")
                    capital_flow_rows = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM theme_mapping")
                    theme_rows = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM financial_indicator")
                    financial_rows = cur.fetchone()[0]

                    cur.execute("SELECT MIN(date), MAX(date) FROM kline_daily")
                    min_d, max_d = cur.fetchone()
                    kline_last_date = max_d
                    if min_d and max_d:
                        historical_range = f"{min_d} ~ {max_d}"
                        
                        today_str = str(datetime.now().date())
                        cur.execute("SELECT MAX(date) FROM trade_calendar WHERE is_open = 1 AND date <= ?", (today_str,))
                        latest_trading_day = cur.fetchone()[0]
                        if latest_trading_day:
                            if max_d >= latest_trading_day:
                                today_status = "已完成"
                            else:
                                from datetime import time as dt_time
                                now_dt = datetime.now()
                                cur.execute("SELECT is_open FROM trade_calendar WHERE date = ?", (today_str,))
                                row = cur.fetchone()
                                is_today_open = row[0] if row else 0
                                
                                if is_today_open and now_dt.time() >= dt_time(15, 35):
                                    today_status = "同步延迟/失败"
                                else:
                                    today_status = "等待下午收盘"
                        else:
                            today_status = "未同步历法"

                    # Data health alerts
                    if total_stocks < 3000:
                        health_alerts.append(f"⚠ 股票元数据不足（{total_stocks} 条，应≥5000）")
                    if kline_rows < 1_000_000:
                        health_alerts.append(f"⚠ K线数据偏少（{kline_rows:,} 行，应≥900万）")
                    if valuation_rows < 100_000:
                        health_alerts.append(f"⚠ 估值数据不足（{valuation_rows:,} 行）")
                    if capital_flow_rows < 100_000:
                        health_alerts.append(f"⚠ 资金流数据不足（{capital_flow_rows:,} 行）")
                    if theme_rows < 5000:
                        health_alerts.append(f"⚠ 概念题材数据不足（{theme_rows:,} 行）")
                    if today_status == "同步延迟/失败":
                        health_alerts.append("🔴 今日收盘数据同步延迟或失败，请检查")
                    # Data freshness: kline last date vs latest trading day
                    if kline_last_date and latest_trading_day and kline_last_date < latest_trading_day:
                        days_behind = (
                            datetime.strptime(latest_trading_day, "%Y-%m-%d") -
                            datetime.strptime(kline_last_date, "%Y-%m-%d")
                        ).days
                        if days_behind > 3:
                            health_alerts.append(f"⚠ K线数据已落后 {days_behind} 天（最新：{kline_last_date}）")

                    # Coverage: what % of stocks in stock_meta have kline data
                    if total_stocks > 0 and kline_rows > 0:
                        cur.execute("SELECT COUNT(DISTINCT code) FROM kline_daily")
                        kline_stocks = cur.fetchone()[0]
                        meta_coverage_pct = round(kline_stocks / total_stocks * 100, 1)
                        if meta_coverage_pct < 80:
                            health_alerts.append(f"⚠ K线覆盖率仅 {meta_coverage_pct}%（{kline_stocks}/{total_stocks} 只股票有数据）")

                    conn.close()
                except Exception:
                    pass
                    
            maintenance_running = False
            try:
                maintenance_running = CloseDataMaintenanceService()._running
            except Exception:
                pass

            if not maintenance_running:
                health_alerts.append("🔴 收盘维护服务未运行（CloseDataMaintenanceService stopped）")
                
            services_info["data_maintenance"] = {
                "name": "收盘行情同步与 Gap Healing",
                "running": maintenance_running,
                "historical_range": historical_range,
                "today_status": today_status,
                "total_stocks": total_stocks,
                "db_size_mb": round(db_size_mb, 2),
                # Per-dimension health metrics
                "kline_rows": kline_rows,
                "valuation_rows": valuation_rows,
                "capital_flow_rows": capital_flow_rows,
                "theme_rows": theme_rows,
                "financial_rows": financial_rows,
                "kline_last_date": kline_last_date,
                "meta_coverage_pct": meta_coverage_pct,
                "health_alerts": health_alerts,
                "health_ok": len(health_alerts) == 0,
            }
        except Exception:
            pass


        # 5.2 THS Watchlist Sync
        try:
            from src.market.ths_sync import ThsSyncService
            ths_running = False
            try:
                ths_running = ThsSyncService()._running
            except Exception:
                pass
            services_info["ths_sync"] = {
                "name": "同花顺自选股双向同步",
                "running": ths_running
            }
        except Exception:
            pass

        # 5.3 Watchlist Monitor
        try:
            from src.market.watchlist_monitor import WatchlistMonitorService
            monitor_running = False
            try:
                monitor_running = WatchlistMonitorService()._running
            except Exception:
                pass
            services_info["watchlist_monitor"] = {
                "name": "自选股秒级高频预警",
                "running": monitor_running
            }
        except Exception:
            pass

        # 5.4 Xueqiu Combination Watcher
        try:
            xueqiu_running = False
            try:
                watcher = host._get_xueqiu_watcher()
                xueqiu_running = watcher is not None and watcher._task is not None and not watcher._task.done()
            except Exception:
                pass
            
            cached_count = 0
            if hasattr(app.state, "xueqiu_global_details_cache"):
                cached_count = len(app.state.xueqiu_global_details_cache)
                
            services_info["xueqiu_watcher"] = {
                "name": "雪球大V组合盯哨",
                "running": xueqiu_running,
                "cached_count": cached_count
            }
        except Exception:
            pass

        # 5.5 Swarm Multi-Agent Engine
        try:
            services_info["swarm_engine"] = {
                "name": "Swarm 智能体协作引擎",
                "running": True,
                "active_runtimes": len(host._swarm_runtime_cache)
            }
        except Exception:
            pass

        # 5.6 MCP Tool Gateway
        try:
            services_info["mcp_gateway"] = {
                "name": "MCP 外部组件网关",
                "running": True
            }
        except Exception:
            pass

        return MonitorStatsResponse(
            active_tenants=active_tenants,
            total_sessions=total_sessions,
            total_runs=total_runs,
            memory_usage_mb=memory_usage_mb,
            services=services_info,
        )

    @app.get(
        "/admin/monitor/logs",
        response_model=List[LogEntry],
        dependencies=[Depends(require_admin)],
    )
    async def get_monitor_logs(
        limit: int = Query(100, ge=1, le=1000),
        level: Optional[str] = Query(None),
        keyword: Optional[str] = Query(None),
    ):
        """Retrieve uvicorn root logs from the MemoryLogHandler."""
        return host.memory_log_handler.get_logs(limit=limit, level=level, keyword=keyword)

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Liveness probe."""
        return HealthResponse(
            status="healthy",
            service="TideTrading API",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @app.get("/correlation")
    async def get_correlation_matrix(
        codes: str = Query(..., description="Comma-separated asset codes, e.g. BTC-USDT,ETH-USDT,SPY"),
        days: int = Query(90, description="Lookback window in days", ge=7, le=365),
        method: str = Query("pearson", description="Correlation method: pearson or spearman"),
    ):
        """Compute cross-asset correlation matrix from daily returns.

        Fetches price data for each code via available data loaders,
        computes pairwise correlation of daily returns over the lookback window.
        """
        from backtest.correlation import compute_correlation_matrix

        code_list = [c.strip() for c in codes.split(",") if c.strip()]
        if len(code_list) < 2:
            raise HTTPException(status_code=400, detail="At least 2 asset codes required")
        if len(code_list) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 assets per request")
        if method not in ("pearson", "spearman"):
            raise HTTPException(status_code=400, detail="method must be 'pearson' or 'spearman'")

        try:
            result = compute_correlation_matrix(codes=code_list, days=days, method=method)
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Correlation computation failed: {exc}")

    @app.post("/system/shutdown")
    async def shutdown_local_api(
        background_tasks: BackgroundTasks,
        request: Request,
        cred: Optional[HTTPAuthorizationCredentials] = Security(_security),
    ):
        """Shut down the local API server after explicit local authorization."""
        _require_shutdown_authorization(request=request, cred=cred)
        client_host = request.client.host if request.client else ""
        if client_host not in {"127.0.0.1", "::1", "localhost"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Local access only")

        background_tasks.add_task(_get_terminate_process())
        return {
            "status": "shutting-down",
            "service": "TideTrading API",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/skills")
    async def list_skills():
        """List registered skills (name and description)."""
        from src.agent.skills import SkillsLoader

        loader = SkillsLoader()
        return [
            {
                "name": s.name,
                "description": s.description,
            }
            for s in loader.skills
        ]

    @app.get("/api")
    async def api_info():
        """Service metadata."""
        return {
            "service": "TideTrading API",
            "version": _app_version,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/api/system/changelog")
    async def get_system_changelog(lang: Optional[str] = Query(None, description="Language code: zh or en")):
        """Get the latest parsed system changelog entries from README files."""
        language = "zh"
        if lang:
            if "en" in lang.lower():
                language = "en"
        
        filename = "README_zh.md" if language == "zh" else "README.md"
        readme_path = _AGENT_DIR.parent / filename
        if not readme_path.exists() and language == "zh":
            readme_path = _AGENT_DIR.parent / "README.md"
        
        if not readme_path.exists():
            return {"changelog": []}
        
        try:
            mtime = os.path.getmtime(readme_path)
            cache = _changelog_cache[language]
            if cache["mtime"] != mtime or not cache["data"]:
                parsed_data = _parse_readme_changelog(readme_path)
                _changelog_cache[language] = {
                    "mtime": mtime,
                    "data": parsed_data
                }
            return {"changelog": _changelog_cache[language]["data"]}
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed to fetch changelog: %s", e)
            return {"changelog": []}
