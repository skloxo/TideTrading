"""Shared Memory Hub for batch caching A-share realtime quotes.

Implements thread-safe singleton cache with automatic background polling
for indexes and recently requested symbols during market trading hours.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, time as datetime_time
from typing import Dict, List, Optional, Set
from src.market.tdx_bridge import TdxGateway, TdxConnectionError

logger = logging.getLogger(__name__)


def is_market_open() -> bool:
    """Check if Chinese A-share market is currently trading (9:15-11:30, 13:00-15:00 weekdays)."""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    current_time = now.time()
    morning_start = datetime_time(9, 15)
    morning_end = datetime_time(11, 30)
    afternoon_start = datetime_time(13, 0)
    afternoon_end = datetime_time(15, 0)
    return (morning_start <= current_time <= morning_end) or (afternoon_start <= current_time <= afternoon_end)


class SharedMemoryHub:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SharedMemoryHub, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.lock = threading.Lock()
        
        # cache schema: symbol -> { "data": dict, "updated_at": float, "last_requested_at": float }
        self._cache: Dict[str, dict] = {}
        
        # Cache configuration
        self.cache_ttl = 3.0  # 3 seconds cache validity
        self.inactive_timeout = 30.0  # 30 seconds to determine cold/inactive stock
        self.refresh_interval = 3.0  # background refresh interval during market hours
        self.idle_refresh_interval = 60.0  # background refresh interval during off hours
        
        # Permanent indexes to keep refreshed
        self.permanent_symbols: Set[str] = {
            "sh000001", "sz399001", "sz399006", "sh000688",
            "000001", "399001", "399006"
        }
        
        self.running = False
        self.refresh_thread: Optional[threading.Thread] = None

        # Pre-initialize permanent symbols in cache
        now = time.time()
        for s in self.permanent_symbols:
            self._cache[s] = {
                "data": {},
                "updated_at": 0.0,
                "last_requested_at": now
            }

    def start(self) -> None:
        """Start the background refresh thread."""
        with self.lock:
            if self.running:
                return
            self.running = True
        
        # Ensure TdxGateway is started
        try:
            TdxGateway().start()
        except Exception as e:
            logger.error("Failed to start TdxGateway from SharedMemoryHub: %s", e)

        self.refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="shared-market-cache-refresher"
        )
        self.refresh_thread.start()
        logger.info("SharedMemoryHub background refresher started.")

    def stop(self) -> None:
        """Stop the background refresh thread."""
        with self.lock:
            self.running = False
        logger.info("SharedMemoryHub background refresher stopped.")

    def get_quotes(self, symbols: List[str]) -> Dict[str, dict]:
        """Get quotes for the requested symbols, checking the memory cache first."""
        if not symbols:
            return {}

        now = time.time()
        results: Dict[str, dict] = {}
        missing_symbols: List[str] = []

        with self.lock:
            for s in symbols:
                cached = self._cache.get(s)
                if cached and (now - cached["updated_at"] < self.cache_ttl):
                    results[s] = cached["data"]
                    cached["last_requested_at"] = now
                else:
                    missing_symbols.append(s)
                    if cached:
                        cached["last_requested_at"] = now
                    else:
                        # Initialize cache entry for tracking
                        self._cache[s] = {
                            "data": {},
                            "updated_at": 0.0,
                            "last_requested_at": now
                        }

        if missing_symbols:
            try:
                gateway = TdxGateway()
                fetched = gateway.get_quotes(missing_symbols)
            except TdxConnectionError:
                logger.warning("TdxGateway failed in SharedMemoryHub. Falling back to Tencent HTTP: %s", missing_symbols)
                try:
                    fetched = TdxGateway().fetch_tencent_quotes(missing_symbols)
                except Exception as ex:
                    logger.error("Failed to fetch fallback tencent quotes in SharedMemoryHub: %s", ex)
                    fetched = {}
            except Exception as e:
                logger.error("Error getting quotes in SharedMemoryHub: %s", e)
                fetched = {}

            now_updated = time.time()
            with self.lock:
                for s in missing_symbols:
                    data = fetched.get(s, {})
                    if data or s not in self._cache or not self._cache[s]["data"]:
                        self._cache[s] = {
                            "data": data,
                            "updated_at": now_updated,
                            "last_requested_at": now
                        }
                    results[s] = self._cache[s]["data"]

        return results

    def _refresh_loop(self) -> None:
        """Background loop to periodically refresh permanent indexes and active stocks."""
        while True:
            with self.lock:
                if not self.running:
                    break

            try:
                self._refresh_active_cache()
            except Exception as e:
                logger.error("Error refreshing market cache in background loop: %s", e)

            # Adjust sleep time based on whether the market is open
            sleep_time = self.refresh_interval if is_market_open() else self.idle_refresh_interval
            time.sleep(sleep_time)

    def _refresh_active_cache(self) -> None:
        """Select permanent and recently active symbols, and batch refresh their quotes."""
        now = time.time()
        to_refresh: List[str] = []

        with self.lock:
            for s, entry in self._cache.items():
                is_permanent = s in self.permanent_symbols
                is_active = (now - entry["last_requested_at"]) < self.inactive_timeout
                if is_permanent or is_active:
                    to_refresh.append(s)

        if not to_refresh:
            return

        # Fetch in batches of 50 to avoid overloading TDX or mootdx limits
        batch_size = 50
        for i in range(0, len(to_refresh), batch_size):
            batch = to_refresh[i:i+batch_size]
            try:
                gateway = TdxGateway()
                fetched = gateway.get_quotes(batch)
            except TdxConnectionError:
                try:
                    fetched = TdxGateway().fetch_tencent_quotes(batch)
                except Exception:
                    fetched = {}
            except Exception:
                fetched = {}

            now_updated = time.time()
            with self.lock:
                for s in batch:
                    data = fetched.get(s, {})
                    if data or s not in self._cache or not self._cache[s]["data"]:
                        last_req = self._cache[s]["last_requested_at"] if s in self._cache else now
                        self._cache[s] = {
                            "data": data,
                            "updated_at": now_updated,
                            "last_requested_at": last_req
                        }
