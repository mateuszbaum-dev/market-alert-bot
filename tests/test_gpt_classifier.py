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


def test_successful_valid_gpt_response_with_all_new_fields(monkeypatch) -> None:
    payload = {
        "impact_level": "HIGH",
        "impact_score": 8,
        "market_direction": "BULLISH",
        "direction_confidence": 76,
        "event_probability": 72,
        "category": "earnings",
        "reasoning_summary": "The event may be relevant for monitoring due to earnings context.",
        "should_notify": True,
    }
    calls = _mock_openai(monkeypatch, payload)

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


def test_invalid_impact_score_returns_fallback(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["impact_score"] = 11
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result == _fallback(score_level="HIGH", impact_score=6, event_probability=50, should_notify=True)
    captured = capsys.readouterr()
    assert "symbol=AAPL event_id=event-1" in captured.out
    assert "invalid impact_score range" in captured.out


def test_invalid_direction_confidence_returns_fallback(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["direction_confidence"] = -1
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=5, level="MEDIUM"))

    assert result == _fallback(score_level="MEDIUM", impact_score=4, event_probability=35, should_notify=False)
    captured = capsys.readouterr()
    assert "invalid direction_confidence range" in captured.out


def test_invalid_event_probability_returns_fallback(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["event_probability"] = 101
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=2, level="LOW"))

    assert result == _fallback(score_level="LOW", impact_score=2, event_probability=20, should_notify=False)
    captured = capsys.readouterr()
    assert "invalid event_probability range" in captured.out


def test_invalid_market_direction_returns_fallback(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["market_direction"] = "POSITIVE"
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["market_direction"] == "UNCLEAR"
    assert result["category"] == "rule_based_fallback"
    assert result["should_notify"] is True
    captured = capsys.readouterr()
    assert "invalid market_direction" in captured.out


def test_missing_required_field_returns_fallback_and_logs_reason(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    del payload["category"]
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result == _fallback(score_level="HIGH", impact_score=6, event_probability=50, should_notify=True)
    captured = capsys.readouterr()
    assert "missing required field" in captured.out
    assert "category" in captured.out


def test_invalid_json_returns_rule_based_fallback(monkeypatch, capsys) -> None:
    _mock_openai(monkeypatch, "not json", raw_content=True)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result == _fallback(score_level="HIGH", impact_score=6, event_probability=50, should_notify=True)
    captured = capsys.readouterr()
    assert "invalid JSON response" in captured.out


def test_api_failure_returns_rule_based_fallback(monkeypatch, capsys) -> None:
    _mock_openai(monkeypatch, RuntimeError("api failed for key test-key"))

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=5, level="MEDIUM"))

    assert result == _fallback(score_level="MEDIUM", impact_score=4, event_probability=35, should_notify=False)
    captured = capsys.readouterr()
    assert "OpenAI API error" in captured.out
    assert "[REDACTED]" in captured.out
    assert "test-key" not in captured.out


def _mock_openai(monkeypatch, payload, raw_content: bool = False) -> list[dict]:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setattr(gpt_classifier, "load_dotenv", lambda: None)
    calls = []

    class FakeOpenAI:
        def __init__(self, api_key, timeout) -> None:
            calls.append({"api_key": api_key, "timeout": timeout})
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create),
            )

        def create(self, **kwargs):
            calls.append(kwargs)
            if isinstance(payload, Exception):
                raise payload
            content = payload if raw_content else json.dumps(payload)
            return _response(content)

    monkeypatch.setattr(gpt_classifier, "OpenAI", FakeOpenAI)
    return calls


def _valid_payload() -> dict:
    return {
        "impact_level": "HIGH",
        "impact_score": 8,
        "market_direction": "BULLISH",
        "direction_confidence": 76,
        "event_probability": 72,
        "category": "earnings",
        "reasoning_summary": "The event may be relevant for monitoring due to earnings context.",
        "should_notify": True,
    }


def _fallback(score_level: str, impact_score: int, event_probability: int, should_notify: bool) -> dict:
    return {
        "impact_level": score_level,
        "impact_score": impact_score,
        "market_direction": "UNCLEAR",
        "direction_confidence": 40,
        "event_probability": event_probability,
        "category": "rule_based_fallback",
        "reasoning_summary": "GPT classification failed or returned invalid data; using rule-based score.",
        "should_notify": should_notify,
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
