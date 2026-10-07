# Active Context: job-curation

> Current work focus and immediate next steps. Update this file frequently.
> Source of truth: `DESIGN.md`.

## Current State
- Repository initialized with: `DESIGN.md` (master design doc), `.clinerules/rules.md`,
  `Dockerfile` (Python 3.11 multi-stage), `README.md`, `commands.txt`, `.gitignore`.
- **Postgres + pgvector database is up and verified** (M0): `docker-compose.yml` runs
  `pgvector/pgvector:pg16` as `job_curation_db`; the normalized schema in `db/schema.sql`
  (18 tables, HNSW index, `updated_at` triggers) applies on first start, and
  `db/smoke_test.sql` passes. Embeddings are `vector(384)` for `all-MiniLM-L6-v2`.
- Git: branch `main`; the new DB files are currently untracked.
- **Memory Bank initialized** from `DESIGN.md`. No application source code exists yet — the
  project is at **M0 (scaffolding)**.
- No general dependency manifest (`requirements.txt`/`pyproject.toml`) yet (DB deps are in
  `requirements-db.txt`).
- **Frontend User Profile UI built**: React + TS + Vite + MUI app in `frontend/` with an app
  shell (Profile/Settings/Dashboard routes), a document uploader that triggers extraction,
  and the full editable profile form mirroring the DB.
- **Agent 1 (backend) implemented and verified** (`app/`): FastAPI + psycopg + LangChain
  (Groq — `openai/gpt-oss-120b` for text, `qwen/qwen3.8-27b` for vision). Ran as a
  `backend` compose service on port 8000. Uploading
  documents converts them to clean text, extracts a `CandidateProfile` via Pydantic +
  LLM, and writes it transactionally to Postgres; `PUT /api/profile` is a diff-aware upsert.
  End-to-end tested through the API (upload -> extract -> edit/save -> delete -> re-run).
  The frontend now runs against the real API (`VITE_USE_MOCK_API=false`).

## Current Focus
Agent 1 (user data acquisition) is implemented and verified end-to-end. **Agent 2 Steps 1–2**
are implemented and verified: scraping (Settings "job postings per run" default 10 + Start
curation button; Eluta working, HiringCafe Cloudflare-blocked) and the **dedup + cosine
pre-filter** (per-posting duplicate check against `jobs`/`curated_jobs`, profile embedded
once per run, "Semantic Text Match" threshold default 0.5 editable in Settings). Next:
**Agent 2 Steps 3–4** (LLM ATS/compatibility scoring → priority queue) and the Main
Dashboard.

## Immediate Next Steps (recommended order)
1. **Agent 2 Step 3** — LLM compatibility scorer (strict JSON contract, weighted rubric).
2. **Agent 2 Step 4** — priority queue builder (`compatibility_score_threshold`), write to
   `curated_jobs`; **move the run-limit check to count postings surviving Step 3**.
3. **Unblock HiringCafe** — needs a stealth browser / residential proxy to pass Cloudflare.
4. **Agent 3 (Resume Builder)** — Jake's template LaTeX, PDF + optional `.docx`.
5. **Main Dashboard** — ranked curated jobs + resumes + apply links + delete.
6. **Orchestrate with LangGraph** — wire agents into a graph; background/scheduled runs.

## Active Decisions / Assumptions
- Treat `DESIGN.md` as the master spec (`.clinerules` refers to it as `SYSTEM_DESIGN.md`).
- Follow the bracket-on-new-line style and minimal-dependency rules from `.clinerules`.
- Do not invent algorithms or change UI patterns; ask first if a task conflicts with the
  design.
- Every design change must be reflected back into the Memory Bank.

## Known Watch-Outs
- Keep agent contexts small to prevent hallucination and reduce token cost.
- The embedding filter MUST run before the LLM step (cost control).
- Resumes must never fabricate — the candidate profile is the only source of truth.
- Respect the one-page / single-column / standard-header ATS formatting constraints.

