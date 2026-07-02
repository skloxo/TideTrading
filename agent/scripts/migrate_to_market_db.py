#!/usr/bin/env python3
"""
migrate_to_market_db.py — 一次性迁移脚本
将公共市场数据从 stocks_default.db 迁移到 stocks_market.db（共享公开层）。
"""
import logging
import shutil
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('migrate_to_market_db')

MARKET_TABLES = [
    'stock_meta', 'theme_mapping', 'trade_calendar', 'company_profile',
    'kline_daily', 'kline_weekly', 'kline_monthly', 'kline_yearly',
    'stock_valuation', 'financial_income', 'financial_balance', 'financial_cashflow',
    'financial_indicator', 'top10_shareholders', 'dividend_records',
    'capital_flow', 'margin_trading', 'north_bound_flow', 'block_trade',
    'longhu_records', 'limit_up_records',
    'intraday_1min', 'intraday_5min', 'intraday_15min', 'intraday_30min', 'intraday_60min',
]


def get_existing_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def migrate(src_path, dst_path):
    logger.info('='*60)
    logger.info('Vibe-Trading DB Two-Layer Architecture Migration')
    logger.info(f'  Source (stocks_default.db): {src_path}')
    logger.info(f'  Target (stocks_market.db) : {dst_path}')
    logger.info('='*60)

    if not src_path.exists():
        logger.error(f'Source DB not found: {src_path}')
        sys.exit(1)

    backup = src_path.with_suffix('.db.bak')
    logger.info(f'Backing up source -> {backup}')
    shutil.copy2(str(src_path), str(backup))

    src = sqlite3.connect(str(src_path))
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(str(dst_path))
    dst.execute('PRAGMA journal_mode=WAL')
    dst.execute('PRAGMA synchronous=NORMAL')

    src_tables = get_existing_tables(src)
    total_rows = 0

    for table in MARKET_TABLES:
        if table not in src_tables:
            logger.debug(f'  [SKIP] {table} - not in source DB')
            continue

        schema_row = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not schema_row or not schema_row[0]:
            continue

        schema = schema_row[0]
        dst.execute(schema.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS'))

        # Copy indexes
        for idx in src.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
            (table,)
        ).fetchall():
            try:
                idx_sql = idx[0]
                idx_sql = idx_sql.replace('CREATE INDEX', 'CREATE INDEX IF NOT EXISTS')
                idx_sql = idx_sql.replace('CREATE UNIQUE INDEX', 'CREATE UNIQUE INDEX IF NOT EXISTS')
                dst.execute(idx_sql)
            except Exception:
                pass

        count = src.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        if count == 0:
            logger.info(f'  [SKIP] {table} - 0 rows')
            continue

        logger.info(f'  [COPY] {table}: {count:,} rows...')
        rows = src.execute(f'SELECT * FROM {table}').fetchall()
        desc = src.execute(f'SELECT * FROM {table} LIMIT 1').description
        cols = [d[0] for d in desc]
        placeholders = ','.join('?' for _ in cols)
        col_str = ','.join(cols)
        dst.executemany(
            f'INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})',
            [tuple(r) for r in rows]
        )
        dst.commit()
        total_rows += count
        logger.info(f'  [DONE] {table}: {count:,} rows')

    dst.execute('VACUUM')
    dst.close()
    src.close()

    dst_size = dst_path.stat().st_size / 1024 / 1024
    logger.info('')
    logger.info(f'Migration complete! Total rows: {total_rows:,}, stocks_market.db: {dst_size:.1f} MB')


def main():
    base = Path.home() / '.vibe-trading-cnx'
    src_path = base / 'stocks_default.db'
    dst_path = base / 'stocks_market.db'
    if dst_path.exists() and dst_path.stat().st_size > 1024 * 1024:
        logger.info(f'stocks_market.db already exists ({dst_path.stat().st_size/1024/1024:.1f} MB). Skipping.')
        return
    migrate(src_path, dst_path)


if __name__ == '__main__':
    main()
