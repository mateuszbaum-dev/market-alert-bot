from __future__ import annotations

import os

from dotenv import load_dotenv
from supabase import create_client

TABLE_NAME = "sent_alerts"


def get_supabase_client():
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url:
        raise ValueError("SUPABASE_URL is required when STORAGE_BACKEND=supabase")
    if not service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required when STORAGE_BACKEND=supabase")
    return create_client(supabase_url, service_role_key)


def init_db() -> None:
    get_supabase_client()


def was_alert_sent(event_id: str) -> bool:
    if not event_id:
        return False

    response = (
        get_supabase_client()
        .table(TABLE_NAME)
        .select("event_id")
        .eq("event_id", event_id)
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", None))


def mark_alert_sent(event_id: str, symbol: str, source: str, title: str) -> None:
    if not event_id:
        raise ValueError("event_id is required")

    payload = {
        "event_id": event_id,
        "symbol": symbol,
        "source": source,
        "title": title,
    }
    try:
        get_supabase_client().table(TABLE_NAME).insert(payload).execute()
    except Exception as exc:
        if _looks_like_duplicate_error(exc):
            return
        raise RuntimeError(f"Failed to mark alert as sent in Supabase: {exc}") from exc


def _looks_like_duplicate_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "duplicate" in message or "23505" in message or "unique" in message
