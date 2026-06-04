from __future__ import annotations

from typing import Literal, TypedDict

from src.models.event import MarketEvent

ScoreLevel = Literal["LOW", "MEDIUM", "HIGH"]


class ScoreResult(TypedDict):
    score: int
    level: ScoreLevel
    reasons: list[str]


MAJOR_SEC_EVENT_TYPES = {"8-k", "10-q", "10-k", "s-1"}
OWNERSHIP_SEC_EVENT_TYPES = {"form 4", "4", "13d", "13g"}


def score_event(event: MarketEvent) -> ScoreResult:
    score = 0
    reasons: list[str] = []
    text = f"{event.title} {event.summary or ''}".lower()
    event_type = event.event_type.strip().lower()

    if event_type == "company_news":
        score += 1
        reasons.append("Company news event")

    if "earnings" in text:
        score += 4
        reasons.append("Mentions earnings")

    if "guidance" in text:
        score += 5
        reasons.append("Mentions guidance")

    if _contains_any(text, ["acquisition", "merger"]):
        score += 5
        reasons.append("Mentions acquisition or merger")

    if _contains_any(text, ["lawsuit", "investigation"]):
        score += 4
        reasons.append("Mentions lawsuit or investigation")

    if _contains_any(text, ["bankruptcy", "restructuring"]):
        score += 5
        reasons.append("Mentions bankruptcy or restructuring")

    if _contains_any(text, ["upgrade", "downgrade"]):
        score += 3
        reasons.append("Mentions upgrade or downgrade")

    if _contains_any(text, ["ceo", "cfo"]) and _contains_any(text, ["resigns", "steps down"]):
        score += 4
        reasons.append("Mentions CEO or CFO resignation")

    if _contains_any(text, ["fda approval", "fda rejection"]):
        score += 5
        reasons.append("Mentions FDA approval or rejection")

    if event_type in MAJOR_SEC_EVENT_TYPES:
        score += 4
        reasons.append(f"SEC filing event: {event.event_type}")

    if event_type in OWNERSHIP_SEC_EVENT_TYPES:
        score += 3
        reasons.append(f"SEC ownership event: {event.event_type}")

    return {
        "score": score,
        "level": _level_for_score(score),
        "reasons": reasons,
    }


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _level_for_score(score: int) -> ScoreLevel:
    if score >= 6:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"
