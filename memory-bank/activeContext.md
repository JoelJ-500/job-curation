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
  and the full editable profile form mirroring the DB. Runs against a mock data layer until
  the backend exists (`VITE_USE_MOCK_API`).

## Current Focus
The database schema and the User Profile UI are complete. Next is scaffolding the Python
backend (proposed FastAPI) and implementing **Agent 1 (Acquire User Data)** so the upload →
extract flow becomes real, then wiring the frontend to it.

## Immediate Next Steps (recommended order)
1. **Confirm remaining open technical decisions with the user** (blocking for
   design-consistent code):
   - LLM provider + model (embedding resolved: `all-MiniLM-L6-v2`, `vector(384)`).
   - LaTeX→PDF toolchain (local `latexmk`/`pdflatex`) and `.docx` export (e.g., Pandoc).
   - React build tooling (Vite recommended) and styling library.
   - Clarify "Skill Match threshold" vs. "Semantic Text Match" threshold.
2. **Scaffold the backend** — package layout (e.g., `app/agents`, `app/models`,
   `app/services`, `app/api`), add `requirements.txt`/`pyproject.toml` with pinned,
   non-deprecated versions (langchain, langgraph, pydantic, psycopg + pgvector, selenium,
   scrapy, fastapi or similar), and wire the Postgres vector store (`langchain-postgres`)
   to the existing schema.
3. **Implement Agent 1** — Pydantic models (`CandidateProfile`, `WorkExp`) matching the
   schema in `systemPatterns.md`, ingest/normalize uploads, extraction chain with the
   design's prompt, and profile persistence.
4. **Implement Agent 2 Step 1** — scrapers for Hiring Cafe and Eluta (HTML-first, Scrapy
   fallback), queue sorted by posting age with the "job" data format.
5. **Implement Agent 2 Steps 2–4** — embedding + cosine filter, LLM scoring chain with the
   strict JSON contract, and priority queue builder.
6. **Implement Agent 3** — resume-generation chain (Jake's template), LaTeX output, PDF +
   optional `.docx`.
7. **Build the React front-end** — 🟡 Profile form done (upload + editable form, mock data
   layer). Remaining: wire the UI to the backend API contract, then Settings + Main Dashboard.
8. **Orchestrate with LangGraph** — wire agents into a graph; support background/scheduled
   curator runs and the configurable per-job time delay.

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
