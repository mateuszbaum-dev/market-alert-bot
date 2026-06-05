from __future__ import annotations

from pathlib import Path
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


def load_symbols_from_google_sheets(
    spreadsheet_id: str,
    range_name: str,
    credentials_path: str,
) -> list[str]:
    spreadsheet_id = (spreadsheet_id or "").strip()
    range_name = (range_name or "").strip()
    credentials_path = (credentials_path or "").strip()

    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is required")
    if not range_name:
        raise ValueError("GOOGLE_SHEETS_RANGE is required")
    if not credentials_path:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS_PATH is required")

    credentials_file = Path(credentials_path)
    if not credentials_file.exists():
        raise FileNotFoundError(f"Google Sheets credentials file not found: {credentials_path}")

    credentials = Credentials.from_service_account_file(
        credentials_path,
        scopes=[SHEETS_READONLY_SCOPE],
    )
    service = build("sheets", "v4", credentials=credentials)
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    return _normalize_symbol_rows(response.get("values", []))


def _normalize_symbol_rows(rows: list[list[Any]]) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()

    for row in rows:
        if not row:
            continue
        symbol = str(row[0]).strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)

    return symbols
