"""Schema-versioned Research Card delivery model."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.reliability.quant.scorecard import BacktestReliabilityScorecard
from src.reliability.redaction import redact_secrets


RESEARCH_CARD_SCHEMA_VERSION = "1.0.0"
ConclusionLevel = Literal["not_reliable", "exploratory", "research_candidate", "paper_trade_candidate"]


class StructuredWarning(BaseModel):
    """Stable warning code rendered in Research Cards and panels."""

    model_config = ConfigDict(allow_inf_nan=False)

    code: str
    severity: Literal["info", "warning", "hard_failure"] = "warning"
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _redact(cls, value: Any) -> Any:
        return redact_secrets(value)


class StructuredFailure(BaseModel):
    """Stable hard-failure code rendered in Research Cards and panels."""

    model_config = ConfigDict(allow_inf_nan=False)

    code: str
    severity: Literal["hard_failure"] = "hard_failure"
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _redact(cls, value: Any) -> Any:
        return redact_secrets(value)


class ResearchCard(BaseModel):
    """Machine-readable, auditable research delivery card."""

    model_config = ConfigDict(allow_inf_nan=False, arbitrary_types_allowed=False)

    card_id: str
    schema_version: str = RESEARCH_CARD_SCHEMA_VERSION
    title: str
    protocol_ref: str | None = None
    hypothesis: str | None = None
    universe: dict[str, Any] = Field(default_factory=dict)
    data_sources: list[dict[str, Any]] = Field(default_factory=list)
    data_audit_refs: list[str] = Field(default_factory=list)
    policy_decision_refs: list[str] = Field(default_factory=list)
    tool_trace_refs: list[str] = Field(default_factory=list)
    backtest_refs: list[str] = Field(default_factory=list)
    alpha_bench_refs: list[str] = Field(default_factory=list)
    scorecard: BacktestReliabilityScorecard | None = None
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    benchmark: dict[str, Any] = Field(default_factory=dict)
    cost_model: dict[str, Any] = Field(default_factory=dict)
    execution_assumptions: dict[str, Any] = Field(default_factory=dict)
    oos_results: dict[str, Any] = Field(default_factory=dict)
    warnings: list[StructuredWarning] = Field(default_factory=list)
    hard_failures: list[StructuredFailure] = Field(default_factory=list)
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    conclusion_level: ConclusionLevel = "exploratory"

    @model_validator(mode="before")
    @classmethod
    def _redact_untrusted_content(cls, value: Any) -> Any:
        return redact_secrets(value)

    @model_validator(mode="after")
    def _hard_failures_force_not_reliable(self) -> "ResearchCard":
        if self.hard_failures:
            self.conclusion_level = "not_reliable"
        return self
