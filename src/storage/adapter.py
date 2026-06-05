from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from dotenv import load_dotenv


@dataclass(frozen=True)
class StorageBackend:
    init_db: Callable[[], None]
    was_alert_sent: Callable[[str], bool]
    mark_alert_sent: Callable[[str, str, str, str], None]


def get_storage_backend() -> StorageBackend:
    load_dotenv()
    backend = os.getenv("STORAGE_BACKEND", "sqlite").strip().lower()

    if backend == "sqlite":
        from src.storage import db

        return StorageBackend(
            init_db=db.init_db,
            was_alert_sent=db.was_alert_sent,
            mark_alert_sent=db.mark_alert_sent,
        )

    if backend == "supabase":
        from src.storage import supabase_db

        return StorageBackend(
            init_db=supabase_db.init_db,
            was_alert_sent=supabase_db.was_alert_sent,
            mark_alert_sent=supabase_db.mark_alert_sent,
        )

    raise ValueError(f"Unsupported STORAGE_BACKEND: {backend}")
