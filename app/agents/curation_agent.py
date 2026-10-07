"""Agent 2, Step 1: curate job postings by scraping HiringCafe and Eluta.

The coordinator runs both site workers concurrently against a shared, thread-safe
queue capped at the user's `curator_job_limit`. Whichever site yields jobs first
contributes; when one site runs out of roles/results the other keeps going, so the
scrape order is never static. Scraped jobs are written to a text file (and the
`jobs` table) for the later steps (embeddings -> LLM scoring).
"""

import logging
import threading
from datetime import datetime
from pathlib import Path

from app.agents.scrape_agent import plan_searches
from app.config import settings
from app.db import repository
from app.db.connection import get_connection
from app.scrapers.base import polite_pause
from app.scrapers.eluta import ElutaScraper
from app.scrapers.hiring_cafe import HiringCafeScraper
from app.services import curation_state

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 10

# What each site's search controls support (passed to the filter agent).
SITE_HINTS = {
    "hiringcafe": (
        "Search box labelled 'Job title or keyword'. Filters: Location, Experience "
        "(match the candidate's years of experience), Language. Sort by most recent. "
        "No category filter."
    ),
    "eluta": (
        "Search box labelled 'job title or keywords'. Location box 'city, province'. "
        "Category filter chosen from the allowed list. Sort by date posted."
    ),
}


