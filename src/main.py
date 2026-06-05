from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.config import load_watchlist_symbols, prepare_google_credentials_from_env
from src.notifications.formatter import format_market_alert
from src.notifications.telegram import send_telegram_message
from src.providers.finnhub import fetch_company_news
from src.scoring.gpt_classifier import classify_event_with_gpt, fallback_classification
from src.scoring.rules import score_event
from src.storage.adapter import get_storage_backend


@dataclass(frozen=True)
class PipelineSettings:
    watchlist_path: Path
    use_ai: bool
    ai_threshold: int
    min_score_to_notify: int
    max_gpt_calls_per_run: int
    dry_run: bool


def load_pipeline_settings() -> PipelineSettings:
    load_dotenv()
    return PipelineSettings(
        watchlist_path=Path(os.getenv("WATCHLIST_PATH", "watchlist.yaml")),
        use_ai=_env_bool("USE_AI", default=True),
        ai_threshold=_env_int("AI_THRESHOLD", default=4),
        min_score_to_notify=_env_int("MIN_SCORE_TO_NOTIFY", default=6),
        max_gpt_calls_per_run=_env_int("MAX_GPT_CALLS_PER_RUN", default=10),
        dry_run=_env_bool("DRY_RUN", default=True),
    )


def run_pipeline() -> dict[str, int]:
    settings = load_pipeline_settings()
    prepare_google_credentials_from_env()
    symbols = load_watchlist_symbols()
    storage = get_storage_backend()
    storage.init_db()

    stats = {
        "symbols": len(symbols),
        "symbols_processed": 0,
        "events_fetched": 0,
        "skipped_duplicates": 0,
        "rule_scored_events": 0,
        "gpt_calls_used": 0,
        "alerts": 0,
        "alerts_printed": 0,
        "alerts_sent": 0,
        "alerts_skipped": 0,
    }

    _log("Market Alert Bot started")
    _log(f"Symbols: {stats['symbols']}")

    for symbol in symbols:
        stats["symbols_processed"] += 1
        try:
            events = fetch_company_news(symbol, days_back=1)
            stats["events_fetched"] += len(events)
            _log(f"{symbol}: fetched {len(events)} events")
            if not events:
                _log(f"{symbol}: no events returned")

            for event in events:
                if storage.was_alert_sent(event.event_id):
                    stats["skipped_duplicates"] += 1
                    continue

                rule_score = score_event(event)
                stats["rule_scored_events"] += 1
                gpt_result = None
                if settings.use_ai:
                    if _should_call_gpt(settings, rule_score, stats["gpt_calls_used"]):
                        gpt_result = _classify_with_fallback(event, rule_score)
                        stats["gpt_calls_used"] += 1
                    elif _gpt_would_qualify(settings, rule_score) and stats["gpt_calls_used"] >= settings.max_gpt_calls_per_run:
                        stats["alerts_skipped"] += 1
                        _log("Skipped alert because GPT limit was reached and GPT analysis is required.")
                        continue

                if not _should_notify(settings, rule_score, gpt_result):
                    stats["alerts_skipped"] += 1
                    continue

                message = format_market_alert(event, rule_score, gpt_result)
                if settings.dry_run:
                    _log(message)
                    stats["alerts"] += 1
                    stats["alerts_printed"] += 1
                    continue

                try:
                    if send_telegram_message(message):
                        storage.mark_alert_sent(event.event_id, event.symbol, event.source, event.title)
                        stats["alerts"] += 1
                        stats["alerts_sent"] += 1
                    else:
                        stats["alerts_skipped"] += 1
                        _log(f"{symbol}: Telegram send returned false for {event.event_id}")
                except Exception as exc:
                    stats["alerts_skipped"] += 1
                    _log(f"{symbol}: Telegram send failed for {event.event_id}: {exc}")
        except Exception as exc:
            _log(f"{symbol}: error: {_friendly_symbol_error(exc)}")

    _log("Run summary:")
    _log(f"Symbols processed: {stats['symbols_processed']}")
    _log(f"Events fetched: {stats['events_fetched']}")
    _log(f"Duplicates skipped: {stats['skipped_duplicates']}")
    _log(f"Rule-scored events: {stats['rule_scored_events']}")
    _log(f"GPT calls used: {stats['gpt_calls_used']}")
    _log(f"Alerts sent: {stats['alerts_sent']}")
    _log(f"Alerts printed: {stats['alerts_printed']}")
    _log(f"Alerts skipped: {stats['alerts_skipped']}")
    return stats


def main() -> None:
    run_pipeline()


def _should_call_gpt(settings: PipelineSettings, rule_score: dict[str, Any], gpt_calls_used: int) -> bool:
    return (
        _gpt_would_qualify(settings, rule_score)
        and gpt_calls_used < settings.max_gpt_calls_per_run
    )


def _gpt_would_qualify(settings: PipelineSettings, rule_score: dict[str, Any]) -> bool:
    return settings.use_ai and int(rule_score.get("score", 0)) >= settings.ai_threshold


def _should_notify(settings: PipelineSettings, rule_score: dict[str, Any], gpt_result: dict | None) -> bool:
    if settings.use_ai:
        return bool(gpt_result and gpt_result.get("should_notify", False))
    if gpt_result is not None:
        return bool(gpt_result.get("should_notify", False))
    return int(rule_score.get("score", 0)) >= settings.min_score_to_notify


def _classify_with_fallback(event: Any, rule_score: dict[str, Any]) -> dict[str, Any]:
    try:
        return classify_event_with_gpt(event, rule_score)
    except Exception:
        return fallback_classification(rule_score)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _log(message: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    safe_message = message.encode(encoding, errors="backslashreplace").decode(encoding)
    print(safe_message)


def _friendly_symbol_error(exc: Exception) -> str:
    message = str(exc)
    if "429" in message:
        return f"rate limit from provider: {message}"
    return message


if __name__ == "__main__":
    main()
