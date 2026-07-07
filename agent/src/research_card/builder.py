"""Build Research Cards from existing IRR-AGL artifacts and metadata."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.governance.decisions import PolicyDecision
from src.reliability.data.contracts import DataAuditReport, StructuredWarning as DataWarning
from src.reliability.quant.scorecard import BacktestReliabilityScorecard, QuantIssue
from src.research_card.model import ConclusionLevel, ResearchCard, StructuredFailure, StructuredWarning
from src.research_protocol.model import ResearchProtocol


_CONCLUSION_RANK: dict[ConclusionLevel, int] = {
    "not_reliable": 0,
    "exploratory": 1,
    "research_candidate": 2,
    "paper_trade_candidate": 3,
}


class ResearchCardGraph(BaseModel):
    """Minimal artifact graph consumed by the Research Card builder."""

    model_config = ConfigDict(allow_inf_nan=False, arbitrary_types_allowed=True)

    card_id: str
    title: str
    protocol: ResearchProtocol | dict[str, Any] | None = None
    data_audits: list[DataAuditReport | dict[str, Any]] = Field(default_factory=list)
    policy_decisions: list[PolicyDecision | dict[str, Any]] = Field(default_factory=list)
    tool_trace_refs: list[str] = Field(default_factory=list)
    backtest_refs: list[str] = Field(default_factory=list)
    alpha_bench_refs: list[str] = Field(default_factory=list)
    scorecard: BacktestReliabilityScorecard | dict[str, Any] | None = None
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    benchmark: dict[str, Any] = Field(default_factory=dict)
    cost_model: dict[str, Any] = Field(default_factory=dict)
    execution_assumptions: dict[str, Any] = Field(default_factory=dict)
    oos_results: dict[str, Any] = Field(default_factory=dict)
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    requested_conclusion_level: ConclusionLevel | None = None
    has_oos: bool | None = None
    has_cost_model: bool | None = None
    has_benchmark: bool | None = None
    has_pit_violation: bool = False
    claims_alpha: bool = False
    missing_artifacts: list[str] = Field(default_factory=list)


def build_research_card(graph: ResearchCardGraph) -> ResearchCard:
    """Build a Research Card without mutating existing run or artifact records."""
    protocol = _protocol(graph.protocol)
    data_audits = [_data_audit(item) for item in graph.data_audits]
    decisions = [_policy_decision(item) for item in graph.policy_decisions]
    scorecard = _scorecard(graph.scorecard)

    warnings: list[StructuredWarning] = []
    hard_failures: list[StructuredFailure] = []
    warnings.extend(_missing_artifact_warnings(graph.missing_artifacts))
    for audit in data_audits:
        warnings.extend(_warnings_from_data_audit(audit))
        for violation in audit.pit_violations:
            code = str(getattr(violation, "code", "") or getattr(violation, "violation_code", "") or "PIT_VIOLATION")
            warnings.append(StructuredWarning(code=code, message="PIT violation recorded"))
    if scorecard is not None:
        warnings.extend(_warnings_from_quant(scorecard.warnings))
        hard_failures.extend(_failures_from_quant(scorecard.hard_failures))

    if graph.claims_alpha and not _has_benchmark(graph, protocol):
        warnings.append(
            StructuredWarning(
                code="RESEARCH_CARD_ALPHA_CLAIM_WITHOUT_BENCHMARK",
                message="alpha claim requires benchmark evidence",
            )
        )

    conclusion = graph.requested_conclusion_level or "paper_trade_candidate"
    if scorecard is not None:
        conclusion = _min_conclusion(conclusion, scorecard.conclusion_cap)
    else:
        conclusion = _min_conclusion(conclusion, "exploratory")
        warnings.append(
            StructuredWarning(
                code="RESEARCH_CARD_SCORECARD_MISSING",
                message="research card has no quant reliability scorecard",
            )
        )
    if not _has_oos(graph, protocol, scorecard):
        conclusion = _min_conclusion(conclusion, "research_candidate")
    if not _has_cost_model(graph, protocol):
        conclusion = _min_conclusion(conclusion, "research_candidate")
    if not _has_benchmark(graph, protocol):
        conclusion = _min_conclusion(conclusion, "research_candidate")
    if graph.has_pit_violation or any(audit.pit_violations for audit in data_audits):
        conclusion = _min_conclusion(conclusion, "research_candidate")
    if hard_failures:
        conclusion = "not_reliable"

    return ResearchCard(
        card_id=graph.card_id,
        title=graph.title,
        protocol_ref=protocol.protocol_hash if protocol is not None else None,
        hypothesis=protocol.hypothesis if protocol is not None else None,
        universe=protocol.universe.model_dump(mode="json") if protocol is not None else {},
        data_sources=[_data_source_summary(audit) for audit in data_audits],
        data_audit_refs=[audit.audit_id for audit in data_audits],
        policy_decision_refs=[decision.decision_id for decision in decisions],
        tool_trace_refs=list(graph.tool_trace_refs),
        backtest_refs=list(graph.backtest_refs),
        alpha_bench_refs=list(graph.alpha_bench_refs),
        scorecard=scorecard,
        key_metrics=dict(graph.key_metrics),
        benchmark=_benchmark(graph, protocol),
        cost_model=_cost_model(graph, protocol),
        execution_assumptions=_execution_assumptions(graph, protocol),
        oos_results=dict(graph.oos_results),
        warnings=warnings,
        hard_failures=hard_failures,
        reproducibility=dict(graph.reproducibility),
        conclusion_level=conclusion,
    )


def _protocol(value: ResearchProtocol | dict[str, Any] | None) -> ResearchProtocol | None:
    if value is None:
        return None
    if isinstance(value, ResearchProtocol):
        return value
    return ResearchProtocol.model_validate(value)


def _data_audit(value: DataAuditReport | dict[str, Any]) -> DataAuditReport:
    if isinstance(value, DataAuditReport):
        return value
    return DataAuditReport.model_validate(value)


def _policy_decision(value: PolicyDecision | dict[str, Any]) -> PolicyDecision:
    if isinstance(value, PolicyDecision):
        return value
    return PolicyDecision.model_validate(value)


def _scorecard(value: BacktestReliabilityScorecard | dict[str, Any] | None) -> BacktestReliabilityScorecard | None:
    if value is None:
        return None
    if isinstance(value, BacktestReliabilityScorecard):
        return value
    return BacktestReliabilityScorecard.model_validate(value)


def _warnings_from_data_audit(audit: DataAuditReport) -> list[StructuredWarning]:
    warnings: list[StructuredWarning] = []
    for item in [*audit.quality_warnings, *audit.market_rule_warnings]:
        warnings.append(_warning_from_data(item))
    if audit.all_sources_open:
        warnings.append(
            StructuredWarning(
                code="DATA_ALL_SOURCES_OPEN",
                severity="hard_failure",
                message="all fallback data sources were circuit-open",
            )
        )
    return warnings


def _warning_from_data(item: DataWarning) -> StructuredWarning:
    return StructuredWarning(
        code=item.code,
        severity=item.severity,
        message=item.message,
        metadata=item.metadata,
    )


def _warnings_from_quant(items: list[QuantIssue]) -> list[StructuredWarning]:
    return [
        StructuredWarning(
            code=item.code,
            severity=item.severity,
            message=item.message,
            metadata=item.metadata,
        )
        for item in items
    ]


def _failures_from_quant(items: list[QuantIssue]) -> list[StructuredFailure]:
    return [
        StructuredFailure(
            code=item.code,
            message=item.message,
            metadata=item.metadata,
        )
        for item in items
    ]


def _missing_artifact_warnings(items: list[str]) -> list[StructuredWarning]:
    return [
        StructuredWarning(
            code="RESEARCH_CARD_ARTIFACT_MISSING",
            message="referenced artifact was unavailable while building research card",
            metadata={"artifact_ref": item},
        )
        for item in items
    ]


def _data_source_summary(audit: DataAuditReport) -> dict[str, Any]:
    access = audit.access_contract
    return {
        "audit_id": audit.audit_id,
        "source": access.source,
        "selected_source": access.selected_source,
        "fallback_chain": list(access.fallback_chain),
        "runtime_source": access.selected_source,
        "row_count": audit.row_count,
        "symbol_count": audit.symbol_count,
        "field_coverage": dict(audit.field_coverage),
        "all_sources_open": audit.all_sources_open,
    }


def _benchmark(graph: ResearchCardGraph, protocol: ResearchProtocol | None) -> dict[str, Any]:
    if graph.benchmark:
        return dict(graph.benchmark)
    if protocol is not None and protocol.benchmark_policy is not None:
        return protocol.benchmark_policy.model_dump(mode="json")
    return {}


def _cost_model(graph: ResearchCardGraph, protocol: ResearchProtocol | None) -> dict[str, Any]:
    if graph.cost_model:
        return dict(graph.cost_model)
    if protocol is not None and protocol.cost_model is not None:
        return protocol.cost_model.model_dump(mode="json")
    return {}


def _execution_assumptions(graph: ResearchCardGraph, protocol: ResearchProtocol | None) -> dict[str, Any]:
    if graph.execution_assumptions:
        return dict(graph.execution_assumptions)
    if protocol is not None and protocol.execution_assumptions is not None:
        return protocol.execution_assumptions.model_dump(mode="json")
    return {}


def _has_oos(
    graph: ResearchCardGraph,
    protocol: ResearchProtocol | None,
    scorecard: BacktestReliabilityScorecard | None,
) -> bool:
    if graph.has_oos is not None:
        return graph.has_oos
    if graph.oos_results:
        return True
    if scorecard is not None and scorecard.walk_forward is not None:
        return True
    if protocol is not None:
        return protocol.split_policy.method in {"walk_forward", "rolling", "expanding"} or bool(
            protocol.split_policy.test_start or protocol.split_policy.fold_count
        )
    return False


def _has_cost_model(graph: ResearchCardGraph, protocol: ResearchProtocol | None) -> bool:
    if graph.has_cost_model is not None:
        return graph.has_cost_model
    return bool(graph.cost_model or (protocol is not None and protocol.cost_model is not None))


def _has_benchmark(graph: ResearchCardGraph, protocol: ResearchProtocol | None) -> bool:
    if graph.has_benchmark is not None:
        return graph.has_benchmark
    return bool(graph.benchmark or (protocol is not None and protocol.benchmark_policy is not None))


def _min_conclusion(left: str, right: str) -> ConclusionLevel:
    left_level = left if left in _CONCLUSION_RANK else "exploratory"
    right_level = right if right in _CONCLUSION_RANK else "exploratory"
    return min(left_level, right_level, key=lambda item: _CONCLUSION_RANK[item])  # type: ignore[index,return-value]
