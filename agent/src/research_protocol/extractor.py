"""Draft protocol extraction helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from src.reliability.data.contracts import DataSetContract
from src.research_protocol.model import EvaluationPlan, ResearchProtocol, SplitSpec, UniverseSpec


def draft_protocol_from_hypothesis(
    hypothesis: str,
    *,
    protocol_id: str = "proto_draft",
    created_by: str = "cli",
) -> ResearchProtocol:
    """Create a conservative draft protocol for CLI/manual refinement."""

    return ResearchProtocol(
        protocol_id=protocol_id,
        schema_version="1.0.0",
        status="draft",
        hypothesis=hypothesis,
        universe=UniverseSpec(asset_class="other", universe_name="unspecified"),
        data_requirements=[
            DataSetContract(
                dataset_id="unspecified",
                asset_class="other",
                frequency="1D",
                calendar="unspecified",
                fields=[],
                timezone="UTC",
            )
        ],
        split_policy=SplitSpec(method="holdout"),
        evaluation_plan=EvaluationPlan(metrics=["return", "sharpe"]),
        created_at=datetime.now(timezone.utc),
        created_by=created_by,
    )
