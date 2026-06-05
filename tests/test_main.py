from pathlib import Path
from types import SimpleNamespace

import src.main as main_module
from src.models.event import MarketEvent


def test_dry_run_prints_alert_but_does_not_send_or_mark_sent(tmp_path, monkeypatch, capsys) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "false")
    mark_calls = []
    _set_storage(monkeypatch, was_sent=False, mark_calls=mark_calls)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    send_calls = []
    monkeypatch.setattr(main_module, "send_telegram_message", lambda message: send_calls.append(message))

    stats = main_module.run_pipeline()

    captured = capsys.readouterr()
    assert "Market Alert" in captured.out
    assert stats["alerts"] == 1
    assert stats["alerts_printed"] == 1
    assert stats["alerts_sent"] == 0
    assert send_calls == []
    assert mark_calls == []


def test_duplicate_event_is_skipped(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "true")
    _set_storage(monkeypatch, was_sent=True)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    score_calls = []
    monkeypatch.setattr(main_module, "score_event", lambda event: score_calls.append(event))

    stats = main_module.run_pipeline()

    assert stats["skipped_duplicates"] == 1
    assert stats["rule_scored_events"] == 0
    assert stats["alerts"] == 0
    assert score_calls == []


def test_gpt_is_called_when_rule_score_meets_threshold(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "true")
    monkeypatch.setenv("AI_THRESHOLD", "4")
    _set_storage(monkeypatch, was_sent=False)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=4, level="MEDIUM"))
    gpt_calls = []
    monkeypatch.setattr(main_module, "classify_event_with_gpt", lambda event, score: gpt_calls.append((event, score)) or _gpt_result())

    stats = main_module.run_pipeline()

    assert stats["gpt_calls_used"] == 1
    assert len(gpt_calls) == 1


def test_gpt_is_not_called_when_threshold_is_not_met(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "true")
    monkeypatch.setenv("AI_THRESHOLD", "4")
    _set_storage(monkeypatch, was_sent=False)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=3, level="MEDIUM"))
    gpt_calls = []
    monkeypatch.setattr(main_module, "classify_event_with_gpt", lambda event, score: gpt_calls.append((event, score)))

    stats = main_module.run_pipeline()

    assert stats["gpt_calls_used"] == 0
    assert gpt_calls == []


def test_gpt_limit_is_respected(tmp_path, monkeypatch, capsys) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "true")
    monkeypatch.setenv("AI_THRESHOLD", "4")
    monkeypatch.setenv("MAX_GPT_CALLS_PER_RUN", "1")
    _set_storage(monkeypatch, was_sent=False)
    monkeypatch.setattr(
        main_module,
        "fetch_company_news",
        lambda symbol, days_back: [_event(symbol, suffix="1"), _event(symbol, suffix="2")],
    )
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    gpt_calls = []
    monkeypatch.setattr(main_module, "classify_event_with_gpt", lambda event, score: gpt_calls.append((event, score)) or _gpt_result())

    stats = main_module.run_pipeline()

    captured = capsys.readouterr()
    assert stats["gpt_calls_used"] == 1
    assert len(gpt_calls) == 1
    assert "Skipped alert because GPT limit was reached and GPT analysis is required." in captured.out


def test_use_ai_true_and_gpt_limit_reached_skips_alert(tmp_path, monkeypatch, capsys) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("USE_AI", "true")
    monkeypatch.setenv("AI_THRESHOLD", "4")
    monkeypatch.setenv("MAX_GPT_CALLS_PER_RUN", "0")
    _set_storage(monkeypatch, was_sent=False)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    send_calls = []
    monkeypatch.setattr(main_module, "send_telegram_message", lambda message: send_calls.append(message) or True)

    stats = main_module.run_pipeline()

    captured = capsys.readouterr()
    assert stats["gpt_calls_used"] == 0
    assert stats["alerts"] == 0
    assert stats["alerts_skipped"] == 1
    assert send_calls == []
    assert "Skipped alert because GPT limit was reached and GPT analysis is required." in captured.out


