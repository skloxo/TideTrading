"""Pydantic models for IRR-AGL artifact records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.reliability.redaction import redact_secrets
from src.reliability.schema import ArtifactType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactRef(BaseModel):
    """Lightweight reference to a persisted IRR-AGL artifact."""

    artifact_id: str
    artifact_type: ArtifactType
    sha256: str | None = None
    uri: str | None = None


class ArtifactRecord(BaseModel):
    """Metadata record for a persisted IRR-AGL artifact."""

    artifact_id: str
    artifact_type: ArtifactType
    schema_version: str
    sha256: str
    uri: str
    path: str | None = None
    inline_ref: str | None = None
    parent_artifacts: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    generated_by: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def _created_at_must_be_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("metadata", mode="before")
    @classmethod
    def _redact_metadata(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        redacted = redact_secrets(value)
        if not isinstance(redacted, dict):
            raise ValueError("metadata must be a JSON object")
        return redacted

    def to_ref(self) -> ArtifactRef:
        """Return a lightweight reference to this artifact."""
        return ArtifactRef(
            artifact_id=self.artifact_id,
            artifact_type=self.artifact_type,
            sha256=self.sha256,
            uri=self.uri,
        )
