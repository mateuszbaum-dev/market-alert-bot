from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    symbol: str
    source: str
    event_type: str
    title: str
    url: str
    published_at: str
    summary: str | None = None
    raw_payload: dict | None = None


def generate_event_id(
    source: str,
    symbol: str,
    title: str,
    url: str,
    published_at: str,
) -> str:
    raw = "|".join(
        [
            source.strip().lower(),
            symbol.strip().upper(),
            title.strip(),
            url.strip(),
            published_at.strip(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
