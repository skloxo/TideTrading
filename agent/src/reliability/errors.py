"""Exceptions raised by IRR-AGL reliability components."""

from __future__ import annotations


class ReliabilityError(Exception):
    """Base class for reliability-layer failures."""


class CanonicalJsonError(ReliabilityError, ValueError):
    """Raised when a value cannot be canonically hashed as JSON."""


class ArtifactStoreError(ReliabilityError):
    """Raised when artifact persistence fails."""


class ArtifactPathError(ArtifactStoreError, ValueError):
    """Raised when an artifact path escapes the configured root."""
