#!/usr/bin/env python3
"""
check_db_status.py — 检查数据库各表数据状态
可在容器内运行: docker exec vibe-trading-dev python3 /tmp/check_db_status.py
"""
import os
import sqlite3
from pathlib import Path

db = '/home/vibe/.vibe-trading-cnx/stocks_default.db'
if not os.path.exists(db):
    print(f'DB not found at {db}')
    exit(1)

conn = sqlite3.connect(db)

# 所有表按维度分组显示
DIMENSION_TABLES = {
    "🏷️  基础身份 (Identity / Seed)": [
        "stock_meta", "theme_mapping", "trade_calendar", "company_profile",
    ],
    "📈  行情数据 (Price/Volume)": [
        "kline_daily", "kline_weekly",
    ],
    "💰  基本面 (Fundamentals)": [
        "stock_valuation", "financial_income", "financial_balance",
        "financial_cashflow", "financial_indicator",
        "top10_shareholders", "dividend_records",
    ],
    "🔥  资金面 (Capital Flow)": [
        "capital_flow", "margin_trading", "north_bound_flow", "block_trade",
    ],
    "🧠  情绪面 (Sentiment)": [
        "longhu_records", "limit_up_records",
    ],
    "🔒  用户私有 (Tenant Private)": [
        "Watchlist", "AlertRules",
    ],
}

all_tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
).fetchall()]

shown = set()
total_rows = 0

for dim, tables in DIMENSION_TABLES.items():
    print(f"\n{dim}")
    print("  " + "-" * 42)
    for t in tables:
        if t in all_tables:
            try:
                count = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                status = "✅" if count > 0 else "⚠️ "
                print(f"  {status}  {t:<28} {count:>10,}")
                total_rows += count
                shown.add(t)
            except Exception as e:
                print(f"  ❌  {t:<28} ERROR: {e}")
        else:
            print(f"  ➕  {t:<28} {'(not created yet)':>14}")

# Any unlisted tables
extra = [t for t in all_tables if t not in shown]
if extra:
    print("\n📋  其他表 (Other)")
    print("  " + "-" * 42)
    for t in extra:
        count = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"       {t:<28} {count:>10,}")
        total_rows += count

conn.close()

size_mb = os.path.getsize(db) / 1024 / 1024
print(f"\n{'=' * 46}")
print(f"  DB 文件大小: {size_mb:.1f} MB")
print(f"  总行数:      {total_rows:,}")
print(f"  路径:        {db}")
print(f"{'=' * 46}\n")

# Phase 1 completion check
phase1_tables = ["stock_meta", "theme_mapping", "kline_daily", "capital_flow",
                 "company_profile", "financial_indicator", "longhu_records", "limit_up_records"]
missing = []
conn2 = sqlite3.connect(db)
for t in phase1_tables:
    try:
        c = conn2.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        if c == 0:
            missing.append(t)
    except Exception:
        missing.append(t)
conn2.close()

if missing:
    print(f"⏳  Phase 1 数据还在初始化中，以下表尚未填充: {', '.join(missing)}")
    print(f"    等待后台 initialize_history_data.py 完成...")
else:
    print(f"🎉  Phase 1 数据全部就绪！可执行种子库导出:")
    print(f"    docker cp stocks_seed.db vibe-trading-dev:/tmp/ (反向)")
    print(f"    或: python3 agent/scripts/export_seed_db.py")
