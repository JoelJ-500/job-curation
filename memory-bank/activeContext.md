# Active Context: job-curation

> Current work focus and immediate next steps. Update this file frequently.
> Source of truth: `DESIGN.md`.

## Current State
- Repository initialized with: `DESIGN.md` (master design doc), `.clinerules/rules.md`,
  `Dockerfile` (Python 3.11 multi-stage), `README.md`, `commands.txt`, `.gitignore`.
- Git: branch `main`, single "Initial commit" (`f5e2f69`); new files currently untracked.
- **Memory Bank initialized** from `DESIGN.md` (this task). No application source code
  exists yet — the project is at **M0 (scaffolding)**.
- No dependency manifest (`requirements.txt`/`pyproject.toml`), no Postgres setup, no React
  app yet.

## Current Focus
Bootstrap the Memory Bank and align on the first build steps. The design is fully
specified for the core pipeline; the immediate need is to turn it into a runnable skeleton.

## Immediate Next Steps (recommended order)
1. **Confirm open technical decisions with the user** (blocking for design-consistent code):
   - LLM provider + model, and embedding model.
   - LangChain storage integration for the candidate profile store.
   - LaTeX→PDF toolchain (local `latexmk`/`pdflatex`) and `.docx` export (e.g., Pandoc).
   - React build tooling (Vite recommended) and styling library.
   - Clarify "Skill Match threshold" vs. "Semantic Text Match" threshold.
2. **Scaffold the backend** — package layout (e.g., `app/agents`, `app/models`,
   `app/services`, `app/api`), add `requirements.txt`/`pyproject.toml` with pinned,
   non-deprecated versions (langchain, langgraph, pydantic, psycopg + pgvector, selenium,
   scrapy, fastapi or similar), and wire Postgres vector store config.
3. **Implement Agent 1** — Pydantic models (`CandidateProfile`, `WorkExp`) matching the
   schema in `systemPatterns.md`, ingest/normalize uploads, extraction chain with the
   design's prompt, and profile persistence.
4. **Implement Agent 2 Step 1** — scrapers for Hiring Cafe and Eluta (HTML-first, Scrapy
   fallback), queue sorted by posting age with the "job" data format.
5. **Implement Agent 2 Steps 2–4** — embedding + cosine filter, LLM scoring chain with the
   strict JSON contract, and priority queue builder.
6. **Implement Agent 3** — resume-generation chain (Jake's template), LaTeX output, PDF +
   optional `.docx`.
7. **Build the React front-end** — Settings, Profile form (edit + reupload), Main Dashboard.
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
- 2026-01-10: Created `memory-bank/` and populated `projectbrief.md`, `productContext.md`,
  `systemPatterns.md`, `techContext.md`, `progress.md`, `activeContext.md`; added Memory
  Bank instructions to `.clinerules/`.
