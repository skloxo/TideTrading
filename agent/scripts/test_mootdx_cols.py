from mootdx.quotes import Quotes

server_ip = '119.97.185.59'
server_port = 7709

try:
    client = Quotes.factory(market="std", timeout=10, server=(server_ip, server_port))
    res = client.finance(market=1, symbol="600519")
    for col in res.columns:
        print(f"Col {col}: {res.iloc[0][col]}")
    client.close()
except Exception as e:
    print("Failed:", e)
