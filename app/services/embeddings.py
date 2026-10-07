"""Sentence-embedding service for the semantic (cosine) pre-filter (Agent 2, Step 2).

Wraps LangChain's `FastEmbedEmbeddings` (ONNX Runtime via `fastembed`, **no
PyTorch**) for the `all-MiniLM-L6-v2` model (384-dim, matching the DB
`vector(384)` columns).

The candidate profile is embedded **once** per curation run, and every scraped
posting is embedded per iteration; cosine similarity between the two vectors gates
which postings enter the queue (against the "Semantic Text Match" threshold).
"""

import logging
import math
import threading

from app.config import settings

logger = logging.getLogger(__name__)

_EMBEDDINGS = None
_EMBEDDINGS_LOCK = threading.Lock()


def _get_embeddings():
    """Load and cache the LangChain embeddings object (thread-safe, lazy)."""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        with _EMBEDDINGS_LOCK:
            if _EMBEDDINGS is None:
                from langchain_community.embeddings import FastEmbedEmbeddings

                logger.info("Loading embedding model %s...", settings.embedding_model)
                _EMBEDDINGS = FastEmbedEmbeddings(model=settings.embedding_model)
    return _EMBEDDINGS


def embed_text(text: str) -> list[float]:
    """Return the embedding vector for a piece of text."""
    vector = _get_embeddings().embed_query(text or "")
    return list(vector)


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Cosine of the angle between two vectors (robust to un-normalised inputs)."""
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vector_a, vector_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (math.sqrt(norm_a) * math.sqrt(norm_b)))


def build_profile_text(profile: dict) -> str:
    """Compose the text embedded once per run: skills + education + years of experience."""
    skills = profile.get("skills") or []
    educations = profile.get("educations") or []
    yoe = profile.get("yoe")

    parts: list[str] = []
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    if educations:
        parts.append("Education: " + "; ".join(educations))
    if yoe is not None:
        parts.append(f"Years of experience: {yoe}")
    return ". ".join(parts)