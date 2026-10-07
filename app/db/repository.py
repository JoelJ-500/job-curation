"""Data access for the candidate profile and uploaded documents.

All writes happen inside a single transaction so the database always matches the
profile the user saved. Child collections are diff-synced by their primary key
`id` (the frontend sends ids for rows that already exist), and the `users` row is
updated column-by-column so only changed attributes are written.
"""

from datetime import date, datetime
from typing import Any

from psycopg import Connection
from psycopg import sql

# Columns of each child table that come from the UI (id and user_id are handled
# separately).
_SOCIAL_MEDIA_COLUMNS = ["platform", "username", "link"]
_WORK_ELIGIBILITY_COLUMNS = ["country_name", "type"]
_EDUCATION_COLUMNS = ["institution_name", "credential_name", "type", "start_date", "end_date"]
_ADDITIONAL_CONTEXT_COLUMNS = ["entry"]
_EXPERIENCE_COLUMNS = ["company_or_org", "role", "start_date", "end_date", "sort_order"]

_USER_COLUMNS = [
    "full_name",
    "contact_email",
    "location",
    "language_preference",
    "requires_sponsorship",
    "yoe",
]


def _iso(value: Any) -> Any:
    """Serialise dates to ISO strings for JSON responses."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _clean_text(value: Any) -> Any:
    """Treat empty/whitespace strings as NULL."""
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def ensure_user(connection: Connection) -> int:
    """Return the (single) user's id, creating the row on first use."""
    row = connection.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    if row is not None:
        return row["id"]

    created = connection.execute("INSERT INTO users DEFAULT VALUES RETURNING id").fetchone()
    return created["id"]


