# Tech Context: job-curation

> Tech stack, dependencies, development setup, and technical constraints.
> Source of truth: `DESIGN.md`, `.clinerules/rules.md`, `Dockerfile`, `commands.txt`.

## Primary Stack (from project rules)
- **LangChain** — LLM orchestration, embeddings, vector store integration.
- **LangGraph** — agentic workflow / multi-agent graph orchestration.
- **Selenium** — browser automation (job site interaction / scraping navigation).
- **Scrapy** — only use if you cannot extract HTML data from the parsed websites.
- **React** — front-end (OPTIONAL: any styling/theming library as deemed fit).
- **Postgres Vector Database** — long-term data storage (candidate profiles, job data,
  embeddings).

## Language & Runtime
- **Python 3.11** (base image `python:3.11-slim`).
- Backend dependencies installed via pip (currently `langchain` and `langgraph` in the
  Dockerfile).

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

## Development Setup
- **Containerized** via `Dockerfile` (multi-stage build: builder + runtime).
  - Builder: Python 3.11 slim venv at `/opt/venv`, `pip install --no-cache-dir langchain
    langgraph`.
  - Runtime: slim image copies the venv, sets `WORKDIR /app`, copies the project.
  - Env: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`.
- **Commands (`commands.txt`):**
  - Run docker image: `docker exec -it <container name> bash`
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
  handling).

## Open Technical Questions
- Concrete LangChain storage integration: **resolved** — Postgres + pgvector store
  (`langchain-postgres` `PGVectorStore` will wrap the `jobs`/`users` vector columns when the
  agents are built).
- Embedding model: **resolved** — open-source `all-MiniLM-L6-v2` (`vector(384)`).
- LLM provider/model still to confirm.
- How will LaTeX be compiled to PDF (local `latexmk`/`pdflatex` vs. a service) and how will
  `.docx` export be produced (e.g., Pandoc)?
- Exact React project layout, build tooling (Vite/CRA/Next), and styling library — not yet
  specified in the design.
