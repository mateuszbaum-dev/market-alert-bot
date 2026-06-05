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
    watchlist_source: str = "yaml"
    google_sheets_credentials_path: str = ""
    google_sheets_spreadsheet_id: str = ""
    google_sheets_range: str = "Watchlist!A2:A"


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        watchlist_path=Path(os.getenv("WATCHLIST_PATH", "watchlist.yaml")),
        watchlist_source=os.getenv("WATCHLIST_SOURCE", "yaml").strip().lower(),
        google_sheets_credentials_path=os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "").strip(),
        google_sheets_spreadsheet_id=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip(),
        google_sheets_range=os.getenv("GOOGLE_SHEETS_RANGE", "Watchlist!A2:A").strip(),
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


def load_watchlist_symbols(settings: Settings | None = None) -> list[str]:
    settings = settings or load_settings()

    if settings.watchlist_source == "yaml":
        return [target.ticker for target in load_watchlist(settings.watchlist_path)]

    if settings.watchlist_source == "google_sheets":
        try:
            return _load_google_sheet_symbols(settings)
        except (ValueError, FileNotFoundError):
            raise
        except Exception as exc:
            raise RuntimeError(f"Failed to load Google Sheets watchlist: {exc}") from exc

    raise ValueError(f"Unsupported WATCHLIST_SOURCE: {settings.watchlist_source}")


def _normalize_cik(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.zfill(10)


def _load_google_sheet_symbols(settings: Settings) -> list[str]:
    from src.providers.google_sheets_watchlist import load_symbols_from_google_sheets

    return load_symbols_from_google_sheets(
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        range_name=settings.google_sheets_range,
        credentials_path=settings.google_sheets_credentials_path,
    )