def get_profile(connection: Connection, user_id: int) -> dict[str, Any]:
    """Assemble the full candidate profile for the response."""
    user = connection.execute(
        """
        SELECT full_name, contact_email, location, language_preference,
               requires_sponsorship, yoe
        FROM users WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    social_media = connection.execute(
        "SELECT id, platform, username, link FROM social_media WHERE user_id = %s ORDER BY id",
        (user_id,),
    ).fetchall()

    work_eligibility = connection.execute(
        "SELECT id, country_name, type FROM work_eligibility WHERE user_id = %s ORDER BY id",
        (user_id,),
    ).fetchall()

    skills = connection.execute(
        """
        SELECT s.id, s.name, s.type
        FROM skills s
        JOIN user_skills us ON us.skill_id = s.id
        WHERE us.user_id = %s
        ORDER BY lower(s.name)
        """,
        (user_id,),
    ).fetchall()

    roles = connection.execute(
        """
        SELECT r.id, r.name
        FROM roles r
        JOIN user_roles ur ON ur.role_id = r.id
        WHERE ur.user_id = %s
        ORDER BY lower(r.name)
        """,
        (user_id,),
    ).fetchall()

    experiences = connection.execute(
        """
        SELECT id, company_or_org, role, start_date, end_date, sort_order
        FROM experiences WHERE user_id = %s ORDER BY sort_order, id
        """,
        (user_id,),
    ).fetchall()

    highlights = connection.execute(
        """
        SELECT h.experience_id, h.highlight
        FROM experience_highlights h
        JOIN experiences e ON e.id = h.experience_id
        WHERE e.user_id = %s
        ORDER BY h.sort_order, h.id
        """,
        (user_id,),
    ).fetchall()

    highlights_by_experience: dict[int, list[str]] = {}
    for row in highlights:
        highlights_by_experience.setdefault(row["experience_id"], []).append(row["highlight"])

    educations = connection.execute(
        """
        SELECT id, institution_name, credential_name, type, start_date, end_date
        FROM educations WHERE user_id = %s ORDER BY start_date NULLS LAST, id
        """,
        (user_id,),
    ).fetchall()

    additional_context = connection.execute(
        "SELECT id, entry FROM additional_context_entries WHERE user_id = %s ORDER BY id",
        (user_id,),
    ).fetchall()

    profile = {
        "user_id": user_id,
        "full_name": user["full_name"],
        "contact_email": user["contact_email"],
        "location": user["location"],
        "language_preference": user["language_preference"],
        "requires_sponsorship": user["requires_sponsorship"],
        "yoe": float(user["yoe"]) if user["yoe"] is not None else None,
        "social_media": [dict(row) for row in social_media],
        "work_eligibility": [dict(row) for row in work_eligibility],
        "skills": [dict(row) for row in skills],
        "roles": [dict(row) for row in roles],
        "experiences": [
            {
                "id": row["id"],
                "company_or_org": row["company_or_org"],
                "role": row["role"],
                "start_date": _iso(row["start_date"]),
                "end_date": _iso(row["end_date"]),
                "sort_order": row["sort_order"],
                "highlights": highlights_by_experience.get(row["id"], []),
            }
            for row in experiences
        ],
        "educations": [
            {
                "id": row["id"],
                "institution_name": row["institution_name"],
                "credential_name": row["credential_name"],
                "type": row["type"],
                "start_date": _iso(row["start_date"]),
                "end_date": _iso(row["end_date"]),
            }
            for row in educations
        ],
        "additional_context": [dict(row) for row in additional_context],
    }
    return profile


# ---------------------------------------------------------------------------
# Write helpers (diff-sync)
# ---------------------------------------------------------------------------


def _fetch_existing_ids(connection: Connection, table: str, user_id: int) -> set[int]:
    rows = connection.execute(
        sql.SQL("SELECT id FROM {} WHERE user_id = %s").format(sql.Identifier(table)),
        (user_id,),
    ).fetchall()
    return {row["id"] for row in rows}


def _fetch_row(connection: Connection, table: str, row_id: int) -> dict[str, Any] | None:
    return connection.execute(
        sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(table)),
        (row_id,),
    ).fetchone()


def _insert_child(connection: Connection, table: str, user_id: int, values: dict[str, Any]) -> int:
    columns = list(values.keys())
    insert_statement = sql.SQL("INSERT INTO {} (user_id, {}) VALUES (%s, {}) RETURNING id").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(sql.SQL("%s") for _ in columns),
    )
    params = [user_id] + [values[column] for column in columns]
    return connection.execute(insert_statement, params).fetchone()["id"]


def _update_child(
    connection: Connection, table: str, row_id: int, user_id: int, values: dict[str, Any]
) -> None:
    """Update only the columns that actually changed for this row."""
    current = _fetch_row(connection, table, row_id)
    if current is None:
        return

    changed = {key: value for key, value in values.items() if current.get(key) != value}
    if not changed:
        return

    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(column)) for column in changed
    )
    update_statement = sql.SQL("UPDATE {} SET {} WHERE id = %s AND user_id = %s").format(
        sql.Identifier(table), assignments
    )
    connection.execute(update_statement, list(changed.values()) + [row_id, user_id])


def _delete_missing_children(
    connection: Connection, table: str, user_id: int, kept_ids: set[int]
) -> None:
    if kept_ids:
        connection.execute(
            sql.SQL("DELETE FROM {} WHERE user_id = %s AND NOT (id = ANY(%s))").format(
                sql.Identifier(table)
            ),
            (user_id, list(kept_ids)),
        )
    else:
        connection.execute(
            sql.SQL("DELETE FROM {} WHERE user_id = %s").format(sql.Identifier(table)),
            (user_id,),
        )


def _sync_child_collection(
    connection: Connection,
    table: str,
    user_id: int,
    rows: list[dict[str, Any]],
    columns: list[str],
    required_columns: tuple[str, ...] = (),
) -> None:
    """Insert new rows, update changed rows, delete removed rows (by id).

    Rows missing any `required_columns` value are skipped, since they would
    violate a NOT NULL constraint.
    """
    existing_ids = _fetch_existing_ids(connection, table, user_id)
    kept_ids: set[int] = set()

    for row in rows:
        values = {column: _clean_text(row.get(column)) for column in columns}
        if any(not values.get(column) for column in required_columns):
            continue

        row_id = row.get("id")
        if row_id is not None and row_id in existing_ids:
            _update_child(connection, table, row_id, user_id, values)
            kept_ids.add(row_id)
        else:
            kept_ids.add(_insert_child(connection, table, user_id, values))

    _delete_missing_children(connection, table, user_id, kept_ids)


def _update_user(connection: Connection, user_id: int, profile: dict[str, Any]) -> None:
    """Update only the changed columns on the users row."""
    current = _fetch_row(connection, "users", user_id)
    changed: dict[str, Any] = {}
    for column in _USER_COLUMNS:
        value = _clean_text(profile.get(column))
        if current.get(column) != value:
            changed[column] = value

    if not changed:
        return

    assignments = sql.SQL(", ").join(
        sql.SQL("{} = %s").format(sql.Identifier(column)) for column in changed
    )
    connection.execute(
        sql.SQL("UPDATE users SET {} WHERE id = %s").format(assignments),
        list(changed.values()) + [user_id],
    )


def _sync_skills(connection: Connection, user_id: int, skills: list[dict[str, Any]]) -> None:
    """Reconcile the skills dictionary and the user_skills join table."""
    skill_ids: set[int] = set()
    for skill in skills:
        name = _clean_text(skill.get("name"))
        if not name:
            continue
        row = connection.execute(
            """
            INSERT INTO skills (name, type) VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET type = COALESCE(EXCLUDED.type, skills.type)
            RETURNING id
            """,
            (name, _clean_text(skill.get("type"))),
        ).fetchone()
        skill_ids.add(row["id"])

    connection.execute("DELETE FROM user_skills WHERE user_id = %s", (user_id,))
    for skill_id in skill_ids:
        connection.execute(
            "INSERT INTO user_skills (user_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, skill_id),
        )


def _sync_roles(connection: Connection, user_id: int, roles: list[dict[str, Any]]) -> None:
    """Reconcile the roles dictionary and the user_roles join table."""
    role_ids: set[int] = set()
    for role in roles:
        name = _clean_text(role.get("name"))
        if not name:
            continue
        row = connection.execute(
            """
            INSERT INTO roles (name) VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            (name,),
        ).fetchone()
        role_ids.add(row["id"])

    connection.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
    for role_id in role_ids:
        connection.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, role_id),
        )


