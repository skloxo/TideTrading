#!/usr/bin/env python3
"""
export_seed_db.py — 从运行时数据库导出种子数据库快照

导出内容（仅静态元数据）:
  - stock_meta       : 全市场股票基础信息（代码、名称、行业）
  - theme_mapping    : 题材/概念/行业成分映射
  - trade_calendar   : A股交易日历

不导出（运行时动态数据）:
  - kline_daily / kline_weekly / stock_valuation / capital_flow / margin_trading
  - Watchlist / AlertRules（租户私有数据，绝对不进 seed）

用法:
  python3 scripts/export_seed_db.py
  python3 scripts/export_seed_db.py --source /path/to/stocks_default.db --output data/stocks_seed.db
"""
import argparse
import logging
import os
import shutil
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export_seed_db")

# Tables to include in the seed database (static/semi-static only)
# Dynamic tables (kline_daily, capital_flow, etc.) stay in runtime DB only
SEED_TABLES = [
    "stock_meta",        # All A-share stock names, industry, listing date
    "theme_mapping",     # Industry/concept/theme mappings (updates ~quarterly)
    "trade_calendar",    # Trading calendar (updates annually)
    "company_profile",   # Company overview (relatively static, updates ~annually)
]

# Schema DDL for seed tables (copied from initialize_history_data.py to stay consistent)
SEED_SCHEMAS = {
    "stock_meta": """
        CREATE TABLE IF NOT EXISTS stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            list_date TEXT
        );
    """,
    "theme_mapping": """
        CREATE TABLE IF NOT EXISTS theme_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            theme_type TEXT NOT NULL,
            theme_name TEXT NOT NULL,
            UNIQUE(code, theme_type, theme_name)
        );
    """,
    "trade_calendar": """
        CREATE TABLE IF NOT EXISTS trade_calendar (
            date TEXT PRIMARY KEY,
            is_open INTEGER DEFAULT 1
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
}

SEED_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_stock_meta_code ON stock_meta(code);",
    "CREATE INDEX IF NOT EXISTS idx_theme_code ON theme_mapping(code);",
    "CREATE INDEX IF NOT EXISTS idx_theme_name ON theme_mapping(theme_name);",
    "CREATE INDEX IF NOT EXISTS idx_company_profile_code ON company_profile(code);",
]


def find_source_db() -> Path:
    """Find the best available source database."""
    from src.config.paths import _get_active_runtime_dir
    base = _get_active_runtime_dir()
    home = Path.home()
    candidates = [
        base / "stocks_default.db",
        base / "stocks.db",
        home / ".tide-trading" / "stocks_default.db",
        home / ".vibe-trading-cnx" / "stocks_default.db",
        home / ".vibe-trading" / "stocks_default.db",
        home / ".vibe-trading-cnx" / "stocks.db",
    ]
    for path in candidates:
        if path.exists():
            logger.info("Found source database: %s", path)
            return path
    logger.error("No source database found. Run initialize_history_data.py first.")
    sys.exit(1)


def get_table_row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except Exception:
        return 0


def export_seed_db(source_path: Path, output_path: Path) -> None:
    """Export seed database from source runtime database."""
    logger.info("=== Vibe-Trading Seed DB Export ===")
    logger.info("Source : %s", source_path)
    logger.info("Output : %s", output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing seed DB
    if output_path.exists():
        logger.info("Removing existing seed database...")
        output_path.unlink()

    # Connect to source
    src_conn = sqlite3.connect(str(source_path))
    src_conn.row_factory = sqlite3.Row

    # Create seed database
    dst_conn = sqlite3.connect(str(output_path))
    dst_conn.execute("PRAGMA journal_mode=WAL;")
    dst_conn.execute("PRAGMA synchronous=NORMAL;")

    total_exported = 0

    for table in SEED_TABLES:
        # Check source row count
        src_count = get_table_row_count(src_conn, table)
        if src_count == 0:
            logger.warning("Table %s is EMPTY in source — skipping (run initialize_history_data.py first)", table)
            continue

        # Create table in seed DB
        dst_conn.execute(SEED_SCHEMAS[table])
        dst_conn.commit()

        # Batch copy rows
        logger.info("Copying table %s (%d rows)...", table, src_count)
        rows = src_conn.execute(f"SELECT * FROM {table}").fetchall()
        if rows:
            cols = [d[0] for d in src_conn.execute(f"SELECT * FROM {table} LIMIT 1").description]
            placeholders = ",".join("?" for _ in cols)
            col_str = ",".join(cols)
            dst_conn.executemany(
                f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})",
                [tuple(r) for r in rows]
            )
            dst_conn.commit()
            total_exported += len(rows)
            logger.info("  ✓ Exported %d rows from %s", len(rows), table)

    # Create indexes
    for idx_sql in SEED_INDEXES:
        try:
            dst_conn.execute(idx_sql)
        except Exception:
            pass
    dst_conn.commit()

    # VACUUM to compact the file
    logger.info("Running VACUUM to compact seed database...")
    dst_conn.execute("VACUUM;")
    dst_conn.close()
    src_conn.close()

    # Report
    size_mb = output_path.stat().st_size / 1024 / 1024
    logger.info("")
    logger.info("=== Export Complete ===")
    logger.info("Total rows exported : %d", total_exported)
    logger.info("Seed DB size        : %.1f MB", size_mb)
    logger.info("Output path         : %s", output_path)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Rebuild Docker image: docker compose --profile dev build")
    logger.info("  2. The seed DB will be baked into the image via Dockerfile COPY")
    logger.info("  3. bootstrap_db.py runs automatically on first container startup")


def main():
    parser = argparse.ArgumentParser(description="Export Vibe-Trading seed database")
    parser.add_argument("--source", type=str, help="Path to source runtime database")
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).parent.parent.parent / "data" / "stocks_seed.db"),
        help="Path to output seed database (default: data/stocks_seed.db)",
    )
    args = parser.parse_args()

    source_path = Path(args.source) if args.source else find_source_db()
    output_path = Path(args.output)

    export_seed_db(source_path, output_path)


if __name__ == "__main__":
    main()
