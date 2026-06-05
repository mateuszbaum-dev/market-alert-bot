from pathlib import Path

import pytest

from src.providers import google_sheets_watchlist as watchlist


def test_missing_spreadsheet_id_raises_value_error(tmp_path: Path) -> None:
    credentials = _credentials_file(tmp_path)

    with pytest.raises(ValueError, match="GOOGLE_SHEETS_SPREADSHEET_ID is required"):
        watchlist.load_symbols_from_google_sheets("", "Watchlist!A2:A", str(credentials))


def test_missing_credentials_path_raises_value_error() -> None:
    with pytest.raises(ValueError, match="GOOGLE_SHEETS_CREDENTIALS_PATH is required"):
        watchlist.load_symbols_from_google_sheets("sheet-id", "Watchlist!A2:A", "")


def test_missing_range_name_raises_value_error(tmp_path: Path) -> None:
    credentials = _credentials_file(tmp_path)

    with pytest.raises(ValueError, match="GOOGLE_SHEETS_RANGE is required"):
        watchlist.load_symbols_from_google_sheets("sheet-id", "", str(credentials))


def test_nonexistent_credentials_file_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError, match="credentials file not found"):
        watchlist.load_symbols_from_google_sheets("sheet-id", "Watchlist!A2:A", "missing.json")


def test_symbols_are_uppercased(tmp_path: Path, monkeypatch) -> None:
    _mock_google_api(tmp_path, monkeypatch, [["nvda"], ["aapl"]])

    symbols = watchlist.load_symbols_from_google_sheets("sheet-id", "Watchlist!A2:A", str(_credentials_file(tmp_path)))

    assert symbols == ["NVDA", "AAPL"]


def test_empty_rows_are_ignored(tmp_path: Path, monkeypatch) -> None:
    _mock_google_api(tmp_path, monkeypatch, [[], [""], ["MSFT"]])

    symbols = watchlist.load_symbols_from_google_sheets("sheet-id", "Watchlist!A2:A", str(_credentials_file(tmp_path)))

    assert symbols == ["MSFT"]


def test_duplicates_are_removed_while_preserving_order(tmp_path: Path, monkeypatch) -> None:
    _mock_google_api(tmp_path, monkeypatch, [["NVDA"], ["AAPL"], ["nvda"], ["MSFT"], ["AAPL"]])

    symbols = watchlist.load_symbols_from_google_sheets("sheet-id", "Watchlist!A2:A", str(_credentials_file(tmp_path)))

    assert symbols == ["NVDA", "AAPL", "MSFT"]


def test_rows_with_spaces_are_trimmed(tmp_path: Path, monkeypatch) -> None:
    _mock_google_api(tmp_path, monkeypatch, [[" nvda "], [" aapl"]])

    symbols = watchlist.load_symbols_from_google_sheets("sheet-id", "Watchlist!A2:A", str(_credentials_file(tmp_path)))

    assert symbols == ["NVDA", "AAPL"]


def _credentials_file(tmp_path: Path) -> Path:
    credentials = tmp_path / "google-service-account.json"
    credentials.write_text("{}", encoding="utf-8")
    return credentials


def _mock_google_api(tmp_path: Path, monkeypatch, rows: list[list[str]]) -> None:
    calls = []

    class FakeCredentials:
        @classmethod
        def from_service_account_file(cls, credentials_path, scopes):
            calls.append({"credentials_path": credentials_path, "scopes": scopes})
            return "credentials"

    class FakeRequest:
        def execute(self):
            return {"values": rows}

    class FakeValues:
        def get(self, spreadsheetId, range):
            calls.append({"spreadsheet_id": spreadsheetId, "range": range})
            return FakeRequest()

    class FakeSpreadsheets:
        def values(self):
            return FakeValues()

    class FakeService:
        def spreadsheets(self):
            return FakeSpreadsheets()

    def fake_build(service_name, version, credentials):
        calls.append({"service_name": service_name, "version": version, "credentials": credentials})
        return FakeService()

    monkeypatch.setattr(watchlist, "Credentials", FakeCredentials)
    monkeypatch.setattr(watchlist, "build", fake_build)
