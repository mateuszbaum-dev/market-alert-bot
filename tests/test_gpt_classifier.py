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


def test_direction_confidence_percent_string_becomes_int(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["direction_confidence"] = "75%"
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["direction_confidence"] == 75
    assert result["category"] == "earnings"
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_direction_confidence_decimal_becomes_percent(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["direction_confidence"] = 0.75
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["direction_confidence"] == 75
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_direction_confidence_about_string_becomes_int(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["direction_confidence"] = "about 60"
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["direction_confidence"] == 60
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_direction_confidence_above_range_is_clamped(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["direction_confidence"] = 150
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["direction_confidence"] == 100
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_impact_score_fraction_string_becomes_int(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["impact_score"] = "8/10"
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["impact_score"] == 8
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_event_probability_percent_string_becomes_int(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["event_probability"] = "45%"
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["event_probability"] == 45
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_invalid_numeric_field_uses_default_without_fallback(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["impact_score"] = "not sure"
    payload["direction_confidence"] = ""
    payload["event_probability"] = None
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=5, level="MEDIUM"))

    assert result["impact_score"] == 4
    assert result["direction_confidence"] == 40
    assert result["event_probability"] == 35
    assert result["category"] == "earnings"
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_valid_gpt_response_with_numeric_strings_does_not_fallback(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["impact_level"] = "medium"
    payload["impact_score"] = "8"
    payload["direction_confidence"] = "75%"
    payload["event_probability"] = "0.45"
    payload["should_notify"] = "true"
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["impact_level"] == "MEDIUM"
    assert result["impact_score"] == 8
    assert result["direction_confidence"] == 75
    assert result["event_probability"] == 45
    assert result["should_notify"] is True
    assert result["category"] == "earnings"
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


def test_normalize_market_direction_lowercase_bullish() -> None:
    assert gpt_classifier.normalize_market_direction("bullish") == "BULLISH"


def test_normalize_market_direction_slightly_bullish() -> None:
    assert gpt_classifier.normalize_market_direction("Slightly bullish") == "BULLISH"


def test_normalize_market_direction_negative() -> None:
    assert gpt_classifier.normalize_market_direction("negative") == "BEARISH"


def test_normalize_market_direction_mixed() -> None:
    assert gpt_classifier.normalize_market_direction("mixed") == "UNCLEAR"


def test_normalize_market_direction_unexpected_value() -> None:
    assert gpt_classifier.normalize_market_direction("directionally complex") == "UNCLEAR"


def test_lowercase_market_direction_does_not_fallback(monkeypatch, capsys) -> None:
    payload = _valid_payload()
    payload["market_direction"] = "bullish"
    _mock_openai(monkeypatch, payload)

    result = gpt_classifier.classify_event_with_gpt(_event(), _rule_score(score=7, level="HIGH"))

    assert result["market_direction"] == "BULLISH"
    assert result["category"] == "earnings"
    assert result["should_notify"] is True
    captured = capsys.readouterr()
    assert "GPT classification fallback" not in captured.out


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
