#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
full_market_sync.py — 全量市场数据补齐脚本
==============================================
直接读取 tdx_a_shares.json（5156 只 A 股），对 stocks_market.db 执行：
  Phase 1 — stock_meta 全量写入（姓名+代码）
  Phase 2 — K 线增量补齐（从上次最新日期到今天）
  Phase 3 — 估值 + 资金流增量补齐
  Phase 4 — 概念题材全量刷新（theme_mapping）
  Phase 5 — 基本面（财务指标 + 分红 + 前十大股东）—— 仅周日跑或 --fundamentals

用法：
  docker exec tide-trading python3 /tmp/full_market_sync.py [--fundamentals] [--sentiment]

作者：Antigravity (自动生成)，v1.0  2026-07-10
"""
import os, sys, argparse, json, logging, time, sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# 设置 Python 路径
sys.path.insert(0, '/app/agent')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("full_market_sync")

# ==============================================================
# 参数
# ==============================================================
parser = argparse.ArgumentParser(description="Full market data sync for stocks_market.db")
parser.add_argument("--fundamentals", action="store_true", help="Also sync financial indicators/dividends/shareholders")
parser.add_argument("--sentiment", action="store_true", help="Also sync longhu/limit-up/northbound")
parser.add_argument("--years", type=int, default=1, help="Years of history to sync (default: 1)")
parser.add_argument("--max-stocks", type=int, default=0, help="Limit number of stocks (0=all, for testing)")
args = parser.parse_args()

# ==============================================================
# 路径 & DB
# ==============================================================
from src.config.paths import _get_active_runtime_dir, get_market_db_path, active_tenant_var
active_tenant_var.set("default")

RUNTIME_DIR = _get_active_runtime_dir()
DB_PATH = str(get_market_db_path())
TDX_JSON = RUNTIME_DIR / "tdx_a_shares.json"

logger.info(f"Runtime dir : {RUNTIME_DIR}")
logger.info(f"Market DB   : {DB_PATH}")
logger.info(f"TDX JSON    : {TDX_JSON}  exists={TDX_JSON.exists()}")

# ==============================================================
# Phase 0: Load stock list from TDX JSON (guaranteed 5000+)
# ==============================================================
if not TDX_JSON.exists():
    logger.error("tdx_a_shares.json not found! Cannot proceed.")
    sys.exit(1)

with open(TDX_JSON, 'r', encoding='utf-8') as f:
    tdx_data = json.load(f)
stocks = tdx_data.get('stocks', [])
logger.info(f"Phase 0 ✓ — Loaded {len(stocks)} stocks from TDX JSON")

if args.max_stocks > 0:
    stocks = stocks[:args.max_stocks]
    logger.info(f"  (limited to {len(stocks)} for testing)")

# ==============================================================
# Phase 1: stock_meta — upsert all stocks
# ==============================================================
logger.info(f"\n{'='*60}")
logger.info(f"Phase 1 — Writing stock_meta ({len(stocks)} stocks)...")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
for s in stocks:
    code = s['code']
    name = s['name']
    exchange = s.get('exchange', '')
    cur.execute(
        "INSERT OR IGNORE INTO stock_meta (code, name) VALUES (?, ?)",
        (code, name)
    )
    cur.execute(
        "UPDATE stock_meta SET name = ? WHERE code = ?",
        (name, code)
    )
conn.commit()
cur.execute("SELECT COUNT(*) FROM stock_meta")
count = cur.fetchone()[0]
logger.info(f"Phase 1 ✓ — stock_meta now has {count} rows")
conn.close()

# ==============================================================
# Phase 2 + 3: K线 + 估值 + 资金流 (增量)
# ==============================================================
logger.info(f"\n{'='*60}")
logger.info("Phase 2+3 — Running incremental K-line / valuation / capital_flow sync...")
logger.info("  (This calls initialize_history_data.py --all --years N with stock list pre-resolved)")
logger.info("  NOTE: Stock list is guaranteed via TDX JSON — no network needed for stock list.")

# 直接调用 initialize_history_data 的核心函数
from scripts.initialize_history_data import (
    backfill_kline,
    backfill_valuation,
    backfill_capital_flow,
    backfill_margin_trading,
    backfill_company_profile,
    backfill_all_theme_mappings,
    get_sync_dates,
    init_db,
    backfill_trade_calendar,
)

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=args.years * 365)).strftime('%Y-%m-%d')
logger.info(f"  Date range: {start_date} → {end_date}")

# Init DB tables
init_db(DB_PATH)
backfill_trade_calendar(DB_PATH, start_date, end_date)

# Tushare
ts_pro = None
ts_token = os.getenv("TUSHARE_TOKEN", "").strip()
if ts_token:
    try:
        import tushare as ts
        ts.set_token(ts_token)
        ts_pro = ts.pro_api()
        logger.info("  Tushare token loaded ✓")
    except Exception as e:
        logger.warning(f"  Tushare init failed: {e}")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

total = len(stocks)
for idx, stock in enumerate(stocks):
    code = stock['code']
    name = stock['name']

    if (idx + 1) % 50 == 0 or idx == 0:
        logger.info(f"  [{idx+1}/{total}] Processing {code} ({name})...")

    adjusted_start, is_synced = get_sync_dates(DB_PATH, code, start_date)

    if not is_synced:
        backfill_kline(DB_PATH, code, adjusted_start, end_date)

    backfill_valuation(DB_PATH, code, adjusted_start, end_date, ts_pro)
    backfill_capital_flow(DB_PATH, code, adjusted_start, end_date)
    backfill_margin_trading(DB_PATH, code, adjusted_start, end_date, ts_pro)
    backfill_company_profile(DB_PATH, code)

    if args.fundamentals:
        from scripts.initialize_history_data import (
            backfill_financial_indicator,
            backfill_dividends,
            backfill_top10_shareholders,
        )
        backfill_financial_indicator(DB_PATH, code)
        backfill_dividends(DB_PATH, code)
        backfill_top10_shareholders(DB_PATH, code)

    if args.sentiment:
        from scripts.initialize_history_data import (
            backfill_longhu_for_stock,
            backfill_north_bound,
        )
        backfill_longhu_for_stock(DB_PATH, code, adjusted_start, end_date)
        backfill_north_bound(DB_PATH, code, adjusted_start, end_date)

    time.sleep(0.2)  # throttle

conn.close()
logger.info("Phase 2+3 ✓ — K-line / valuation / capital_flow sync complete")

# ==============================================================
# Phase 4: Theme Mapping (概念题材)
# ==============================================================
logger.info(f"\n{'='*60}")
logger.info("Phase 4 — Refreshing theme_mapping (概念题材)...")
backfill_all_theme_mappings(DB_PATH)
logger.info("Phase 4 ✓ — theme_mapping refreshed")

# ==============================================================
# Phase 5: Sentiment (if --sentiment)
# ==============================================================
if args.sentiment:
    logger.info(f"\n{'='*60}")
    logger.info("Phase 5 — Backfilling limit-up board / sentiment...")
    from scripts.initialize_history_data import backfill_limit_up_by_date_range
    backfill_limit_up_by_date_range(DB_PATH, start_date, end_date)
    logger.info("Phase 5 ✓ — sentiment data complete")

# ==============================================================
# Final check
# ==============================================================
logger.info(f"\n{'='*60}")
logger.info("Final DB row counts:")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
for table in ['stock_meta','kline_daily','stock_valuation','capital_flow','theme_mapping',
              'financial_indicator','top10_shareholders','longhu_records','limit_up_records']:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    cnt = cur.fetchone()[0]
    logger.info(f"  {table}: {cnt:,}")
conn.close()
logger.info("\n✅ full_market_sync.py DONE")
