"""Scraping agents (Agent 2, Step 1).

Two LangChain agents share this module:
  - `plan_searches` maps the candidate profile onto a site's search controls
    (role keyword, location, experience, language, category).
  - `parse_jobs_from_html` extracts jobs from a page's HTML when the deterministic
    selectors stop matching (changing UI layouts).

Both use the shared Groq chat model with structured output and deterministic
fallbacks, so scraping never hard-fails if the LLM is unavailable.
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm import get_chat_model

logger = logging.getLogger(__name__)

# Eluta's fixed Category filter values (from the site's Category dropdown).
ELUTA_CATEGORIES = [
    "Hospitality/Food Service",
    "Retail",
    "Finance/Banking",
    "Computing - Software & Web Development",
    "Health/Medical - Nursing",
    "Trades/Technicians",
    "Accounting",
    "Engineering - Electrical",
    "Manufacturing/Operations",
    "Health/Medical - Support Services",
    "Sales",
    "Logistics/Supply Chain",
]


class SearchPlan(BaseModel):
    """Concrete values to enter into one site's search controls for one role."""

    role_query: str = Field(description="Text to type into the site's job title/keyword box.")
    location: str | None = Field(default=None, description="Location filter value, or null to skip.")
    experience: str | None = Field(default=None, description="Experience filter matching the candidate's years of experience, or null to skip.")
    language: str | None = Field(default=None, description="Language filter value, or null to skip.")
    category: str | None = Field(default=None, description="Site category filter value (Eluta only), or null to skip.")
    sort_recent: bool = Field(default=True, description="Whether to sort results by most recent postings.")


class SearchPlanList(BaseModel):
    plans: list[SearchPlan]


class ParsedJob(BaseModel):
    title: str
    link: str
    date_text: str | None = None
    description: str = ""


class ParsedJobs(BaseModel):
    jobs: list[ParsedJob]


_PLAN_SYSTEM_PROMPT = (
    "You configure a job-board search from a candidate profile. For each role, "
    "produce the exact filter values that site supports. Rules:\n"
    "- Use only values supported by the site's controls (provided per site).\n"
    "- Return null for any filter whose source profile field is missing.\n"
    "- Never invent values that the controls cannot accept.\n"
    "- Always sort by most recent.\n"
    "- For Eluta's category, choose the closest value from the allowed list, or null."
)


def _experience_bucket(yoe: float | None) -> str | None:
    if yoe is None:
        return None
    if yoe < 2:
        return "1-2 years"
    if yoe < 5:
        return "3-5 years"
    return "5+ years"


def _deterministic_plan(role: str, profile: dict, site: str) -> SearchPlan:
    """Fallback plan built directly from the profile (no LLM)."""
    return SearchPlan(
        role_query=role,
        location=profile.get("location") or None,
        experience=_experience_bucket(profile.get("yoe")) if site == "hiringcafe" else None,
        language=profile.get("language_preference") if site == "hiringcafe" else None,
        category=None,
        sort_recent=True,
    )


def _plan_user_prompt(profile: dict, site: str, site_hints: str, roles: list[str]) -> str:
    inputs = {
        "roles": roles,
        "location": profile.get("location"),
        "yoe": profile.get("yoe"),
        "language_preference": profile.get("language_preference"),
    }
    return (
        f"Site: {site}\nSite controls: {site_hints}\n\n"
        f"Candidate filter inputs: {json.dumps(inputs)}\n\n"
        f"Allowed Eluta categories: {ELUTA_CATEGORIES}\n\n"
        "Return one plan per role, in the same order."
    )


def plan_searches(
    profile: dict, site: str, site_hints: str, max_roles: int | None = None
) -> list[SearchPlan]:
    """Return one search plan per role, using the LLM with a deterministic fallback."""
    roles = [role for role in (profile.get("roles") or []) if role]
    if not roles:
        return []
    if max_roles:
        roles = roles[:max_roles]

    try:
        model = get_chat_model().with_structured_output(SearchPlanList, method="json_schema")
        result = model.invoke(
            [
                SystemMessage(content=_PLAN_SYSTEM_PROMPT),
                HumanMessage(content=_plan_user_prompt(profile, site, site_hints, roles)),
            ]
        )
        plans = result.plans if isinstance(result, SearchPlanList) else []
    except Exception as error:  # noqa: BLE001 - fall back to deterministic plans
        logger.warning("Search planning via LLM failed (%s); using fallback.", error)
        plans = []

    if not plans or len(plans) != len(roles):
        return [_deterministic_plan(role, profile, site) for role in roles]
    return plans


def parse_jobs_from_html(
    html: str, source: str, base_url: str, max_chars: int = 40000
) -> list[dict]:
    """LLM fallback: extract job cards from a page's HTML when selectors fail."""
    if not html:
        return []

    model = get_chat_model().with_structured_output(ParsedJobs, method="json_schema")
    system = (
        "You extract job postings from a web page's HTML. Return each posting's "
        "title, absolute link, optional posted-date text, and a description string. "
        "Only return jobs actually present in the HTML."
    )
    user = f"Base URL: {base_url}\nSource: {source}\n\nHTML:\n{html[:max_chars]}"
    try:
        result = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        jobs = result.jobs if isinstance(result, ParsedJobs) else []
    except Exception as error:  # noqa: BLE001
        logger.warning("HTML parsing via LLM failed for %s: %s", source, error)
        return []

    return [
        {
            "source": source,
            "title": job.title,
            "link": job.link,
            "date_text": job.date_text,
            "company": "",
            "location": "",
            "summary": job.description,
        }
        for job in jobs
    ]
