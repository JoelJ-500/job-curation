**Constraints to consider in agentic system:**

Before building and finalizing on an algorithm, I curated a list of tips from across the web that we can incorporate into the algorithm to increase the chances of bypassing the autonomous AI hiring systems companies use. 

- Applying to jobs less than 24 hours old  
- Aiming to be the in the First 10 applicants (Recruiters often mention that the first 5-10 resumes are often shortlisted after a keyword match test)  
- Remove irrelevant keywords that don’t match keywords from job postings to increase job match score  
- Every experience/project point should follow STAR (Situation, Task, Action, Result)  
- Resume must use action words.

**Building the Optimal Job Search Algorithm:**

The job application process can be divided into the following 4 subprocesses(as agents?): 

**\-\> Agent: Acquiring User data**\- Invoked during setup or when user wants to change information,

Run for the time period set by user in user settings:    
**\-\> Curate relevant job postings**    
**\-\> Generate a high match resume for every curated job posting**

**\-\> Send highly compatible jobs with respective resumes to the front end.**   \- Dashboard to view curated job postings with a high match resume. 

1. **Acquiring User Data, and building User Profile:**

This is where we acquire the data to build the user's job application profile that we need for the following sub processes. 

**Step 1: Prompt user for commonly asked job application info**  
This includes commonly asked information like name, address, Language preference, GitHub, LinkedIn, Country of Origin, Eligibility to work in locality, Sponsorship Y/N, desired position, previous experience, projects etc.   
The user may automatically upload any number of documents like a resume or text file containing all the information or fill it out manually.  

This is a one time step, until the user wants to change any information. 

**Step 2: Processing relevant data from user provided data**  
First, convert all data to a lightweight form like plain text format, remove text that has no semantic meaning. 

Use Pydantic with an LLM to extract all relevant info from uploaded documents to whatever storage/database Langchain provides. 

Prompt: “Analyze all the provided multi-format source materials, which may include resumes, text notes, code files, and visual documents or portfolio screenshots. Cross-reference and synthesize all information across these disparate sources to build a comprehensive, unified candidate profile. Ensure that skills, technical proficiencies, or project details discovered in code files or images are intelligently merged with the textual history”

Data fields to extract with Pydantic (If not found, fill in field with ‘null’):  
\- full\_name: “Candidates full name “  
\- contact\_email: “Email address”  
\- social\_media: “Any social media links the user has, eg:Linkedin”   
\- location: “Physical location or region”  
\- work\_eligib: “List of citizenships, work permits, residency the user has”  
\- skills: “Professional skills, domain expertise, tools, methodologies, programming languages, frameworks, languages, or specialized proficiencies across any field (e.g.," " creative, administrative, medical, legal, retail, blue-collar, business, technical, etc.).”  
\- roles: “List of all roles that this candidate would be suitable for based on the provided materials. ”  
\- experience List\[WorkExp\]: “Employment history, professional roles, or major projects”  
\- yoe: “Total years of professional experience"  
\- education\_and\_credentials: “Employment history, professional roles, or major projects.”   
\- additional\_context: “Unique domain expertise, portfolio highlights, awards, publications, or notable achievements evident in any file type.”

WorkExp:  
company\_or\_org: "Company, organization, client, or institution name."  
role: “Job title, position, or professional role”  
highlights: “Key responsibilities, achievements, projects, or duties performed" " across any industry."

Ensure that data fields containing multiple items, are a list of strings

There must be a form containing all the data fields above, with the extracted data that the user may edit/fix. 

Improv Notes for future:  
\- Have an option to provide data in structured data(like a resume) with strict rules,  to be able to use regex for data extraction and reduce token cost? 

2. **Job Curation:**

After gathering and refining user data into a user profile, we can now curate compatible jobs based on the constraints mentioned above, and the users profile. This subprocess will also be running continuously in the background unlike the previous sub-process.

Data format for every “job”: title, link, date of posting, job posting (massive string), ATS score (null until Step 3\) 

(First check if the vector database has required attributes)

