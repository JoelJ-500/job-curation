"""Profile API endpoints.

Mirrors the frontend contract in `frontend/src/api/profile.ts`.
"""

from fastapi import APIRouter, BackgroundTasks

from app.agents import user_data_agent
from app.api.deps import current_user_id
from app.db import repository
from app.db.connection import get_connection
from app.models.api import ExtractionStatusResponse, UserProfileResponse
from app.services import extraction_state

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=UserProfileResponse)
def read_profile() -> UserProfileResponse:
    """Return the current candidate profile."""
    user_id = current_user_id()
    with get_connection() as connection:
        profile = repository.get_profile(connection, user_id)
    return UserProfileResponse.model_validate(profile)


@router.put("", response_model=UserProfileResponse)
def update_profile(profile: UserProfileResponse) -> UserProfileResponse:
    """Save an edited profile, updating only the changed database attributes."""
    user_id = current_user_id()
    with get_connection() as connection:
        saved = repository.save_profile(connection, user_id, profile.model_dump())
    return UserProfileResponse.model_validate(saved)


@router.post("/extract", response_model=ExtractionStatusResponse)
def start_extraction(background_tasks: BackgroundTasks) -> ExtractionStatusResponse:
    """Re-run Agent 1 on the already uploaded documents."""
    user_id = current_user_id()
    background_tasks.add_task(user_data_agent.run_extraction, user_id)
    return extraction_state.get_status()


@router.get("/status", response_model=ExtractionStatusResponse)
def read_status() -> ExtractionStatusResponse:
    """Poll the current extraction status."""
    return extraction_state.get_status()
