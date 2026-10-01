import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

// Placeholder for the Settings page (thresholds, curator run params, time delay).
// The route and layout already exist so the page can be filled in later.
export default function SettingsPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h5">Settings</Typography>
      <Alert severity="info">
        Coming soon: skill match threshold, semantic text match threshold, compatibility score
        threshold, curator time period / job limit, and per-job time delay.
      </Alert>
    </Stack>
  );
}
