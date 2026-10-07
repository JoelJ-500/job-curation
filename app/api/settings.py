"""Curator settings endpoints.

Mirrors the frontend contract in `frontend/src/api/settings.ts`.
"""

from fastapi import APIRouter

from app.api.deps import current_user_id
from app.db import repository
from app.db.connection import get_connection
from app.models.api import UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=UserSettings)
def read_settings() -> UserSettings:
    """Return the user's curator settings (defaults if never saved)."""
    user_id = current_user_id()
    with get_connection() as connection:
        data = repository.get_settings(connection, user_id)
    return UserSettings.model_validate(data)


@router.put("", response_model=UserSettings)
def update_settings(settings: UserSettings) -> UserSettings:
    """Save the user's curator settings."""
    user_id = current_user_id()
    with get_connection() as connection:
        data = repository.save_settings(connection, user_id, settings.model_dump())
    return UserSettings.model_validate(data)
