# System Patterns: job-curation

> System architecture, component relationships, design patterns, and algorithms.
> Source of truth: `DESIGN.md` (master design document).

## High-Level Architecture
The system is an **agentic pipeline** built with LangChain + LangGraph, backed by a
Postgres Vector Database for long-term storage, with a React front-end dashboard.

The job application process is divided into 4 sub-processes, each implemented as an agent:

1. **Agent: Acquiring User Data** — invoked during setup or when the user changes info.
2. **Curate relevant job postings** — runs for a user-set time period (continuously in
   the background).
3. **Generate a high-match resume** for every curated job posting.
4. **Send highly compatible jobs (with resumes) to the front-end Main Dashboard.**

```
[User Profile Form / Uploads]
        │
        ▼
[Agent 1: Acquire User Data] ──> [Candidate Profile (Pydantic) ──> Vector DB]
        │
        ▼
[Agent 2: Job Curation]
   Step 1: Scrape (Hiring Cafe, Eluta) ──> queue (sorted by age)
   Step 2: Embeddings + VectorStore filter (cosine sim >= threshold)
   Step 3: LLM compatibility scoring (weighted rubric)
   Step 4: Priority queue (match score >= compatibility threshold)
        │
        ▼
[Agent 3: Resume Builder] ──> LaTeX resumes (Jake's template, ATS-optimized)
        │
        ▼
[Main Dashboard: ranked jobs + resumes + apply links]
```

## Design Pattern: Emulating OOP in a Multi-Agent System
- Treat each step as an agent.
- Each agent follows the OOP principle of an object: it has an **overall purpose** and
  encapsulates the logic/state for that purpose.
- **Manage context length deliberately** to prevent hallucination (keep each agent's
  prompt/context focused on its single responsibility).

## Core Data Model
### Candidate Profile (via Pydantic + LLM extraction)
Fields extracted from all uploaded sources (fill `null` if not found):
- `full_name`: candidate's full name
- `contact_email`: email address
- `social_media`: any social media links (e.g., LinkedIn, GitHub)
- `location`: physical location or region
- `work_eligib`: citizenships, work permits, residencies the user holds
- `skills`: professional skills, domain expertise, tools, methodologies, languages,
  frameworks — across any field (creative, administrative, medical, legal, retail,
  blue-collar, business, technical, etc.)
- `roles`: list of all roles the candidate would be suitable for
- `experience`: `List[WorkExp]` — employment history, roles, or major projects
- `yoe`: total years of professional experience
- `education_and_credentials`: education, degrees, credentials
- `additional_context`: unique domain expertise, portfolio highlights, awards,
  publications, notable achievements (mine for project material)

**WorkExp**:
- `company_or_org`: company/organization/client/institution name
- `role`: job title, position, or professional role
- `highlights`: key responsibilities, achievements, projects, duties

**Rule:** fields containing multiple items must be a **list of strings**.

### "job" Data Format
Every scraped/curated job is stored as:
- `title`
- `link`
- `date of posting`
- `job posting` (a massive string)
- `ATS score` (`null` until Resume Builder / Step 3)

**Persisted form:** these fields live in the `jobs` table (raw scraped postings,
deduplicated) plus the `curated_jobs` table (the per-user dashboard queue with scores).
`ATS score` lives on the generated `resumes` row, not on the raw job. See **Persistent
Data Model** below and `db/schema.sql`.

---

## Persistent Data Model (Postgres + pgvector)
Normalized from the design's first draft; the source of truth (DDL) is `db/schema.sql`,
applied automatically on first DB start. Key fixes: FKs moved onto child tables, PKs added,
multi-valued fields split into their own tables, `skills`/`roles` made canonical
dictionaries with join tables, education dates made atomic, the raw-vs-curated job split,
and tables added for resumes, settings, and embeddings.

Tables:
- **users** — profile root: `full_name`, `contact_email`, `location`,
  `language_preference`, `requires_sponsorship`, `yoe`, `profile_embedding vector(384)`.
- **user_settings** — `skill_match_threshold`, `semantic_text_match_threshold` (0–1,
  default 0.5), `compatibility_score_threshold` (default 70),
  `curator_time_period_minutes` XOR `curator_job_limit`, `time_delay_seconds`.
- **social_media**, **work_eligibility**, **experiences** (+ **experience_highlights**),
  **educations**, **additional_context_entries**, **user_documents** — one-to-many children
  of `users`.
