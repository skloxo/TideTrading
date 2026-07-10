"""Configuration helpers for IRR-AGL reliability features."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

ReliabilityMode = Literal["off", "observe", "warn", "enforce"]

VALID_RELIABILITY_MODES: frozenset[str] = frozenset({"off", "observe", "warn", "enforce"})
_DEFAULT_MODE: ReliabilityMode = "observe"


def parse_reliability_mode(raw: str | None, *, default: ReliabilityMode = _DEFAULT_MODE) -> ReliabilityMode:
    """Parse an IRR-AGL reliability mode."""
    value = (raw or default).strip().lower()
    if value not in VALID_RELIABILITY_MODES:
        raise ValueError(f"unsupported reliability mode: {raw!r}")
    return value  # type: ignore[return-value]


def reliability_mode() -> ReliabilityMode:
    """Return the current reliability feature mode."""
    return parse_reliability_mode(os.getenv("VIBE_TRADING_RELIABILITY_MODE"))


def reliability_enabled() -> bool:
    """Return whether reliability writes should produce artifacts."""
    return reliability_mode() != "off"


def artifact_root() -> Path:
    """Return the local artifact root, honoring the environment override."""
    raw = os.getenv("VIBE_TRADING_ARTIFACT_ROOT")
    if raw:
        return Path(os.path.expandvars(os.path.expanduser(raw))).resolve(strict=False)
    return (Path.home() / ".vibe-trading" / "artifacts").resolve(strict=False)
