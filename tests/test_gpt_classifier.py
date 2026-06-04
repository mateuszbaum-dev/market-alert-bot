import json
from types import SimpleNamespace

import pytest

from src.models.event import MarketEvent
from src.scoring import gpt_classifier


def test_missing_api_key_raises_value_error(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(gpt_classifier, "load_dotenv", lambda: None)

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        gpt_classifier.classify_event_with_gpt(_event(), _rule_score())


def test_successful_valid_json_response(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setattr(gpt_classifier, "load_dotenv", lambda: None)
    calls = []
    payload = {
        "impact_level": "HIGH",
        "confidence": 87,
        "category": "earnings",
        "reasoning_summary": "The event may matter for market monitoring.",
        "should_notify": True,
    }

    class FakeOpenAI:
        def __init__(self, api_key, timeout) -> None:
            calls.append({"api_key": api_key, "timeout": timeout})
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create),
            )

        def create(self, **kwargs):
            calls.append(kwargs)
            return _response(json.dumps(payload))

    monkeypatch.setattr(gpt_classifier, "OpenAI", FakeOpenAI)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score())

    assert result == payload
    assert calls[0]["api_key"] == "test-key"
    assert calls[0]["timeout"] == gpt_classifier.OPENAI_TIMEOUT_SECONDS
    assert calls[1]["model"] == "test-model"
    assert calls[1]["response_format"] == {"type": "json_object"}
    compact_payload = json.loads(calls[1]["messages"][1]["content"])
    assert set(compact_payload) == {
        "symbol",
        "source",
        "event_type",
        "title",
        "summary",
        "url",
        "rule_score",
    }


def test_invalid_json_returns_rule_based_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(gpt_classifier, "load_dotenv", lambda: None)

    class FakeOpenAI:
        def __init__(self, api_key, timeout) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: _response("not json")),
            )

    monkeypatch.setattr(gpt_classifier, "OpenAI", FakeOpenAI)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result == {
        "impact_level": "HIGH",
        "confidence": 50,
        "category": "rule_based_fallback",
        "reasoning_summary": "GPT classification failed; using rule-based score.",
        "should_notify": True,
    }


def test_api_failure_returns_rule_based_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(gpt_classifier, "load_dotenv", lambda: None)

    class FakeOpenAI:
        def __init__(self, api_key, timeout) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create),
            )

        def create(self, **kwargs):
            raise RuntimeError("api failed")

    monkeypatch.setattr(gpt_classifier, "OpenAI", FakeOpenAI)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=5, level="MEDIUM"))

    assert result == {
        "impact_level": "MEDIUM",
        "confidence": 50,
        "category": "rule_based_fallback",
        "reasoning_summary": "GPT classification failed; using rule-based score.",
        "should_notify": False,
    }


def _event() -> MarketEvent:
    return MarketEvent(
        event_id="event-1",
        symbol="AAPL",
        source="finnhub",
        event_type="company_news",
        title="Apple reports earnings",
        url="https://example.com/aapl",
        published_at="2026-06-04T10:00:00Z",
        summary="Company earnings were released.",
        raw_payload={"ignored": True},
    )


def _rule_score(score: int = 5, level: str = "MEDIUM") -> dict:
    return {
        "score": score,
        "level": level,
        "reasons": ["Company news event", "Mentions earnings"],
    }


def _response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )
