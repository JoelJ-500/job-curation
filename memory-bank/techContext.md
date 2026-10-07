# Tech Context: job-curation

> Tech stack, dependencies, development setup, and technical constraints.
> Source of truth: `DESIGN.md`, `.clinerules/rules.md`, `Dockerfile`, `commands.txt`.

## Primary Stack (from project rules)
- **LangChain** — LLM orchestration, embeddings, vector store integration.
- **LangGraph** — agentic workflow / multi-agent graph orchestration.
- **Selenium** — browser automation (job site interaction / scraping navigation).
- **Scrapy** — only use if you cannot extract HTML data from the parsed websites.
- **React** — front-end. Implemented with **React + TypeScript + Vite 5 + React Router +
  MUI** (forms via `react-hook-form`) in `frontend/`.
- **Postgres Vector Database** — long-term data storage (candidate profiles, job data,
  embeddings).

## Backend (implemented — `app/`)
- **FastAPI** (uvicorn) API + **psycopg 3** + **LangChain** (`langchain-groq`).
- Runs as the `backend` service in `docker-compose.yml` (port `8000`, joined to the
  same network as `db`, repo mounted at `/app`). Start everything with
  `docker compose up -d --build`.
- LLM: **Groq**. Text model **`openai/gpt-oss-120b`** (configurable via `GROQ_MODEL`)
  for profile extraction and reading text files; vision model **`qwen/qwen3.8-27b`**
  (configurable via `GROQ_VISION_MODEL`) for images and scanned PDFs, because GPT-OSS
  is text-only. API key in `GROQ_API_KEY` (root `.env`).
- Backend dependencies are in `requirements.txt`
  (fastapi, uvicorn, python-multipart, pydantic, pydantic-settings, python-dotenv,
  psycopg[binary], pgvector, langchain, langchain-core, langchain-groq, selenium,
  langchain-community, fastembed, pypdf, python-docx, pymupdf).

## Job-site scraping (Agent 2, Step 1 — implemented)
- **Selenium 4 + Chromium 154 + ChromeDriver 154**, installed into the backend image
  (`Dockerfile` apt-installs `chromium`/`chromium-driver`; env `CHROME_BIN`,
  `CHROMEDRIVER_PATH`). Scrapers run **inside the backend container**, not on the host.
- Two **unique Selenium setups** (independent driver/ChromeOptions/user-data-dir):
  `HiringCafeScraper` and `ElutaScraper` (`app/scrapers/`), each paired with the
  scraping agents in `app/agents/scrape_agent.py`.
- `HEADLESS_BROWSER` (default true) toggles headless; `QUEUE_DIR` (default
  `/app/data/queue`) holds the per-run queue text files.
- **Eluta** is server-rendered and scrapes reliably (keywords `#f-ss-q`, location
  `input[name=l]`, category via `filter-field`, sort `sort=post`, results
  `div.organic-job`, full posting text from the `spl/<slug>` detail page, `pg` paging).
- **HiringCafe** (`hiringcafe.com/classic`) loads in Selenium (search box
  `#query-search-v4`) but its search navigation is gated by a **Cloudflare challenge**;
  fully automated scraping is currently blocked (headed/Xvfb and stealth patches did not
  clear it). The scraper detects the challenge, logs it, and the curator falls back to
  the other site. Bypassing this likely needs a stealth driver/residential proxy.

## Scraper API endpoints (Step 1)
- `GET/PUT /api/settings` — curator settings (incl. `curator_job_limit`, default 10).
- `POST /api/curation/start`, `GET /api/curation/status` — start/poll a curation run.

## Embeddings (Agent 2, Step 2 — implemented)
- **LangChain `FastEmbedEmbeddings`** (`langchain-community` + `fastembed`) — runs the
  ONNX `all-MiniLM-L6-v2` model **without PyTorch**; `app/services/embeddings.py`
  wraps it (`embed_text`, `cosine_similarity`, `build_profile_text`). Model configurable
  via `EMBEDDING_MODEL`. `langchain-community` emits a "sunset" deprecation warning but
  works; can migrate to a standalone package later.
- Cosine similarity is computed in Python (not pgvector) for the Step-2 pre-filter.

## Language & Runtime
- **Python 3.11** (base image `python:3.11-slim`).
- Backend dependencies installed via pip from `requirements.txt` in the Docker builder
  stage; the runtime stage apt-installs Chromium + ChromeDriver for Selenium.

## Project Rules & Conventions (`.clinerules/rules.md`)
- Primary libraries/frameworks: LangChain, LangGraph, Selenium, Scrapy (fallback),
  React, Postgres Vector DB.
- Read the design doc to inform library choices and understand the user's intent.
- **Bracket placement:** opening curly brace on a NEW line, e.g.:
  ```python
  def example()
  {
      # code
  }
  ```
- Prefer code structure/style an average developer can read easily; avoid rarely-used,
  confusing syntax.
- Use the **bare minimum of imported libraries/frameworks** — primarily those in the
  rules files, plus non-mentioned libraries only if they meaningfully shorten/simplify code
  by removing hand-written logic.
