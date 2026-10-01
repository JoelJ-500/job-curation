import { apiRequest } from './client';
import { mockProfileApi } from './mock/mockAdapter';
import type { ExtractionStatus, UserDocument, UserProfile } from '../types/profile';

// The data layer for the user profile. Two implementations share this interface:
// a real HTTP adapter (used once the backend exists) and a mock adapter (used
// now, before the LangChain agent is built). Switched via VITE_USE_MOCK_API.
export interface ProfileApi {
  getProfile(): Promise<UserProfile>;
  saveProfile(profile: UserProfile): Promise<UserProfile>;
  listDocuments(): Promise<UserDocument[]>;
  uploadDocuments(files: File[]): Promise<UserDocument[]>;
  deleteDocument(id: number): Promise<void>;
  startExtraction(): Promise<ExtractionStatus>;
  getStatus(): Promise<ExtractionStatus>;
}

const httpProfileApi: ProfileApi = {
  getProfile: () => apiRequest<UserProfile>('/profile'),
  saveProfile: (profile) =>
    apiRequest<UserProfile>('/profile', { method: 'PUT', body: JSON.stringify(profile) }),
  listDocuments: () => apiRequest<UserDocument[]>('/profile/documents'),
  uploadDocuments: (files) => {
    const form = new FormData();
    files.forEach((file) => form.append('files', file));
    return apiRequest<UserDocument[]>('/profile/documents', { method: 'POST', body: form });
  },
  deleteDocument: (id) => apiRequest<void>(`/profile/documents/${id}`, { method: 'DELETE' }),
  startExtraction: () => apiRequest<ExtractionStatus>('/profile/extract', { method: 'POST' }),
  getStatus: () => apiRequest<ExtractionStatus>('/profile/status')
};

const useMockApi = (import.meta.env.VITE_USE_MOCK_API ?? 'true') !== 'false';

export const isUsingMockApi = useMockApi;

export const profileApi: ProfileApi = useMockApi ? mockProfileApi : httpProfileApi;
