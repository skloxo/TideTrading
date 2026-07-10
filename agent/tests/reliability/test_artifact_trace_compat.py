"""Trace and run-card compatibility tests for Phase 1 artifact refs."""

from __future__ import annotations

import json
from pathlib import Path

from backtest.run_card import write_run_card
from src.agent.trace import TraceWriter


def test_trace_reader_accepts_old_trace_without_new_fields(tmp_path: Path) -> None:
    (tmp_path / "trace.jsonl").write_text(
        json.dumps({"type": "tool_result", "tool": "get_market_data", "status": "ok"}) + "\n",
        encoding="utf-8",
    )

    [entry] = TraceWriter.read(tmp_path)

    assert entry["tool"] == "get_market_data"
    assert "artifact_refs" not in entry
    assert "policy_decision_id" not in entry


def test_trace_writer_preserves_optional_artifact_refs(tmp_path: Path) -> None:
    trace = TraceWriter(tmp_path)
    trace.write(
        {
            "type": "tool_result",
            "tool": "backtest",
            "status": "ok",
            "artifact_refs": [{"artifact_id": "art_1", "artifact_type": "backtest_result"}],
            "data_audit_id": "audit_1",
            "policy_decision_id": "pd_1",
            "governance_overhead_ms": 1.5,
            "warning_codes": ["W_TEST"],
            "hard_failure_codes": ["H_TEST"],
        }
    )
    trace.close()

    [entry] = TraceWriter.read(tmp_path)

    assert entry["artifact_refs"] == [{"artifact_id": "art_1", "artifact_type": "backtest_result"}]
    assert entry["data_audit_id"] == "audit_1"
    assert entry["policy_decision_id"] == "pd_1"
    assert entry["governance_overhead_ms"] == 1.5
    assert entry["warning_codes"] == ["W_TEST"]
    assert entry["hard_failure_codes"] == ["H_TEST"]


def test_run_card_old_shape_still_valid(tmp_path: Path) -> None:
    card = write_run_card(
        tmp_path,
        {"codes": ["AAPL"], "source": "yfinance"},
        {"sharpe": 1.0},
    )

    loaded = json.loads((tmp_path / "run_card.json").read_text(encoding="utf-8"))

    assert loaded == card
    assert isinstance(loaded["artifacts"], list)
    assert "artifact_refs" not in loaded


def test_run_card_can_include_optional_irr_artifact_refs(tmp_path: Path) -> None:
    artifact_refs = [
        {
            "artifact_id": "art_scorecard",
            "artifact_type": "scorecard",
            "sha256": "e" * 64,
            "uri": "artifact://sha256/" + "e" * 64,
        }
    ]

    card = write_run_card(
        tmp_path,
        {"codes": ["AAPL"], "source": "yfinance"},
        {"sharpe": 1.0},
        artifact_refs=artifact_refs,
    )

    loaded = json.loads((tmp_path / "run_card.json").read_text(encoding="utf-8"))

    assert loaded["artifacts"] == card["artifacts"]
    assert loaded["artifact_refs"] == artifact_refs
    assert "art_scorecard" in (tmp_path / "run_card.md").read_text(encoding="utf-8")
