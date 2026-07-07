"""Filesystem protocol registry with artifact-backed registration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.reliability.artifacts.model import ArtifactRef
from src.reliability.artifacts.store import ArtifactStore
from src.research_protocol.hashing import compute_protocol_hash
from src.research_protocol.model import ResearchProtocol


class ProtocolImmutableError(ValueError):
    """Raised when a registered protocol is mutated in place."""


class ProtocolRegistry:
    """Store draft/registered protocols without replacing GoalStore or Hypotheses."""

    def __init__(self, root: Path | None = None, *, artifact_root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path.home() / ".vibe-trading" / "research-protocols"
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifact_store = ArtifactStore(root=artifact_root) if artifact_root is not None else ArtifactStore()

    def save_draft(self, protocol: ResearchProtocol) -> ResearchProtocol:
        """Persist a draft protocol; registered protocols are immutable."""

        existing = self.get(protocol.protocol_id)
        if existing is not None and existing.status == "registered":
            raise ProtocolImmutableError(f"registered protocol is immutable: {protocol.protocol_id}")
        if protocol.status == "registered":
            raise ProtocolImmutableError("use register() to create registered protocols")
        draft = protocol.model_copy(update={"status": "draft", "protocol_hash": compute_protocol_hash(protocol)})
        self._write_protocol(draft)
        return draft

    def register(self, protocol_id: str, *, created_by: str | None = None) -> ResearchProtocol:
        """Register a draft protocol and write a research_protocol artifact."""

        current = self.get(protocol_id)
        if current is None:
            raise KeyError(f"protocol not found: {protocol_id}")
        if current.status == "registered":
            return current
        digest = compute_protocol_hash(current)
        registered = current.model_copy(
            update={
                "status": "registered",
                "protocol_hash": digest,
                "registered_at": datetime.now(timezone.utc),
                "created_by": created_by or current.created_by,
            }
        )
        self._write_protocol(registered)
        record = self.artifact_store.write_json(
            registered.model_dump(mode="json"),
            artifact_type="research_protocol",
            generated_by="ProtocolRegistry",
            metadata={
                "protocol_id": registered.protocol_id,
                "protocol_hash": registered.protocol_hash,
                "goal_id": registered.goal_id,
                "hypothesis_id": registered.hypothesis_id,
            },
        )
        if record is not None:
            self._write_artifact_ref(registered.protocol_hash, record.to_ref())
        return registered

    def get(self, protocol_id: str) -> ResearchProtocol | None:
        path = self._protocol_path(protocol_id)
        if not path.exists():
            return None
        return ResearchProtocol.model_validate_json(path.read_text(encoding="utf-8"))

    def is_registered(self, protocol_hash: str) -> bool:
        for path in self.root.glob("*.json"):
            protocol = ResearchProtocol.model_validate_json(path.read_text(encoding="utf-8"))
            if protocol.status == "registered" and protocol.protocol_hash == protocol_hash:
                return True
        return False

    def artifact_refs_for(self, protocol_hash: str) -> list[ArtifactRef]:
        path = self.root / f"{protocol_hash}.artifact_refs.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [ArtifactRef.model_validate(item) for item in raw]

    def _protocol_path(self, protocol_id: str) -> Path:
        safe = "".join(ch for ch in protocol_id if ch.isalnum() or ch in {"_", "-"})
        if not safe:
            raise ValueError("protocol_id must contain a safe filename character")
        return self.root / f"{safe}.json"

    def _write_protocol(self, protocol: ResearchProtocol) -> None:
        path = self._protocol_path(protocol.protocol_id)
        path.write_text(protocol.model_dump_json(indent=2), encoding="utf-8")

    def _write_artifact_ref(self, protocol_hash: str, ref: ArtifactRef) -> None:
        path = self.root / f"{protocol_hash}.artifact_refs.json"
        refs = self.artifact_refs_for(protocol_hash)
        refs.append(ref)
        path.write_text(
            json.dumps([item.model_dump(mode="json") for item in refs], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
