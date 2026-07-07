"""Research protocol registry and trial ledger."""

from src.research_protocol.acceptance import AcceptanceError, AcceptedResult, validate_accepted_result
from src.research_protocol.hashing import compute_protocol_hash
from src.research_protocol.ledger import TrialLedger
from src.research_protocol.model import (
    BenchmarkSpec,
    CostModelSpec,
    DataSetContract,
    EvaluationPlan,
    ExecutionAssumptions,
    FilterSpec,
    ResearchProtocol,
    SplitSpec,
    UniverseSpec,
)
from src.research_protocol.registry import ProtocolImmutableError, ProtocolRegistry
from src.research_protocol.trial import TrialEvent, TrialEventType

__all__ = [
    "AcceptanceError",
    "AcceptedResult",
    "BenchmarkSpec",
    "CostModelSpec",
    "DataSetContract",
    "EvaluationPlan",
    "ExecutionAssumptions",
    "FilterSpec",
    "ProtocolImmutableError",
    "ProtocolRegistry",
    "ResearchProtocol",
    "SplitSpec",
    "TrialEvent",
    "TrialEventType",
    "TrialLedger",
    "UniverseSpec",
    "compute_protocol_hash",
    "validate_accepted_result",
]
