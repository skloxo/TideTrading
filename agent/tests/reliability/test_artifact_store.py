"""Tests for Phase 1 SQLite-backed artifact store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.reliability.artifacts.hashing import sha256_bytes
from src.reliability.artifacts.store import ArtifactStore, resolve_under_root
from src.reliability.errors import ArtifactPathError


def test_artifact_store_atomic_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBE_TRADING_RELIABILITY_MODE", "observe")
    store = ArtifactStore(tmp_path)
    payload = b"atomic payload"

    record = store.write_bytes(
        payload,
        artifact_type="backtest_result",
        generated_by="pytest",
        metadata={"label": "atomic"},
    )

    assert record is not None
    assert record.sha256 == sha256_bytes(payload)
    assert record.path is not None
    payload_path = Path(record.path)
    assert payload_path.read_bytes() == payload
    assert not list(payload_path.parent.glob("*.tmp"))


def test_artifact_store_sqlite_wal_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBE_TRADING_RELIABILITY_MODE", "observe")
    store = ArtifactStore(tmp_path)
    store.write_bytes(b"wal", artifact_type="tool_trace", generated_by="pytest")

    with sqlite3.connect(tmp_path / "artifact_index.sqlite") as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert mode.lower() == "wal"


def test_artifact_store_path_containment_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(ArtifactPathError):
        resolve_under_root(tmp_path, Path("..") / "escape.bin")


def test_artifact_store_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")

    with pytest.raises(ArtifactPathError):
        resolve_under_root(tmp_path, link / "payload.bin")


def test_artifact_store_redacts_secret_like_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBE_TRADING_RELIABILITY_MODE", "observe")
    store = ArtifactStore(tmp_path)

    record = store.write_bytes(
        b"secret metadata",
        artifact_type="policy_decision",
        generated_by="pytest",
        metadata={
            "token": "plain-token",
            "note": "visible",
            "nested": {"cookie": "session=abcdef"},
        },
    )

    assert record is not None
    with sqlite3.connect(tmp_path / "artifact_index.sqlite") as conn:
        metadata_json = conn.execute(
            "SELECT metadata_json FROM artifacts WHERE artifact_id = ?",
            (record.artifact_id,),
        ).fetchone()[0]

    metadata = json.loads(metadata_json)
    assert metadata["token"] == "[REDACTED]"
    assert metadata["nested"]["cookie"] == "[REDACTED]"
    assert metadata["note"] == "visible"
    assert "plain-token" not in metadata_json
    assert "session=abcdef" not in metadata_json


def test_reliability_mode_off_does_not_require_artifact_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBE_TRADING_RELIABILITY_MODE", "off")
    store = ArtifactStore(tmp_path)

    record = store.write_bytes(b"disabled", artifact_type="tool_trace", generated_by="pytest")

    assert record is None
    assert not (tmp_path / "artifact_index.sqlite").exists()
    assert not (tmp_path / "objects").exists()
