-- ===========================================================================
-- USE FOR TESTING DATABASE
-- Smoke test for the job-curation schema.
-- Exercises the full happy path (profile -> scraped job -> curated job ->
-- resume) plus the cosine-similarity query and the updated_at trigger.
-- Everything runs inside a transaction that is rolled back, so it leaves no
-- data behind.
--
-- Run it with:
--   docker exec -i job_curation_db psql -U job_curation -d job_curation \
--     -v ON_ERROR_STOP=1 < db/smoke_test.sql
-- ===========================================================================

BEGIN;

-- Candidate profile (with an embedding so cosine similarity can be computed).
INSERT INTO users
    (full_name, contact_email, location, language_preference, requires_sponsorship,
     yoe, profile_embedding, embedding_model)
VALUES
    ('Test User', 'test@example.com', 'Toronto, ON', 'English', false, 5.0,
     array_fill(0.02::real, ARRAY[384])::vector, 'all-MiniLM-L6-v2');

-- Settings row (defaults applied).
INSERT INTO user_settings (user_id)
SELECT id FROM users WHERE contact_email = 'test@example.com';

-- Canonical skill/role plus the joins to the user.
INSERT INTO skills (name, type) VALUES ('Python', 'prog_language')
    ON CONFLICT (name) DO NOTHING;
INSERT INTO roles (name) VALUES ('Backend Engineer')
    ON CONFLICT (name) DO NOTHING;

INSERT INTO user_skills (user_id, skill_id)
SELECT u.id, s.id FROM users u, skills s
WHERE u.contact_email = 'test@example.com' AND s.name = 'Python';

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.contact_email = 'test@example.com' AND r.name = 'Backend Engineer';

-- A scraped job (status = 'scraped', with its embedding).
INSERT INTO jobs
    (source, title, company, link, date_posted, description,
     description_embedding, embedding_model)
VALUES
    ('hiring_cafe', 'Backend Engineer', 'Acme', 'https://example.com/job/1',
     now() - interval '2 hours', 'We need a Python backend engineer.',
     array_fill(0.01::real, ARRAY[384])::vector, 'all-MiniLM-L6-v2');

-- Promote it to the curated queue with a cosine similarity and LLM scores.
INSERT INTO curated_jobs
    (user_id, job_id, semantic_score, overall_match_score,
     hard_skills_score, experience_depth_score, role_seniority_score, eligibility_score)
SELECT u.id, j.id,
       1 - (u.profile_embedding <=> j.description_embedding),
       82, 85, 80, 78, 90
FROM users u, jobs j
WHERE u.contact_email = 'test@example.com' AND j.link = 'https://example.com/job/1';

-- A generated resume for the curated job.
INSERT INTO resumes (curated_job_id, latex_content, ats_score)
SELECT id, 'test-latex', 75 FROM curated_jobs ORDER BY id DESC LIMIT 1;

-- Dashboard-style read: curated job + its resume.
SELECT cj.id AS curated_id,
       round(cj.semantic_score::numeric, 4) AS semantic_score,
       cj.overall_match_score,
       r.ats_score
FROM curated_jobs cj
JOIN resumes r ON r.curated_job_id = cj.id;

-- updated_at trigger check (backdate created_at so now() is clearly later).
UPDATE users SET created_at = now() - interval '1 day'
WHERE contact_email = 'test@example.com';
UPDATE users SET full_name = 'Test User 2'
WHERE contact_email = 'test@example.com';
SELECT (updated_at > created_at) AS updated_at_trigger_ok
FROM users WHERE contact_email = 'test@example.com';

ROLLBACK;
