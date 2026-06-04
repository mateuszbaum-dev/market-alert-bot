from pathlib import Path

from src.config import load_watchlist


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
