import json
f = '/home/tide/.tide-trading/tdx_a_shares.json'
d = json.load(open(f))
stocks = d.get('stocks', [])
print('Stock count:', len(stocks))
print('Sample:', stocks[:3])
print('Updated:', d.get('updated', 'N/A'))