def _sync_experiences(
    connection: Connection, user_id: int, experiences: list[dict[str, Any]]
) -> None:
    """Diff-sync experiences, replacing each row's highlight bullets."""
    existing_ids = _fetch_existing_ids(connection, "experiences", user_id)
    kept_ids: set[int] = set()

    for index, experience in enumerate(experiences):
        values = {
            "company_or_org": _clean_text(experience.get("company_or_org")),
            "role": _clean_text(experience.get("role")),
            "start_date": _clean_text(experience.get("start_date")),
            "end_date": _clean_text(experience.get("end_date")),
            "sort_order": index,
        }

        row_id = experience.get("id")
        if row_id is not None and row_id in existing_ids:
            _update_child(connection, "experiences", row_id, user_id, values)
            experience_id = row_id
        else:
            experience_id = _insert_child(connection, "experiences", user_id, values)
        kept_ids.add(experience_id)

        connection.execute(
            "DELETE FROM experience_highlights WHERE experience_id = %s", (experience_id,)
        )
        for highlight_index, highlight in enumerate(experience.get("highlights") or []):
            text = _clean_text(highlight)
            if text:
                connection.execute(
                    """
                    INSERT INTO experience_highlights (experience_id, highlight, sort_order)
                    VALUES (%s, %s, %s)
                    """,
                    (experience_id, text, highlight_index),
                )

    _delete_missing_children(connection, "experiences", user_id, kept_ids)


