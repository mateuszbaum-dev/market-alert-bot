import pytest

from src.storage import adapter


def test_default_backend_is_sqlite(monkeypatch) -> None:
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.setattr(adapter, "load_dotenv", lambda: None)

    backend = adapter.get_storage_backend()

    assert backend.init_db.__module__ == "src.storage.db"
    assert backend.was_alert_sent.__module__ == "src.storage.db"
    assert backend.mark_alert_sent.__module__ == "src.storage.db"


def test_supabase_backend_is_selected(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(adapter, "load_dotenv", lambda: None)

    backend = adapter.get_storage_backend()

    assert backend.init_db.__module__ == "src.storage.supabase_db"
    assert backend.was_alert_sent.__module__ == "src.storage.supabase_db"
    assert backend.mark_alert_sent.__module__ == "src.storage.supabase_db"


def test_unknown_backend_raises_value_error(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "unknown")
    monkeypatch.setattr(adapter, "load_dotenv", lambda: None)

    with pytest.raises(ValueError, match="Unsupported STORAGE_BACKEND"):
        adapter.get_storage_backend()
