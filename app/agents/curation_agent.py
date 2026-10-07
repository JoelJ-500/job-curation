"""Agent 2, Steps 1-2: scrape job postings, then dedup + cosine-filter them.

Both site workers run concurrently against a shared, thread-safe queue capped at the
user's `curator_job_limit` (order is never static; an exhausted site yields to the
other). The candidate profile is embedded **once**, before any scraping; each
posting, in the same iteration it is read, is:
  1. checked against `jobs` + `curated_jobs` (duplicates are skipped), then
  2. embedded and compared to the profile vector by cosine similarity (anything
     below the "Semantic Text Match" threshold is discarded).
Surviving postings are written to a text file (and the `jobs` table) for the LLM
ATS-scoring step.
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
from app.services import curation_state, embeddings

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
            handle.write(f"similarity: {job.get('semantic_score')}\n")
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


class _RunContext:
    """Shared state passed to both site workers for one curation run."""

    def __init__(self, buffer: "_CurationBuffer", delay: float, profile_vector: list[float],
                 threshold: float, user_id: int) -> None:
        self.buffer = buffer
        self.delay = delay
        self.profile_vector = profile_vector
        self.threshold = threshold
        self.user_id = user_id
        self.stats: dict[str, dict[str, int]] = {}
        self.stats_lock = threading.Lock()

    def record(self, name: str, found: int, kept: int) -> None:
        with self.stats_lock:
            self.stats[name] = {"found": found, "kept": kept}


def _job_similarity(profile_vector: list[float], job: dict) -> float:
    """Cosine similarity between the profile vector and a posting's embedding."""
    text = (f"{job.get('title') or ''}\n{job.get('job_posting') or ''}").strip()
    if not text or not profile_vector:
        return 0.0
    try:
        job_vector = embeddings.embed_text(text)
    except Exception as error:  # noqa: BLE001 - a single bad posting shouldn't stop the run
        logger.warning("Embedding failed for %s: %s", job.get("link"), error)
        return 0.0
    return embeddings.cosine_similarity(profile_vector, job_vector)


def _site_worker(name: str, scraper, plans: list, context: _RunContext, finalize) -> None:
    """Scrape one site, applying the dedup + cosine filter to every posting."""
    found = 0
    kept = 0
    buffer = context.buffer
    try:
        opener = getattr(scraper, "open_search", None)
        if callable(opener):
            opener()

        # Each worker thread owns its own connection (psycopg isn't thread-safe).
        with get_connection() as connection:
            for plan in plans:
                if buffer.is_full():
                    break
                logger.info("%s: searching role=%r", name, plan.role_query)
                try:
                    for raw in scraper.iter_jobs(plan):
                        if buffer.is_full():
                            break
                        link = raw.get("link")
                        if not link:
                            continue
                        found += 1

                        # 1. Skip postings already in jobs or curated_jobs (checked right
                        #    after reading the result, before the costlier detail fetch).
                        if repository.job_exists(connection, link):
                            logger.info("%s: duplicate, skipping %s", name, link)
                            continue

                        # Build the final record (Eluta fetches the full posting text here).
                        job = finalize(scraper, raw)

                        # 2. Cosine similarity vs. the (once-computed) profile vector.
                        similarity = _job_similarity(context.profile_vector, job)
                        if similarity < context.threshold:
                            logger.info(
                                "%s: %.3f < %.3f threshold, discarding %s",
                                name, similarity, context.threshold, link,
                            )
                            continue

                        job["semantic_score"] = round(similarity, 4)
                        if not buffer.add(job):
                            break

                        # Persist so later runs dedup this posting.
                        repository.upsert_job(
                            connection,
                            job.get("source") or "unknown",
                            job.get("title") or "",
                            link,
                            None,
                            job.get("job_posting") or "",
                        )
                        kept += 1
                        curation_state.set_progress(
                            buffer.count(),
                            f"Queued {buffer.count()} matching postings "
                            f"(min similarity {context.threshold})...",
                        )
                        polite_pause(context.delay)
                except Exception as error:  # noqa: BLE001 - one bad role shouldn't stop the site
                    logger.warning("%s: role %r failed: %s", name, plan.role_query, error)
    except Exception as error:  # noqa: BLE001
        logger.warning("%s: worker failed: %s", name, error)
    finally:
        scraper.close()
        context.record(name, found, kept)


def _log_scrape_runs(stats: dict[str, dict[str, int]]) -> None:
    """Record a scrape_runs telemetry row per source (best effort)."""
    try:
        with get_connection() as connection:
            for source, counts in stats.items():
                run_id = repository.start_scrape_run(connection, source)
                repository.finish_scrape_run(connection, run_id, counts["found"])
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not log scrape_runs: %s", error)


def run_curation(user_id: int) -> None:
    """Run the Step 1-2 pipeline: scrape both sites, dedup + cosine-filter."""
    curation_state.set_running("Starting the job curator...")

    try:
        with get_connection() as connection:
            user_settings = repository.get_settings(connection, user_id)
            profile = repository.get_filter_inputs(connection, user_id)
            semantic_profile = repository.get_semantic_profile(connection, user_id)

        if not profile.get("roles"):
            curation_state.set_error("No roles found in the profile. Add roles before curating.")
            return

        limit = int(user_settings.get("curator_job_limit") or DEFAULT_LIMIT)
        delay = float(user_settings.get("time_delay_seconds") or 0)
        threshold = float(user_settings.get("semantic_text_match_threshold") or 0.0)

        # Embed the candidate profile ONCE, before any scraping happens.
        curation_state.set_running("Computing your profile embedding...")
        profile_vector = embeddings.embed_text(embeddings.build_profile_text(semantic_profile))

        buffer = _CurationBuffer(limit)
        context = _RunContext(buffer, delay, profile_vector, threshold, user_id)

        plans = {
            "hiringcafe": plan_searches(profile, "hiringcafe", SITE_HINTS["hiringcafe"]),
            "eluta": plan_searches(profile, "eluta", SITE_HINTS["eluta"]),
        }

        curation_state.set_running(
            f"Scraping up to {limit} postings (min similarity {threshold})..."
        )
        workers = [
            threading.Thread(
                target=_site_worker,
                args=("eluta", ElutaScraper(), plans["eluta"], context, _finalize_eluta),
                name="eluta-worker",
                daemon=True,
            ),
            threading.Thread(
                target=_site_worker,
                args=("hiringcafe", HiringCafeScraper(), plans["hiringcafe"], context, _finalize_plain),
                name="hiringcafe-worker",
                daemon=True,
            ),
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        jobs = buffer.snapshot()
        output_file = _write_queue_file(jobs)
        _log_scrape_runs(context.stats)

        if not jobs:
            curation_state.set_error(
                "No new postings passed the filters. They may already be curated or "
                "below the Semantic Text Match threshold — try again later or lower it."
            )
            return

        curation_state.set_done(
            f"Queued {len(jobs)} postings (cosine >= {threshold}). Queue written to {output_file}.",
            len(jobs),
            output_file,
        )
    except Exception as error:  # noqa: BLE001 - surface any failure to the UI
        logger.exception("Curation failed")
        curation_state.set_error(f"Curation failed: {error}")
