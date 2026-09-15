"""Database package for SQLite integration."""

from src.database.connection import get_db_connection, get_db_path
from src.database.schema import init_db, seed_products_from_json

__all__ = [
    "get_db_connection",
    "get_db_path",
    "init_db",
    "seed_products_from_json",
]
