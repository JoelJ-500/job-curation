import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

// Placeholder for the Main Dashboard (curated jobs + recommended resumes).
export default function DashboardPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h5">Dashboard</Typography>
      <Alert severity="info">
        Coming soon: curated job postings ranked by compatibility, each with its generated
        resume and a direct link to apply.
      </Alert>
    </Stack>
  );
}
