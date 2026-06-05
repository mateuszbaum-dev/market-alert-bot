"""Storage helpers for alert deduplication."""

from .adapter import StorageBackend, get_storage_backend
from .db import init_db, mark_alert_sent, was_alert_sent

__all__ = ["StorageBackend", "get_storage_backend", "init_db", "mark_alert_sent", "was_alert_sent"]