- **skills** (`name`, `type`) + **user_skills**; **roles** (`name`) + **user_roles** —
  canonical dictionaries with many-to-many joins.
- **jobs** — every scraped posting (unique on `source`+`link`): `title`, `company`,
  `location`, `date_posted`, `description`, `status`, `description_embedding vector(384)`.
- **curated_jobs** — per-user dashboard queue: FKs to `users` + `jobs`, `semantic_score`,
  `overall_match_score`, the four criterion scores, and a `status` for soft delete.
- **resumes** — generated `latex_content` (+ `pdf_path`/`docx_path`), `ats_score`, `version`.
- **scrape_runs** — curator telemetry; **schema_migrations** — applied versions.

Embeddings: `vector(384)`, sized for the open-source model `all-MiniLM-L6-v2`. Cosine
similarity uses the pgvector `<=>` operator, with an HNSW index (`vector_cosine_ops`) on
`jobs.description_embedding`.

---

## Agent 1 — Acquiring User Data (implemented)
Code lives in `app/` (FastAPI + psycopg + LangChain). Pipeline: the user uploads
documents via the UI -> each file is converted to clean plain text -> a single
`CandidateProfile` is extracted with a Groq LLM using Pydantic structured output
-> the profile is written transactionally to Postgres.

- **Ingestion** (`app/agents/document_ingest.py`): PDF via pypdf; scanned/image-only
  PDFs are rendered to PNG with PyMuPDF and read by the Groq vision model; DOCX via
  python-docx; images via Groq vision; text/code read directly (code keeps indentation).
- **Normalisation** (`app/agents/text_cleaning.py`): deterministic removal of
  non-semantic content (page numbers, rules, boilerplate) and whitespace collapse.
- **Extraction** (`app/agents/profile_extractor.py`): `ChatGroq`
  (`openai/gpt-oss-120b`) + `.with_structured_output(CandidateProfile,
  method="json_schema")` using the design's synthesis prompt; per-field instructions
  live in the Pydantic schema (`app/models/profile.py`). Missing fields remain `null`.
- **Persistence** (`app/agents/user_data_agent.py` + `app/db/repository.py`):
  writes `users`, `social_media`, `work_eligibility`, `skills`+`user_skills`,
  `roles`+`user_roles`, `experiences`+`experience_highlights`, `educations`,
  `additional_context_entries`. Each extraction run replaces the document-derived
  profile (`clear_profile`) so re-runs never duplicate rows.
- **Save edits**: `PUT /api/profile` is a diff-aware upsert (only changed columns
  / rows are touched; canonical skills/roles are reused via `ON CONFLICT`).
- **Status**: in-memory holder (`app/services/extraction_state.py`) polled by the UI.
- **Embedding** (`users.profile_embedding`): deferred behind
  `ENABLE_PROFILE_EMBEDDING` (Agent 2 concern).

API (matches the frontend contract exactly): `GET/PUT /api/profile`,
`POST/GET /api/profile/documents`, `DELETE /api/profile/documents/{id}`,
`POST /api/profile/extract`, `GET /api/profile/status`.

---

## Agent 2 — Job Curation (Step 1 implemented)

Step 1 (gather postings) is built; Steps 2–4 (embeddings → LLM scoring → priority
queue) are still to come.

- **Settings** (`app/api/settings.py`, `user_settings` table): the user sets **how many
  postings to gather per run** (`curator_job_limit`, default 10). The run stops once the
  queue reaches this number.
- **Orchestration** (`app/agents/curation_agent.py`): `run_curation` runs the two site
  workers **concurrently** (threads) against a shared, thread-safe, deduplicated queue
  capped at the limit — so the scrape order is never static and an exhausted site yields
  to the other. Scraped jobs are written to a text file and to the `jobs` table (a
  `scrape_runs` row is logged per source).
- **Scrapers** (`app/scrapers/`): `ElutaScraper` (working) and `HiringCafeScraper`
  (Cloudflare-blocked); each owns a unique Selenium setup and paginates.
- **Scraping agents** (`app/agents/scrape_agent.py`): `plan_searches` maps the profile
  (roles, location, yoe, language) onto each site's controls via Groq structured output
  (with a deterministic fallback); `parse_jobs_from_html` is an LLM fallback for changed
  HTML layouts.
