"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import curation, documents, profile
from app.api import settings as settings_api
from app.config import settings
from app.db.connection import check_connection


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ensure the working directories exist and the database is reachable."""
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.queue_dir).mkdir(parents=True, exist_ok=True)
    check_connection()
    yield


app = FastAPI(title="job-curation API", version="0.1.0", lifespan=lifespan)

# The React dev server runs on the host (localhost:5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router)
app.include_router(documents.router)
app.include_router(settings_api.router)
app.include_router(curation.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}
