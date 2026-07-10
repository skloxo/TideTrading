"""Shared schema constants for IRR-AGL reliability artifacts."""

from __future__ import annotations

from typing import Literal

ARTIFACT_SCHEMA_VERSION = "1.0.0"

ArtifactType = Literal[
    "data_audit",
    "tool_trace",
    "policy_decision",
    "research_protocol",
    "trial_event",
    "backtest_result",
    "alpha_bench_result",
    "scorecard",
    "research_card",
]

ARTIFACT_TYPES: frozenset[str] = frozenset(
    {
        "data_audit",
        "tool_trace",
        "policy_decision",
        "research_protocol",
        "trial_event",
        "backtest_result",
        "alpha_bench_result",
        "scorecard",
        "research_card",
    }
)
