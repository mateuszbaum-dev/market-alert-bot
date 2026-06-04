# Market Alert Bot

Market Alert Bot is a Python 3.11+ MVP for monitoring a configurable market watchlist and preparing future alert workflows.

This first version focuses on clean project structure, configuration loading, SQLite alert deduplication, and test setup. External data providers, scoring logic, and notification delivery are intentionally left as placeholders for later implementation.

## Project Structure

```text
market-alert-bot/
  src/
    main.py
    config.py
    providers/
    scoring/
    notifications/
    storage/
    models/
  tests/
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
copy watchlist.example.yaml watchlist.yaml
python -m src.main
```

## Configuration

Configuration is loaded from environment variables, with optional `.env` support.

| Variable | Required | Description |
| --- | --- | --- |
| `WATCHLIST_PATH` | No | Defaults to `watchlist.yaml`. |
| `ALERT_DB_PATH` | No | Defaults to `alerts.db`. Stores sent alert records for deduplication. |
| `FINNHUB_API_KEY` | For Finnhub | API key used by the Finnhub company news provider. |

## Watchlist Format

See [watchlist.example.yaml](watchlist.example.yaml).

Each company can define:

- `ticker`: Stock ticker.
- `cik`: SEC Central Index Key.
- `keywords`: Important words or phrases.

## Event Model

All future providers should normalize incoming data into the `MarketEvent` dataclass. This gives scoring, storage, and notification code a consistent shape regardless of whether an event came from filings, news, or another source.

## Finnhub Provider

The Finnhub provider fetches company news and normalizes every valid article into `MarketEvent`. To use it, create a Finnhub API key and set `FINNHUB_API_KEY` in `.env`.

## Rule-Based Scoring

Market events can be scored with deterministic rules in `src/scoring/rules.py`. The scorer returns a numeric score, a `LOW`, `MEDIUM`, or `HIGH` level, and human-readable reasons explaining which rules matched.

## Running Tests

```powershell
pytest
```

## Alert Deduplication

Sent alerts are tracked in SQLite using the `sent_alerts` table. Each alert is keyed by a unique `event_id`, so the bot can check whether an event has already been sent before sending another notification.
