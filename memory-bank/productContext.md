# Product Context: job-curation

> Why this project exists, the user experience goals, and the UI/UX design features.
> Source of truth: `DESIGN.md` (master design document).

## Why It Exists
Two forces make modern job hunting inefficient and unfair:
1. **ATS filtering** — automated systems reject candidates on keyword/context matching
   before any human reviews them.
2. **Manual effort** — searching boards and re-writing a resume per posting is repetitive
   and slow.

This product exists so a candidate can (a) be matched only to genuinely compatible roles,
and (b) receive a resume tailored to each role — automatically — turning a slow manual
loop into a background pipeline that works while the user is away.

## User Experience Goals
- **Minimal setup, one time.** The user provides profile data once (manual form or by
  uploading any number of documents), then only revisits settings/profile when changing.
- **Zero-touch curation.** Once configured, the curator runs in the background for a
  user-set duration (or up to a user-set job limit) and returns a ranked shortlist.
- **Trust and control.** The user can view and edit every extracted field, reupload
  documents to refill the form, tune thresholds, and delete unwanted postings.
- **Apply in one place.** Each curated job pairs with its recommended resume and a direct
  link to the posting for immediate application.
- **Transparency of fit.** Fit is surfaced as a compatibility score with a criteria
  breakdown, so the user understands *why* a job was recommended.

## Core User Journey
1. **Setup** — User opens the app, fills the profile form, and/or uploads documents
   (resume, notes, code, portfolio screenshots).
2. **Extraction** — System converts uploads to plain text, strips meaningless content,
   and extracts structured fields via Pydantic + LLM into the candidate profile store.
3. **Review** — User reviews/edits extracted data in the profile form.
4. **Configure** — User sets thresholds and curator run parameters in Settings.
5. **Curate** — Background agents scrape job boards, filter by embeddings, then score with
   an LLM, and build a priority queue.
6. **Generate** — For each queued job, a tailored LaTeX resume is generated.
7. **Consume** — User views the dashboard: ranked jobs, resumes, apply links; deletes
   postings as desired.

## UI/UX Design Features (UI Layout)

### User Settings
A settings page where the user can adjust thresholds and behavior. Each setting should be
hoverable to show a short explanation of what it does:
- **Skill Match threshold** — how many skills must overlap between the user profile and a
  job posting. Higher = more accuracy but fewer compatible positions.
- **Semantic Text Match threshold** — 0 to 1 (default 0.5); controls the embedding-based
  pre-filter (see `systemPatterns.md` → Job Curation Step 2).
- **Compatibility score threshold** — LLM match score cutoff (default 70; editable).
- **Curator time period** — how long the curator runs for.
  OR **Curator job limit** — number of jobs to scout through in a set time interval
  (once or periodically).
- **Time Delay** — delay applied to every job parsed, to help bypass anti-bot measures.

### User Profile Form (implemented)
A page presenting all extracted profile data, editable by the user, with a document upload
area at the top. Adding documents uploads them and triggers the extraction agent; while it
runs the UI shows a status banner, then refills the form (the user reviews and saves).
Sections mirror the database (see `systemPatterns.md` → Persistent Data Model):
- **Documents** — drag & drop multi-file upload, file list with remove, "re-run extraction".
- **Basic information** — `full_name`, `contact_email`, `location`, `language_preference`,
  `requires_sponsorship`, `yoe`.
- **Social media**, **Work eligibility**, **Skills**, **Roles** — repeatable rows.
- **Experience** — repeatable cards, each with a nested list of highlight bullets.
- **Education & credentials**, **Additional context** — repeatable rows.
Actions: Save profile, Discard changes (reverts to the last saved/extracted state).

### Main Dashboard
- Displays all final curated job postings (priority-ordered by compatibility).
- Each posting shows its generated recommended resume (LaTeX).
- Each posting links directly to the source job posting for quick application.
- Users can delete job postings from the dashboard.

## UX Design Principles
- **Standard, recognizable sections** in generated resumes (Education, Experience,
  Projects, Skills, Summary, Certifications) — never creative section names.
- **Explanatory affordances** — hover text on settings to reduce configuration mistakes.
- **Editable extraction** — never trap the user with wrong AI-extracted data; the form is
  always the final word.

## Future UX Enhancements
- **Telemetrics dashboard** — track how many jobs were searched, how many passed the skill
  filter, the ATS filter, etc., viewable in the Main Dashboard.
- **Built-in application tracker** — let the user track application status in-app.
