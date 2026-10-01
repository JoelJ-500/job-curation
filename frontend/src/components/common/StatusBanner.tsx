import Alert from '@mui/material/Alert';
import type { ExtractionState } from '../../types/profile';

interface StatusBannerProps {
  state: ExtractionState;
  message?: string;
}

// Shows upload/extraction feedback above the form. Renders nothing when idle.
export default function StatusBanner({ state, message }: StatusBannerProps) {
  if (state === 'idle') {
    return null;
  }

  const severity = state === 'error' ? 'error' : state === 'done' ? 'success' : 'info';
  return <Alert severity={severity}>{message ?? 'Working…'}</Alert>;
}
