import pytest

from src.notifications import telegram


class FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def test_send_telegram_message_uses_html_parse_mode(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(telegram, "load_dotenv", lambda: None)
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(200)

    monkeypatch.setattr(telegram.requests, "post", fake_post)

    assert telegram.send_telegram_message("Ticker: <b>NVDA</b>")

    payload = calls[0]["json"]
    assert payload["parse_mode"] == "HTML"
    assert payload["disable_web_page_preview"] is True
    assert payload["text"] == "Ticker: <b>NVDA</b>"


def test_send_telegram_message_raises_clear_error_on_api_failure(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(telegram, "load_dotenv", lambda: None)
    monkeypatch.setattr(telegram.requests, "post", lambda url, json, timeout: FakeResponse(400, "bad request"))

    with pytest.raises(RuntimeError, match="Telegram send failed with status 400"):
        telegram.send_telegram_message("bad")
