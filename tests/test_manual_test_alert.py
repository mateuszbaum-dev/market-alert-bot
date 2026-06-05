import src.test_alert as test_alert


def test_build_sample_alert_contains_test_symbol() -> None:
    message = test_alert.build_sample_alert()

    assert "Ticker: <b>TEST</b>" in message
    assert "Direction: \U0001f7e2 BULLISH" in message
    assert "Category: test_alert" in message


def test_main_sends_sample_alert(monkeypatch, capsys) -> None:
    sent_messages = []
    monkeypatch.setattr(test_alert, "send_telegram_message", lambda message: sent_messages.append(message) or True)

    test_alert.main()

    captured = capsys.readouterr()
    assert "Test alert sent successfully." in captured.out
    assert len(sent_messages) == 1
    assert "Ticker: <b>TEST</b>" in sent_messages[0]


def test_main_prints_failure(monkeypatch, capsys) -> None:
    def fail_send(message: str) -> bool:
        raise RuntimeError("telegram unavailable")

    monkeypatch.setattr(test_alert, "send_telegram_message", fail_send)

    test_alert.main()

    captured = capsys.readouterr()
    assert "Test alert failed: telegram unavailable" in captured.out
