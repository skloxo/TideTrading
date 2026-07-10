"""Small helpers for artifact lineage graphs."""

from __future__ import annotations

from dataclasses import dataclass

from src.reliability.artifacts.model import ArtifactRecord, ArtifactRef


@dataclass(frozen=True)
class ArtifactLineageEdge:
    """Parent-child edge in the local artifact graph."""

    parent_artifact_id: str
    child_artifact_id: str


def refs_for_records(records: list[ArtifactRecord]) -> list[ArtifactRef]:
    """Return lightweight refs for a list of records."""
    return [record.to_ref() for record in records]


def lineage_edges(record: ArtifactRecord) -> list[ArtifactLineageEdge]:
    """Return parent-child edges implied by one artifact record."""
    return [
        ArtifactLineageEdge(parent_artifact_id=parent, child_artifact_id=record.artifact_id)
        for parent in record.parent_artifacts
    ]
