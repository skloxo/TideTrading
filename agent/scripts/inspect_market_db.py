import sqlite3

db = '/home/tide/.tide-trading/stocks_market.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)
for t in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        cnt = cur.fetchone()[0]
        print(f'  {t}: {cnt} rows')
    except Exception as e:
        print(f'  {t}: ERROR {e}')
conn.close()
