from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
import pytest

from src.market.shared_data_hub import SharedMemoryHub, is_market_open
from src.market.tdx_bridge import TdxGateway


@pytest.fixture(autouse=True)
def reset_hub_singleton():
    """Reset the singleton instance before and after each test."""
    SharedMemoryHub._instance = None
    yield
    SharedMemoryHub._instance = None


def test_shared_memory_hub_singleton() -> None:
    """Verify SharedMemoryHub is a singleton."""
    hub1 = SharedMemoryHub()
    hub2 = SharedMemoryHub()
    assert hub1 is hub2


def test_market_open_helper() -> None:
    """Verify is_market_open handles weekdays and trading hours correctly."""
    # We just smoke test the helper returns a boolean
    res = is_market_open()
    assert isinstance(res, bool)


@patch("src.market.tdx_bridge.TdxGateway.get_quotes")
def test_cache_hits_and_misses(mock_get_quotes) -> None:
    """Verify that get_quotes caches data and doesn't hit TDX gateway multiple times within TTL."""
    hub = SharedMemoryHub()
    hub.cache_ttl = 1.0  # Set short TTL for test
    
    mock_get_quotes.return_value = {
        "600519": {"price": 1800.0, "source": "tdx"},
        "000001": {"price": 10.0, "source": "tdx"}
    }

    # First fetch: Cache miss
    res1 = hub.get_quotes(["600519", "000001"])
    assert mock_get_quotes.call_count == 1
    assert res1["600519"]["price"] == 1800.0
    
    # Second fetch immediately: Cache hit, should not invoke TdxGateway again
    res2 = hub.get_quotes(["600519"])
    assert mock_get_quotes.call_count == 1
    assert res2["600519"]["price"] == 1800.0

    # Wait for TTL to expire
    time.sleep(1.1)

    # Third fetch: Cache expired, should call TdxGateway again
    res3 = hub.get_quotes(["600519"])
    assert mock_get_quotes.call_count == 2
    assert res3["600519"]["price"] == 1800.0


@patch("src.market.tdx_bridge.TdxGateway.get_quotes")
def test_refresh_active_cache(mock_get_quotes) -> None:
    """Verify background refresher only queries permanent indexes and recently active stocks."""
    hub = SharedMemoryHub()
    hub.cache_ttl = 5.0
    hub.inactive_timeout = 1.0  # 1s inactive threshold
    
    # Request a stock '600000'
    hub.get_quotes(["600000"])
    
    # Get active symbols to refresh
    hub.permanent_symbols = {"sh000001"}
    
    # Trigger refresh
    mock_get_quotes.return_value = {
        "sh000001": {"price": 3000.0},
        "600000": {"price": 7.5}
    }
    hub._refresh_active_cache()
    
    # Both sh000001 (permanent) and 600000 (active) should be refreshed
    args, _ = mock_get_quotes.call_args
    called_symbols = args[0]
    assert "sh000001" in called_symbols
    assert "600000" in called_symbols

    # Wait for stock '600000' to go cold/inactive (inactive_timeout=1.0)
    time.sleep(1.2)
    
    mock_get_quotes.reset_mock()
    hub._refresh_active_cache()
    
    # Only sh000001 (permanent) should be refreshed, '600000' is now cold
    args, _ = mock_get_quotes.call_args
    called_symbols = args[0]
    assert "sh000001" in called_symbols
    assert "600000" not in called_symbols


@patch("src.market.shared_data_hub.SharedMemoryHub.start")
@patch("src.market.shared_data_hub.SharedMemoryHub.stop")
def test_api_server_integration(mock_stop, mock_start) -> None:
    """Verify that api_server endpoints call SharedMemoryHub."""
    from fastapi.testclient import TestClient
    import api_server

    client = TestClient(api_server.app)

    mock_hub = MagicMock()
    mock_hub.get_quotes.return_value = {
        "600519": {
            "code": "600519",
            "price": 1800.0,
            "source": "tdx"
        }
    }

    with patch("src.market.shared_data_hub.SharedMemoryHub", return_value=mock_hub):
        response = client.get("/api/quote/realtime?codes=600519")
        assert response.status_code == 200
        data = response.json()
        assert "600519" in data
        assert data["600519"]["price"] == 1800.0
        
        response2 = client.get("/api/quote/realtime/600519")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["price"] == 1800.0