## Recent Changes
- 2026-10-07: **Agent 2 Step 2 (dedup + cosine pre-filter) built & verified.** The
  curation agent now, per posting and in the same iteration it is read, (1) skips links
  already in `jobs`/`curated_jobs` and (2) embeds the posting and drops it if its cosine
  similarity to the profile vector is below the **Semantic Text Match** threshold
  (default 0.5, editable in Settings). The profile (skills + education + yoe) is embedded
  **once** per run. Embeddings use LangChain `FastEmbedEmbeddings` (`langchain-community`
  + `fastembed`, ONNX, **no PyTorch**), model `all-MiniLM-L6-v2`, via
  `app/services/embeddings.py`; cosine is computed in Python. New repository helpers
  `get_semantic_profile` / `job_exists`; the Settings page gained the threshold field.
  Verified: a run queued 10 postings with `similarity` recorded (e.g. 0.579); threshold
  0.99 queued 0; a re-run skipped already-stored links and scraped deeper for new ones.
- 2026-10-06: **Agent 2 Step 1 (gather job postings) built & verified.** Added a
  "job postings per run" setting (default 10) + `GET/PUT /api/settings`; a **Start
  curation** button + status on the Settings page; two concurrent Selenium scrapers
  (`ElutaScraper` working, `HiringCafeScraper` Cloudflare-blocked) each with a unique
  driver; scraping agents (`app/agents/scrape_agent.py`) that plan per-site filters and
  offer an LLM HTML-parse fallback; a curation orchestrator
  (`app/agents/curation_agent.py`) running both sites concurrently with a shared
  limit-capped queue; and a queue text-file output (`data/queue/`) plus `jobs` /
  `scrape_runs` persistence. Docker image now installs Chromium + ChromeDriver
  (`chromium`/`chromium-driver`) and `selenium`. Verified end-to-end: a run gathered 10
  Eluta postings with full posting text and wrote the queue file.
- 2026-10-05: **Switched Agent 1's LLM from Google Gemini to Groq** (the Gemini
  `gemini-3.5-flash` calls were all failing). Extraction now uses `langchain-groq` with
  `openai/gpt-oss-120b` (structured output via `method="json_schema"`, `max_tokens=16384`,
  `reasoning_effort="low"`); images and scanned PDFs route to the Groq vision model
  `qwen/qwen3.8-27b` (scanned PDFs rendered to PNG with PyMuPDF, capped at 3 pages).
  Added config `GROQ_API_KEY`/`GROQ_MODEL`/`GROQ_VISION_MODEL`; `requirements.txt` now
  installs `langchain-groq` + `pymupdf` (dropped `langchain-google-genai`). Verified
  end-to-end through the API: text PDF, image, and scanned PDF all extract successfully.
- 2026-10-01: Implemented **Agent 1** (`app/`): FastAPI + psycopg 3 + LangChain
  (`langchain-google-genai`, `gemini-3.5-flash`). Added a `backend` docker-compose service
  (port 8000), `requirements.txt`, backend config, DB repository (diff-aware save + clear),
  agents (document ingest, text cleaning, profile extractor, orchestrator), the profile /
  documents API, and the `size_bytes` column on `user_documents`. Verified end-to-end and
  flipped the frontend to the real API (`VITE_USE_MOCK_API=false`).
- 2026-10-01: Built the **User Profile UI** in `frontend/` (Vite 5 + React + TS + React
  Router + MUI + react-hook-form): app shell with routed Profile/Settings/Dashboard, a
  document uploader that triggers extraction and refills the form, and the full editable
  profile form mirroring the DB schema. Includes a swappable mock data layer + the backend
  API contract; build + dev-server smoke checks pass.
- 2026-10-01: Added the Postgres + pgvector database: `docker-compose.yml`, `db/schema.sql`
  (normalized 18-table schema), `db/README.md`, `db/smoke_test.sql`, `requirements-db.txt`,
  `.env`/`.env.example`; container verified healthy and the smoke test passes. Updated
  `DESIGN.md`'s schema section and Memory Bank (`systemPatterns`, `techContext`, `progress`,
  `activeContext`).
- 2026-01-10: Created `memory-bank/` and populated `projectbrief.md`, `productContext.md`,
  `systemPatterns.md`, `techContext.md`, `progress.md`, `activeContext.md`; added Memory
  Bank instructions to `.clinerules/`.
