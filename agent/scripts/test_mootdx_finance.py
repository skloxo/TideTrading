from mootdx.quotes import Quotes

server_ip = '119.97.185.59'
server_port = 7709

try:
    client = Quotes.factory(market="std", timeout=10, server=(server_ip, server_port))
    print("Methods:", [m for m in dir(client) if not m.startswith('_')])
    try:
        # standard standard-quotes client has finance info or quotes
        res = client.finance(market=1, symbol="600519")
        print("Finance Info Type:", type(res))
        print("Finance Info:")
        print(res)
    except Exception as e:
        print("Finance failed:", e)
    client.close()
except Exception as e:
    print("Connect failed:", e)