- **Job format** written for each posting: **title, link, date of posting, job posting
  (massive string)**, plus source/company/location.
- **Endpoints**: `GET/PUT /api/settings`, `POST /api/curation/start`,
  `GET /api/curation/status`.
- **Step 2 (dedup + cosine pre-filter)** — implemented in `app/agents/curation_agent.py`
  with `app/services/embeddings.py`:
  - The candidate profile (**skills + education + yoe**) is embedded **once** per run,
    before any scraping (`repository.get_semantic_profile`).
  - Each posting, in the same iteration it is read, is: (1) checked against `jobs` +
    `curated_jobs` by link (`repository.job_exists`) and **skipped if already stored**;
    then (2) embedded (title + full posting text) and compared to the profile vector by
    **cosine similarity**; anything **below `semantic_text_match_threshold`** (default 0.5)
    is **discarded**; survivors are queued and persisted to `jobs`.
  - Embeddings use LangChain **`FastEmbedEmbeddings`** (ONNX via `fastembed`, **no
    PyTorch**), model `all-MiniLM-L6-v2` (384-dim). Cosine is computed in Python.
  - Settings UI exposes the **"Semantic Text Match" threshold** (0–1, default 0.5).
- **NOTE:** `curator_job_limit` currently counts postings surviving Step 2 (dedup +
  cosine). Once Step 3 (LLM ATS scoring) lands, switch it to count postings surviving
  that final filter.

---

## Frontend Architecture (User Profile UI)
React + TypeScript + Vite + React Router + MUI, in `frontend/`.

- **App shell** (`components/layout/AppShell.tsx`) renders the top nav; routes live in
  `App.tsx`: `/profile`, `/settings`, `/dashboard` (Settings + Dashboard are placeholders so
  the shell is future-proof).
- **Data layer** (`api/`): a typed `ProfileApi` interface with two adapters — a real HTTP
  adapter (`api/client.ts` + `api/profile.ts`) and a mock adapter
  (`api/mock/mockAdapter.ts`, simulated extraction, localStorage backed). Chosen by
  `VITE_USE_MOCK_API`. Types in `types/profile.ts` use `snake_case` to match the backend.
- **Reusable pieces**: `SectionCard`, `RepeatableSection` (generic add/remove rows),
  `FormFields` (`FormTextField`/`FormCheckbox` wrapping MUI + react-hook-form `Controller`),
  `StatusBanner`.
- **Save helper**: `utils/profile.ts` → `normalizeProfileForSave` converts empty strings to
  `null`, normalizes the education enum, drops empty highlights, and pins experience order.

**Backend contract (to implement with the agents):**
```
GET    /api/profile                 -> UserProfile
PUT    /api/profile                 <- UserProfile
POST   /api/profile/documents       <- multipart files[]  -> UserDocument[]
GET    /api/profile/documents       -> UserDocument[]
DELETE /api/profile/documents/{id}
POST   /api/profile/extract         -> trigger Agent 1
GET    /api/profile/status          -> { state: idle|extracting|done|error }
# future: /api/settings, /api/jobs, /api/resumes
```

---

## Algorithm Details

### Agent 1 — Acquiring User Data
**Step 1: Prompt user for commonly asked job application info.**
Commonly asked fields: name, address, language preference, GitHub, LinkedIn, country of
origin, eligibility to work in locality, sponsorship Y/N, desired position, previous
experience, projects, etc. User may automatically upload any number of documents
(resume, text file with all info) or fill it out manually. This is a one-time step until
the user changes information.

**Step 2: Process relevant data from user-provided data.**
1. Convert all data to a lightweight form (plain text) and remove text with no semantic
   meaning.
2. Use **Pydantic + an LLM** to extract all relevant info into the storage/database that
   LangChain provides.

**Extraction prompt (verbatim intent):**
> "Analyze all the provided multi-format source materials, which may include resumes,
> text notes, code files, and visual documents or portfolio screenshots. Cross-reference
> and synthesize all information across these disparate sources to build a comprehensive,
> unified candidate profile. Ensure that skills, technical proficiencies, or project
> details discovered in code files or images are intelligently merged with the textual
> history."

**Output:** there must be a form containing all the data fields above, pre-filled with the
extracted data, that the user may edit/fix.

*Future improvement:* provide data in structured form (like a resume) with strict rules to
enable regex extraction and reduce token cost.

