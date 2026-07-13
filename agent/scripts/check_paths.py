import sys
sys.path.insert(0, '/app/agent')
from src.config.paths import _get_active_runtime_dir
d = _get_active_runtime_dir()
print('Runtime dir:', d)
p = d / 'tdx_a_shares.json'
print('tdx path:', p)
print('exists:', p.exists())
