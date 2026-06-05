from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.config import load_watchlist
from src.notifications.formatter import format_market_alert
from src.notifications.telegram import send_telegram_message
from src.providers.finnhub import fetch_company_news
from src.scoring.gpt_classifier import classify_event_with_gpt
from src.scoring.rules import score_event
from src.storage.db import init_db, mark_alert_sent, was_alert_sent


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
    targets = load_watchlist(settings.watchlist_path)
    init_db()

    stats = {
        "symbols": len(targets),
        "events_fetched": 0,
        "skipped_duplicates": 0,
        "gpt_calls_used": 0,
        "alerts": 0,
    }

    _log("Market Alert Bot started")
    _log(f"Symbols: {stats['symbols']}")

    for target in targets:
        symbol = target.ticker
        try:
            events = fetch_company_news(symbol, days_back=1)
            stats["events_fetched"] += len(events)
            _log(f"{symbol}: fetched {len(events)} events")

            for event in events:
                if was_alert_sent(event.event_id):
                    stats["skipped_duplicates"] += 1
                    continue

                rule_score = score_event(event)
                gpt_result = None
                if _should_call_gpt(settings, rule_score, stats["gpt_calls_used"]):
                    gpt_result = classify_event_with_gpt(event, rule_score)
                    stats["gpt_calls_used"] += 1

                if not _should_notify(settings, rule_score, gpt_result):
                    continue

                message = format_market_alert(event, rule_score, gpt_result)
                if settings.dry_run:
                    _log(message)
                    stats["alerts"] += 1
                    continue

                if send_telegram_message(message):
                    mark_alert_sent(event.event_id, event.symbol, event.source, event.title)
                    stats["alerts"] += 1
        except Exception as exc:
            _log(f"{symbol}: error: {exc}")

    _log(f"Events fetched: {stats['events_fetched']}")
    _log(f"Skipped duplicates: {stats['skipped_duplicates']}")
    _log(f"GPT calls used: {stats['gpt_calls_used']}")
    _log(f"Alerts {'printed' if settings.dry_run else 'sent'}: {stats['alerts']}")
    return stats


def main() -> None:
    run_pipeline()


def _should_call_gpt(settings: PipelineSettings, rule_score: dict[str, Any], gpt_calls_used: int) -> bool:
    return (
        settings.use_ai
        and int(rule_score.get("score", 0)) >= settings.ai_threshold
        and gpt_calls_used < settings.max_gpt_calls_per_run
    )


def _should_notify(settings: PipelineSettings, rule_score: dict[str, Any], gpt_result: dict | None) -> bool:
    if gpt_result is not None:
        return bool(gpt_result.get("should_notify", False))
    return int(rule_score.get("score", 0)) >= settings.min_score_to_notify


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


if __name__ == "__main__":
    main()
