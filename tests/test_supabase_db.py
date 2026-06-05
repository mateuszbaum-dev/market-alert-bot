import pytest

from src.storage import supabase_db


def test_missing_supabase_url_raises_value_error(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
    monkeypatch.setattr(supabase_db, "load_dotenv", lambda: None)

    with pytest.raises(ValueError, match="SUPABASE_URL is required"):
        supabase_db.get_supabase_client()


def test_missing_supabase_service_role_key_raises_value_error(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(supabase_db, "load_dotenv", lambda: None)

    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY is required"):
        supabase_db.get_supabase_client()


def test_was_alert_sent_queries_by_event_id(monkeypatch) -> None:
    client = FakeSupabaseClient(select_data=[{"event_id": "event-1"}])
    monkeypatch.setattr(supabase_db, "get_supabase_client", lambda: client)

    assert supabase_db.was_alert_sent("event-1")
    assert client.table_name == "sent_alerts"
    assert client.filters == [("event_id", "event-1")]


def test_was_alert_sent_returns_false_when_missing(monkeypatch) -> None:
    client = FakeSupabaseClient(select_data=[])
    monkeypatch.setattr(supabase_db, "get_supabase_client", lambda: client)

    assert not supabase_db.was_alert_sent("event-1")


def test_mark_alert_sent_inserts_payload(monkeypatch) -> None:
    client = FakeSupabaseClient()
    monkeypatch.setattr(supabase_db, "get_supabase_client", lambda: client)

    supabase_db.mark_alert_sent("event-1", "NVDA", "finnhub", "Nvidia alert")

    assert client.insert_payload == {
        "event_id": "event-1",
        "symbol": "NVDA",
        "source": "finnhub",
        "title": "Nvidia alert",
    }


def test_duplicate_insert_is_ignored(monkeypatch) -> None:
    client = FakeSupabaseClient(insert_error=RuntimeError("duplicate key value violates unique constraint 23505"))
    monkeypatch.setattr(supabase_db, "get_supabase_client", lambda: client)

    supabase_db.mark_alert_sent("event-1", "NVDA", "finnhub", "Nvidia alert")


class FakeResponse:
    def __init__(self, data=None) -> None:
        self.data = data or []


class FakeSupabaseClient:
    def __init__(self, select_data=None, insert_error=None) -> None:
        self.select_data = select_data or []
        self.insert_error = insert_error
        self.table_name = None
        self.filters = []
        self.insert_payload = None

    def table(self, table_name):
        self.table_name = table_name
        return self

    def select(self, fields):
        self.selected_fields = fields
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def insert(self, payload):
        self.insert_payload = payload
        return self

    def execute(self):
        if self.insert_error:
            raise self.insert_error
        return FakeResponse(self.select_data)
