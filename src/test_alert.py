from __future__ import annotations

from src.models.event import MarketEvent
from src.notifications.formatter import format_market_alert
from src.notifications.telegram import send_telegram_message


def build_sample_alert() -> str:
    event = MarketEvent(
        event_id="manual-test-alert",
        symbol="TEST",
        source="manual_test",
        event_type="test_alert",
        title="Manual Telegram formatting test alert",
        url="https://example.com/test-alert",
        published_at="2026-06-05T10:00:00Z",
        summary="Sample alert used to verify Telegram formatting.",
    )
    rule_score = {
        "score": 8,
        "level": "HIGH",
        "reasons": ["Test alert", "High impact sample"],
    }
    gpt_result = {
        "impact_level": "HIGH",
        "impact_score": 8,
        "market_direction": "BULLISH",
        "direction_confidence": 82,
        "event_probability": 67,
        "category": "test_alert",
        "reasoning_summary": "This is a sample alert used to verify Telegram formatting.",
        "should_notify": True,
    }
    return format_market_alert(event, rule_score, gpt_result)


def main() -> None:
    message = build_sample_alert()
    try:
        if send_telegram_message(message):
            print("Test alert sent successfully.")
        else:
            print("Test alert was not sent.")
    except Exception as exc:
        print(f"Test alert failed: {exc}")


if __name__ == "__main__":
    main()
