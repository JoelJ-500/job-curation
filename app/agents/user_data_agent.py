"""Agent 1 orchestrator.

Flow: read the user's uploaded documents -> convert each to clean plain text ->
extract a `CandidateProfile` with Groq -> persist it to Postgres.

Runs in a background task when documents are uploaded or extraction is re-run.
"""

from typing import Any

from app.agents.document_ingest import extract_document_text
from app.agents.profile_extractor import extract_profile
from app.config import settings
from app.db import repository
from app.db.connection import get_connection
from app.models.profile import CandidateProfile
from app.services import extraction_state

WORK_ELIGIBILITY_TYPES = {"citizenship", "work_visa", "residency"}
EDUCATION_TYPES = {"associate", "bachelors", "masters", "phd", "diploma", "certificate"}


def _clean_choice(value: str | None, allowed: set[str]) -> str | None:
    """Return the value only if it is one of the allowed enum values."""
    if value is None:
        return None
    text = str(value).strip().lower()
    return text if text in allowed else None


def _to_profile_dict(extracted: CandidateProfile) -> dict[str, Any]:
    """Map the extracted Pydantic profile onto the database column shape."""
    work_eligibility = []
    for item in extracted.work_eligibility:
        eligibility_type = _clean_choice(item.type, WORK_ELIGIBILITY_TYPES)
        if item.country_name and eligibility_type:
            work_eligibility.append(
                {"country_name": item.country_name.strip(), "type": eligibility_type}
            )

    social_media = [
        {
            "platform": item.platform.strip(),
            "username": (item.username or None),
            "link": item.link.strip(),
        }
        for item in extracted.social_media
        if item.platform and item.link
    ]

    skills = [
        {"name": item.name.strip(), "type": (item.type.strip() if item.type else None)}
        for item in extracted.skills
        if item.name
    ]

    roles = [{"name": item.name.strip()} for item in extracted.roles if item.name]

    experiences = [
        {
            "company_or_org": item.company_or_org,
            "role": item.role,
            "start_date": item.start_date,
            "end_date": item.end_date,
            "highlights": [
                highlight for highlight in item.highlights if highlight and highlight.strip()
            ],
        }
        for item in extracted.experiences
    ]

    educations = [
        {
            "institution_name": item.institution_name,
            "credential_name": item.credential_name,
            "type": _clean_choice(item.type, EDUCATION_TYPES),
            "start_date": item.start_date,
            "end_date": item.end_date,
        }
        for item in extracted.educations
    ]

    additional_context = [
        {"entry": item.entry.strip()} for item in extracted.additional_context if item.entry
    ]

    return {
        "full_name": extracted.full_name,
        "contact_email": extracted.contact_email,
        "location": extracted.location,
        "language_preference": extracted.language_preference,
        "requires_sponsorship": extracted.requires_sponsorship,
        "yoe": extracted.yoe,
        "social_media": social_media,
        "work_eligibility": work_eligibility,
        "skills": skills,
        "roles": roles,
        "experiences": experiences,
        "educations": educations,
        "additional_context": additional_context,
    }


def _maybe_embed_profile(connection, user_id: int, profile: dict[str, Any]) -> None:
    """Optionally compute users.profile_embedding (used by Agent 2).

    Disabled by default (ENABLE_PROFILE_EMBEDDING) because it downloads the
    sentence-transformers model. Skips silently if the dependency is missing.
    """
    if not settings.enable_profile_embedding:
        return

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return

    parts = [
        profile.get("full_name") or "",
        profile.get("location") or "",
        " ".join(skill["name"] for skill in profile.get("skills", [])),
        " ".join(role["name"] for role in profile.get("roles", [])),
        " ".join(
            education.get("credential_name") or "" for education in profile.get("educations", [])
        ),
        " ".join(experience.get("role") or "" for experience in profile.get("experiences", [])),
    ]
    text = ". ".join(part for part in parts if part)
    if not text.strip():
        return

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vector = model.encode(text, normalize_embeddings=True).tolist()
    connection.execute(
        """
        UPDATE users
        SET profile_embedding = %s, embedding_model = %s, embedded_at = now()
        WHERE id = %s
        """,
        (vector, "all-MiniLM-L6-v2", user_id),
    )
    connection.commit()


def run_extraction(user_id: int) -> None:
    """Run the full Agent 1 pipeline and record progress in the status holder."""
    extraction_state.set_status("extracting", "Reading your documents and building your profile…")

    try:
        with get_connection() as connection:
            documents = repository.get_documents_with_paths(connection, user_id)

            sources: list[tuple[str, str]] = []
            for document in documents:
                text = extract_document_text(
                    document["storage_path"], document["mime_type"], document["file_name"]
                )
                repository.set_document_text(connection, document["id"], text)
                if text.strip():
                    sources.append((document["file_name"], text))

        if not sources:
            extraction_state.set_status(
                "error", "No readable text was found in the uploaded documents."
            )
            return

        extracted = extract_profile(sources)
        profile = _to_profile_dict(extracted)

        with get_connection() as connection:
            # Extraction replaces the document-derived profile (documents are the
            # source of truth); user settings and uploads are left untouched.
            repository.clear_profile(connection, user_id)
            repository.save_profile(connection, user_id, profile)
            _maybe_embed_profile(connection, user_id, profile)

        extraction_state.set_status(
            "done", "Profile updated from your documents. Review the form and save your changes."
        )
    except Exception as error:  # noqa: BLE001 - surface any failure to the UI
        extraction_state.set_status("error", f"Extraction failed: {error}")