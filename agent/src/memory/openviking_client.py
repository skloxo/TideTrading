"""OpenViking Memory Client for Tide-Trading.

Provides lightweight HTTP REST API integration with OpenViking (http://127.0.0.1:1933).
No A2A dependency, zero overhead.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

OPENVIKING_HOST = "http://127.0.0.1:1933"
ACTOR_PEER = "tide-trading"


class OpenVikingMemoryClient:
    """Lightweight HTTP client for OpenViking Exocortex Memory Engine."""

    def __init__(self, base_url: str = OPENVIKING_HOST, peer_name: str = ACTOR_PEER):
        self.base_url = base_url.rstrip("/")
        self.peer_name = peer_name

    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search OpenViking for relevant memories, backtest lessons, or research notes."""
        url = f"{self.base_url}/api/v1/search/search"
        payload = json.dumps({"query": query, "limit": limit}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=payload, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("result", {}).get("items", [])
        except Exception as err:
            logger.warning(f"[OpenViking] Failed to search memories for '{query}': {err}")
            return []

    def commit_session_message(self, session_id: str, role: str, content: str) -> bool:
        """Commit a conversation or trading analysis log to OpenViking session history."""
        url = f"{self.base_url}/api/v1/sessions/{session_id}/messages"
        payload = json.dumps({"role": role, "content": content}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-OpenViking-Actor-Peer": self.peer_name,
        }
        req = urllib.request.Request(url, data=payload, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("status") == "ok"
        except Exception as err:
            logger.warning(f"[OpenViking] Failed to commit session message: {err}")
            return False

    def store_trade_lesson(self, symbol: str, strategy: str, lesson_summary: str) -> bool:
        """Store a trade lesson or strategy backtest insight into OpenViking."""
        message = (
            f"[Trade Lesson] Symbol: {symbol} | Strategy: {strategy}\n"
            f"Insight: {lesson_summary}"
        )
        return self.commit_session_message("tide-trading-lessons", "user", message)
