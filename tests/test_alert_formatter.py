from src.models.event import MarketEvent
from src.notifications.formatter import DISCLAIMER, format_market_alert


def test_high_alert_with_gpt_result() -> None:
    message = format_market_alert(
        _event(),
        {"score": 5, "level": "MEDIUM", "reasons": ["Mentions earnings"]},
        {
            "impact_level": "HIGH",
            "confidence": 91,
            "category": "earnings",
            "reasoning_summary": "Relevant for market monitoring.",
            "should_notify": True,
        },
    )

    assert message.startswith("\U0001f6a8 Market Monitoring Alert")
    assert "Symbol: AAPL" in message
    assert "Impact Level: HIGH" in message
    assert "Rule Score: 5" in message
    assert "- Mentions earnings" in message
    assert "GPT Category: earnings" in message
    assert "GPT Confidence: 91" in message
    assert "GPT Summary: Relevant for market monitoring." in message


def test_medium_alert_without_gpt_result() -> None:
    message = format_market_alert(
        _event(),
        {"score": 4, "level": "MEDIUM", "reasons": ["SEC filing event: 8-K"]},
    )

    assert message.startswith("\u26a0\ufe0f Market Monitoring Alert")
    assert "Impact Level: MEDIUM" in message
    assert "- SEC filing event: 8-K" in message
    assert "GPT Category:" not in message


def test_missing_url_does_not_crash() -> None:
    message = format_market_alert(
        _event(url=""),
        {"score": 1, "level": "LOW", "reasons": []},
    )

    assert message.startswith("\u2139\ufe0f Market Monitoring Alert")
    assert "Link:" not in message
    assert "- None provided" in message


def test_disclaimer_is_included() -> None:
    message = format_market_alert(
        _event(),
        {"score": 1, "level": "LOW", "reasons": []},
    )

    assert DISCLAIMER in message


def _event(url: str = "https://example.com/aapl") -> MarketEvent:
    return MarketEvent(
        event_id="event-1",
        symbol="AAPL",
        source="finnhub",
        event_type="company_news",
        title="Apple reports earnings",
        url=url,
        published_at="2026-06-04T10:00:00Z",
        summary="Company earnings were released.",
    )
