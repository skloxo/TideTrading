"""Stable Markdown renderer for Research Cards."""

from __future__ import annotations

from src.research_card.model import ResearchCard


def render_research_card_markdown(card: ResearchCard) -> str:
    """Render a deterministic Markdown Research Card snapshot."""
    lines = [
        f"# Research Card: {card.title}",
        "",
        f"- Card ID: `{card.card_id}`",
        f"- Schema Version: `{card.schema_version}`",
        f"- Conclusion: `{card.conclusion_level}`",
    ]
    if card.protocol_ref:
        lines.append(f"- Protocol: `{card.protocol_ref}`")
    if card.scorecard is not None:
        lines.append(f"- Scorecard: `{card.scorecard.scorecard_id}`")
    lines.extend(["", "## Hypothesis", "", card.hypothesis or "Not recorded."])
    if card.key_metrics:
        lines.extend(["", "## Key Metrics", ""])
        for key, value in sorted(card.key_metrics.items()):
            lines.append(f"- {key}: {value}")
    if card.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in card.warnings:
            lines.append(f"- `{warning.code}` ({warning.severity}): {warning.message}")
    if card.hard_failures:
        lines.extend(["", "## Hard Failures", ""])
        for failure in card.hard_failures:
            lines.append(f"- `{failure.code}` ({failure.severity}): {failure.message}")
    return "\n".join(lines) + "\n"
