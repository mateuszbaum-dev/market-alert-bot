import sqlite3

from src.storage.db import init_db, mark_alert_sent, was_alert_sent


def test_database_initialization_creates_sent_alerts_table(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "alerts.db"
    monkeypatch.setenv("ALERT_DB_PATH", str(db_path))

    init_db()

    with sqlite3.connect(db_path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sent_alerts'"
        ).fetchone()

    assert table == ("sent_alerts",)


def test_event_not_sent_yet(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ALERT_DB_PATH", str(tmp_path / "alerts.db"))

    assert not was_alert_sent("event-1")


def test_marking_event_as_sent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ALERT_DB_PATH", str(tmp_path / "alerts.db"))

    mark_alert_sent("event-1", "AAPL", "test", "Apple alert")

    assert was_alert_sent("event-1")


def test_duplicate_event_id_is_not_inserted_twice(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "alerts.db"
    monkeypatch.setenv("ALERT_DB_PATH", str(db_path))

    mark_alert_sent("event-1", "AAPL", "test", "First title")
    mark_alert_sent("event-1", "MSFT", "test", "Duplicate title")

    with sqlite3.connect(db_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sent_alerts WHERE event_id = ?",
            ("event-1",),
        ).fetchone()[0]

    assert count == 1
