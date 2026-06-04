from pathlib import Path

from src.main import main


def test_main_prints_startup_message(tmp_path: Path, monkeypatch, capsys) -> None:
    watchlist = tmp_path / "watchlist.yaml"
    watchlist.write_text("companies: []\n", encoding="utf-8")
    monkeypatch.setenv("WATCHLIST_PATH", str(watchlist))

    main()

    captured = capsys.readouterr()
    assert "Market Alert Bot started" in captured.out
