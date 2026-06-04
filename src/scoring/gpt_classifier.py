from __future__ import annotations

import json
import os
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from openai import OpenAI

from src.models.event import MarketEvent

ImpactLevel = Literal["LOW", "MEDIUM", "HIGH"]

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
OPENAI_TIMEOUT_SECONDS = 20
VALID_IMPACT_LEVELS = {"LOW", "MEDIUM", "HIGH"}


class GptClassification(TypedDict):
    impact_level: ImpactLevel
    confidence: int
    category: str
    reasoning_summary: str
    should_notify: bool


def classify_event_with_gpt(event: MarketEvent, rule_score: dict) -> GptClassification:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for GPT market event classification")

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    try:
        client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT_SECONDS)
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify market-monitoring relevance. Do not provide investment advice. "
                        "Do not recommend buying or selling. Return only valid JSON with keys: "
                        "impact_level, confidence, category, reasoning_summary, should_notify."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(_compact_event_payload(event, rule_score), separators=(",", ":")),
                },
            ],
        )
        content = response.choices[0].message.content or ""
        return _normalize_classification(json.loads(content), rule_score)
    except Exception:
        return _fallback_classification(rule_score)


def _compact_event_payload(event: MarketEvent, rule_score: dict) -> dict[str, Any]:
    return {
        "symbol": event.symbol,
        "source": event.source,
        "event_type": event.event_type,
        "title": event.title,
        "summary": event.summary,
        "url": event.url,
        "rule_score": rule_score,
    }


def _normalize_classification(payload: dict[str, Any], rule_score: dict) -> GptClassification:
    impact_level = str(payload.get("impact_level", rule_score.get("level", "LOW"))).upper()
    if impact_level not in VALID_IMPACT_LEVELS:
        impact_level = str(rule_score.get("level", "LOW")).upper()
    if impact_level not in VALID_IMPACT_LEVELS:
        impact_level = "LOW"

    return {
        "impact_level": impact_level,  # type: ignore[typeddict-item]
        "confidence": _clamp_int(payload.get("confidence", 50), minimum=0, maximum=100),
        "category": str(payload.get("category", "market_monitoring")),
        "reasoning_summary": str(payload.get("reasoning_summary", "")),
        "should_notify": _coerce_bool(payload.get("should_notify", rule_score.get("score", 0) >= 6)),
    }


def _fallback_classification(rule_score: dict) -> GptClassification:
    return {
        "impact_level": str(rule_score.get("level", "LOW")).upper(),  # type: ignore[typeddict-item]
        "confidence": 50,
        "category": "rule_based_fallback",
        "reasoning_summary": "GPT classification failed; using rule-based score.",
        "should_notify": int(rule_score.get("score", 0)) >= 6,
    }


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = minimum
    return max(minimum, min(maximum, number))


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)
