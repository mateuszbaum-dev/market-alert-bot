from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

TELEGRAM_SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"
REQUEST_TIMEOUT_SECONDS = 10


def send_telegram_message(message: str) -> bool:
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required to send Telegram alerts")

    response = requests.post(
        TELEGRAM_SEND_MESSAGE_URL.format(token=bot_token),
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        response_text = getattr(response, "text", "")
        raise RuntimeError(f"Telegram send failed with status {response.status_code}: {response_text}")
    return True
