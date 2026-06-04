from src.models.event import MarketEvent
from src.scoring.rules import score_event


def test_basic_company_news_is_low() -> None:
    result = score_event(_event(event_type="company_news", title="Apple releases product update"))

    assert result["score"] == 1
    assert result["level"] == "LOW"
    assert "Company news event" in result["reasons"]


def test_earnings_news_is_medium_or_high() -> None:
    result = score_event(_event(event_type="company_news", title="Apple reports earnings"))

    assert result["score"] == 5
    assert result["level"] == "MEDIUM"
    assert "Mentions earnings" in result["reasons"]


def test_acquisition_or_merger_news_is_high() -> None:
    result = score_event(
        _event(
            event_type="company_news",
            title="Apple announces acquisition",
            summary="The company confirmed merger plans.",
        )
    )

    assert result["score"] == 6
    assert result["level"] == "HIGH"
    assert "Mentions acquisition or merger" in result["reasons"]


def test_lawsuit_or_investigation_news() -> None:
    result = score_event(
        _event(
            event_type="company_news",
            title="Apple faces lawsuit",
            summary="Regulators opened an investigation.",
        )
    )

    assert result["score"] == 5
    assert result["level"] == "MEDIUM"
    assert "Mentions lawsuit or investigation" in result["reasons"]


def test_ceo_resigns_news() -> None:
    result = score_event(_event(event_type="company_news", title="Apple CEO resigns"))

    assert result["score"] == 5
    assert result["level"] == "MEDIUM"
    assert "Mentions CEO or CFO resignation" in result["reasons"]


def test_sec_8k_event() -> None:
    result = score_event(_event(event_type="8-K", title="Apple files current report"))

    assert result["score"] == 4
    assert result["level"] == "MEDIUM"
    assert "SEC filing event: 8-K" in result["reasons"]


def test_case_insensitive_matching() -> None:
    result = score_event(
        _event(
            event_type="COMPANY_NEWS",
            title="Apple issues GUIDANCE update",
            summary="The CFO STEPS DOWN.",
        )
    )

    assert result["score"] == 10
    assert result["level"] == "HIGH"
    assert "Company news event" in result["reasons"]
    assert "Mentions guidance" in result["reasons"]
    assert "Mentions CEO or CFO resignation" in result["reasons"]


def _event(event_type: str, title: str, summary: str | None = None) -> MarketEvent:
    return MarketEvent(
        event_id="event-1",
        symbol="AAPL",
        source="test",
        event_type=event_type,
        title=title,
        url="https://example.com",
        published_at="2026-06-04T10:00:00Z",
        summary=summary,
    )