def clear_profile(connection: Connection, user_id: int) -> None:
    """Remove the extractable profile data before a fresh extraction.

    Document-derived collections are fully replaced on each extraction run (the
    uploaded documents are the source of truth). User-owned settings and the
    uploaded documents themselves are left untouched.
    """
    with connection.transaction():
        connection.execute("DELETE FROM user_skills WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM social_media WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM work_eligibility WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM additional_context_entries WHERE user_id = %s", (user_id,))
        connection.execute("DELETE FROM educations WHERE user_id = %s", (user_id,))
        connection.execute(
            "DELETE FROM experience_highlights WHERE experience_id IN "
            "(SELECT id FROM experiences WHERE user_id = %s)",
            (user_id,),
        )
        connection.execute("DELETE FROM experiences WHERE user_id = %s", (user_id,))
        connection.execute(
            """
            UPDATE users
            SET full_name = NULL, contact_email = NULL, location = NULL,
                language_preference = NULL, requires_sponsorship = NULL, yoe = NULL
            WHERE id = %s
            """,
            (user_id,),
        )


def save_profile(connection: Connection, user_id: int, profile: dict[str, Any]) -> dict[str, Any]:
    """Persist an edited profile, updating only what changed (one transaction)."""
    with connection.transaction():
        _update_user(connection, user_id, profile)
        _sync_child_collection(
            connection,
            "social_media",
            user_id,
            profile.get("social_media", []),
            _SOCIAL_MEDIA_COLUMNS,
            required_columns=("platform", "link"),
        )
        _sync_child_collection(
            connection,
            "work_eligibility",
            user_id,
            profile.get("work_eligibility", []),
            _WORK_ELIGIBILITY_COLUMNS,
            required_columns=("country_name", "type"),
        )
        _sync_skills(connection, user_id, profile.get("skills", []))
        _sync_roles(connection, user_id, profile.get("roles", []))
        _sync_experiences(connection, user_id, profile.get("experiences", []))
        _sync_child_collection(
            connection, "educations", user_id, profile.get("educations", []), _EDUCATION_COLUMNS
        )
        _sync_child_collection(
            connection,
            "additional_context_entries",
            user_id,
            profile.get("additional_context", []),
            _ADDITIONAL_CONTEXT_COLUMNS,
            required_columns=("entry",),
        )

    return get_profile(connection, user_id)


# ---------------------------------------------------------------------------
# Uploaded documents
# ---------------------------------------------------------------------------


def document_to_response(row: dict[str, Any]) -> dict[str, Any]:
    """Shape a user_documents row for the API response."""
    return {
        "id": row["id"],
        "file_name": row["file_name"],
        "mime_type": row["mime_type"],
        "size_bytes": row["size_bytes"],
        "uploaded_at": _iso(row["created_at"]),
    }


def insert_document(
    connection: Connection,
    user_id: int,
    file_name: str,
    mime_type: str | None,
    storage_path: str,
    size_bytes: int | None,
) -> dict[str, Any]:
    row = connection.execute(
        """
        INSERT INTO user_documents (user_id, file_name, mime_type, storage_path, size_bytes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, file_name, mime_type, size_bytes, created_at
        """,
        (user_id, file_name, mime_type, storage_path, size_bytes),
    ).fetchone()
    connection.commit()
    return document_to_response(row)


