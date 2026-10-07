// Types for the candidate profile UI.
//
// Field names use snake_case to mirror the backend Pydantic models and the
// Postgres schema (see db/schema.sql) so no mapping layer is needed.

export type WorkEligibilityType = 'citizenship' | 'work_visa' | 'residency';

export type EducationType =
  | 'associate'
  | 'bachelors'
  | 'masters'
  | 'phd'
  | 'diploma'
  | 'certificate';

export interface SocialMediaEntry {
  id?: number;
  platform: string;
  username: string | null;
  link: string;
}

export interface WorkEligibilityEntry {
  id?: number;
  country_name: string;
  type: WorkEligibilityType;
}

export interface SkillEntry {
  id?: number;
  name: string;
  type: string | null;
}

export interface RoleEntry {
  id?: number;
  name: string;
}

export interface ExperienceEntry {
  id?: number;
  company_or_org: string | null;
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  sort_order: number;
  highlights: string[];
}

export interface EducationEntry {
  id?: number;
  institution_name: string | null;
  credential_name: string | null;
  type: EducationType | null;
  start_date: string | null;
  end_date: string | null;
}

export interface AdditionalContextEntry {
  id?: number;
  entry: string;
}

export interface UserProfile {
  user_id?: number;
  full_name: string | null;
  contact_email: string | null;
  location: string | null;
  language_preference: string | null;
  requires_sponsorship: boolean | null;
  yoe: number | null;
  social_media: SocialMediaEntry[];
  work_eligibility: WorkEligibilityEntry[];
  skills: SkillEntry[];
  roles: RoleEntry[];
  experiences: ExperienceEntry[];
  educations: EducationEntry[];
  additional_context: AdditionalContextEntry[];
}

export interface UserDocument {
  id: number;
  file_name: string;
  mime_type: string | null;
  size_bytes?: number | null;
  uploaded_at: string;
}

export type ExtractionState = 'idle' | 'uploading' | 'extracting' | 'done' | 'error';

export interface ExtractionStatus {
  state: ExtractionState;
  message?: string;
}

export interface UserSettings {
  curator_job_limit: number | null;
  curator_time_period_minutes: number | null;
  skill_match_threshold: number;
  semantic_text_match_threshold: number;
  compatibility_score_threshold: number;
  time_delay_seconds: number;
}

export type CurationState = 'idle' | 'running' | 'done' | 'error';

export interface CurationStatus {
  state: CurationState;
  message?: string;
  jobs_scraped: number;
  output_file?: string | null;
}

// A fresh, empty profile. Returned as a factory so callers never share a
// mutable reference across resets.
export function createEmptyProfile(): UserProfile {
  return {
    full_name: null,
    contact_email: null,
    location: null,
    language_preference: null,
    requires_sponsorship: null,
    yoe: null,
    social_media: [],
    work_eligibility: [],
    skills: [],
    roles: [],
    experiences: [],
    educations: [],
    additional_context: []
  };
}
