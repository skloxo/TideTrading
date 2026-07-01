import time
import pytest
from src.providers.key_pool import LLMKeyPoolManager


@pytest.fixture(autouse=True)
def clean_pool():
    manager = LLMKeyPoolManager()
    manager.clear()
    yield
    manager.clear()


def test_parse_keys():
    manager = LLMKeyPoolManager()
    keys = manager.get_keys("tenant_1", "openai", "key1, key2, key3")
    assert keys == ["key1", "key2", "key3"]


def test_round_robin_rotation():
    manager = LLMKeyPoolManager()
    raw_keys = "key1,key2,key3"
    
    # SUCCESSIVE calls should rotate
    k1 = manager.get_next_key("tenant_1", "openai", raw_keys)
    k2 = manager.get_next_key("tenant_1", "openai", raw_keys)
    k3 = manager.get_next_key("tenant_1", "openai", raw_keys)
    k4 = manager.get_next_key("tenant_1", "openai", raw_keys)
    
    assert k1 == "key1"
    assert k2 == "key2"
    assert k3 == "key3"
    assert k4 == "key1"  # wraps around


def test_key_cooling():
    manager = LLMKeyPoolManager()
    raw_keys = "key1,key2"
    
    # Initialize
    manager.get_keys("tenant_1", "openai", raw_keys)
    
    # Mark key1 cooling
    manager.mark_cooling("tenant_1", "openai", "key1", duration=10.0)
    
    # get_next_key should skip key1 and return key2
    assert manager.get_next_key("tenant_1", "openai", raw_keys) == "key2"
    assert manager.get_next_key("tenant_1", "openai", raw_keys) == "key2"


def test_key_cooling_auto_recovery():
    manager = LLMKeyPoolManager()
    raw_keys = "key1,key2"
    
    # Initialize
    manager.get_keys("tenant_1", "openai", raw_keys)
    
    # Mark key1 cooling for 0.05 seconds
    manager.mark_cooling("tenant_1", "openai", "key1", duration=0.05)
    
    # Immediately it should return key2
    assert manager.get_next_key("tenant_1", "openai", raw_keys) == "key2"
    
    # Sleep to let key1 recover
    time.sleep(0.06)
    
    # Now it should be able to return key1 again
    assert manager.get_next_key("tenant_1", "openai", raw_keys) == "key1"


def test_all_keys_cooling_fallback_and_sleep():
    manager = LLMKeyPoolManager()
    raw_keys = "key1,key2"
    
    # Initialize
    manager.get_keys("tenant_1", "openai", raw_keys)
    
    # Mark both cooling: key1 cools down in 0.1s, key2 in 10s
    manager.mark_cooling("tenant_1", "openai", "key1", duration=0.1)
    manager.mark_cooling("tenant_1", "openai", "key2", duration=10.0)
    
    start = time.time()
    # Should select key1 (earliest recovery) and wait for it to recover (0.1s)
    key = manager.get_next_key("tenant_1", "openai", raw_keys)
    elapsed = time.time() - start
    
    assert key == "key1"
    assert elapsed >= 0.08  # waited for key1 to recover