### Agent 2 — Job Curation
Runs continuously in the background. Before work, **check that the vector database has the
required attributes.**

**Step 1: Gather job postings from across the web.**
- Scrape **Hiring Cafe** and **Eluta** (North American focus; more sites later, or an
  autonomous agent).
- Search for every element in the profile's `roles` attribute on those sites.
- Filter by **job posting age, location, and yoe**.
- Create a queue of job postings (in the "job" format above), **sorted by age**, to pass to
  the next step. Each job must be added following the format.

*Future improvement:* an autonomous agent that figures out and navigates the layout of any
user-added job site (very token heavy); allow the user to paste in GitHub job repos.

**Step 2: Filter down with LangChain Embeddings + VectorStore.**
- User sets a **"Semantic Text Match" threshold between 0 and 1 (default 0.5)**.
- For every job in the queue, run the `skills`, `education`, and `yoe` elements of the
  user profile and the job posting through an embedding model to get a vector for each.
- Compute **cosine similarity** (angle between the vectors).
- If score `>=` threshold, keep the job in the queue; else remove it.
- Purpose: trim postings that need LLM evaluation, saving token cost.

**Step 3: Filter down again, with an LLM (compatibility scoring).**
Use an agent to assess a compatibility score for every job that passed Step 2, using the
recruiter rubric below.

**Recruiter scoring rubric (weights):**
1. **Hard Skill Alignment — Weight 50%.** Cross-reference the profile's `skills` array and
   `experience` against job requirements. Recognize semantic synonyms.
2. **Context, Depth & YOE — Weight 25%.** Check `yoe` against requirement; review
   `experience` for depth, metrics, scale, responsibilities. Disregard skills lacking
   proof of execution.
3. **Education and Certification Fit — Weight 15%.** Verify the posting matches the
   candidate's `education_and_credentials`.
4. **Work Eligibility — Weight 10%.** Match `work_eligib` against any visa/location/
   citizenship requirements.

**LLM output (strict JSON only, no markdown/filler):**
```json
{
  "overall_match_score": "<Integer between 0 and 100>",
  "criteria_breakdown": {
    "hard_skills_score": "<Integer between 0 and 100>",
    "experience_depth_score": "<Integer between 0 and 100>",
    "role_seniority_score": "<Integer between 0 and 100>",
    "eligibility_score": "<Integer between 0 and 100>"
  }
}
```

**Step 4: Build the priority queue of curated postings.**
- If `overall_match_score >= Compatibility Score` (**default 70, editable in Settings**),
  add the job to the final curated priority queue.
- Sort the queue **highest to lowest compatibility**.

### Agent 3 — Resume Builder
For every job in the final curated queue, generate a **one-page LaTeX resume using Jake's
Resume template**, using the prompt adapted from a job-search forum post. Inputs come from
the user profile (the ONLY source of truth — never fabricate).

**Task:** read the job posting, identify its **top 3–4 core requirements**, then produce the
resume following the rules below. ATS scoring understanding that drives the rules:
- ATS does **not** reward raw keyword volume — it scores keywords **in context**. A keyword
  in a skills list with no backing experience can be flagged as a **mismatch**.
- Content appearing **earlier** in a section and on the page is weighted **more heavily**.
- Recruiters surface candidates above a **~60–70% match threshold**, then review manually.
  Goal: clear the threshold naturally, then win the human with clear achievements,
  quantified results, and relevance.

**Rules:**
1. **Structure — only standard section headers** (Education, Experience, Projects, Skills,
   Summary, Certifications — never creative names).
   - Header: `full_name`, `contact_email` (hyperlinked), each `social_media` link
     (hyperlinked), `location`. Phone only if present in `additional_context`.
   - Education (from `education_and_credentials`): degree, institution, location, dates
     (expected graduation if applicable). "Relevant Coursework" line only if the posting
     mentions a specific technical area covered by coursework.
   - Experience (from `experience`).
   - Projects (only if project work demonstrates posting requirements not already covered
     by Experience bullets).
   - Technical Skills (grouped categories).
   - (Optional) Certifications — only those in `education_and_credentials`; do not fabricate.
   - **Section-order rule:** if `yoe < 3`: Header → Education → Technical Skills →
     Experience → Projects → Certifications. If `yoe >= 3`: Header → Experience → Projects
     → Education → Technical Skills → Certifications.
