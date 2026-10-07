"""Curation (job scraping) endpoints.

Mirrors the frontend contract in `frontend/src/api/curation.ts`.
"""

from fastapi import APIRouter, BackgroundTasks

from app.agents import curation_agent
from app.api.deps import current_user_id
from app.models.api import CurationStatusResponse
from app.services import curation_state

router = APIRouter(prefix="/api/curation", tags=["curation"])


@router.post("/start", response_model=CurationStatusResponse)
def start_curation(background_tasks: BackgroundTasks) -> CurationStatusResponse:
    """Start a curation run (scrape both job sites in the background)."""
    user_id = current_user_id()
    background_tasks.add_task(curation_agent.run_curation, user_id)
    return curation_state.get_status()


@router.get("/status", response_model=CurationStatusResponse)
def read_status() -> CurationStatusResponse:
    """Poll the current curation status."""
    return curation_state.get_status()
