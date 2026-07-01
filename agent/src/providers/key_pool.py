import time
import threading
from typing import Dict, List, Optional, Tuple


class KeyState:
    def __init__(self, key: str):
        self.key = key
        self.status = "active"  # active / cooling
        self.cool_down_until = 0.0

    def is_available(self) -> bool:
        if self.status == "cooling":
            if time.time() >= self.cool_down_until:
                self.status = "active"
                return True
            return False
        return True


class LLMKeyPoolManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LLMKeyPoolManager, cls).__new__(cls)
                cls._instance._pools = {}  # (tenant_id, provider) -> List[KeyState]
                cls._instance._rr_index = {}  # (tenant_id, provider) -> int
                cls._instance._state_lock = threading.Lock()
        return cls._instance

    def get_keys(self, tenant_id: str, provider: str, raw_key_str: str) -> List[str]:
        """Parse comma-separated key string and initialize or sync key states for a provider."""
        if not raw_key_str:
            return []
        
        # Clean and split
        raw_keys = [k.strip() for k in raw_key_str.split(",") if k.strip()]
        
        pool_key = (tenant_id, provider)
        with self._state_lock:
            if pool_key not in self._pools:
                self._pools[pool_key] = [KeyState(k) for k in raw_keys]
                self._rr_index[pool_key] = 0
            else:
                # Merge keys to preserve state of unchanged keys
                existing_pool = self._pools[pool_key]
                existing_keys = {ks.key: ks for ks in existing_pool}
                new_pool = []
                for k in raw_keys:
                    if k in existing_keys:
                        new_pool.append(existing_keys[k])
                    else:
                        new_pool.append(KeyState(k))
                self._pools[pool_key] = new_pool
                # Reset index if out of bounds
                if self._rr_index[pool_key] >= len(new_pool):
                    self._rr_index[pool_key] = 0
                    
            return [ks.key for ks in self._pools[pool_key]]

    def get_next_key(self, tenant_id: str, provider: str, raw_key_str: str) -> Optional[str]:
        """Get the next available (non-cooling) key for the provider using Round Robin.
        If all keys are cooling, waits for the earliest cooling key up to 10 seconds.
        """
        keys = self.get_keys(tenant_id, provider, raw_key_str)
        if not keys:
            return None
            
        pool_key = (tenant_id, provider)
        wait_time = 0.0
        target_key = None
        
        with self._state_lock:
            pool = self._pools[pool_key]
            idx = self._rr_index[pool_key]
            
            n = len(pool)
            for i in range(n):
                check_idx = (idx + i) % n
                if pool[check_idx].is_available():
                    self._rr_index[pool_key] = (check_idx + 1) % n
                    return pool[check_idx].key
                    
            # If all keys are cooling, fallback to the one that cools down earliest
            earliest_idx = 0
            min_cool_down = float("inf")
            for i, ks in enumerate(pool):
                if ks.cool_down_until < min_cool_down:
                    min_cool_down = ks.cool_down_until
                    earliest_idx = i
            
            ks = pool[earliest_idx]
            target_key = ks.key
            self._rr_index[pool_key] = (earliest_idx + 1) % n
            wait_time = max(0.0, ks.cool_down_until - time.time())
            
        if wait_time > 0.0:
            # Wait up to 10s
            sleep_duration = min(wait_time, 10.0)
            time.sleep(sleep_duration)
            
        return target_key

    def mark_cooling(self, tenant_id: str, provider: str, key: str, duration: float = 60.0) -> None:
        """Mark a key as cooling down for a certain duration."""
        pool_key = (tenant_id, provider)
        with self._state_lock:
            pool = self._pools.get(pool_key, [])
            for ks in pool:
                if ks.key == key:
                    ks.status = "cooling"
                    ks.cool_down_until = time.time() + duration
                    break

    def clear(self) -> None:
        """Clear all pools (primarily for testing)."""
        with self._state_lock:
            self._pools.clear()
            self._rr_index.clear()
