import type { UserProfile } from '../types/profile';

// Converts empty strings coming from the form into null so the saved payload
// matches the database (which uses NULL and CHECK constraints, e.g. the
// education `type` enum). Also pins experience ordering to the row index.
export function normalizeProfileForSave(profile: UserProfile): UserProfile {
  const nullIfEmpty = (value: string | null): string | null => (value ? value : null);

  return {
    ...profile,
    full_name: nullIfEmpty(profile.full_name),
    contact_email: nullIfEmpty(profile.contact_email),
    location: nullIfEmpty(profile.location),
    language_preference: nullIfEmpty(profile.language_preference),
    social_media: profile.social_media.map((entry) => ({
      ...entry,
      username: nullIfEmpty(entry.username)
    })),
    skills: profile.skills.map((skill) => ({
      ...skill,
      type: nullIfEmpty(skill.type)
    })),
    experiences: profile.experiences.map((experience, index) => ({
      ...experience,
      company_or_org: nullIfEmpty(experience.company_or_org),
      role: nullIfEmpty(experience.role),
      start_date: nullIfEmpty(experience.start_date),
      end_date: nullIfEmpty(experience.end_date),
      sort_order: index,
      highlights: experience.highlights.filter((highlight) => highlight.trim() !== '')
    })),
    educations: profile.educations.map((education) => ({
      ...education,
      institution_name: nullIfEmpty(education.institution_name),
      credential_name: nullIfEmpty(education.credential_name),
      type: education.type ? education.type : null,
      start_date: nullIfEmpty(education.start_date),
      end_date: nullIfEmpty(education.end_date)
    }))
  };
}