2. **Experience selection & prioritization:** map top 3–4 requirements to strongest
   concrete evidence; skip unevidenced requirements (no padding). Order matters — most
   relevant role FIRST, most relevant bullet FIRST under each role. Drop irrelevant roles/
   projects. Fill the page without fluff.
3. **Bullet point writing:** begin with a strong action verb (Engineered, Developed,
   Implemented, Diagnosed, Designed, Automated, Optimized, Documented); be
   achievement-oriented, not responsibility-oriented; mirror exact keywords **inside the
   context of real work**; be specific/concrete (technologies, quantities, outcomes);
   never fabricate.
4. **Skills section:** include only skills that are in BOTH the posting and the candidate's
   `skills`. **Corroboration rule:** every listed skill must be backed by a bullet,
   coursework item, or credential; omit unbacked keywords. Group into 4–6 logical
   categories matching the posting's language. Mirror exact tool names from the posting.
   Do not list every profile skill — trim ruthlessly.
5. **Keyword strategy:** pull keywords in BOTH posting and profile; inject by impact:
   (1) experience/project bullets with concrete examples, (2) Skills (only with bullet
   evidence), (3) Summary if included. Never stuff keywords.

6. **Summary/Objective (optional — only if the posting asks):** 2–3 sentences, standard
   "Summary" header; open with "[field] professional with [yoe] years of hands-on
   experience in [2–3 skills]..."; close with intent tailored to the company/role. Omit
   generic objectives.
7. **Formatting (critical for ATS):** one page only (shorten bullets, reduce to 3 projects,
   or drop coursework line if overflowing); use Jake's template structure exactly (do not
   change `\resumeSubheading`, `\resumeProjectHeading`, `\resumeItemListStart`); no tables,
   columns, graphics, icons, or text boxes (parsers read left-to-right — two columns become
   word soup); standard section headers only; font 11pt; margins 0.5in sides / 0.5in top
   (Jake's template); all hyperlinks use `\href{}{\underline{}}`; dates on the right in
   `\textit{\small}`.
8. **Submission guidance:** compile to PDF by default; submit `.docx` too for Fortune 500 /
   government roles (older ATS like Taleo parse `.docx` more reliably). Run the final
   resume through a free ATS parser/scoring tool to confirm parsing and clear the ~60–70%
   recruiter threshold.
9. **Final check before output:**
   - Resume is exactly one page.
   - Posting's top 3–4 requirements each addressed with the posting's exact terminology,
     placed prominently.
   - Every Skills keyword is backed by at least one experience/project bullet (no orphans).
   - Most relevant role FIRST; most relevant bullet FIRST under each role.
   - Every bullet uses an action verb.
   - Exact job title (or close variant) appears in Skills, coursework line, or Summary.
   - Only standard section headers used.
   - No information fabricated beyond the candidate profile.
   - LaTeX compiles cleanly with Jake's template (no unclosed braces, no undefined commands).

---

## Component Relationships (logical)
- **User Profile Form (front-end)** ⇄ **Agent 1 (Acquire User Data)** ⇄ **Vector DB /
  Candidate Profile store**.
- **Settings (front-end)** provides thresholds/time delay/run parameters → consumed by
  **Agent 2 (Job Curation)**.
- **Agent 2** reads the candidate profile + scraped postings; writes the curated priority
  queue.
- **Agent 3 (Resume Builder)** reads each queued job + candidate profile; writes LaTeX
  resumes (+ eventually `ATS score` back onto the job).
- **Main Dashboard (front-end)** reads the priority queue + resumes for display; supports
  deletion and apply links.

## Cross-Cutting Concerns
- **Token cost** — the 2-stage filter (embeddings → LLM) and context-length discipline are
  the primary cost controls.
- **Anti-bot / anti-detection** — configurable per-job time delay; recommendation to target
  postings < 24h old and be among the first ~10 applicants.
- **No fabrication** — the candidate profile is the single source of truth for resumes.

## Known Open Questions / To Confirm
- Exact storage mechanism "that LangChain provides" for the extracted profile (see
  `techContext.md`).
- Whether `ATS score` in the job format is written back by the Resume Builder step.
- Whether Settings' "Skill Match threshold" (skill overlap count) is distinct from the
  "Semantic Text Match" embedding threshold — the design lists both; clarify mapping.

