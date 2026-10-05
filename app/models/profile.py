"""Pydantic schemas for Agent 1 (user data extraction).

These models are handed to the LLM (via LangChain structured output) plus the
field descriptions below, which tell the model exactly what to look for. Any
field that is not found in the documents must be returned as `null` (empty
lists for collections) -- the model must never invent data.

Field names match the database (see db/schema.sql) so the extracted profile can
be persisted without a mapping layer.
"""

from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    """A single employment history entry, role, or major project."""

    company_or_org: str | None = Field(
        default=None,
        description="Company, organization, client, or institution name for this role or project.",
    )
    role: str | None = Field(
        default=None,
        description="Job title, position, or professional role held at this company.",
    )
    start_date: str | None = Field(
        default=None,
        description=(
            "Start date in ISO format (YYYY-MM-DD). Use the first day of the month "
            "if only a month and year are known. Null if unknown."
        ),
    )
    end_date: str | None = Field(
        default=None,
        description=(
            "End date in ISO format (YYYY-MM-DD). Null if this is the current role "
            "or the date is unknown."
        ),
    )
    highlights: list[str] = Field(
        default_factory=list,
        description=(
            "Key responsibilities, achievements, projects, or duties performed at this "
            "role. One string per bullet, across any industry. Prefer concrete results "
            "and metrics found in the documents."
        ),
    )


class SocialMedia(BaseModel):
    """A social media profile or link belonging to the candidate."""

    platform: str = Field(
        description="Platform name, for example LinkedIn, GitHub, Behance, or a personal website.",
    )
    username: str | None = Field(
        default=None,
        description="Handle or username on the platform. Null if it cannot be determined.",
    )
    link: str = Field(
        description="Full URL to the profile or website.",
    )


class WorkEligibility(BaseModel):
    """A citizenship, work permit, or residency the candidate holds."""

    country_name: str = Field(
        description="Country for this eligibility, for example Canada or United States.",
    )
    type: str = Field(
        description=(
            "One of exactly: 'citizenship', 'work_visa', or 'residency'. "
            "Use 'work_visa' for work permits and 'residency' for permanent residency."
        ),
    )


class Skill(BaseModel):
    """A professional skill, tool, language, framework, or expertise."""

    name: str = Field(
        description="Name of the skill, tool, framework, or language. Use the exact name, e.g. 'Python'.",
    )
    type: str | None = Field(
        default=None,
        description=(
            "Category of the skill, for example: prog_language, framework, tool, "
            "methodology, or other. Null if unclear."
        ),
    )


class Role(BaseModel):
    """A job title or role the candidate would be suitable for."""

    name: str = Field(
        description="Job title or role, for example 'Backend Engineer'. Use standard, searchable titles.",
    )


class Education(BaseModel):
    """An education entry or credential."""

    institution_name: str | None = Field(
        default=None,
        description="School, university, college, or institution name.",
    )
    credential_name: str | None = Field(
        default=None,
        description="Field of study, major, or credential name, for example 'Computer Science' or 'Red Seal'.",
    )
    type: str | None = Field(
        default=None,
        description=(
            "One of exactly: 'associate', 'bachelors', 'masters', 'phd', 'diploma', "
            "'certificate'. Null if unclear."
        ),
    )
    start_date: str | None = Field(
        default=None,
        description="Start date in ISO format (YYYY-MM-DD). Null if unknown.",
    )
    end_date: str | None = Field(
        default=None,
        description="End or completion date in ISO format (YYYY-MM-DD). Null if unknown or in progress.",
    )


class AdditionalContext(BaseModel):
    """A miscellaneous notable item about the candidate."""

    entry: str = Field(
        description=(
            "A single notable item: unique domain expertise, portfolio highlight, award, "
            "publication, certification, or achievement found in any file type."
        ),
    )


class CandidateProfile(BaseModel):
    """The unified candidate profile extracted from all uploaded documents."""

    full_name: str | None = Field(
        default=None,
        description="The candidate's full name.",
    )
    contact_email: str | None = Field(
        default=None,
        description="The candidate's email address.",
    )
    location: str | None = Field(
        default=None,
        description="The candidate's physical location or region, for example 'Toronto, ON'.",
    )
    language_preference: str | None = Field(
        default=None,
        description="The candidate's preferred language, for example English.",
    )
    requires_sponsorship: bool | None = Field(
        default=None,
        description=(
            "True if the candidate states they need work sponsorship, false if they state "
            "they do not. Null if unknown."
        ),
    )
    yoe: float | None = Field(
        default=None,
        description="Total years of professional experience as a number. Null if it cannot be estimated.",
    )
    social_media: list[SocialMedia] = Field(
        default_factory=list,
        description="All social media profiles and personal links found, for example LinkedIn or GitHub.",
    )
    work_eligibility: list[WorkEligibility] = Field(
        default_factory=list,
        description="All citizenships, work permits, and residencies the candidate holds.",
    )
    skills: list[Skill] = Field(
        default_factory=list,
        description=(
            "Professional skills, domain expertise, tools, methodologies, programming "
            "languages, frameworks, spoken languages, or specialized proficiencies across "
            "any field (creative, administrative, medical, legal, retail, blue-collar, "
            "business, technical, and so on)."
        ),
    )
    roles: list[Role] = Field(
        default_factory=list,
        description="All roles the candidate would be suitable for, based on the provided materials.",
    )
    experiences: list[WorkExperience] = Field(
        default_factory=list,
        description="Employment history, professional roles, and major projects.",
    )
    educations: list[Education] = Field(
        default_factory=list,
        description="Education, degrees, diplomas, and credentials.",
    )
    additional_context: list[AdditionalContext] = Field(
        default_factory=list,
        description=(
            "Unique domain expertise, portfolio highlights, awards, publications, or "
            "notable achievements evident in any file type."
        ),
    )