def test_use_ai_true_and_gpt_result_alert_includes_market_direction(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("USE_AI", "true")
    monkeypatch.setenv("AI_THRESHOLD", "4")
    _set_storage(monkeypatch, was_sent=False)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    monkeypatch.setattr(main_module, "classify_event_with_gpt", lambda event, score: _gpt_result(direction="BULLISH"))
    sent_messages = []
    monkeypatch.setattr(main_module, "send_telegram_message", lambda message: sent_messages.append(message) or True)

    stats = main_module.run_pipeline()

    assert stats["alerts_sent"] == 1
    assert len(sent_messages) == 1
    assert "Direction: \U0001f7e2 BULLISH" in sent_messages[0]
    assert "Impact: 7/10" in sent_messages[0]
    assert "Direction confidence: 40%" in sent_messages[0]
    assert "Reaction probability: 50%" in sent_messages[0]


def test_use_ai_false_rule_based_alert_can_still_be_sent(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("USE_AI", "false")
    mark_calls = []
    _set_storage(monkeypatch, was_sent=False, mark_calls=mark_calls)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    sent_messages = []
    monkeypatch.setattr(main_module, "send_telegram_message", lambda message: sent_messages.append(message) or True)
    gpt_calls = []
    monkeypatch.setattr(main_module, "classify_event_with_gpt", lambda event, score: gpt_calls.append((event, score)))

    stats = main_module.run_pipeline()

    assert stats["alerts_sent"] == 1
    assert mark_calls == [("event-AAPL", "AAPL", "test", "AAPL earnings")]
    assert gpt_calls == []
    assert "Rule score: 6" in sent_messages[0]
    assert "Direction:" not in sent_messages[0]


def test_telegram_send_success_marks_alert_as_sent(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("USE_AI", "false")
    mark_calls = []
    _set_storage(monkeypatch, was_sent=False, mark_calls=mark_calls)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    monkeypatch.setattr(main_module, "send_telegram_message", lambda message: True)

    stats = main_module.run_pipeline()

    assert stats["alerts"] == 1
    assert stats["alerts_sent"] == 1
    assert mark_calls == [("event-AAPL", "AAPL", "test", "AAPL earnings")]


def test_telegram_send_failure_does_not_mark_alert_as_sent(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("USE_AI", "false")
    mark_calls = []
    _set_storage(monkeypatch, was_sent=False, mark_calls=mark_calls)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))

    def send_failure(message: str) -> bool:
        raise RuntimeError("send failed")

    monkeypatch.setattr(main_module, "send_telegram_message", send_failure)

    stats = main_module.run_pipeline()

    assert stats["alerts"] == 0
    assert stats["alerts_skipped"] == 1
    assert mark_calls == []


def test_one_symbol_failure_does_not_stop_another_symbol(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL", "MSFT"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "false")
    _set_storage(monkeypatch, was_sent=False)

    def fetch(symbol: str, days_back: int):
        if symbol == "AAPL":
            raise RuntimeError("Finnhub company news request failed with status 429: rate limit")
        return [_event(symbol)]

    monkeypatch.setattr(main_module, "fetch_company_news", fetch)
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))

    stats = main_module.run_pipeline()

    assert stats["symbols"] == 2
    assert stats["symbols_processed"] == 2
    assert stats["events_fetched"] == 1
    assert stats["alerts"] == 1


def _set_watchlist(tmp_path: Path, monkeypatch, symbols: list[str]) -> None:
    monkeypatch.setattr(main_module, "load_watchlist_symbols", lambda: symbols)
    monkeypatch.setenv("WATCHLIST_PATH", str(tmp_path / "watchlist.yaml"))


def _set_storage(monkeypatch, was_sent: bool, mark_calls: list | None = None) -> None:
    mark_calls = mark_calls if mark_calls is not None else []
    backend = SimpleNamespace(
        init_db=lambda: None,
        was_alert_sent=lambda event_id: was_sent,
        mark_alert_sent=lambda *args: mark_calls.append(args),
    )
    monkeypatch.setattr(main_module, "get_storage_backend", lambda: backend)


def test_google_sheets_watchlist_source_runs_with_mocked_loader(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["NVDA"])
    monkeypatch.setenv("WATCHLIST_SOURCE", "google_sheets")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "false")
    _set_storage(monkeypatch, was_sent=False)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))

    stats = main_module.run_pipeline()

    assert stats["symbols"] == 1
    assert stats["alerts"] == 1


def _event(symbol: str, suffix: str = "") -> MarketEvent:
    title = f"{symbol} earnings{suffix}"
    return MarketEvent(
        event_id=f"event-{symbol}{suffix}",
        symbol=symbol,
        source="test",
        event_type="company_news",
        title=title,
        url=f"https://example.com/{symbol}",
        published_at="2026-06-05T10:00:00Z",
        summary="Earnings update.",
    )


def _rule_score(score: int, level: str) -> dict:
    return {"score": score, "level": level, "reasons": ["Test reason"]}


def _gpt_result(direction: str = "UNCLEAR") -> dict:
    return {
        "impact_level": "HIGH",
        "impact_score": 7,
        "market_direction": direction,
        "direction_confidence": 40,
        "event_probability": 50,
        "category": "test",
        "reasoning_summary": "Test GPT result.",
        "should_notify": True,
    }
