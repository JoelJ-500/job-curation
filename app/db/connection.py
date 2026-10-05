"""Database connection helpers (psycopg 3).

A simple per-request connection is used; the app is single-user so a connection
pool is not required.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from app.config import settings


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Open a connection to the job-curation database (rows as dicts)."""
    connection = psycopg.connect(settings.database_dsn, row_factory=dict_row)
    try:
        yield connection
    finally:
        connection.close()


def check_connection() -> None:
    """Raise if the database cannot be reached."""
    with get_connection() as connection:
        connection.execute("SELECT 1")
