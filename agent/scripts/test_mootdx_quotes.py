from mootdx.quotes import Quotes

server_ip = '119.97.185.59'
server_port = 7709

try:
    client = Quotes.factory(market="std", timeout=10, server=(server_ip, server_port))
    # query quotes for a batch of stocks using correct parameter 'symbol'
    res = client.quotes(symbol=["600519", "000001"])
    print("Type:", type(res))
    print("Columns:", list(res.columns) if hasattr(res, 'columns') else "No columns")
    if hasattr(res, 'to_dict') and len(res) > 0:
        for col in res.columns:
            print(f"Col {col}: {res.iloc[0][col]}")
    client.close()
except Exception as e:
    print("Failed:", e)
