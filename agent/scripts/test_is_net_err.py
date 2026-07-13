import requests

try:
    # Trigger a connection error by accessing a fake domain
    requests.get("https://this-domain-does-not-exist-at-all-1234.com", timeout=2)
except Exception as e:
    err_str = str(e).lower()
    print("Error string:", err_str)
    terms = ("connection", "timeout", "disconnected", "remote end closed", "aborted", "rate limit", "time out")
    is_net_err = any(term in err_str for term in terms)
    print("Is net err:", is_net_err)
    print("Terms matched:", [t for t in terms if t in err_str])
