"""In-memory curation (scraping) status for the /api/curation/status endpoint.

This is a single-user app, so a module-level holder is sufficient (same pattern
as `extraction_state`). It can be swapped for a database table later.
"""

import threading
from dataclasses import dataclass

from app.models.api import CurationStatusResponse


@dataclass
class _CurationState:
    state: str = "idle"
    message: str | None = None
    jobs_scraped: int = 0
    output_file: str | None = None


_lock = threading.Lock()
_current = _CurationState()


def get_status() -> CurationStatusResponse:
    with _lock:
        return CurationStatusResponse(
            state=_current.state,
            message=_current.message,
            jobs_scraped=_current.jobs_scraped,
            output_file=_current.output_file,
        )


def set_running(message: str | None = None) -> None:
    with _lock:
        _current.state = "running"
        _current.message = message
        _current.jobs_scraped = 0
        _current.output_file = None


def set_progress(jobs_scraped: int, message: str | None = None) -> None:
    with _lock:
        _current.jobs_scraped = jobs_scraped
        if message is not None:
            _current.message = message


def set_done(message: str, jobs_scraped: int, output_file: str) -> None:
    with _lock:
        _current.state = "done"
        _current.message = message
        _current.jobs_scraped = jobs_scraped
        _current.output_file = output_file


def set_error(message: str) -> None:
    with _lock:
        _current.state = "error"
        _current.message = message
