import { apiRequest } from './client';
import type { CurationStatus } from '../types/profile';

// Job curation: start a scrape run and poll its status.
export const curationApi = {
  startCuration: () => apiRequest<CurationStatus>('/curation/start', { method: 'POST' }),
  getStatus: () => apiRequest<CurationStatus>('/curation/status')
};
