from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv

from src.models.event import MarketEvent, generate_event_id

FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"
REQUEST_TIMEOUT_SECONDS = 10


def fetch_company_news(symbol: str, days_back: int = 1) -> list[MarketEvent]:
    load_dotenv()
    api_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not api_key:
        raise ValueError("FINNHUB_API_KEY is required to fetch Finnhub company news")

    today = date.today()
    from_date = today - timedelta(days=days_back)

    try:
        response = requests.get(
            FINNHUB_COMPANY_NEWS_URL,
            params={
                "symbol": symbol,
                "from": from_date.isoformat(),
                "to": today.isoformat(),
                "token": api_key,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Finnhub company news request failed: {exc}") from exc

    if response.status_code != 200:
        response_text = getattr(response, "text", "")
        raise RuntimeError(
            f"Finnhub company news request failed with status {response.status_code}: {response_text}"
        )

    try:
        articles = response.json()
    except ValueError as exc:
        raise RuntimeError("Finnhub company news response was not valid JSON") from exc

    if not isinstance(articles, list):
        raise RuntimeError("Finnhub company news response must be a list of articles")

    return [_article_to_event(symbol, article) for article in articles if _has_required_fields(article)]


def _article_to_event(symbol: str, article: dict[str, Any]) -> MarketEvent:
    title = str(article["headline"]).strip()
    url = str(article["url"]).strip()
    published_at = _published_at_to_iso(article.get("datetime"))
    event_id = generate_event_id(
        source="finnhub",
        symbol=symbol,
        title=title,
        url=url,
        published_at=published_at,
    )

    return MarketEvent(
        event_id=event_id,
        symbol=symbol,
        source="finnhub",
        event_type="company_news",
        title=title,
        url=url,
        published_at=published_at,
        summary=article.get("summary"),
        raw_payload=article,
    )


def _has_required_fields(article: Any) -> bool:
    if not isinstance(article, dict):
        return False
    return bool(str(article.get("headline") or "").strip()) and bool(str(article.get("url") or "").strip())


def _published_at_to_iso(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return str(value)
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
