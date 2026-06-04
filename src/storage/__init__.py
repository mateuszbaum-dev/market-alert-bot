"""Storage helpers for alert deduplication."""

from .db import init_db, mark_alert_sent, was_alert_sent

__all__ = ["init_db", "mark_alert_sent", "was_alert_sent"]
