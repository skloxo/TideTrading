"""Tests for Phase 1 canonical artifact hashing."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.reliability.artifacts.hashing import sha256_bytes, sha256_file, sha256_json
from src.reliability.errors import CanonicalJsonError


class ExampleModel(BaseModel):
    value: str
    created_at: datetime


def test_sha256_bytes_matches_sha256_file(tmp_path: Path) -> None:
    payload = b"stable artifact payload"
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)

    assert sha256_file(path) == sha256_bytes(payload)


def test_sha256_json_requires_json_serializable_dict() -> None:
    with pytest.raises(CanonicalJsonError):
        sha256_json(["not", "a", "dict"])  # type: ignore[arg-type]


def test_sha256_json_is_stable_for_key_order() -> None:
    left = {"z": 1, "a": {"b": [True, None, "x"]}}
    right = {"a": {"b": [True, None, "x"]}, "z": 1}

    assert sha256_json(left) == sha256_json(right)


def test_sha256_json_rejects_datetime() -> None:
    with pytest.raises(CanonicalJsonError):
        sha256_json({"created_at": datetime.now(timezone.utc)})


def test_sha256_json_rejects_uuid() -> None:
    with pytest.raises(CanonicalJsonError):
        sha256_json({"id": uuid4()})


def test_sha256_json_rejects_nan() -> None:
    with pytest.raises(CanonicalJsonError):
        sha256_json({"score": math.nan})


def test_sha256_json_rejects_inf() -> None:
    with pytest.raises(CanonicalJsonError):
        sha256_json({"score": math.inf})


def test_pydantic_model_hash_requires_model_dump_json() -> None:
    artifact = ExampleModel(value="ok", created_at=datetime(2026, 7, 6, tzinfo=timezone.utc))

    with pytest.raises(CanonicalJsonError):
        sha256_json(artifact)  # type: ignore[arg-type]

    hashable = artifact.model_dump(mode="json")
    digest = sha256_json(hashable)

    assert isinstance(digest, str)
    assert len(digest) == 64
