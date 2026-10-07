import { useCallback, useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import SectionCard from '../../components/common/SectionCard';
import { settingsApi } from '../../api/settings';
import { curationApi } from '../../api/curation';
import type { CurationState, UserSettings } from '../../types/profile';

const POLL_INTERVAL_MS = 3000;
const MAX_POLLS = 300;

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

// Settings page: how many postings to gather per curation run, plus the control
// to start scraping. Thresholds are placeholders until the filtering steps exist.
export default function SettingsPage() {
  const [jobLimit, setJobLimit] = useState(10);
  const [semanticThreshold, setSemanticThreshold] = useState(0.5);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | undefined>();
  const [curationState, setCurationState] = useState<CurationState>('idle');
  const [curationMessage, setCurationMessage] = useState<string | undefined>();
  const [jobsScraped, setJobsScraped] = useState(0);

  useEffect(() => {
    settingsApi
      .getSettings()
      .then((settings) => {
        setJobLimit(settings.curator_job_limit ?? 10);
        setSemanticThreshold(settings.semantic_text_match_threshold ?? 0.5);
      })
      .catch(() => undefined);
  }, []);

  const saveSettings = useCallback(async () => {
    const current = await settingsApi.getSettings();
    const updated: UserSettings = {
      ...current,
      curator_job_limit: jobLimit,
      curator_time_period_minutes: null,
      semantic_text_match_threshold: semanticThreshold
    };
    return settingsApi.saveSettings(updated);
  }, [jobLimit, semanticThreshold]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(undefined);
    try {
      await saveSettings();
      setSaveMessage('Settings saved.');
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : 'Could not save settings.');
    } finally {
      setSaving(false);
    }
  };

  const followCuration = useCallback(async () => {
    setCurationState('running');
    setCurationMessage('Scraping job postings from HiringCafe and Eluta…');

    for (let attempt = 0; attempt < MAX_POLLS; attempt += 1) {
      await delay(POLL_INTERVAL_MS);
      const status = await curationApi.getStatus();
      setJobsScraped(status.jobs_scraped ?? 0);

      if (status.state === 'done') {
        setCurationState('done');
        setCurationMessage(status.message ?? 'Curation complete.');
        return;
      }
      if (status.state === 'error') {
        setCurationState('error');
        setCurationMessage(status.message ?? 'Curation failed.');
        return;
      }
    }

    setCurationState('error');
    setCurationMessage('Curation is taking longer than expected.');
  }, []);

  const handleStart = async () => {
    setSaveMessage(undefined);
    try {
      await saveSettings();
    } catch {
      // Keep going: the run will use the last saved limit.
    }

    try {
      const status = await curationApi.startCuration();
      setJobsScraped(status.jobs_scraped ?? 0);
      await followCuration();
    } catch (error) {
      setCurationState('error');
      setCurationMessage(error instanceof Error ? error.message : 'Could not start curation.');
    }
  };

  const busy = curationState === 'running';

  return (
    <Stack spacing={3}>
      <Typography variant="h5">Settings</Typography>

      <SectionCard
        title="Curator run"
        description="Choose how many job postings to gather per run, then start curating."
      >
        <Stack spacing={2} sx={{ maxWidth: 380 }}>
          <TextField
            label="Job postings per run"
            type="number"
            value={jobLimit}
            onChange={(event) => setJobLimit(Math.max(1, Number(event.target.value) || 1))}
            helperText="The scraper stops once this many postings are gathered."
            disabled={busy}
          />
          <Stack direction="row" spacing={2}>
            <Button variant="outlined" onClick={handleSave} disabled={saving || busy}>
              Save settings
            </Button>
            <Button variant="contained" onClick={handleStart} disabled={busy}>
              {busy ? 'Curating…' : 'Start curation'}
            </Button>
          </Stack>
          {saveMessage ? <Alert severity="info">{saveMessage}</Alert> : null}
        </Stack>
      </SectionCard>

      <SectionCard
        title="Curation status"
        description="Live progress while the curator scrapes both job sites."
      >
        {curationState === 'idle' ? (
          <Alert severity="info">
            Idle. Set the number of postings and press “Start curation”.
          </Alert>
        ) : (
          <Alert
            severity={
              curationState === 'error' ? 'error' : curationState === 'done' ? 'success' : 'info'
            }
          >
            {curationMessage ?? 'Working…'}
            {jobsScraped > 0 ? ` (${jobsScraped} postings so far)` : ''}
          </Alert>
        )}
      </SectionCard>

      <SectionCard
        title="Filter thresholds"
        description="Postings whose semantic similarity to your profile falls below this are discarded before scoring."
      >
        <Stack spacing={2} sx={{ maxWidth: 380 }}>
          <TextField
            label="Semantic Text Match threshold"
            type="number"
            value={semanticThreshold}
            onChange={(event) =>
              setSemanticThreshold(Math.min(1, Math.max(0, Number(event.target.value) || 0)))
            }
            helperText="0 to 1 (default 0.5). Higher = fewer, more relevant postings."
            disabled={busy}
          />
        </Stack>
      </SectionCard>
    </Stack>
  );
}

