import os
from pathlib import Path

from src.config import Settings, load_watchlist, load_watchlist_symbols, prepare_google_credentials_from_env


def test_load_watchlist_reads_companies(tmp_path: Path) -> None:
    watchlist = tmp_path / "watchlist.yaml"
    watchlist.write_text(
        """
companies:
  - name: Example Corp
    ticker: exm
    cik: "12345"
    keywords:
      - earnings
""",
        encoding="utf-8",
    )

    targets = load_watchlist(watchlist)

    assert len(targets) == 1
    assert targets[0].name == "Example Corp"
    assert targets[0].ticker == "EXM"
    assert targets[0].cik == "0000012345"
    assert targets[0].keywords == ["earnings"]


def test_load_watchlist_symbols_uses_yaml_by_default(tmp_path: Path) -> None:
    watchlist = tmp_path / "watchlist.yaml"
    watchlist.write_text(
        """
companies:
  - name: Example Corp
    ticker: exm
""",
        encoding="utf-8",
    )

    symbols = load_watchlist_symbols(Settings(watchlist_path=watchlist))

    assert symbols == ["EXM"]


def test_load_watchlist_symbols_uses_google_sheets(monkeypatch) -> None:
    settings = Settings(
        watchlist_path=Path("unused.yaml"),
        watchlist_source="google_sheets",
        google_sheets_credentials_path="creds.json",
        google_sheets_spreadsheet_id="sheet-id",
        google_sheets_range="Watchlist!A2:A",
    )
    calls = []
    monkeypatch.setattr(
        "src.config._load_google_sheet_symbols",
        lambda loaded_settings: calls.append(loaded_settings) or ["NVDA", "AAPL"],
    )

    symbols = load_watchlist_symbols(settings)

    assert symbols == ["NVDA", "AAPL"]
    assert calls == [settings]


def test_prepare_google_credentials_from_env_writes_file_and_sets_path(tmp_path: Path, monkeypatch) -> None:
    secret = '{"client_email":"bot@example.com"}'
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", secret)
    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS_PATH", raising=False)

    credentials_path = prepare_google_credentials_from_env(project_root=tmp_path)

    assert credentials_path == tmp_path / "google-service-account.json"
    assert credentials_path.read_text(encoding="utf-8") == secret
    assert os.environ["GOOGLE_SHEETS_CREDENTIALS_PATH"] == str(credentials_path)


def test_prepare_google_credentials_from_env_missing_keeps_existing_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "existing.json")

    credentials_path = prepare_google_credentials_from_env(project_root=tmp_path)

    assert credentials_path is None
    assert os.environ["GOOGLE_SHEETS_CREDENTIALS_PATH"] == "existing.json"
    assert not (tmp_path / "google-service-account.json").exists()


def test_prepare_google_credentials_from_env_does_not_print_secret(tmp_path: Path, monkeypatch, capsys) -> None:
    secret = '{"private_key":"super-secret"}'
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", secret)

    prepare_google_credentials_from_env(project_root=tmp_path)

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
