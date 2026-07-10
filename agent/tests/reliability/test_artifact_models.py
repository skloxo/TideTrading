"""Tests for Phase 1 artifact Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

from src.reliability.artifacts.model import ArtifactRecord, ArtifactRef


def test_artifact_record_defaults_to_timezone_aware_utc() -> None:
    record = ArtifactRecord(
        artifact_id="art_test",
        artifact_type="tool_trace",
        schema_version="1.0.0",
        sha256="a" * 64,
        uri="artifact://sha256/" + "a" * 64,
        generated_by="pytest",
    )

    assert record.created_at.tzinfo is not None
    assert record.created_at.utcoffset().total_seconds() == 0


def test_artifact_record_normalizes_aware_datetime_to_utc() -> None:
    created = datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc)

    record = ArtifactRecord(
        artifact_id="art_test",
        artifact_type="scorecard",
        schema_version="1.0.0",
        sha256="b" * 64,
        uri="artifact://sha256/" + "b" * 64,
        created_at=created,
        generated_by="pytest",
    )

    assert record.created_at == created


def test_artifact_record_redacts_secret_like_metadata() -> None:
    record = ArtifactRecord(
        artifact_id="art_test",
        artifact_type="policy_decision",
        schema_version="1.0.0",
        sha256="c" * 64,
        uri="artifact://sha256/" + "c" * 64,
        generated_by="pytest",
        metadata={
            "api_key": "plain-secret",
            "nested": {"authorization": "Bearer abcdefghijklmnopqrstuvwxyz012345"},
            "safe": "visible",
        },
    )

    assert record.metadata["api_key"] == "[REDACTED]"
    assert record.metadata["nested"]["authorization"] == "[REDACTED]"
    assert record.metadata["safe"] == "visible"


def test_artifact_ref_is_lightweight() -> None:
    ref = ArtifactRef(
        artifact_id="art_test",
        artifact_type="research_card",
        sha256="d" * 64,
        uri="artifact://sha256/" + "d" * 64,
    )

    assert ref.model_dump(mode="json") == {
        "artifact_id": "art_test",
        "artifact_type": "research_card",
        "sha256": "d" * 64,
        "uri": "artifact://sha256/" + "d" * 64,
    }