class _CurationBuffer:
    """Thread-safe, deduplicated queue capped at the run's job limit."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._jobs: list[dict] = []
        self._links: set[str] = set()
        self._lock = threading.Lock()

    def add(self, job: dict) -> bool:
        """Add a job. Returns False once the limit has been reached."""
        with self._lock:
            if len(self._jobs) >= self.limit:
                return False
            link = job.get("link")
            if not link or link in self._links:
                return True
            self._links.add(link)
            self._jobs.append(job)
            return True

    def is_full(self) -> bool:
        with self._lock:
            return len(self._jobs) >= self.limit

    def count(self) -> int:
        with self._lock:
            return len(self._jobs)

    def snapshot(self) -> list[dict]:
        with self._lock:
            return list(self._jobs)


def _write_queue_file(jobs: list[dict]) -> str:
    """Write the queue to a text file for inspection (testing artifact)."""
    directory = Path(settings.queue_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"curation_{stamp}.txt"

    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"# Job curation queue - {len(jobs)} postings - {stamp}\n\n")
        for index, job in enumerate(jobs, start=1):
            handle.write(f"===== JOB {index} =====\n")
            handle.write(f"source: {job.get('source')}\n")
            handle.write(f"title: {job.get('title')}\n")
            handle.write(f"link: {job.get('link')}\n")
            handle.write(f"date of posting: {job.get('date_of_posting')}\n")
            handle.write(f"company: {job.get('company')}\n")
            handle.write(f"location: {job.get('location')}\n")
            handle.write("job posting:\n")
            handle.write(f"{job.get('job_posting')}\n\n")
    return str(path)


def _finalize_eluta(scraper, job: dict) -> dict:
    """Build the final job record for Eluta, fetching the full posting text."""
    detail = scraper.fetch_detail(job.get("link", "")) if job.get("link") else ""
    posting = (detail or "").strip() or (job.get("summary") or "")
    return {
        "source": "eluta",
        "title": job.get("title") or "",
        "link": job.get("link") or "",
        "date_of_posting": job.get("date_text") or "",
        "company": job.get("company") or "",
        "location": job.get("location") or "",
        "job_posting": posting,
    }


def _finalize_plain(_scraper, job: dict) -> dict:
    """Build the final job record for sites whose results already hold the text."""
    return {
        "source": job.get("source") or "",
        "title": job.get("title") or "",
        "link": job.get("link") or "",
        "date_of_posting": job.get("date_text") or "",
        "company": job.get("company") or "",
        "location": job.get("location") or "",
        "job_posting": job.get("summary") or job.get("job_posting") or "",
    }


def _site_worker(name: str, scraper, plans: list, buffer: _CurationBuffer, delay: float, finalize) -> None:
    """Scrape one site across its role plans until the shared queue is full."""
    try:
        opener = getattr(scraper, "open_search", None)
        if callable(opener):
            opener()

        for plan in plans:
            if buffer.is_full():
                break
            logger.info("%s: searching role=%r", name, plan.role_query)
            try:
                for raw in scraper.iter_jobs(plan):
                    if buffer.is_full():
                        break
                    job = finalize(scraper, raw)
                    if not job.get("link"):
                        continue
                    if not buffer.add(job):
                        break
                    curation_state.set_progress(
                        buffer.count(), f"Scraped {buffer.count()} postings..."
                    )
                    polite_pause(delay)
            except Exception as error:  # noqa: BLE001 - one bad role shouldn't stop the site
                logger.warning("%s: role %r failed: %s", name, plan.role_query, error)
    except Exception as error:  # noqa: BLE001
        logger.warning("%s: worker failed: %s", name, error)
    finally:
        scraper.close()


def _persist_jobs(jobs: list[dict]) -> None:
    """Write scraped jobs to the `jobs` table and log a scrape_run per source."""
    counts: dict[str, int] = {}
    for job in jobs:
        counts[job["source"]] = counts.get(job["source"], 0) + 1

    try:
        with get_connection() as connection:
            for job in jobs:
                repository.upsert_job(
                    connection,
                    job.get("source") or "unknown",
                    job.get("title") or "",
                    job.get("link") or "",
                    None,  # date_posted: relative text kept in the queue file for now
                    job.get("job_posting") or "",
                )
            for source, found in counts.items():
                run_id = repository.start_scrape_run(connection, source)
                repository.finish_scrape_run(connection, run_id, found)
    except Exception as error:  # noqa: BLE001 - persistence is best effort
        logger.warning("Could not persist scraped jobs to the database: %s", error)


def run_curation(user_id: int) -> None:
    """Run the full Step 1 pipeline: scrape both sites into the queue."""
    curation_state.set_running("Starting the job curator...")

    try:
        with get_connection() as connection:
            user_settings = repository.get_settings(connection, user_id)
            profile = repository.get_filter_inputs(connection, user_id)

        if not profile.get("roles"):
            curation_state.set_error("No roles found in the profile. Add roles before curating.")
            return

        limit = int(user_settings.get("curator_job_limit") or DEFAULT_LIMIT)
        delay = float(user_settings.get("time_delay_seconds") or 0)
        buffer = _CurationBuffer(limit)

        plans = {
            "hiringcafe": plan_searches(profile, "hiringcafe", SITE_HINTS["hiringcafe"]),
            "eluta": plan_searches(profile, "eluta", SITE_HINTS["eluta"]),
        }

        curation_state.set_running(f"Scraping up to {limit} postings...")
        workers = [
            threading.Thread(
                target=_site_worker,
                args=("eluta", ElutaScraper(), plans["eluta"], buffer, delay, _finalize_eluta),
                name="eluta-worker",
                daemon=True,
            ),
            threading.Thread(
                target=_site_worker,
                args=("hiringcafe", HiringCafeScraper(), plans["hiringcafe"], buffer, delay, _finalize_plain),
                name="hiringcafe-worker",
                daemon=True,
            ),
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        jobs = buffer.snapshot()
        if not jobs:
            curation_state.set_error("No job postings were scraped. Both sites returned nothing.")
            return

        output_file = _write_queue_file(jobs)
        _persist_jobs(jobs)
        curation_state.set_done(
            f"Scraped {len(jobs)} job postings. Queue written to {output_file}.",
            len(jobs),
            output_file,
        )
    except Exception as error:  # noqa: BLE001 - surface any failure to the UI
        logger.exception("Curation failed")
        curation_state.set_error(f"Curation failed: {error}")
