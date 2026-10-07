import { apiRequest } from './client';
import type { UserSettings } from '../types/profile';

// Curator settings (thresholds + how many postings to gather per run).
export const settingsApi = {
  getSettings: () => apiRequest<UserSettings>('/settings'),
  saveSettings: (settings: UserSettings) =>
    apiRequest<UserSettings>('/settings', { method: 'PUT', body: JSON.stringify(settings) })
};