def list_documents(connection: Connection, user_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, file_name, mime_type, size_bytes, created_at
        FROM user_documents WHERE user_id = %s ORDER BY created_at DESC, id DESC
        """,
        (user_id,),
    ).fetchall()
    return [document_to_response(row) for row in rows]


def get_documents_with_paths(connection: Connection, user_id: int) -> list[dict[str, Any]]:
    return connection.execute(
        """
        SELECT id, file_name, mime_type, storage_path
        FROM user_documents WHERE user_id = %s ORDER BY id
        """,
        (user_id,),
    ).fetchall()


def get_document(connection: Connection, user_id: int, document_id: int) -> dict[str, Any] | None:
    return connection.execute(
        """
        SELECT id, file_name, mime_type, storage_path
        FROM user_documents WHERE id = %s AND user_id = %s
        """,
        (document_id, user_id),
    ).fetchone()


def delete_document(connection: Connection, user_id: int, document_id: int) -> None:
    connection.execute(
        "DELETE FROM user_documents WHERE id = %s AND user_id = %s", (document_id, user_id)
    )
    connection.commit()


def set_document_text(connection: Connection, document_id: int, extracted_text: str) -> None:
    connection.execute(
        "UPDATE user_documents SET extracted_text = %s WHERE id = %s", (extracted_text, document_id)
    )
    connection.commit()


# ---------------------------------------------------------------------------
# Curator settings
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS: dict[str, Any] = {
    "curator_job_limit": 10,
    "curator_time_period_minutes": None,
    "skill_match_threshold": 3,
    "semantic_text_match_threshold": 0.5,
    "compatibility_score_threshold": 70,
    "time_delay_seconds": 0.0,
}

# Columns of user_settings that come from the UI.
_SETTINGS_COLUMNS = [
    "curator_job_limit",
    "curator_time_period_minutes",
    "skill_match_threshold",
    "semantic_text_match_threshold",
    "compatibility_score_threshold",
    "time_delay_seconds",
]


def get_settings(connection: Connection, user_id: int) -> dict[str, Any]:
    """Return the user's curator settings, falling back to the defaults."""
    row = connection.execute(
        """
        SELECT curator_job_limit, curator_time_period_minutes,
               skill_match_threshold, semantic_text_match_threshold,
               compatibility_score_threshold, time_delay_seconds
        FROM user_settings WHERE user_id = %s
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        return dict(DEFAULT_SETTINGS)
    return {
        "curator_job_limit": row["curator_job_limit"],
        "curator_time_period_minutes": row["curator_time_period_minutes"],
        "skill_match_threshold": row["skill_match_threshold"],
        "semantic_text_match_threshold": float(row["semantic_text_match_threshold"]),
        "compatibility_score_threshold": row["compatibility_score_threshold"],
        "time_delay_seconds": float(row["time_delay_seconds"]),
    }


def save_settings(connection: Connection, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Upsert the user's curator settings (only changed columns are overwritten)."""
    values = dict(DEFAULT_SETTINGS)
    for column in _SETTINGS_COLUMNS:
        if column in data:
            values[column] = data[column]

    # The curator runs for a time period OR a job limit, never both.
    if values["curator_job_limit"] is not None:
        values["curator_time_period_minutes"] = None
    elif values["curator_time_period_minutes"] is not None:
        values["curator_job_limit"] = None

    connection.execute(
        """
        INSERT INTO user_settings (
            user_id, curator_job_limit, curator_time_period_minutes,
            skill_match_threshold, semantic_text_match_threshold,
            compatibility_score_threshold, time_delay_seconds
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            curator_job_limit = EXCLUDED.curator_job_limit,
            curator_time_period_minutes = EXCLUDED.curator_time_period_minutes,
            skill_match_threshold = EXCLUDED.skill_match_threshold,
            semantic_text_match_threshold = EXCLUDED.semantic_text_match_threshold,
            compatibility_score_threshold = EXCLUDED.compatibility_score_threshold,
            time_delay_seconds = EXCLUDED.time_delay_seconds
        """,
        (
            user_id,
            values["curator_job_limit"],
            values["curator_time_period_minutes"],
            values["skill_match_threshold"],
            values["semantic_text_match_threshold"],
            values["compatibility_score_threshold"],
            values["time_delay_seconds"],
        ),
    )
    connection.commit()
    return get_settings(connection, user_id)


# ---------------------------------------------------------------------------
# Curator (scraping) helpers
# ---------------------------------------------------------------------------


def get_filter_inputs(connection: Connection, user_id: int) -> dict[str, Any]:
    """Return the profile fields each job-site search is built from."""
    user = connection.execute(
        "SELECT location, language_preference, yoe FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()
    roles = connection.execute(
        """
        SELECT r.name
        FROM roles r
        JOIN user_roles ur ON ur.role_id = r.id
        WHERE ur.user_id = %s
        ORDER BY lower(r.name)
        """,
        (user_id,),
    ).fetchall()
    return {
        "roles": [row["name"] for row in roles],
        "location": user["location"] if user else None,
        "language_preference": user["language_preference"] if user else None,
        "yoe": float(user["yoe"]) if user and user["yoe"] is not None else None,
    }


def upsert_job(
    connection: Connection,
    source: str,
    title: str,
    link: str,
    date_posted: Any,
    description: str,
) -> int:
    """Insert a scraped job, refreshing duplicates on (source, link)."""
    row = connection.execute(
        """
        INSERT INTO jobs (source, title, link, date_posted, description, status)
        VALUES (%s, %s, %s, %s, %s, 'scraped')
        ON CONFLICT (source, link) DO UPDATE SET
            title = EXCLUDED.title,
            date_posted = COALESCE(EXCLUDED.date_posted, jobs.date_posted),
            description = EXCLUDED.description,
            updated_at = now()
        RETURNING id
        """,
        (source, title, link, date_posted, description),
    ).fetchone()
    connection.commit()
    return row["id"]


def start_scrape_run(connection: Connection, source: str) -> int:
    """Open a scrape_runs telemetry row and return its id."""
    row = connection.execute(
        "INSERT INTO scrape_runs (source) VALUES (%s) RETURNING id", (source,)
    ).fetchone()
    connection.commit()
    return row["id"]


def finish_scrape_run(
    connection: Connection, run_id: int, jobs_found: int, status: str = "completed"
) -> None:
    """Close a scrape_runs telemetry row."""
    connection.execute(
        "UPDATE scrape_runs SET finished_at = now(), jobs_found = %s, status = %s WHERE id = %s",
        (jobs_found, status, run_id),
    )
    connection.commit()
# ---------------------------------------------------------------------------
# Semantic pre-filter helpers (Agent 2, Step 2)
# ---------------------------------------------------------------------------


def get_semantic_profile(connection: Connection, user_id: int) -> dict[str, Any]:
    """Return the skills/education/yoe used to build the profile embedding."""
    user = connection.execute(
        "SELECT yoe FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()

    skills = connection.execute(
        """
        SELECT s.name
        FROM skills s
        JOIN user_skills us ON us.skill_id = s.id
        WHERE us.user_id = %s
        ORDER BY lower(s.name)
        """,
        (user_id,),
    ).fetchall()

    educations = connection.execute(
        """
        SELECT institution_name, credential_name
        FROM educations
        WHERE user_id = %s
        ORDER BY start_date NULLS LAST, id
        """,
        (user_id,),
    ).fetchall()

    education_parts: list[str] = []
    for row in educations:
        credential = (row["credential_name"] or "").strip()
        institution = (row["institution_name"] or "").strip()
        combined = ", ".join(part for part in (credential, institution) if part)
        if combined:
            education_parts.append(combined)

    return {
        "skills": [row["name"] for row in skills],
        "educations": education_parts,
        "yoe": float(user["yoe"]) if user and user["yoe"] is not None else None,
    }


def job_exists(connection: Connection, link: str) -> bool:
    """True if the posting already exists in `jobs` or `curated_jobs` (by link)."""
    if not link:
        return False
    row = connection.execute(
        """
        SELECT 1 FROM jobs WHERE link = %s
        UNION ALL
        SELECT 1 FROM curated_jobs c JOIN jobs j ON j.id = c.job_id WHERE j.link = %s
        LIMIT 1
        """,
        (link, link),
    ).fetchone()
    return row is not None
