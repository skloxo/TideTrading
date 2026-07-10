import sqlite3
from src.config.paths import _get_active_runtime_dir
import os
db = os.path.join(str(_get_active_runtime_dir()), 'stocks_market.db')
try:
    conn = sqlite3.connect(db)
    r = conn.execute('SELECT COUNT(*) FROM kline_daily').fetchone()
    print('Total daily K-line rows in stocks_market.db:', r[0])
    conn.close()
except Exception as e:
    print('DB check error:', e)
