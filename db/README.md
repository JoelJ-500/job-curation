# Database — Postgres + pgvector

The project's long-term store: candidate profile, scraped jobs, curated jobs,
generated resumes, and their vector embeddings. It runs as a Docker container so no
system-wide Postgres install is required.

## Stack
- **PostgreSQL 16** (image `pgvector/pgvector:pg16`)
- **pgvector** extension for cosine-similarity search on embeddings
- Embeddings are `vector(384)`, sized for the open-source model `all-MiniLM-L6-v2`.

## Files
| File | Purpose |
| --- | --- |
| `schema.sql` | Single source of truth for the schema. Applied automatically on first start. |
| `../docker-compose.yml` | Defines the `db` service, volume, healthcheck, and init mount. |
| `../.env` / `../.env.example` | Connection settings (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`). |

## Usage
```bash
# Start the database (first run pulls the image and applies db/schema.sql)
docker compose up -d db

# Wait until healthy, then open a psql shell
docker compose exec db psql -U job_curation -d job_curation

# Stop the database (data is preserved in the `pgdata` volume)
docker compose down

# Wipe all data and re-apply the schema from scratch
docker compose down -v && docker compose up -d db
```

`db/schema.sql` is only executed automatically the **first** time the `pgdata` volume is
created. After changing the schema, either apply the new statements manually or recreate
the volume with `docker compose down -v`.

## Connecting from Python
```python
import psycopg

with psycopg.connect("host=localhost port=5432 dbname=job_curation user=job_curation password=job_curation_dev") as conn:
    ...
```
The LangChain integration (`langchain-postgres` → `PGVectorStore`) will be added with the
agent code.

## Entity overview
- **users** — root profile (`full_name`, `contact_email`, `location`, `language_preference`,
  `requires_sponsorship`, `yoe`, `profile_embedding`).
- **user_settings** — thresholds and curator run parameters from the Settings UI.
- Owned one-to-many children of `users`: **social_media**, **work_eligibility**,
  **experiences** → **experience_highlights**, **educations**,
  **additional_context_entries**, **user_documents**.
- Canonical dictionaries + many-to-many joins: **skills** ↔ **user_skills** ↔ users,
  **roles** ↔ **user_roles** ↔ users.
- **jobs** — every scraped posting (deduplicated by `source` + `link`, carries the posting
  text and its `description_embedding`).
- **curated_jobs** — jobs that passed the embedding and LLM filters, scoped to a user with
  scores and a `status` (soft delete).
- **resumes** — generated LaTeX (plus optional PDF/docx paths) and ATS score per curated job.
- **scrape_runs** — telemetry for curator runs.

## Notes / assumptions
- The app is single-user, but the schema is multi-user safe (`user_id` scoping; `jobs` is a
  shared pool).
- `users.language_preference` and `users.requires_sponsorship` come from the design's Step 1
  "commonly asked fields" (language preference / Sponsorship Y/N).
- `experiences.start_date` / `end_date` and `jobs.company` / `location` were added because
  the resume builder and dashboard need them.
- `user_settings.skill_match_threshold` has no default in the design; a default of `3` is
  used and can be tuned.
- Dashboard "delete" is a soft delete (`curated_jobs.status = 'deleted'`) so history and
  telemetry survive.
