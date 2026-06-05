from __future__ import annotations

import html
from typing import Any

from src.models.event import MarketEvent

LEVEL_EMOJI = {
    "HIGH": "\U0001f6a8",
    "MEDIUM": "\u26a0\ufe0f",
    "LOW": "\u2139\ufe0f",
}
DIRECTION_LABELS = {
    "BULLISH": "\U0001f7e2 BULLISH",
    "BEARISH": "\U0001f534 BEARISH",
    "NEUTRAL": "\U0001f7e1 NEUTRAL",
    "UNCLEAR": "\u26aa UNCLEAR",
}


def format_market_alert(event: MarketEvent, rule_score: dict, gpt_result: dict | None = None) -> str:
    final_level = _final_level(rule_score, gpt_result)
    emoji = LEVEL_EMOJI.get(final_level, LEVEL_EMOJI["LOW"])

    lines = [
        f"{emoji} Market Alert",
        "",
        f"Ticker: <b>{_escape(event.symbol)}</b>",
    ]

    if gpt_result:
        lines.extend(
            [
                f"Direction: {_direction_label(gpt_result.get('market_direction'))}",
                f"Impact: {gpt_result.get('impact_score', 'N/A')}/10",
                f"Impact level: {final_level}",
                f"Direction confidence: {gpt_result.get('direction_confidence', 'N/A')}%",
                f"Reaction probability: {gpt_result.get('event_probability', 'N/A')}%",
                "",
                f"Category: {_escape(gpt_result.get('category'))}",
            ]
        )
    else:
        lines.extend(
            [
                f"Impact level: {final_level}",
                f"Rule score: {rule_score.get('score', 0)}",
            ]
        )

    lines.extend(
        [
            f"Source: {_escape(event.source)}",
            f"Type: {_escape(event.event_type)}",
            "",
            "Title:",
            _escape(event.title),
        ]
    )

    if gpt_result:
        lines.extend(
            [
                "",
                "AI summary:",
                _escape(gpt_result.get("reasoning_summary")),
            ]
        )

    if event.url:
        lines.extend(["", "Link:", _escape(event.url)])

    return "\n".join(lines)


def _final_level(rule_score: dict, gpt_result: dict | None) -> str:
    if gpt_result and gpt_result.get("impact_level"):
        return str(gpt_result["impact_level"]).upper()
    return str(rule_score.get("level", "LOW")).upper()


def _safe_text(value: Any) -> str:
    if value is None:
        return "N/A"
    text = str(value).strip()
    return text or "N/A"


def _escape(value: Any) -> str:
    return html.escape(_safe_text(value))


def _direction_label(value: Any) -> str:
    direction = _safe_text(value).upper()
    return DIRECTION_LABELS.get(direction, DIRECTION_LABELS["UNCLEAR"])
