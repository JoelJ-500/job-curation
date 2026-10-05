"""In-memory extraction status for the /api/profile/status polling endpoint.

This is a single-user app, so a module-level holder is sufficient. It can be
swapped for a database table later if the backend becomes multi-user or runs
with multiple workers.
"""

import threading
from dataclasses import dataclass

from app.models.api import ExtractionStatusResponse


@dataclass
class _ExtractionState:
    state: str = "idle"
    message: str | None = None


_lock = threading.Lock()
_current = _ExtractionState()


def get_status() -> ExtractionStatusResponse:
    with _lock:
        return ExtractionStatusResponse(state=_current.state, message=_current.message)


def set_status(state: str, message: str | None = None) -> None:
    with _lock:
        _current.state = state
        _current.message = message
