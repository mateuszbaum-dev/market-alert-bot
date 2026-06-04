from datetime import datetime, timezone

import pytest

from src.models.event import generate_event_id
from src.providers import finnhub


class FakeResponse:
    def __init__(self, status_code: int, payload, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def test_missing_api_key_raises_value_error(monkeypatch) -> None:
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setattr(finnhub, "load_dotenv", lambda: None)

    with pytest.raises(ValueError, match="FINNHUB_API_KEY is required"):
        finnhub.fetch_company_news("AAPL")


def test_successful_response_with_one_article(monkeypatch) -> None:
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    monkeypatch.setattr(finnhub, "load_dotenv", lambda: None)
    article = {
        "headline": "Apple announces update",
        "url": "https://example.com/apple",
        "datetime": 1_717_500_000,
        "summary": "Apple shared an update.",
        "id": 123,
    }
    calls = []

    def fake_get(url, params, timeout):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(200, [article])

    monkeypatch.setattr(finnhub.requests, "get", fake_get)

    events = finnhub.fetch_company_news("AAPL")

    published_at = datetime.fromtimestamp(article["datetime"], tz=timezone.utc).isoformat()
    expected_event_id = generate_event_id(
        "finnhub",
        "AAPL",
        article["headline"],
        article["url"],
        published_at,
    )

    assert len(events) == 1
    assert events[0].event_id == expected_event_id
    assert events[0].symbol == "AAPL"
    assert events[0].source == "finnhub"
    assert events[0].event_type == "company_news"
    assert events[0].title == article["headline"]
    assert events[0].url == article["url"]
    assert events[0].published_at == published_at
    assert events[0].summary == article["summary"]
    assert events[0].raw_payload == article
    assert calls[0]["url"] == finnhub.FINNHUB_COMPANY_NEWS_URL
    assert calls[0]["params"]["symbol"] == "AAPL"
    assert calls[0]["params"]["token"] == "test-key"
    assert calls[0]["timeout"] == finnhub.REQUEST_TIMEOUT_SECONDS


def test_response_with_missing_headline_or_url_is_skipped(monkeypatch) -> None:
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    monkeypatch.setattr(finnhub, "load_dotenv", lambda: None)

    def fake_get(url, params, timeout):
        return FakeResponse(
            200,
            [
                {"headline": "", "url": "https://example.com/empty-headline"},
                {"headline": "Missing URL", "url": ""},
                {"headline": "Valid article", "url": "https://example.com/valid"},
            ],
        )

    monkeypatch.setattr(finnhub.requests, "get", fake_get)

    events = finnhub.fetch_company_news("MSFT")

    assert len(events) == 1
    assert events[0].title == "Valid article"


def test_non_200_response_raises_clear_error(monkeypatch) -> None:
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    monkeypatch.setattr(finnhub, "load_dotenv", lambda: None)

    def fake_get(url, params, timeout):
        return FakeResponse(429, {"error": "rate limit"}, text="rate limit")

    monkeypatch.setattr(finnhub.requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="status 429"):
        finnhub.fetch_company_news("AAPL")
