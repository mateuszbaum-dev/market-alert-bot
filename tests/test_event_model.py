from src.models.event import MarketEvent, generate_event_id


def test_creating_market_event() -> None:
    event = MarketEvent(
        event_id="event-1",
        symbol="AAPL",
        source="example",
        event_type="news",
        title="Apple announces update",
        url="https://example.com/apple",
        published_at="2026-06-04T10:00:00Z",
        summary="Short summary",
        raw_payload={"id": 123},
    )

    assert event.event_id == "event-1"
    assert event.symbol == "AAPL"
    assert event.summary == "Short summary"
    assert event.raw_payload == {"id": 123}


def test_generate_event_id_is_stable_for_same_input() -> None:
    first = generate_event_id(
        source="news",
        symbol="AAPL",
        title="Apple announces update",
        url="https://example.com/apple",
        published_at="2026-06-04T10:00:00Z",
    )
    second = generate_event_id(
        source="news",
        symbol="AAPL",
        title="Apple announces update",
        url="https://example.com/apple",
        published_at="2026-06-04T10:00:00Z",
    )

    assert first == second


def test_generate_event_id_changes_when_title_or_url_changes() -> None:
    base = generate_event_id(
        source="news",
        symbol="AAPL",
        title="Apple announces update",
        url="https://example.com/apple",
        published_at="2026-06-04T10:00:00Z",
    )
    changed_title = generate_event_id(
        source="news",
        symbol="AAPL",
        title="Apple announces major update",
        url="https://example.com/apple",
        published_at="2026-06-04T10:00:00Z",
    )
    changed_url = generate_event_id(
        source="news",
        symbol="AAPL",
        title="Apple announces update",
        url="https://example.com/apple-2",
        published_at="2026-06-04T10:00:00Z",
    )

    assert base != changed_title
    assert base != changed_url
