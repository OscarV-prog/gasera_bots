"""SQLite database connection manager."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from src.config.settings import get_settings


def get_db_path() -> Path:
    """Resolve and ensure the database file path."""
    settings = get_settings()
    db_path = Path(settings.database_path)
    # Ensure parent directory exists (e.g. data/)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connections.
    
    Configures Row factory and enables foreign key constraints.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
