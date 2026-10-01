-- ===========================================================================
-- job-curation — PostgreSQL + pgvector schema
-- ===========================================================================
-- Single source of truth for the database structure. It is applied automatically
-- on first container start (mounted into /docker-entrypoint-initdb.d by
-- docker-compose.yml) and is safe to re-run because every statement is
-- idempotent (CREATE ... IF NOT EXISTS / DROP ... IF EXISTS).
--
-- Contents:
--   1. Extension
--   2. Candidate profile (users + owned child tables)
--   3. Canonical dictionaries + many-to-many joins (skills, roles)
--   4. Jobs: scraped postings to be processed (canonical, deduped)
--   5. Curated jobs (final dashboard queue, per user)
--   6. Generated resumes
--   7. Housekeeping / telemetry tables
--   8. Indexes, updated_at triggers, migration marker
--
-- Embedding column note:
--   vector(384) is sized for the open-source model `all-MiniLM-L6-v2`.
--   Changing the embedding model requires changing the dimension here and
--   re-embedding all stored vectors.
-- ===========================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- 2. Candidate profile
-- ---------------------------------------------------------------------------

-- Root of the candidate profile (one row per user).
CREATE TABLE IF NOT EXISTS users
(
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name            TEXT,
    contact_email        TEXT,
    location             TEXT,
    language_preference  TEXT,
    requires_sponsorship BOOLEAN,
    yoe                  NUMERIC(4, 1),
    profile_embedding    vector(384),
    embedding_model      TEXT,
    embedded_at          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-user curator/threshold settings driven by the Settings UI.
CREATE TABLE IF NOT EXISTS user_settings
(
    user_id                       BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    skill_match_threshold         INTEGER NOT NULL DEFAULT 3 CHECK (skill_match_threshold >= 0),
    semantic_text_match_threshold REAL    NOT NULL DEFAULT 0.5
        CHECK (semantic_text_match_threshold >= 0 AND semantic_text_match_threshold <= 1),
    compatibility_score_threshold INTEGER NOT NULL DEFAULT 70
        CHECK (compatibility_score_threshold >= 0 AND compatibility_score_threshold <= 100),
    curator_time_period_minutes   INTEGER CHECK (curator_time_period_minutes IS NULL OR curator_time_period_minutes > 0),
    curator_job_limit             INTEGER CHECK (curator_job_limit IS NULL OR curator_job_limit > 0),
    time_delay_seconds            NUMERIC(6, 2) NOT NULL DEFAULT 0 CHECK (time_delay_seconds >= 0),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- The curator runs either for a time period OR up to a job limit, never both.
    CONSTRAINT user_settings_run_mode_xor
        CHECK (curator_time_period_minutes IS NULL OR curator_job_limit IS NULL)
);

-- Social media profiles/links (many per user).
CREATE TABLE IF NOT EXISTS social_media
(
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform   TEXT NOT NULL,
    username   TEXT,
    link       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT social_media_unique UNIQUE (user_id, platform, link)
);

-- Work eligibility facts (citizenship / work visa / residency, many per user).
CREATE TABLE IF NOT EXISTS work_eligibility
(
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    country_name TEXT NOT NULL,
    type         TEXT NOT NULL CHECK (type IN ('citizenship', 'work_visa', 'residency')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT work_eligibility_unique UNIQUE (user_id, country_name, type)
);

-- Employment history / major projects (many per user).
CREATE TABLE IF NOT EXISTS experiences
(
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_or_org TEXT,
    role           TEXT,
    start_date     DATE,
    end_date       DATE,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Key responsibilities/achievements, one row per bullet (1NF for the highlights list).
CREATE TABLE IF NOT EXISTS experience_highlights
(
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    experience_id BIGINT NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    highlight     TEXT NOT NULL,
    sort_order    INTEGER NOT NULL DEFAULT 0
);

-- Education and credentials (degrees, diplomas, certificates).
CREATE TABLE IF NOT EXISTS educations
(
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    institution_name TEXT,
    credential_name  TEXT,
    type             TEXT CHECK (type IN ('associate', 'bachelors', 'masters', 'phd', 'diploma', 'certificate')),
    start_date       DATE,
    end_date         DATE,
    sort_order       INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Miscellaneous profile items (awards, publications, portfolio notes), one row each.
CREATE TABLE IF NOT EXISTS additional_context_entries
(
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry      TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------------------
-- 3. Canonical dictionaries + many-to-many joins
-- ---------------------------------------------------------------------------

-- Canonical skill dictionary. `type` describes the kind of skill
-- (tool, framework, prog_language, methodology, ...).
CREATE TABLE IF NOT EXISTS skills
(
    id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT
);

-- Canonical role/title dictionary (used as job-board search terms).
CREATE TABLE IF NOT EXISTS roles
(
    id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_skills
(
    user_id  BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id BIGINT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, skill_id)
);

CREATE TABLE IF NOT EXISTS user_roles
(
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ---------------------------------------------------------------------------
-- 4. Jobs: scraped postings to be processed (canonical, deduplicated pool)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS jobs
(
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source                TEXT NOT NULL,
    external_id           TEXT,
    title                 TEXT NOT NULL,
    company               TEXT,
    location              TEXT,
    link                  TEXT NOT NULL,
    date_posted           TIMESTAMPTZ,
    description           TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'scraped'
        CHECK (status IN ('scraped', 'embedded', 'scored', 'rejected', 'curated')),
    description_embedding vector(384),
    embedding_model       TEXT,
    embedded_at           TIMESTAMPTZ,
    scraped_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT jobs_source_link_unique UNIQUE (source, link)
);

-- ---------------------------------------------------------------------------
-- 5. Curated jobs: final dashboard queue (per user)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS curated_jobs
(
    id                     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id                BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id                 BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    semantic_score         DOUBLE PRECISION
        CHECK (semantic_score IS NULL OR (semantic_score >= -1 AND semantic_score <= 1)),
    overall_match_score    INTEGER
        CHECK (overall_match_score IS NULL OR (overall_match_score >= 0 AND overall_match_score <= 100)),
    hard_skills_score      INTEGER
        CHECK (hard_skills_score IS NULL OR (hard_skills_score >= 0 AND hard_skills_score <= 100)),
    experience_depth_score INTEGER
        CHECK (experience_depth_score IS NULL OR (experience_depth_score >= 0 AND experience_depth_score <= 100)),
    role_seniority_score   INTEGER
        CHECK (role_seniority_score IS NULL OR (role_seniority_score >= 0 AND role_seniority_score <= 100)),
    eligibility_score      INTEGER
        CHECK (eligibility_score IS NULL OR (eligibility_score >= 0 AND eligibility_score <= 100)),
    status                 TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'hidden', 'deleted')),
    added_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT curated_jobs_user_job_unique UNIQUE (user_id, job_id)
);

-- ---------------------------------------------------------------------------
-- 6. Generated resumes (one or more versions per curated job)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS resumes
(
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    curated_job_id BIGINT NOT NULL REFERENCES curated_jobs(id) ON DELETE CASCADE,
    latex_content  TEXT NOT NULL,
    pdf_path       TEXT,
    docx_path      TEXT,
    ats_score      INTEGER CHECK (ats_score IS NULL OR (ats_score >= 0 AND ats_score <= 100)),
    version        INTEGER NOT NULL DEFAULT 1,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT resumes_unique_version UNIQUE (curated_job_id, version)
);

-- ---------------------------------------------------------------------------
-- 7. Housekeeping / telemetry tables
-- ---------------------------------------------------------------------------

-- Raw documents uploaded by the user (metadata + extracted plain text).
CREATE TABLE IF NOT EXISTS user_documents
(
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name      TEXT NOT NULL,
    mime_type      TEXT,
    storage_path   TEXT,
    extracted_text TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per curator/scrape run, used for telemetry (jobs found / filtered / curated).
CREATE TABLE IF NOT EXISTS scrape_runs
(
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source                TEXT NOT NULL,
    started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at           TIMESTAMPTZ,
    jobs_found            INTEGER NOT NULL DEFAULT 0,
    jobs_passed_embedding INTEGER NOT NULL DEFAULT 0,
    jobs_curated          INTEGER NOT NULL DEFAULT 0,
    status                TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed'))
);

-- Applied schema versions (see the marker insert at the bottom of this file).
CREATE TABLE IF NOT EXISTS schema_migrations
(
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 8. Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_jobs_date_posted ON jobs (date_posted);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);

-- Approximate-nearest-neighbour index for cosine similarity search on job text.
CREATE INDEX IF NOT EXISTS idx_jobs_description_embedding
    ON jobs USING hnsw (description_embedding vector_cosine_ops);

-- Dashboard priority ordering: highest compatibility first, per user.
CREATE INDEX IF NOT EXISTS idx_curated_jobs_user_score
    ON curated_jobs (user_id, overall_match_score DESC);
CREATE INDEX IF NOT EXISTS idx_curated_jobs_job ON curated_jobs (job_id);
CREATE INDEX IF NOT EXISTS idx_resumes_curated_job ON resumes (curated_job_id);
CREATE INDEX IF NOT EXISTS idx_experiences_user ON experiences (user_id);
CREATE INDEX IF NOT EXISTS idx_experience_highlights_experience ON experience_highlights (experience_id);
CREATE INDEX IF NOT EXISTS idx_educations_user ON educations (user_id);
CREATE INDEX IF NOT EXISTS idx_social_media_user ON social_media (user_id);
CREATE INDEX IF NOT EXISTS idx_work_eligibility_user ON work_eligibility (user_id);
CREATE INDEX IF NOT EXISTS idx_additional_context_user ON additional_context_entries (user_id);
CREATE INDEX IF NOT EXISTS idx_user_documents_user ON user_documents (user_id);

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS
$$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_user_settings_updated_at ON user_settings;
CREATE TRIGGER trg_user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_curated_jobs_updated_at ON curated_jobs;
CREATE TRIGGER trg_curated_jobs_updated_at
    BEFORE UPDATE ON curated_jobs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Migration marker
-- ---------------------------------------------------------------------------

INSERT INTO schema_migrations (version) VALUES ('001_init') ON CONFLICT (version) DO NOTHING;
