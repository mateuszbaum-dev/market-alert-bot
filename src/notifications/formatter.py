from __future__ import annotations

from typing import Any

from src.models.event import MarketEvent

LEVEL_EMOJI = {
    "HIGH": "\U0001f6a8",
    "MEDIUM": "\u26a0\ufe0f",
    "LOW": "\u2139\ufe0f",
}
DISCLAIMER = "Monitoring alert only. Not financial advice."


def format_market_alert(event: MarketEvent, rule_score: dict, gpt_result: dict | None = None) -> str:
    final_level = _final_level(rule_score, gpt_result)
    emoji = LEVEL_EMOJI.get(final_level, LEVEL_EMOJI["LOW"])
    reasons = rule_score.get("reasons") or []

    lines = [
        f"{emoji} Market Monitoring Alert",
        "",
        f"Symbol: {_safe_text(event.symbol)}",
        f"Source: {_safe_text(event.source)}",
        f"Event Type: {_safe_text(event.event_type)}",
        f"Title: {_safe_text(event.title)}",
        f"Impact Level: {final_level}",
        f"Rule Score: {rule_score.get('score', 0)}",
        "Rule Reasons:",
    ]

    if reasons:
        lines.extend(f"- {_safe_text(reason)}" for reason in reasons)
    else:
        lines.append("- None provided")

    if gpt_result:
        lines.extend(
            [
                "",
                f"GPT Category: {_safe_text(gpt_result.get('category'))}",
                f"GPT Confidence: {gpt_result.get('confidence', 'N/A')}",
                f"GPT Summary: {_safe_text(gpt_result.get('reasoning_summary'))}",
            ]
        )

    if event.url:
        lines.extend(["", f"Link: {event.url}"])

    lines.extend(["", DISCLAIMER])
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
