from pathlib import Path

import src.main as main_module
from src.models.event import MarketEvent


def test_dry_run_prints_alert_but_does_not_send_or_mark_sent(tmp_path, monkeypatch, capsys) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "false")
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: False)
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    send_calls = []
    mark_calls = []
    monkeypatch.setattr(main_module, "send_telegram_message", lambda message: send_calls.append(message))
    monkeypatch.setattr(main_module, "mark_alert_sent", lambda *args: mark_calls.append(args))

    stats = main_module.run_pipeline()

    captured = capsys.readouterr()
    assert "Market Monitoring Alert" in captured.out
    assert stats["alerts"] == 1
    assert stats["alerts_printed"] == 1
    assert stats["alerts_sent"] == 0
    assert send_calls == []
    assert mark_calls == []


def test_duplicate_event_is_skipped(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: True)
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
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: False)
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
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: False)
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
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(
        main_module,
        "fetch_company_news",
        lambda symbol, days_back: [_event(symbol, suffix="1"), _event(symbol, suffix="2")],
    )
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: False)
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    gpt_calls = []
    monkeypatch.setattr(main_module, "classify_event_with_gpt", lambda event, score: gpt_calls.append((event, score)) or _gpt_result())

    stats = main_module.run_pipeline()

    captured = capsys.readouterr()
    assert stats["gpt_calls_used"] == 1
    assert len(gpt_calls) == 1
    assert "MAX_GPT_CALLS_PER_RUN reached" in captured.out


def test_telegram_send_success_marks_alert_as_sent(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("USE_AI", "false")
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: False)
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))
    monkeypatch.setattr(main_module, "send_telegram_message", lambda message: True)
    mark_calls = []
    monkeypatch.setattr(main_module, "mark_alert_sent", lambda *args: mark_calls.append(args))

    stats = main_module.run_pipeline()

    assert stats["alerts"] == 1
    assert stats["alerts_sent"] == 1
    assert mark_calls == [("event-AAPL", "AAPL", "test", "AAPL earnings")]


def test_telegram_send_failure_does_not_mark_alert_as_sent(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL"])
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("USE_AI", "false")
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "fetch_company_news", lambda symbol, days_back: [_event(symbol)])
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: False)
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))

    def send_failure(message: str) -> bool:
        raise RuntimeError("send failed")

    monkeypatch.setattr(main_module, "send_telegram_message", send_failure)
    mark_calls = []
    monkeypatch.setattr(main_module, "mark_alert_sent", lambda *args: mark_calls.append(args))

    stats = main_module.run_pipeline()

    assert stats["alerts"] == 0
    assert stats["alerts_skipped"] == 1
    assert mark_calls == []


def test_one_symbol_failure_does_not_stop_another_symbol(tmp_path, monkeypatch) -> None:
    _set_watchlist(tmp_path, monkeypatch, ["AAPL", "MSFT"])
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("USE_AI", "false")
    monkeypatch.setattr(main_module, "init_db", lambda: None)

    def fetch(symbol: str, days_back: int):
        if symbol == "AAPL":
            raise RuntimeError("Finnhub company news request failed with status 429: rate limit")
        return [_event(symbol)]

    monkeypatch.setattr(main_module, "fetch_company_news", fetch)
    monkeypatch.setattr(main_module, "was_alert_sent", lambda event_id: False)
    monkeypatch.setattr(main_module, "score_event", lambda event: _rule_score(score=6, level="HIGH"))

    stats = main_module.run_pipeline()

    assert stats["symbols"] == 2
    assert stats["symbols_processed"] == 2
    assert stats["events_fetched"] == 1
    assert stats["alerts"] == 1


def _set_watchlist(tmp_path: Path, monkeypatch, symbols: list[str]) -> None:
    companies = "\n".join(
        f"  - name: {symbol}\n    ticker: {symbol}\n" for symbol in symbols
    )
    watchlist = tmp_path / "watchlist.yaml"
    watchlist.write_text(f"companies:\n{companies}", encoding="utf-8")
    monkeypatch.setenv("WATCHLIST_PATH", str(watchlist))


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


def _gpt_result() -> dict:
    return {
        "impact_level": "HIGH",
        "impact_score": 7,
        "market_direction": "UNCLEAR",
        "direction_confidence": 40,
        "event_probability": 50,
        "category": "test",
        "reasoning_summary": "Test GPT result.",
        "should_notify": True,
    }
