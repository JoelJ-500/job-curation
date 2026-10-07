"""Application configuration.

All settings are read from the environment (populated from the root `.env` file).
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load the root .env file (works whether the app runs from /app or a subfolder).
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the backend and Agent 1."""

    # Database
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    # LLM (Groq)
    groq_api_key: str | None
    groq_model: str
    groq_vision_model: str

    # Files
    upload_dir: str

    # Scraping (Selenium / Chromium)
    chrome_binary: str
    chromedriver_path: str
    headless_browser: bool
    queue_dir: str

    # Embeddings (semantic pre-filter)
    embedding_model: str

    # Feature flags
    enable_profile_embedding: bool

    @property
    def database_dsn(self) -> str:
        """libpq connection string used by psycopg."""
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password}"
        )


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    """Build the settings object from environment variables."""
    return Settings(
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_user=os.getenv("POSTGRES_USER", "job_curation"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
        postgres_db=os.getenv("POSTGRES_DB", "job_curation"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        groq_vision_model=os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"),
        upload_dir=os.getenv("UPLOAD_DIR", "/app/data/uploads"),
        chrome_binary=os.getenv("CHROME_BIN", "/usr/bin/chromium"),
        chromedriver_path=os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"),
        headless_browser=_as_bool(os.getenv("HEADLESS_BROWSER"), True),
        queue_dir=os.getenv("QUEUE_DIR", "/app/data/queue"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        enable_profile_embedding=_as_bool(os.getenv("ENABLE_PROFILE_EMBEDDING"), False),
    )


settings = get_settings()
