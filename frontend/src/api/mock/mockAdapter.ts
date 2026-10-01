import {
  createEmptyProfile,
  type ExtractionStatus,
  type UserDocument,
  type UserProfile
} from '../../types/profile';
import type { ProfileApi } from '../profile';

// In-memory (localStorage backed) stand-in for the real backend, so the profile
// page is fully usable before the LangChain agent exists. Uploading documents
// simulates an extraction run that fills the form with a sample profile.

const PROFILE_KEY = 'job-curation.mock.profile';
const DOCUMENTS_KEY = 'job-curation.mock.documents';

const EXTRACTION_DELAY_MS = 2500;

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage errors (e.g. private browsing).
  }
}

let nextDocumentId = Date.now();
let status: ExtractionStatus = { state: 'idle' };

// What the agent "finds" in the uploaded documents. Overwrites the form data,
// matching the design note that re-uploading refills all form data.
const SAMPLE_PROFILE: UserProfile = {
  full_name: 'Jordan Avery',
  contact_email: 'jordan.avery@example.com',
  location: 'Toronto, ON, Canada',
  language_preference: 'English',
  requires_sponsorship: false,
  yoe: 6,
  social_media: [
    { platform: 'LinkedIn', username: 'jordan-avery', link: 'https://www.linkedin.com/in/jordan-avery' },
    { platform: 'GitHub', username: 'jordanavery', link: 'https://github.com/jordanavery' }
  ],
  work_eligibility: [
    { country_name: 'Canada', type: 'citizenship' },
    { country_name: 'United States', type: 'work_visa' }
  ],
  skills: [
    { name: 'Python', type: 'prog_language' },
    { name: 'TypeScript', type: 'prog_language' },
    { name: 'PostgreSQL', type: 'tool' },
    { name: 'LangChain', type: 'framework' }
  ],
  roles: [
    { name: 'Backend Engineer' },
    { name: 'Machine Learning Engineer' }
  ],
  experiences: [
    {
      company_or_org: 'Northwind Analytics',
      role: 'Senior Backend Engineer',
      start_date: '2021-03-01',
      end_date: null,
      sort_order: 0,
      highlights: [
        'Engineered a job-matching service in Python that processes 1M+ postings per day.',
        'Reduced API latency by 40% by introducing PostgreSQL indexing and caching.'
      ]
    },
    {
      company_or_org: 'Brightpath Software',
      role: 'Backend Engineer',
      start_date: '2018-06-01',
      end_date: '2021-02-28',
      sort_order: 1,
      highlights: [
        'Built and maintained REST APIs serving 200k monthly active users.'
      ]
    }
  ],
  educations: [
    {
      institution_name: 'University of Toronto',
      credential_name: 'Computer Science',
      type: 'bachelors',
      start_date: '2014-09-01',
      end_date: '2018-05-01'
    }
  ],
  additional_context: [
    { entry: 'AWS Certified Solutions Architect - Associate (2022).' },
    { entry: 'Presenter at PyCon Canada 2023 on scalable data pipelines.' }
  ]
};

async function runExtraction(): Promise<void> {
  status = { state: 'extracting', message: 'Reading your documents and building your profile…' };
  await delay(EXTRACTION_DELAY_MS);
  writeJson(PROFILE_KEY, SAMPLE_PROFILE);
  status = { state: 'done', message: 'Profile updated from your documents.' };
}

export const mockProfileApi: ProfileApi = {
  async getProfile() {
    await delay(300);
    return readJson<UserProfile>(PROFILE_KEY, createEmptyProfile());
  },

  async saveProfile(profile) {
    await delay(300);
    writeJson(PROFILE_KEY, profile);
    return profile;
  },

  async listDocuments() {
    await delay(200);
    return readJson<UserDocument[]>(DOCUMENTS_KEY, []);
  },

  async uploadDocuments(files) {
    await delay(500);
    const existing = readJson<UserDocument[]>(DOCUMENTS_KEY, []);
    const created: UserDocument[] = files.map((file) => ({
      id: nextDocumentId++,
      file_name: file.name,
      mime_type: file.type || null,
      size_bytes: file.size,
      uploaded_at: new Date().toISOString()
    }));
    writeJson(DOCUMENTS_KEY, [...created, ...existing]);

    // Fire-and-forget: the UI follows progress through getStatus().
    void runExtraction();

    return created;
  },

  async deleteDocument(id) {
    await delay(200);
    const remaining = readJson<UserDocument[]>(DOCUMENTS_KEY, []).filter((doc) => doc.id !== id);
    writeJson(DOCUMENTS_KEY, remaining);
  },

  async startExtraction() {
    void runExtraction();
    return status;
  },

  async getStatus() {
    return status;
  }
};
