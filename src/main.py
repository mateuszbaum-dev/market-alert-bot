from __future__ import annotations

from src.config import load_settings, load_watchlist


def main() -> None:
    settings = load_settings()
    load_watchlist(settings.watchlist_path)
    print("Market Alert Bot started")


if __name__ == "__main__":
    main()
