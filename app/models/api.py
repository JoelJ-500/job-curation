"""API request/response models.

These mirror the frontend types in `frontend/src/types/profile.ts` exactly, so
the React app can talk to the backend without a transformation layer.
"""

from pydantic import BaseModel, Field


class SocialMediaEntry(BaseModel):
    id: int | None = None
    platform: str
    username: str | None = None
    link: str


class WorkEligibilityEntry(BaseModel):
    id: int | None = None
    country_name: str
    type: str


class SkillEntry(BaseModel):
    id: int | None = None
    name: str
    type: str | None = None


class RoleEntry(BaseModel):
    id: int | None = None
    name: str


class ExperienceEntry(BaseModel):
    id: int | None = None
    company_or_org: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    sort_order: int = 0
    highlights: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    id: int | None = None
    institution_name: str | None = None
    credential_name: str | None = None
    type: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class AdditionalContextEntry(BaseModel):
    id: int | None = None
    entry: str


class UserProfileResponse(BaseModel):
    user_id: int | None = None
    full_name: str | None = None
    contact_email: str | None = None
    location: str | None = None
    language_preference: str | None = None
    requires_sponsorship: bool | None = None
    yoe: float | None = None
    social_media: list[SocialMediaEntry] = Field(default_factory=list)
    work_eligibility: list[WorkEligibilityEntry] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    roles: list[RoleEntry] = Field(default_factory=list)
    experiences: list[ExperienceEntry] = Field(default_factory=list)
    educations: list[EducationEntry] = Field(default_factory=list)
    additional_context: list[AdditionalContextEntry] = Field(default_factory=list)


class UserDocumentResponse(BaseModel):
    id: int
    file_name: str
    mime_type: str | None = None
    size_bytes: int | None = None
    uploaded_at: str


class ExtractionStatusResponse(BaseModel):
    state: str
    message: str | None = None