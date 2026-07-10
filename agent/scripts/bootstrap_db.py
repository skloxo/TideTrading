#!/usr/bin/env python3
"""
bootstrap_db.py — 容器首次启动时检查并初始化运行时数据库

逻辑:
  1. 检查运行时 DB 是否存在且 stock_meta 有数据
  2. 若为空 → 从镜像内置的 /app/data/stocks_seed.db 复制基础元数据
  3. 在后台触发 close_maintenance 补充 kline_daily 等运行时动态数据

用法 (由 Docker entrypoint 调用):
  python3 scripts/bootstrap_db.py
  python3 scripts/bootstrap_db.py --force  # 强制重新从 seed 初始化
"""
import argparse
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [bootstrap] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("bootstrap_db")

SEED_DB_PATH = Path("/app/data/stocks_seed.db")
SEED_TABLES = ["stock_meta", "theme_mapping", "trade_calendar"]


def get_runtime_db_path() -> Path:
    """Resolve the runtime database path using the project config."""
    try:
        sys.path.insert(0, "/app/agent")
        from src.config.paths import get_tenant_db_path
        return get_tenant_db_path("default")
    except Exception:
        home = Path.home()
        return home / ".tide-trading" / "stocks_default.db"


def is_db_initialized(db_path: Path) -> bool:
    """Check if the runtime DB has meaningful stock_meta data."""
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "stock_meta" not in tables:
            conn.close()
            return False
        count = conn.execute("SELECT COUNT(*) FROM stock_meta").fetchone()[0]
        conn.close()
        return count >= 10  # Meaningful threshold: at least 10 stocks
    except Exception:
        return False


def copy_seed_tables(seed_path: Path, runtime_path: Path) -> int:
    """Copy static tables from seed DB to runtime DB. Returns total rows copied."""
    logger.info("Copying seed tables from %s → %s", seed_path, runtime_path)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)

    seed_conn = sqlite3.connect(str(seed_path))
    seed_conn.row_factory = sqlite3.Row

    runtime_conn = sqlite3.connect(str(runtime_path))
    runtime_conn.execute("PRAGMA journal_mode=WAL;")

    total_rows = 0
    for table in SEED_TABLES:
        try:
            # Ensure table exists in runtime DB (get schema from seed)
            schema_row = seed_conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'"
            ).fetchone()
            if not schema_row:
                continue
            runtime_conn.execute(schema_row[0])

            rows = seed_conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                logger.warning("Seed table %s is empty, skipping.", table)
                continue

            cols = [d[0] for d in seed_conn.execute(f"SELECT * FROM {table} LIMIT 1").description]
            col_str = ",".join(cols)
            placeholders = ",".join("?" for _ in cols)
            runtime_conn.executemany(
                f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})",
                [tuple(r) for r in rows]
            )
            runtime_conn.commit()
            total_rows += len(rows)
            logger.info("  ✓ %s: %d rows copied", table, len(rows))
        except Exception as e:
            logger.warning("  ✗ Failed to copy table %s: %s", table, e)

    # Copy any indexes from seed
    try:
        indexes = seed_conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
        ).fetchall()
        for (idx_sql,) in indexes:
            try:
                runtime_conn.execute(idx_sql)
            except Exception:
                pass
        runtime_conn.commit()
    except Exception:
        pass

    seed_conn.close()
    runtime_conn.close()
    return total_rows


def trigger_background_maintenance(runtime_db_path: Path) -> None:
    """Fire-and-forget close_maintenance to fill kline_daily in background."""
    script = Path("/app/agent/scripts/initialize_history_data.py")
    if not script.exists():
        logger.warning("initialize_history_data.py not found, skipping background init.")
        return
    try:
        logger.info("Triggering background close_maintenance to fill kline_daily...")
        subprocess.Popen(
            [sys.executable, str(script), "--tenant", "default", "--years", "1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Background data initialization started (runs concurrently with app).")
    except Exception as e:
        logger.warning("Could not start background data init: %s", e)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Vibe-Trading runtime database.")
    parser.add_argument("--force", action="store_true", help="Force re-init even if DB already has data.")
    parser.add_argument("--no-background", action="store_true", help="Skip background kline maintenance trigger.")
    args = parser.parse_args()

    runtime_db = get_runtime_db_path()
    logger.info("Runtime DB path: %s", runtime_db)

    if not args.force and is_db_initialized(runtime_db):
        logger.info("Runtime DB already initialized (%s). Skipping bootstrap.", runtime_db)
        return

    if not SEED_DB_PATH.exists():
        logger.warning(
            "Seed DB not found at %s. Skipping seed copy. "
            "The app will initialize data on first startup via close_maintenance.",
            SEED_DB_PATH
        )
    else:
        total = copy_seed_tables(SEED_DB_PATH, runtime_db)
        logger.info("Bootstrap complete: %d rows copied from seed DB.", total)

    if not args.no_background:
        trigger_background_maintenance(runtime_db)

    logger.info("Bootstrap finished successfully.")


if __name__ == "__main__":
    main()
