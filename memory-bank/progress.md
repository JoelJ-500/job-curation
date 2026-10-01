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
| Backend source code | ⬜ | Not started |
| `requirements.txt` / `pyproject.toml` | ⬜ | Not present |
| Postgres Vector DB setup / schema | ✅ | Applied automatically on container start |
| LangGraph agent graph | ⬜ | Not started |

## What Is Left To Build (High Level)
1. **Project scaffolding** — backend package structure, dependency manifest, frontend app.
2. **Agent 1 (Acquire User Data)** — file ingestion, text normalization, Pydantic extraction,
   profile persistence, and the editable profile form (front-end + API).
3. **Agent 2 (Job Curation)** — Selenium/Scrapy scrapers for Hiring Cafe & Eluta, queue
   builder sorted by age, embedding filter (LangChain + Postgres vector store), LLM
   compatibility scorer, priority queue builder.
4. **Agent 3 (Resume Builder)** — resume-generation chain, LaTeX output, PDF (and optional
   `.docx`) compilation.
5. **Front-end** — 🟡 Profile form done (upload + editable form, mock data layer). Still to
   build: Settings page (thresholds + hover help) and Main Dashboard (ranked jobs + resumes
   + apply links + delete), plus wiring the UI to the backend.
6. **Orchestration** — LangGraph graph wiring the agents, background/scheduled curator runs,
   time-delay anti-bot handling.
7. **Persistence** — ✅ Postgres Vector DB schema for profiles, jobs, embeddings, and
   queues (see `db/schema.sql`); connection helpers still to add with the backend.
8. **Testing & validation** — unit tests for extraction, filters, scoring, and resume output;
   LaTeX compilation checks.

## Open Decisions To Resolve Before/While Building
- LLM provider + model (embedding model resolved: `all-MiniLM-L6-v2`, `vector(384)`).
- LaTeX→PDF toolchain and `.docx` generation approach.
- Frontend build tooling + styling: **resolved** — Vite 5 + TypeScript + React Router + MUI,
  forms via react-hook-form (`frontend/`).
- Backend framework for the API (FastAPI proposed) and where uploaded document files are
  stored (DB `bytea` vs filesystem path) — to decide with Agent 1.
- Mapping between "Skill Match threshold" (skill overlap count) and "Semantic Text Match"
  threshold (embedding cosine) — both persisted in `user_settings`.
- Concrete `langchain-postgres` `PGVectorStore` wiring against the `jobs`/`users` vector
  columns (added with the agent code).

## Milestones (Proposed)
- **M0** — Scaffolding + Memory Bank (this doc).
- **M1** — Profile acquisition + extraction working end-to-end.
- **M2** — Scraping + embedding filter producing a raw queue.
- **M3** — LLM scoring + priority queue.
- **M4** — Resume Builder producing compilable one-page LaTeX.
- **M5** — Front-end dashboard + settings + profile form.
- **M6** — Background orchestration + anti-bot delay.
