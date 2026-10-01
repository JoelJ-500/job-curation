import Stack from '@mui/material/Stack';
import { useFieldArray, type Control } from 'react-hook-form';
import { FormTextField } from '../../../components/common/FormFields';
import RepeatableSection from '../../../components/common/RepeatableSection';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

interface SocialMediaSectionProps {
  control: Control<UserProfile>;
}

export default function SocialMediaSection({ control }: SocialMediaSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'social_media' });

  return (
    <SectionCard title="Social media" description="LinkedIn, GitHub, portfolio, and other profiles.">
      <RepeatableSection
        rows={fields}
        addLabel="Add social profile"
        removeLabel="Remove social profile"
        emptyText="No social profiles yet."
        onAdd={() => append({ platform: '', username: '', link: '' })}
        onRemove={remove}
        renderRow={(index) => (
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <FormTextField
              name={`social_media.${index}.platform`}
              control={control}
              label="Platform"
              fullWidth
            />
            <FormTextField
              name={`social_media.${index}.username`}
              control={control}
              label="Username"
              fullWidth
            />
            <FormTextField
              name={`social_media.${index}.link`}
              control={control}
              label="Link"
              fullWidth
            />
          </Stack>
        )}
      />
    </SectionCard>
  );
}
