# Project Brief: job-curation

> Foundational document. Defines what the project is, its goals, scope, and success criteria.
> Source of truth: `DESIGN.md` (master design document, exported from Google Docs).

## One-Line Summary
Simplify the job search by automatically surfacing the best-suited jobs for a user's
background, and generating a tailored, ATS-optimized resume for each one.

## Problem Statement
Autonomous AI hiring systems (Applicant Tracking Systems, ATS) filter out qualified
candidates before a human ever reads a resume. Candidates also waste time manually
searching job boards and rewriting resumes for each posting. This project automates the
full pipeline: discover relevant postings fast, rank them by real fit, and produce a
per-job tailored resume engineered to pass ATS keyword/context scoring.

## Goals
1. Acquire and structure a comprehensive, unified candidate profile from raw user input
   (manual form + multi-format document uploads: resumes, notes, code files, images).
2. Continuously curate relevant job postings from job boards based on the user's roles,
   location, posting age, and years of experience (YOE).
3. Filter postings in two stages (cheap embeddings first, then LLM) to rank true fit
   while minimizing token cost.
4. Generate a one-page, ATS-optimized LaTeX resume tailored to each curated posting.
5. Present a dashboard of curated jobs + recommended resumes + direct apply links.
6. Maximize the chance of bypassing ATS filters and reaching a human reviewer.

## Core Scope (In)
- User data acquisition + Pydantic extraction into a candidate profile.
- Web scraping of job postings from **Hiring Cafe** and **Eluta** (North America focus).
- Two-stage filtering: semantic embedding match (LangChain Embeddings + VectorStore),
  then LLM compatibility scoring (weighted rubric).
- Priority queue of curated postings.
- LaTeX resume generation using Jake's Resume template (ATS-optimized).
- Front-end: User Settings, User Profile form, Main Dashboard.
- Backend: LangChain + LangGraph agentic workflow; Postgres Vector DB for long-term storage.

## Out of Scope (For Now / Future Improvements)
- Telemetrics dashboard (jobs searched, jobs passing skill filter, ATS filter stats).
- Built-in application tracker.
- Autonomous agent that dynamically learns and navigates any user-supplied job site
  (noted as very token-heavy).
- Pulling jobs directly from GitHub job repos (user-pasted).
- Structured/resume-text extraction via regex to reduce token cost.

## Success Criteria
- User completes a profile once (manual or document upload) and can edit it at any time.
- Curator produces a ranked queue of postings meeting the user's thresholds.
- Every curated posting receives a valid, one-page, compilable LaTeX resume.
- Resume passes the ATS "final check" checklist (see `systemPatterns.md` → Resume Builder).
- Dashboard lets users view curated jobs, open resumes, apply via link, and delete postings.

## Design Constraints (ATS Bypass Tips)
Incorporated into algorithms to increase the chance of passing autonomous hiring systems:
- Apply to jobs less than 24 hours old.
- Aim to be among the first 10 applicants (first 5-10 resumes are often shortlisted after
  a keyword-match test).
- Remove irrelevant keywords that do not match the job posting (to raise match score).
- Every experience/project point should follow STAR (Situation, Task, Action, Result).
- Resumes must use action words.

## Naming / Doc Note
- The master design document currently lives at `DESIGN.md` in the project root.
- `.clinerules/rules.md` and this Memory Bank (`projectbrief.md`) refer to it as
  `SYSTEM_DESIGN.md`. If a `SYSTEM_DESIGN.md` is added later, keep both in sync (single
  source of truth preferred). Flag to the user if the two diverges.
