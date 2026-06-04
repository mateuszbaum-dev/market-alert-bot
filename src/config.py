from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class WatchTarget:
    name: str
    ticker: str
    cik: str | None = None
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Settings:
    watchlist_path: Path


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        watchlist_path=Path(os.getenv("WATCHLIST_PATH", "watchlist.yaml")),
    )


def load_watchlist(path: Path) -> list[WatchTarget]:
    if not path.exists():
        raise FileNotFoundError(f"Watchlist not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}

    companies = data.get("companies", [])
    if not isinstance(companies, list):
        raise ValueError("watchlist.yaml must contain a 'companies' list")

    return [
        WatchTarget(
            name=str(item["name"]),
            ticker=str(item["ticker"]).upper(),
            cik=_normalize_cik(item.get("cik")),
            keywords=[str(keyword) for keyword in item.get("keywords", [])],
        )
        for item in companies
    ]


def _normalize_cik(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.zfill(10)