- Use **non-deprecated** versions of libraries/frameworks.
- Prefer **open-source** libraries over proprietary; if proprietary is unavoidable, prefer
  free, then the lowest-cost option.
- **Always update the Memory Bank whenever the design changes.**

## Technology Decisions & Rationale (from `DESIGN.md`)
- **Pydantic + LLM** for structured extraction of the candidate profile (typed schema,
  predictable fields, `null` for missing values).
- **LangChain Embeddings + VectorStore** for the cheap first-stage semantic filter
  (cosine similarity) to reduce LLM token usage.
- **LLM recruiter agent** with a strict JSON output contract for the second-stage
  compatibility score (weighted rubric).
- **LaTeX (Jake's Resume template)** for resumes — chosen because it is single-column,
  parser-friendly, and deterministic for ATS.
- **PostgreSQL 16 + pgvector** (Docker container `job_curation_db`) for long-term storage
  of profiles/jobs/embeddings. Embeddings are `vector(384)`, sized for the open-source model
  `all-MiniLM-L6-v2`. Schema in `db/schema.sql`; see `db/README.md`.
  `user_documents` also stores `size_bytes` and the normalized `extracted_text` per file.
- **Backend (Docker), `backend` service** — connection defaults to `POSTGRES_HOST=db`,
  `POSTGRES_PORT=5432` (overridden in `docker-compose.yml`).

## Development Setup
- **Containerized** via `Dockerfile` (multi-stage build: builder + runtime).
  - Builder: Python 3.11 slim venv at `/opt/venv`, `pip install --no-cache-dir langchain
    langgraph`.
  - Runtime: slim image copies the venv, sets `WORKDIR /app`, copies the project.
  - Env: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`.
- **Commands (`commands.txt`):**
  - Run docker image: `docker exec -it <container name> bash`
  - Frontend (run on the host — the dev container has no Node): `cd frontend && npm install`,
    then `npm run dev` (http://localhost:5173) or `npm run build` (tsc type-check + Vite).
    Host Node is v18.19, so Vite is pinned to 5.x (Vite 7 needs Node >= 20.19).
  - Backend (Docker): `docker compose up -d --build` (starts `db` + `backend`).
    API at http://localhost:8000 (health: `GET /api/health`).
  - Frontend env flags (`.env`): `VITE_USE_MOCK_API` (mock data layer on/off),
    `VITE_API_BASE_URL` (defaults to `/api`, proxied to the backend by Vite).
- **Git:** repository `origin: https://github.com/JoelJ-500/job-curation.git`, branch `main`.
  `.gitignore` currently ignores `commands.txt` and `.env`.
- **Database (Docker Compose):** `docker-compose.yml` runs `pgvector/pgvector:pg16` as
  `job_curation_db` on port `5432`, with `db/schema.sql` auto-applied on first start and a
  named `pgdata` volume. Connection settings live in `.env` (see `.env.example`). Python DB
  deps are in `requirements-db.txt` (`psycopg[binary]`, `pgvector`). Verified with
  `db/smoke_test.sql`.

## Technical Constraints
- **Context length management** is required to prevent hallucination — keep each agent's
  context focused on its single responsibility.
- **Token cost control** — the embeddings pre-filter must run before the LLM step.
- **Anti-bot measures** — a configurable per-job parse delay (`Time Delay`) and targeting
  fresh postings (< 24h) / first ~10 applicants.
- **ATS constraints** — resume must be one page, single column, standard headers, 11pt,
  0.5in margins, Jake's template structure, `\href{}{\underline{}}` hyperlinks.
- **Scraping fallback hierarchy** — try direct HTML extraction first; use Scrapy only when
  HTML cannot be extracted cleanly.
- **North America focus** initially (Hiring Cafe, Eluta).

## External Dependencies / Services (implied, to confirm)
- An **LLM provider** (for extraction, scoring, and resume generation).
- An **embedding model** for the semantic filter.
- **Job board access** to Hiring Cafe and Eluta (may require Selenium/Scrapy + anti-bot
  handling). Eluta works via Selenium; HiringCafe's **Cloudflare** challenge currently
  blocks automated access.

## Open Technical Questions
- Concrete LangChain storage integration: **resolved** — Postgres + pgvector store
  (`langchain-postgres` `PGVectorStore` will wrap the `jobs`/`users` vector columns when the
  agents are built).
- Embedding model: **resolved** — open-source `all-MiniLM-L6-v2` (`vector(384)`).
- LLM provider/model: **resolved** — **Groq** (`openai/gpt-oss-120b` for text,
  `qwen/qwen3.8-27b` for vision), replacing the earlier Google Gemini choice.
- How will LaTeX be compiled to PDF (local `latexmk`/`pdflatex` vs. a service) and how will
  `.docx` export be produced (e.g., Pandoc)?
- Exact React project layout, build tooling (Vite/CRA/Next), and styling library — not yet
  specified in the design.
