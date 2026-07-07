"""SQLite WAL trial ledger with a linear hash chain."""

from __future__ import annotations

import json
import os
import random
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.reliability.artifacts.hashing import sha256_json
from src.research_protocol.trial import LedgerVerificationResult, TrialEvent, TrialEventType


WRITE_RETRY_COUNT = 5
WRITE_RETRY_DELAY_MS = 100
_LEDGER_ENV = "VIBE_TRADING_RESEARCH_LEDGER_PATH"


def default_ledger_path() -> Path:
    override = os.getenv(_LEDGER_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".vibe-trading" / "research-ledger" / "ledger.sqlite"


class TrialLedger:
    """Append-only trial ledger using BEGIN IMMEDIATE and hash chaining."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        write_retry_count: int = WRITE_RETRY_COUNT,
        write_retry_delay_ms: int = WRITE_RETRY_DELAY_MS,
    ) -> None:
        self.path = Path(path) if path is not None else default_ledger_path()
        self.write_retry_count = int(write_retry_count)
        self.write_retry_delay_ms = int(write_retry_delay_ms)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def append(
        self,
        *,
        protocol_hash: str,
        event_type: TrialEventType | str,
        payload: dict[str, Any] | None = None,
        artifact_refs: list[str] | None = None,
    ) -> TrialEvent:
        """Append one event, assigning sequence and previous hash inside the transaction."""

        last_error: Exception | None = None
        for attempt in range(max(1, self.write_retry_count)):
            conn = self._connect(timeout=0.1)
            try:
                conn.execute("BEGIN IMMEDIATE")
                sequence, previous = self._next_sequence(conn)
                created_at = datetime.now(timezone.utc)
                event_id = f"te_{uuid4().hex}"
                event_type_value = TrialEventType(event_type).value
                payload_dict = dict(payload or {})
                refs = list(artifact_refs or [])
                event_hash = _event_hash(
                    event_id=event_id,
                    event_type=event_type_value,
                    schema_version="1.0.0",
                    protocol_hash=protocol_hash,
                    sequence_number=sequence,
                    previous_event_hash=previous,
                    created_at=created_at.isoformat(),
                    payload=payload_dict,
                    artifact_refs=refs,
                )
                conn.execute(
                    """
                    INSERT INTO trial_events (
                        event_id, event_type, schema_version, protocol_hash,
                        sequence_number, previous_event_hash, event_hash,
                        created_at, payload_json, artifact_refs_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        event_type_value,
                        "1.0.0",
                        protocol_hash,
                        sequence,
                        previous,
                        event_hash,
                        created_at.isoformat(),
                        _json_dump(payload_dict),
                        _json_dump(refs),
                    ),
                )
                conn.commit()
                return TrialEvent(
                    event_id=event_id,
                    event_type=TrialEventType(event_type_value),
                    schema_version="1.0.0",
                    protocol_hash=protocol_hash,
                    sequence_number=sequence,
                    previous_event_hash=previous,
                    event_hash=event_hash,
                    created_at=created_at,
                    payload=payload_dict,
                    artifact_refs=refs,
                )
            except sqlite3.OperationalError as exc:
                conn.rollback()
                last_error = exc
                if "locked" not in str(exc).lower() or attempt >= self.write_retry_count - 1:
                    raise
                delay = (self.write_retry_delay_ms / 1000.0) * (2**attempt)
                delay += random.uniform(0, self.write_retry_delay_ms / 1000.0)
                time.sleep(delay)
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        if last_error is not None:
            raise last_error
        raise RuntimeError("failed to append trial event")

    def verify(self) -> LedgerVerificationResult:
        """Verify sequence, previous hash, event hash, protocol hash, and schema version."""

        errors: list[str] = []
        previous_hash: str | None = None
        expected_sequence = 1
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, event_type, schema_version, protocol_hash,
                       sequence_number, previous_event_hash, event_hash,
                       created_at, payload_json, artifact_refs_json
                FROM trial_events
                ORDER BY sequence_number ASC
                """
            ).fetchall()
        for row in rows:
            sequence = int(row["sequence_number"])
            if sequence != expected_sequence:
                errors.append(f"sequence gap at {row['event_id']}: expected {expected_sequence}, got {sequence}")
            if row["previous_event_hash"] != previous_hash:
                errors.append(f"previous hash mismatch at sequence {sequence}")
            if row["schema_version"] != "1.0.0":
                errors.append(f"schema_version mismatch at sequence {sequence}")
            if not str(row["protocol_hash"] or "").strip():
                errors.append(f"protocol hash missing at sequence {sequence}")
            try:
                TrialEventType(row["event_type"])
            except ValueError:
                errors.append(f"unknown event_type at sequence {sequence}: {row['event_type']}")
            payload = _json_load(row["payload_json"], {})
            refs = _json_load(row["artifact_refs_json"], [])
            expected_hash = _event_hash(
                event_id=row["event_id"],
                event_type=row["event_type"],
                schema_version=row["schema_version"],
                protocol_hash=row["protocol_hash"],
                sequence_number=sequence,
                previous_event_hash=row["previous_event_hash"],
                created_at=row["created_at"],
                payload=payload,
                artifact_refs=refs,
            )
            if expected_hash != row["event_hash"]:
                errors.append(f"event_hash mismatch at sequence {sequence}")
            previous_hash = row["event_hash"]
            expected_sequence += 1
        return LedgerVerificationResult(valid=not errors, event_count=len(rows), errors=errors)

    def _init_db(self) -> None:
        for attempt in range(max(1, self.write_retry_count)):
            try:
                with self._connect(timeout=0.1) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS trial_events (
                            event_id TEXT PRIMARY KEY,
                            event_type TEXT NOT NULL,
                            schema_version TEXT NOT NULL,
                            protocol_hash TEXT NOT NULL,
                            sequence_number INTEGER NOT NULL UNIQUE,
                            previous_event_hash TEXT,
                            event_hash TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            payload_json TEXT NOT NULL,
                            artifact_refs_json TEXT NOT NULL
                        )
                        """
                    )
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_trial_events_protocol ON trial_events(protocol_hash)")
                return
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt >= self.write_retry_count - 1:
                    raise
                delay = (self.write_retry_delay_ms / 1000.0) * (2**attempt)
                delay += random.uniform(0, self.write_retry_delay_ms / 1000.0)
                time.sleep(delay)

    def _connect(self, *, timeout: float = 30.0) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=timeout, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @staticmethod
    def _next_sequence(conn: sqlite3.Connection) -> tuple[int, str | None]:
        row = conn.execute(
            "SELECT sequence_number, event_hash FROM trial_events ORDER BY sequence_number DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return 1, None
        return int(row["sequence_number"]) + 1, str(row["event_hash"])


def _event_hash(
    *,
    event_id: str,
    event_type: str,
    schema_version: str,
    protocol_hash: str,
    sequence_number: int,
    previous_event_hash: str | None,
    created_at: str,
    payload: dict[str, Any],
    artifact_refs: list[str],
) -> str:
    return sha256_json(
        {
            "event_id": event_id,
            "event_type": event_type,
            "schema_version": schema_version,
            "protocol_hash": protocol_hash,
            "sequence_number": sequence_number,
            "previous_event_hash": previous_event_hash,
            "created_at": created_at,
            "payload": payload,
            "artifact_refs": artifact_refs,
        }
    )


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))


def _json_load(value: str, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)
