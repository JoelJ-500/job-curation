"""Shared API dependencies."""

from app.db import repository
from app.db.connection import get_connection


def current_user_id() -> int:
    """Return the single user's id, creating the row on first use."""
    with get_connection() as connection:
        user_id = repository.ensure_user(connection)
        connection.commit()
        return user_id
