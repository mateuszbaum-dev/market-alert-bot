# Market Alert Bot

Market Alert Bot is a Python 3.11+ MVP for monitoring a configurable market watchlist and preparing future alert workflows.

This first version focuses on clean project structure, configuration loading, Finnhub company news, rule-based scoring, optional GPT classification, SQLite alert deduplication, and test setup. Notification delivery is intentionally left as a placeholder for later implementation.

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
| `OPENAI_API_KEY` | For GPT classifier | API key used for AI event classification. |
| `OPENAI_MODEL` | No | Defaults to `gpt-4.1-mini`. |
| `USE_AI` | No | Defaults to `true` in the example config. |
| `AI_THRESHOLD` | No | Suggested minimum rule score before GPT classification. |
| `MAX_GPT_CALLS_PER_RUN` | No | Suggested cap for GPT calls in one run. |

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

## GPT Classifier

The optional GPT classifier in `src/scoring/gpt_classifier.py` can add a compact market-monitoring classification to a scored `MarketEvent`. It sends only the normalized event fields and rule score, asks for JSON output, and falls back to the rule-based score if the API call fails or returns invalid data.

The classifier returns:

- `impact_score`: a 1-10 monitoring estimate of possible market impact.
- `market_direction`: `BULLISH`, `BEARISH`, `NEUTRAL`, or `UNCLEAR`.
- `direction_confidence`: 0-100 confidence in the directional classification.
- `event_probability`: 0-100 estimate that the event may cause a noticeable market reaction.

These are AI-generated monitoring estimates, not predictions. This tool is for market monitoring only. It is not financial advice and must not be used as a recommendation to buy, sell, hold, short, or trade securities.

## Alert Formatting

Telegram alert messages are formatted as plain text to avoid parse errors. Example:

```text
🚨 Market Monitoring Alert

Symbol: AAPL
Source: finnhub
Event Type: company_news
Title: Apple reports earnings
Impact Level: HIGH
Rule Score: 5
Rule Reasons:
- Mentions earnings

Impact Score: 8/10
Direction: BULLISH
Direction Confidence: 76%
Reaction Probability: 72%
Category: earnings
Reasoning Summary: Relevant for market monitoring.

Link: https://example.com/aapl

Monitoring alert only. Not financial advice.
```

## Running Tests

```powershell
pytest
```

## Alert Deduplication

Sent alerts are tracked in SQLite using the `sent_alerts` table. Each alert is keyed by a unique `event_id`, so the bot can check whether an event has already been sent before sending another notification.