**Step 1: Gather job postings from across the web:**  
Develop web scraping functionality to scrape from the following sites:

- Hiring cafe  
- Eluta

(North American focused, can add more sites later on, or autonomous agent)

The search functionality must:  
\- Search for every element in the “role” attr, on the sites above  
\- With a filter for job posting age, location and yoe   
\- Should create a queue of job postings(following the “job” data format highlighted above), sorted by age, to pass to the next step.   
\- Each job must be added to the queue, following the format above. 

Improv Notes for future:  
\- Autonomous Agent: Create a separate agent that scan scour any job posting site a user adds dynamically ie figure out and navigate the layout of any job site, Challenge- very token heavy.   
\- Allow the user to paste in github job repos to pull from. 

**Step 2: Filter down job postings with LangChain Embeddings \+ VectorStore:**   
Allow the user to set a “Semantic Text Match” threshold between 0 and 1, in the settings(by default 0.5). 

For every job in the queue, run the elements in the “skills, education, yoe” attributes of the user profile and the job posting itself through an embedding model to get a vector value for each. Then run the result through a cosine similarity formula, calculating the angle between the vectors . 

If the score \>= “Semantic Text Match” threshold, keep the current job  in the queue. Else remove it. 

This step will trim down the amount of job postings that need to be evaluated by the agent in the next step, saving token costs. 

**Step 3: Filter down again, this time with LLM:**   
Use an agent to assess compatibility score of every job posting that passed Step 2, using the following prompt:

You're a recruiter who has to assess how compatible the candidate’s profile is to the job posting  . Your job is to perform a deep semantic and contextual evaluation of a candidate's structured profile against a specific Job Description.

Analyze the structured candidate profile and the target job description provided below, then return your analysis strictly as a JSON object following the formatting instructions.

1\. Hard Skill Alignment (Weight: 50%): Cross-reference the profile's \`skills\` array and \`experience\` details against the job requirements. Recognize semantic synonyms.  
2\. Context, Depth & YOE (Weight: 25%): Check if the profile's \`yoe\` (Years of Experience) meets the requirement. Review the \`experience\` array for depth, metrics, scale, and responsibilities. Disregard any skills that lack proof of execution in the work or project history.  
3\. Education and Certification Fit (Weight: 15%): Verify if the job posting matches the candidate's target \`education\_and\_credentials\`.  
4\. Work Eligibility (Weight: 10%): Match the candidate's \`work\_eligib\` against any explicit visa, location, or citizenship requirements stated in the job description.

\#\#\# Input Data:

\[TARGET JOB DESCRIPTION\]  //Replace with appropriate langchain variable  
{{insert\_job\_description\_here}}  
\[/TARGET JOB DESCRIPTION\]

\[STRUCTURED CANDIDATE PROFILE\] //Find a way to ge these properly from pydantric variables from Step 1  
\- full\_name: {{candidate.full\_name}}  
\- contact\_email: {{candidate.contact\_email}}  
\- location: {{candidate.location}}  
\- work\_eligib: {{candidate.work\_eligib}}  
\- skills: {{candidate.skills}}  
\- yoe: {{candidate.yoe}}  
\- experience: {{candidate.experience}}  
\- education\_and\_credentials: {{candidate.education\_and\_credentials}}  
\- additional\_context: {{candidate.additional\_context}}  
\[/STRUCTURED CANDIDATE PROFILE\]

