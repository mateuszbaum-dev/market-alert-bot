from src.models.event import MarketEvent
from src.notifications.formatter import format_market_alert


def test_ticker_appears_bold() -> None:
    message = format_market_alert(_event(symbol="NVDA"), _rule_score(), _gpt_result("BULLISH"))

    assert "Ticker: <b>NVDA</b>" in message


def test_bullish_direction_displays_green_indicator() -> None:
    message = format_market_alert(_event(), _rule_score(), _gpt_result("BULLISH"))

    assert "Direction: \U0001f7e2 BULLISH" in message


def test_bearish_direction_displays_red_indicator() -> None:
    message = format_market_alert(_event(), _rule_score(), _gpt_result("BEARISH"))

    assert "Direction: \U0001f534 BEARISH" in message


def test_neutral_direction_displays_yellow_indicator() -> None:
    message = format_market_alert(_event(), _rule_score(), _gpt_result("NEUTRAL"))

    assert "Direction: \U0001f7e1 NEUTRAL" in message


def test_unclear_direction_displays_white_indicator() -> None:
    message = format_market_alert(_event(), _rule_score(), _gpt_result("UNCLEAR"))

    assert "Direction: \u26aa UNCLEAR" in message


def test_disclaimer_text_is_not_included() -> None:
    message = format_market_alert(_event(), _rule_score(), _gpt_result("BULLISH"))

    assert "Monitoring alert only. Not financial advice." not in message


def test_dynamic_text_is_html_escaped() -> None:
    message = format_market_alert(
        _event(title="Nvidia <beats> & raises", url="https://example.com/a?x=1&y=2"),
        _rule_score(),
        _gpt_result("BULLISH", category="earnings & guidance", reasoning_summary="Demand <supply> & improving."),
    )

    assert "Nvidia &lt;beats&gt; &amp; raises" in message
    assert "Category: earnings &amp; guidance" in message
    assert "Demand &lt;supply&gt; &amp; improving." in message
    assert "https://example.com/a?x=1&amp;y=2" in message


def _event(
    symbol: str = "NVDA",
    title: str = "Nvidia shares move after new AI chip demand report",
    url: str = "https://example.com/nvda",
) -> MarketEvent:
    return MarketEvent(
        event_id="event-1",
        symbol=symbol,
        source="finnhub",
        event_type="company_news",
        title=title,
        url=url,
        published_at="2026-06-05T10:00:00Z",
        summary="Demand report.",
    )


def _rule_score() -> dict:
    return {"score": 6, "level": "HIGH", "reasons": ["Mentions guidance"]}


def _gpt_result(
    direction: str,
    category: str = "earnings",
    reasoning_summary: str = "The news may be interpreted positively because it suggests strong demand.",
) -> dict:
    return {
        "impact_level": "HIGH",
        "impact_score": 8,
        "market_direction": direction,
        "direction_confidence": 78,
        "event_probability": 65,
        "category": category,
        "reasoning_summary": reasoning_summary,
        "should_notify": True,
    }
