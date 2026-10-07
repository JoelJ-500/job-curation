# Progress: job-curation

> What has already been specified vs. what is left to build.
> Source of truth: `DESIGN.md`, repo state, `.clinerules/rules.md`.

## Legend
- ✅ Specified (design complete / artifacts exist)
- 🟡 Partially specified (design exists, some decisions open)
- ⬜ Not started (to build)

## Specification Status (Design Doc: `DESIGN.md`)
| Area | Status | Notes |
| --- | --- | --- |
| ATS bypass strategy & constraints | ✅ | 5 curated tips; informs algorithms |
| 4-agent subprocess breakdown | ✅ | Acquire data → Curate → Resume → Dashboard |
| Candidate profile schema (Pydantic) | ✅ | All fields + `WorkExp` defined |
| Profile extraction prompt | ✅ | Verbatim prompt provided |
| Job "data format" | ✅ | title, link, date, posting, ATS score |
| Job board targets | ✅ | Hiring Cafe, Eluta (North America) |
| Search filters | ✅ | role, age, location, yoe |
| Embedding filter (threshold/cosine) | ✅ | Default 0.5, 0–1 range |
| LLM compatibility rubric + JSON output | ✅ | Weights 50/25/15/10; strict JSON schema |
| Priority queue rules | ✅ | Threshold default 70, sorted desc |
| Resume Builder prompt (full) | ✅ | Jake's template + ATS rules |
| UI layout (Settings / Profile / Dashboard) | ✅ | Fields & behaviors described |
| Multi-agent design principles | ✅ | Agent = object; context-length discipline |
| Telemetrics, application tracker | 🟡 | Listed as "Future Improvements" only |
| Autonomous site-scanning agent | 🟡 | Future; noted token-heavy |
| GitHub job repo ingestion | 🟡 | Future |
| Regex/structured extraction to cut tokens | 🟡 | Future |

## Repo Artifacts Status
| Artifact | Status | Notes |
| --- | --- | --- |
| `DESIGN.md` | ✅ | Master design doc (382 lines; schema section normalized) |
| `.clinerules/rules.md` | ✅ | Primary libraries + conventions |
| `Dockerfile` | 🟡 | Multi-stage Python 3.11; only installs `langchain`, `langgraph` |
| `commands.txt` | ✅ | Docker exec instructions (gitignored) |
| `README.md` | ✅ | One-line description |
| `memory-bank/` | ✅ | This Memory Bank (initialized from design doc) |
| `docker-compose.yml` | ✅ | Postgres 16 + pgvector service (`job_curation_db`) |
| `db/schema.sql` | ✅ | Normalized schema (single source of truth) |
| `db/README.md` | ✅ | DB usage + entity overview |
| `db/smoke_test.sql` | ✅ | Rollback smoke test for the schema |
| `.env.example` / `.env` | ✅ | DB connection settings (`.env` gitignored) |
| `requirements-db.txt` | ✅ | `psycopg[binary]`, `pgvector` |
| `frontend/` (React app) | 🟡 | Scaffolded: app shell + **User Profile page** done; Settings/Dashboard placeholders. Mock data layer; not yet wired to the backend |
| `requirements.txt` | ✅ | Backend deps (FastAPI, psycopg, LangChain, langchain-groq, pypdf, python-docx, pymupdf) |
| `app/` (backend + Agent 1) | ✅ | FastAPI + psycopg + LangChain; document ingestion, extraction, persistence |
| Backend source code | ✅ | See `app/` (Agent 1 implemented) |
| Postgres Vector DB setup / schema | ✅ | Applied automatically on container start |
| LangGraph agent graph | ⬜ | Not started |

## What Is Left To Build (High Level)
1. **Project scaffolding** — backend package structure, dependency manifest, frontend app.
2. **Agent 1 (Acquire User Data)** — ✅ Implemented: file ingestion + text
   normalization, Pydantic extraction (Groq `openai/gpt-oss-120b`; vision via
   `qwen/qwen3.8-27b`), profile persistence,
   document upload + extraction API, and the editable profile form now talks to the real
   API. Verified end-to-end. Profile embedding deferred behind a flag.
3. **Agent 2 (Job Curation)** — 🟡 **Step 1 (gather postings) done**: settings
   (`curator_job_limit`, default 10), concurrent Selenium scrapers for Eluta (working) and
   HiringCafe (Cloudflare-blocked), scraping agents, queue text-file output, and `jobs`
   persistence. Still to build: Step 2 (embedding filter), Step 3 (LLM compatibility
   scorer), Step 4 (priority queue).
   - **Temporary:** `curator_job_limit` counts **scraped** postings for now — change it to
     count postings surviving the cosine + LLM steps when Steps 2–4 land.
4. **Agent 3 (Resume Builder)** — resume-generation chain, LaTeX output, PDF (and optional
   `.docx`) compilation.
5. **Front-end** — 🟡 Profile form done; **Settings page** now has the
   "job postings per run" field + **Start curation** button + status. Still to build: the
   remaining Settings thresholds and the Main Dashboard (ranked jobs + resumes + apply
   links + delete).
6. **Orchestration** — LangGraph graph wiring the agents, background/scheduled curator runs,
   time-delay anti-bot handling.
7. **Persistence** — ✅ Postgres Vector DB schema for profiles, jobs, embeddings, and
   queues (see `db/schema.sql`); connection helpers still to add with the backend.
8. **Testing & validation** — unit tests for extraction, filters, scoring, and resume output;
   LaTeX compilation checks.

## Open Decisions To Resolve Before/While Building
- LLM provider + model (embedding model resolved: `all-MiniLM-L6-v2`, `vector(384)`).
- LaTeX→PDF toolchain and `.docx` generation approach.
- Mapping between "Skill Match threshold" (skill overlap count) and "Semantic Text Match"
  threshold (embedding cosine) — both persisted in `user_settings`.
- Concrete `langchain-postgres` `PGVectorStore` wiring against the `jobs`/`users` vector
  columns (Agent 2).
- LLM provider/model: **resolved** — **Groq** (`openai/gpt-oss-120b` text model,
  `qwen/qwen3.8-27b` vision model), replacing Google Gemini.

## Milestones (Proposed)
- **M0** — Scaffolding + Memory Bank (this doc).
- **M1** — Profile acquisition + extraction working end-to-end.
- **M2** — Scraping + embedding filter producing a raw queue.
- **M3** — LLM scoring + priority queue.
- **M4** — Resume Builder producing compilable one-page LaTeX.
- **M5** — Front-end dashboard + settings + profile form.
- **M6** — Background orchestration + anti-bot delay.
