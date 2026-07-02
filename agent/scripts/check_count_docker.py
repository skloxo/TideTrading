import sqlite3
db = '/home/vibe/.vibe-trading-cnx/stocks_market.db'
try:
    conn = sqlite3.connect(db)
    r = conn.execute('SELECT COUNT(*) FROM kline_daily').fetchone()
    print('Total daily K-line rows in stocks_market.db:', r[0])
    conn.close()
except Exception as e:
    print('DB check error:', e)
