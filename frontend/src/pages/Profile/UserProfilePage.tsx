import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { profileApi } from '../../api/profile';
import { createEmptyProfile, type UserProfile } from '../../types/profile';
import { normalizeProfileForSave } from '../../utils/profile';
import AdditionalContextSection from './sections/AdditionalContextSection';
import BasicInfoSection from './sections/BasicInfoSection';
import DocumentsSection from './sections/DocumentsSection';
import EducationSection from './sections/EducationSection';
import ExperienceSection from './sections/ExperienceSection';
import RolesSection from './sections/RolesSection';
import SkillsSection from './sections/SkillsSection';
import SocialMediaSection from './sections/SocialMediaSection';
import WorkEligibilitySection from './sections/WorkEligibilitySection';

// The User Profile page: upload documents to auto-fill the form (the LangChain
// agent does the extraction), then edit and save any field by hand.
export default function UserProfilePage() {
  const { control, handleSubmit, reset, formState } = useForm<UserProfile>({
    defaultValues: createEmptyProfile()
  });
  const [baseline, setBaseline] = useState<UserProfile>(createEmptyProfile());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    profileApi
      .getProfile()
      .then((profile) => {
        if (!active) return;
        reset(profile);
        setBaseline(profile);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setLoadError(error instanceof Error ? error.message : 'Could not load your profile.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [reset]);

  // Called after document extraction fills the profile.
  const handleExtracted = (profile: UserProfile) => {
    reset(profile);
    setBaseline(profile);
    setSaveMessage(null);
  };

  const onSubmit = handleSubmit(async (values) => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const saved = await profileApi.saveProfile(normalizeProfileForSave(values));
      reset(saved);
      setBaseline(saved);
      setSaveMessage('saved');
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : 'Could not save your profile.');
    } finally {
      setSaving(false);
    }
  });

  if (loading) {
    return (
      <Stack alignItems="center" sx={{ py: 8 }}>
        <CircularProgress />
      </Stack>
    );
  }

  return (
    <Stack spacing={3}>
      <div>
        <Typography variant="h5">User profile</Typography>
        <Typography variant="body2" color="text.secondary">
          Upload your documents to auto-fill this profile, then edit anything that looks wrong.
        </Typography>
      </div>

      {loadError ? <Alert severity="error">{loadError}</Alert> : null}
      {saveMessage ? (
        <Alert severity={saveMessage === 'saved' ? 'success' : 'error'}>
          {saveMessage === 'saved' ? 'Profile saved.' : saveMessage}
        </Alert>
      ) : null}

      <DocumentsSection onExtracted={handleExtracted} />

      <form onSubmit={onSubmit} noValidate>
        <Stack spacing={3}>
          <BasicInfoSection control={control} />
          <SocialMediaSection control={control} />
          <WorkEligibilitySection control={control} />
          <SkillsSection control={control} />
          <RolesSection control={control} />
          <ExperienceSection control={control} />
          <EducationSection control={control} />
          <AdditionalContextSection control={control} />

          <Stack direction="row" spacing={2}>
            <Button type="submit" variant="contained" disabled={saving}>
              {saving ? 'Saving…' : 'Save profile'}
            </Button>
            <Button
              variant="outlined"
              onClick={() => reset(baseline)}
              disabled={!formState.isDirty || saving}
            >
              Discard changes
            </Button>
          </Stack>
        </Stack>
      </form>
    </Stack>
  );
}
