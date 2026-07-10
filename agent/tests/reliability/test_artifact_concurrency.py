"""Concurrency tests for Phase 1 artifact metadata writes."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.reliability.artifacts.store import ArtifactStore


def test_artifact_store_concurrent_writes_no_metadata_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBE_TRADING_RELIABILITY_MODE", "observe")
    store = ArtifactStore(tmp_path)
    payloads = [f"payload-{idx}".encode("utf-8") for idx in range(40)]

    def write_payload(payload: bytes) -> str:
        record = store.write_bytes(payload, artifact_type="tool_trace", generated_by="pytest")
        assert record is not None
        return record.artifact_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        artifact_ids = list(pool.map(write_payload, payloads))

    with sqlite3.connect(tmp_path / "artifact_index.sqlite") as conn:
        count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]

    assert count == len(payloads)
    assert len(set(artifact_ids)) == len(payloads)
