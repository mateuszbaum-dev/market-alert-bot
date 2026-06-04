from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def init_db() -> None:
    """Create the sent_alerts table if it does not already exist."""
    try:
        with closing(_connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    symbol TEXT,
                    source TEXT,
                    title TEXT,
                    sent_at TEXT
                )
                """
            )
            connection.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to initialize alert database: {exc}") from exc


def was_alert_sent(event_id: str) -> bool:
    """Return True when an event_id has already been marked as sent."""
    if not event_id:
        return False

    init_db()
    try:
        with closing(_connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM sent_alerts WHERE event_id = ? LIMIT 1",
                (event_id,),
            ).fetchone()
        return row is not None
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to check alert status: {exc}") from exc


def mark_alert_sent(event_id: str, symbol: str, source: str, title: str) -> None:
    """Record that an alert was sent, ignoring duplicate event IDs."""
    if not event_id:
        raise ValueError("event_id is required")

    init_db()
    try:
        with closing(_connect()) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO sent_alerts (
                    event_id, symbol, source, title, sent_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    symbol,
                    source,
                    title,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to mark alert as sent: {exc}") from exc


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def _db_path() -> Path:
    return Path(os.getenv("ALERT_DB_PATH", "alerts.db"))
