"""Shared LangChain chat models (Groq).

Two models are exposed:
  - `get_chat_model()`   -> the text model (OpenAI GPT-OSS 120B) used for profile
                            extraction and reading plain-text files.
  - `get_vision_model()` -> the multimodal model used only to read images and
                            scanned PDFs, because GPT-OSS is text-only.
"""

from functools import lru_cache

from langchain_groq import ChatGroq

from app.config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGroq:
    """Return the configured Groq text model (file reading and extraction)."""
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to the root .env file.")

    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
        max_tokens=16384,
        reasoning_effort="low",
        max_retries=2,
    )


@lru_cache(maxsize=1)
def get_vision_model() -> ChatGroq:
    """Return the Groq vision model (reads images and scanned PDFs)."""
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to the root .env file.")

    return ChatGroq(
        model=settings.groq_vision_model,
        api_key=settings.groq_api_key,
        temperature=0,
        max_tokens=8192,
        max_retries=2,
    )


def message_text(message) -> str:
    """Flatten a LangChain message's content (string or content blocks) to text."""
    content = message.content
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)
