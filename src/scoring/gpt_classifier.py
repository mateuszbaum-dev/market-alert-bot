from __future__ import annotations

import json
import os
import re
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from openai import OpenAI

from src.models.event import MarketEvent

ImpactLevel = Literal["LOW", "MEDIUM", "HIGH"]
MarketDirection = Literal["BULLISH", "BEARISH", "NEUTRAL", "UNCLEAR"]

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
OPENAI_TIMEOUT_SECONDS = 20
VALID_IMPACT_LEVELS = {"LOW", "MEDIUM", "HIGH"}
VALID_MARKET_DIRECTIONS = {"BULLISH", "BEARISH", "NEUTRAL", "UNCLEAR"}


class GptClassification(TypedDict):
    impact_level: ImpactLevel
    impact_score: int
    market_direction: MarketDirection
    direction_confidence: int
    event_probability: int
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
                        "Classify this event for market monitoring only. Do not provide investment "
                        "advice. Do not recommend buying, selling, holding, shorting, or trading. "
                        "Do not predict exact price movement or claim certainty. Be conservative "
                        "when information is vague. Return only valid JSON with exactly these keys: "
                        "impact_level, impact_score, market_direction, direction_confidence, "
                        "event_probability, category, reasoning_summary, should_notify."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(_compact_event_payload(event, rule_score), separators=(",", ":")),
                },
            ],
        )
        content = response.choices[0].message.content or ""
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON response from GPT classifier") from exc
        return _validate_classification(payload)
    except Exception as exc:
        _log_fallback_reason(event, exc)
        return fallback_classification(rule_score)


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


def _validate_classification(payload: Any) -> GptClassification:
    if not isinstance(payload, dict):
        raise ValueError("GPT classification must be a JSON object")

    impact_level = _required_choice(payload, "impact_level", VALID_IMPACT_LEVELS)
    market_direction = _required_choice(payload, "market_direction", VALID_MARKET_DIRECTIONS)

    return {
        "impact_level": impact_level,  # type: ignore[typeddict-item]
        "impact_score": _required_int(payload, "impact_score", minimum=1, maximum=10),
        "market_direction": market_direction,  # type: ignore[typeddict-item]
        "direction_confidence": _required_int(payload, "direction_confidence", minimum=0, maximum=100),
        "event_probability": _required_int(payload, "event_probability", minimum=0, maximum=100),
        "category": _required_text(payload, "category"),
        "reasoning_summary": _required_text(payload, "reasoning_summary"),
        "should_notify": _required_bool(payload, "should_notify"),
    }


def fallback_classification(rule_score: dict) -> GptClassification:
    rule_score_value = _rule_score_value(rule_score)
    return {
        "impact_level": _rule_level(rule_score),  # type: ignore[typeddict-item]
        "impact_score": _fallback_impact_score(rule_score_value),
        "market_direction": "UNCLEAR",
        "direction_confidence": 40,
        "event_probability": _fallback_event_probability(rule_score_value),
        "category": "rule_based_fallback",
        "reasoning_summary": "GPT classification failed or returned invalid data; using rule-based score.",
        "should_notify": rule_score_value >= 6,
    }


def _required_choice(payload: dict[str, Any], key: str, valid_values: set[str]) -> str:
    if key not in payload:
        raise ValueError(f"Missing required GPT field: {key}")
    value = str(payload[key]).upper()
    if value not in valid_values:
        raise ValueError(f"Invalid GPT field value: {key}")
    return value


def _required_int(payload: dict[str, Any], key: str, minimum: int, maximum: int) -> int:
    if key not in payload:
        raise ValueError(f"Missing required GPT field: {key}")
    if isinstance(payload[key], bool) or not isinstance(payload[key], int):
        raise ValueError(f"Invalid GPT integer field: {key}")
    value = payload[key]
    if value < minimum or value > maximum:
        raise ValueError(f"Invalid GPT field range: {key} must be between {minimum} and {maximum}")
    return value


def _required_text(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        raise ValueError(f"Missing required GPT text field: {key}")
    value = str(payload[key]).strip()
    if not value:
        raise ValueError(f"Empty GPT text field: {key}")
    return value


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    if key not in payload or not isinstance(payload[key], bool):
        raise ValueError(f"Missing or invalid GPT boolean field: {key}")
    return payload[key]


def _log_fallback_reason(event: MarketEvent, exc: Exception) -> None:
    symbol = _safe_context_value(getattr(event, "symbol", None))
    event_id = _safe_context_value(getattr(event, "event_id", None))
    reason = _fallback_reason(exc)
    print(f"GPT classification fallback for symbol={symbol} event_id={event_id}: {reason}")


def _fallback_reason(exc: Exception) -> str:
    message = _safe_error_message(exc)
    lower_message = message.lower()

    if isinstance(exc, ValueError) and "invalid json response" in lower_message:
        return f"invalid JSON response ({type(exc).__name__}: {message})"
    if "missing required gpt field" in lower_message or "missing required gpt text field" in lower_message:
        return f"missing required field ({type(exc).__name__}: {message})"
    if "impact_score" in lower_message and ("range" in lower_message or "integer" in lower_message):
        return f"invalid impact_score range ({type(exc).__name__}: {message})"
    if "market_direction" in lower_message:
        return f"invalid market_direction ({type(exc).__name__}: {message})"
    if "direction_confidence" in lower_message and ("range" in lower_message or "integer" in lower_message):
        return f"invalid direction_confidence range ({type(exc).__name__}: {message})"
    if "event_probability" in lower_message and ("range" in lower_message or "integer" in lower_message):
        return f"invalid event_probability range ({type(exc).__name__}: {message})"
    return f"OpenAI API error ({type(exc).__name__}: {message})"


def _safe_context_value(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text or "N/A"


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip() or "No error message provided"
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    return re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", message)


def _rule_score_value(rule_score: dict) -> int:
    try:
        return int(rule_score.get("score", 0))
    except (TypeError, ValueError):
        return 0


def _rule_level(rule_score: dict) -> str:
    level = str(rule_score.get("level", "LOW")).upper()
    if level in VALID_IMPACT_LEVELS:
        return level
    return "LOW"


def _fallback_impact_score(rule_score_value: int) -> int:
    if rule_score_value >= 6:
        return 6
    if rule_score_value >= 3:
        return 4
    return 2


def _fallback_event_probability(rule_score_value: int) -> int:
    if rule_score_value >= 6:
        return 50
    if rule_score_value >= 3:
        return 35
    return 20
