"""Uploaded document endpoints (upload / list / delete)."""

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.agents import user_data_agent
from app.api.deps import current_user_id
from app.config import settings
from app.db import repository
from app.db.connection import get_connection
from app.models.api import UserDocumentResponse

router = APIRouter(prefix="/api/profile/documents", tags=["documents"])

CHUNK_SIZE = 1024 * 1024


def _store_file(user_id: int, upload: UploadFile) -> tuple[str, int]:
    """Write an uploaded file to disk and return (storage_path, size_bytes)."""
    directory = Path(settings.upload_dir) / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)

    original_name = Path(upload.filename or "upload").name
    destination = directory / f"{uuid.uuid4().hex}_{original_name}"

    size = 0
    with destination.open("wb") as output:
        while True:
            chunk = upload.file.read(CHUNK_SIZE)
            if not chunk:
                break
            output.write(chunk)
            size += len(chunk)

    return str(destination), size


@router.post("", response_model=list[UserDocumentResponse])
def upload_documents(
    background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)
) -> list[UserDocumentResponse]:
    """Store uploaded documents and start Agent 1 extraction."""
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    user_id = current_user_id()
    created: list[UserDocumentResponse] = []

    with get_connection() as connection:
        for upload in files:
            storage_path, size = _store_file(user_id, upload)
            row = repository.insert_document(
                connection,
                user_id,
                upload.filename or "upload",
                upload.content_type,
                storage_path,
                size,
            )
            created.append(UserDocumentResponse.model_validate(row))

    # Adding documents re-runs extraction.
    background_tasks.add_task(user_data_agent.run_extraction, user_id)
    return created


@router.get("", response_model=list[UserDocumentResponse])
def list_documents() -> list[UserDocumentResponse]:
    """List the uploaded documents, newest first."""
    user_id = current_user_id()
    with get_connection() as connection:
        rows = repository.list_documents(connection, user_id)
    return [UserDocumentResponse.model_validate(row) for row in rows]


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int) -> None:
    """Delete a document row and its file on disk."""
    user_id = current_user_id()
    with get_connection() as connection:
        document = repository.get_document(connection, user_id, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        repository.delete_document(connection, user_id, document_id)

    storage_path = document["storage_path"]
    if storage_path:
        try:
            Path(storage_path).unlink(missing_ok=True)
        except OSError:
            pass