\#\#\# Output Format Instructions:  
You must respond ONLY with a valid JSON object. Do not include any introductory text, markdown formatting (like \`\`\`json), or conversational filler.

The JSON structure must match this template exactly:  
{  
  "overall\_match\_score": \<Integer between 0 and 100\>,  
  "criteria\_breakdown": {  
    "hard\_skills\_score": \<Integer between 0 and 100\>,  
    "experience\_depth\_score": \<Integer between 0 and 100\>,  
    "role\_seniority\_score": \<Integer between 0 and 100\>,  
    "eligibility\_score": \<Integer between 0 and 100\>  
  }

**Step 4: Building a priority queue of curated job postings**  
If the overall match score is \>= Compatibility Score (Default of 70, make this editable by the user in user settings), add this to the final curated job posting priority queue. The queue should be sorted from highest to lowest compatibility. Then add this queue to the CuratedJobs database. 

3. **Resume Builder**

For every job posting in the final curated job posting queue, generate a resume in latex code with the following prompt ([adjusted from this post](https://www.reddit.com/r/jobsearchhacks/comments/1rchioh/i_spent_3_months_figuring_out_how_ats_systems/)) 

\---PROMPT START---

You are an expert resume writer and ATS (Applicant Tracking System) optimization specialist. Your task is to produce a polished, one-page, submission-ready resume in LaTeX using \*\*Jake's Resume template\*\*, tailored to the job posting provided below.

\---

\#\# INPUT // get this from the user profile

\#\#\# CANDIDATE PROFILE (the ONLY source of truth — never fabricate anything not found here):  
\- \*\*full\_name\*\*: {full\_name}  
\- \*\*contact\_email\*\*: {contact\_email}  
\- \*\*social\_media\*\*: {social\_media} — e.g., LinkedIn, GitHub; hyperlink each one provided  
\- \*\*location\*\*: {location}  
\- \*\*skills\*\*: {skills}  
\- \*\*experience\*\*: {experience}  
\- \*\*yoe\*\*: {yoe}  
\- \*\*education\_and\_credentials\*\*: {education\_and\_credentials}  
\- \*\*additional\_context\*\*: {additional\_context} — domain expertise, portfolio highlights, awards, publications, notable achievements; mine this for project material and bullet evidence

\#\#\# JOB POSTING:  
{job\_posting}

\---

\#\# YOUR TASK

Read the job posting carefully and identify its \*\*top 3–4 core requirements\*\*.

Understand how modern ATS scoring actually works before writing:  
\- ATS platforms do NOT reward raw keyword volume — they score keywords \*\*in context\*\*. A keyword sitting in a skills list with nothing in the experience section backing it up can be flagged as a \*\*mismatch\*\*, which hurts more than it helps.  
\- Content that appears \*\*earlier\*\* in each section and on the page is weighted \*\*more heavily\*\*.  
\- Recruiters typically configure their ATS to surface candidates above a \*\*\~60–70% match threshold\*\*, then review manually. The goal is NOT a 100% keyword score — it is to clear the threshold naturally so a human reads the resume, then win the human with clear achievements, quantified results, and relevance.

Then follow every instruction in the RULES section below to produce the final LaTeX resume.

\---

\#\# RULES

\#\#\# 1\. STRUCTURE — Use ONLY standard section headers (ATS parsers recognize "Education", "Experience", "Projects", "Skills", "Summary", "Certifications" — never creative names like "Where I've Made an Impact"):  
1\. \*\*Header\*\* — full\_name, contact\_email (hyperlinked), each social\_media link (hyperlinked), location. Include a phone number only if one appears in additional\_context.  
2\. \*\*Education\*\* (from education\_and\_credentials) — Degree, institution, location, dates (expected graduation if applicable). Include a "Relevant Coursework" line only if the posting mentions a specific technical area covered by coursework.  
3\. \*\*Experience\*\* — employment history from \`experience\`.  
4\. \*\*Projects\*\* — only if project work (from \`experience\` or \`additional\_context\`) demonstrates posting requirements not already covered by Experience bullets.  
5\. \*\*Technical Skills\*\* — grouped categories (see Rule 4).  
6\. \*(Optional)\* \*\*Certifications\*\* — only those actually listed in education\_and\_credentials. Do not fabricate.

\*\*Section-order rule (order matters — earlier content is weighted more heavily):\*\*  
\- If \*\*yoe \< 3\*\*: Header → Education → Technical Skills → Experience → Projects → Certifications  
\- If \*\*yoe ≥ 3\*\*: Header → Experience → Projects → Education → Technical Skills → Certifications

\#\#\# 2\. EXPERIENCE SELECTION & PRIORITIZATION — Pick the most relevant work experiences and projects from \`experience\` and \`additional\_context\`:  
\- Map each of the posting's top 3–4 requirements to the strongest concrete evidence in the profile. If a requirement cannot be truthfully evidenced, skip it — do not pad.  
\- \*\*Order matters:\*\* list the most posting-relevant role FIRST, and under each role list the most posting-relevant bullet FIRST. If the posting's \#1 requirement is "stakeholder communication", that bullet must be first under the role — not buried fourth.  
\- Drop any role or project that adds no new signal for this specific posting.  
\- Try to fill the page with no blank space, but without fluff.

\#\#\# 3\. BULLET POINT WRITING — Every bullet must:  
\- Begin with a strong \*\*action verb\*\* (e.g., Engineered, Developed, Implemented, Diagnosed, Designed, Automated, Optimized, Documented).  
\- Be \*\*achievement-oriented\*\*, not responsibility-oriented. Show \*what you built or solved\*, not just \*what you worked on\*.  
\- Mirror \*\*exact keywords and phrases\*\* from the job description \*\*inside the context of real work\*\*. Keywords woven into bullets describing actual accomplishments carry far more weight (and trigger no mismatch flags) than keywords sitting alone in a skills list.  
\- Be \*\*specific and concrete\*\*. Include technologies, quantities, or outcomes where possible (e.g., "supporting 3 concurrent clients", "6 interconnected tables", "150+ data elements").  
\- \*\*Never fabricate\*\* tools, certifications, or experiences not present in the candidate profile.

\#\#\# 4\. SKILLS SECTION — Tailor aggressively, with evidence:  
\- Include only skills mentioned in the job posting that appear in the candidate's \`skills\`.  
\- \*\*Corroboration rule:\*\* every skill listed must be backed by at least one experience/project bullet, coursework item, or credential elsewhere in the resume. If a posting keyword cannot be backed by real work, omit it — an unbacked keyword is a mismatch risk, not a match.  
\- Add relevant ATS keywords from the posting that are honest reflections of work experience, coursework, or project work (e.g., "TCP/IP", "REST APIs", "relational databases", "SDLC", "Agile").  
\- Group skills into 4–6 logical categories matching the posting's language (e.g., "Operating Systems", "Networking", "Databases", "Languages", "Tools").  
\- Mirror the exact tool names from the job description wherever possible (e.g., if they say "Microsoft SQL Server", use that over "MySQL" if applicable).  
\- Do NOT list every skill from the profile. Ruthlessly trim to what is relevant.

\#\#\# 5\. KEYWORD STRATEGY (use only keywords relevant to the specific posting):  
\- Pull keywords that appear in BOTH the job posting and the candidate profile.  
\- Inject them in order of impact: (1) inside experience/project bullets with concrete examples, (2) in the Skills section — only where bullet-level evidence exists, (3) in the Summary if one is included.  
\- Never stuff keywords artificially. One keyword backed by a real achievement beats five keywords dumped into a list.

\#\#\# 6\. SUMMARY/OBJECTIVE (optional — include only if the posting explicitly asks for one):  
\- 2–3 sentences max. Use the standard "Summary" header.  
\- Open with: "\[field\] professional with \[yoe\] years of hands-on experience in \[2–3 skills from the posting\]..." (adapt phrasing naturally for early-career candidates).  
\- Close with a statement of intent tailored to the company/role.  
\- Do NOT include a generic objective statement if the posting does not ask for one — it wastes space.

\#\#\# 7\. FORMATTING RULES (critical for ATS):  
\- \*\*One page only.\*\* If content overflows, shorten bullet points (aim for 1 line each), reduce to 3 projects, or remove the optional coursework line.  
\- Use \*\*Jake's Resume LaTeX template\*\* structure exactly — do not change the \`\\resumeSubheading\`, \`\\resumeProjectHeading\`, \`\\resumeItemListStart\` command structure.  
\- Do NOT use tables, columns, graphics, icons, or text boxes — most parsers read left-to-right across the full page width, so a two-column layout becomes word soup on the other end.  
\- Standard section headers only (see Rule 1).  
\- Font size: 11pt. Margins: as in Jake's template (0.5in sides, 0.5in top).  
\- All hyperlinks must use \`\\href{}{\\underline{}}\` format.  
\- Dates go on the right in \`\\textit{\\small}\` format.

\#\#\# 8\. SUBMISSION GUIDANCE — After the LaTeX code, output this short note to the candidate:  
\- Compile to PDF by default, but if applying to Fortune 500 companies or government roles (which often run older ATS platforms like Taleo), also submit a .docx export — .docx parses more reliably on those systems.  
\- Before submitting, run the final resume through a free ATS parser/scoring tool to confirm nothing is lost in parsing and it clears the typical 60–70% recruiter threshold. The score is only the first filter — past it, humans read for clear achievements, quantified results, and relevance.

\#\#\# 9\. FINAL CHECK — Before outputting, verify:  
\- \[ \] The resume is exactly one page (count bullets — no section should be bloated).  
\- \[ \] The posting's top 3–4 requirements are each addressed using the posting's exact terminology, placed prominently (top sections, first bullets).  
\- \[ \] Every keyword in the Skills section is backed by at least one experience/project bullet — no orphan keywords.  
\- \[ \] The most relevant role appears FIRST, and the most relevant bullet appears FIRST under each role.  
\- \[ \] Every bullet uses an action verb.  
\- \[ \] The exact job title or a close variant appears in the Skills section, coursework line, or Summary (for ATS title matching).  
\- \[ \] Only standard section headers are used.  
\- \[ \] No information was fabricated beyond what is in the candidate profile.  
\- \[ \] The LaTeX compiles cleanly with Jake's template (no unclosed braces, no undefined commands).

\---PROMPT END---

4. **Send the curated job posting priority queue back to the Main Dashboard in the front-end.** 

**UI Layout**

* **User Settings:** Settings page where the user can adjust the following, can hover over each to see what its about:   
  \- Skill Match threshold: how many skills are in both user profile and job posting, higher value \= more accuracy , but lower compatible postions  
  \- Compatibility score threshold  
  \- Curator time period: Set a time period that the curator runs for   
      OR Curator job limit: Amount of jobs to scout through in a set time interval (once or periodically)  
  \- Time Delay: delay for every job parsed-\> anti-bot bypass 

* **Form for user profile:** User form where the user can edit or view all the extracted data of their user profile. Have the option to reupload documents to refill all form data. 

* **Main Dashboard:** Dashboard containing all the final curated jobs along with their generated recommended resumes(in latex), with a link to the direct job posting so they can apply. Users may also delete job postings. 

Frontend implementation (User Profile page — built):
- Stack: React + TypeScript + Vite + React Router + MUI; forms via react-hook-form. App in `frontend/`.
- Shared app shell with routed pages (`/profile`, `/settings`, `/dashboard`) so Settings and Dashboard slot in later.
- Documents: multi-file drag & drop; adding files uploads them and invokes Agent 1; the UI polls extraction status and refills the form when finished; files can be removed and extraction re-run.
- Editable sections mirroring the database: basic info, social media, work eligibility, skills, roles, experience (+ per-role highlight bullets), education & credentials, additional context; Save / Discard actions.
- Data layer: typed API client with a mock adapter (simulated extraction) used until the backend exists, toggled by `VITE_USE_MOCK_API`. Backend contract: `GET/PUT /api/profile`, `POST/GET /api/profile/documents`, `DELETE /api/profile/documents/{id}`, `POST /api/profile/extract`, `GET /api/profile/status`.

**Future Improvements:**  
\- Telemetrics, track how many jobs have been searched, pass through the skill filter, ATS filter etc, viewable in the main dashboard.  
\- In built application tracker?

**Building the Agentic System:**

- **Treat each step as an agent**  
- **Consider context length to prevent hallucination**  
- **Emulating OOP in multi agent sys:** Each agent can follow the OOP principle of an object- in this case agent, having an overall purpose.  
-  


Database Schema (Postgres + pgvector):

The tables below are the normalized version of the first-draft schema. The single source
of truth (DDL) is `db/schema.sql`, applied automatically when the database container is
first created (see `docker-compose.yml` and `db/README.md`). Fields are still extracted
from the user's documents via a Pydantic description handed to the LLM.

Architectural fixes applied to the first draft:
- Foreign keys were inverted: each collection (skills, roles, social media, etc.) now holds
  a `user_id` FK to `users`, instead of `UserInfo` pointing at single child rows.
- Added primary keys to every table, plus `created_at`/`updated_at` audit columns.
- Split multi-valued fields into their own tables (no lists stored inside a single row).
- `skills` and `roles` are canonical dictionaries joined to users many-to-many, which
  removes the `skill_name -> type` dependency.
- Education dates are atomic (`start_date`, `end_date`) instead of a "start-end" string.
- The massive job posting string is stored once in `jobs`; `curated_jobs` references it by
  `job_id` (no duplication), and `curated_jobs` is scoped per user.
- `ATS score` lives on the generated resume, not on the raw job.
- Added tables the pipeline needs but the draft omitted: `resumes`, `user_settings`,
  `scrape_runs`, `user_documents`, `schema_migrations`.
- Embeddings are `vector(384)` (open-source model `all-MiniLM-L6-v2`).

Tables:

users (candidate profile root)
- id (PK)
- full_name
- contact_email
- location
- language_preference
- requires_sponsorship
- yoe
- profile_embedding vector(384)   (null until embedded)
- embedding_model, embedded_at
- created_at, updated_at

user_settings (one row per user)
- user_id (PK, FK -> users)
- skill_match_threshold          (default 3)
- semantic_text_match_threshold  (0-1, default 0.5)
- compatibility_score_threshold  (0-100, default 70)
- curator_time_period_minutes    (XOR curator_job_limit)
- curator_job_limit
- time_delay_seconds
- updated_at

Owned one-to-many children of users:
- social_media(user_id FK, platform, username, link)
- work_eligibility(user_id FK, country_name, type: citizenship|work_visa|residency)
- experiences(user_id FK, company_or_org, role, start_date, end_date, sort_order)
- experience_highlights(experience_id FK, highlight, sort_order)
- educations(user_id FK, institution_name, credential_name, type, start_date, end_date)
- additional_context_entries(user_id FK, entry, sort_order)
- user_documents(user_id FK, file_name, mime_type, storage_path, extracted_text)

Canonical dictionaries + many-to-many joins:
- skills(id, name UNIQUE, type)   +  user_skills(user_id, skill_id)
- roles(id, name UNIQUE)          +  user_roles(user_id, role_id)

jobs (every scraped posting, deduplicated pool)
- id (PK)
- source, external_id
- title, company, location, link
- date_posted
- description (the massive posting string)
- status: scraped|embedded|scored|rejected|curated
- description_embedding vector(384)
- embedding_model, embedded_at
- scraped_at, created_at, updated_at
- UNIQUE (source, link)

curated_jobs (final curated priority queue / dashboard, per user)
- id (PK)
- user_id (FK -> users), job_id (FK -> jobs)   UNIQUE (user_id, job_id)
- semantic_score
- overall_match_score
- hard_skills_score, experience_depth_score, role_seniority_score, eligibility_score
- status: active|hidden|deleted   (dashboard "delete" = soft delete)
- added_at, updated_at

resumes (one or more versions per curated job)
- id (PK)
- curated_job_id (FK -> curated_jobs)   UNIQUE (curated_job_id, version)
- latex_content
- pdf_path, docx_path
- ats_score
- version, created_at

scrape_runs (curator telemetry)
- id (PK), source, started_at, finished_at
- jobs_found, jobs_passed_embedding, jobs_curated
- status: running|completed|failed

schema_migrations (version PK, applied_at)

Embeddings: `vector(384)` sized for `all-MiniLM-L6-v2`; cosine similarity uses the pgvector
`<=>` operator with an HNSW index (`vector_cosine_ops`) on `jobs.description_embedding`.
