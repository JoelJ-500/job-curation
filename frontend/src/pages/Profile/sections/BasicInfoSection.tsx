import Stack from '@mui/material/Stack';
import type { Control } from 'react-hook-form';
import { FormCheckbox, FormTextField } from '../../../components/common/FormFields';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

interface BasicInfoSectionProps {
  control: Control<UserProfile>;
}

export default function BasicInfoSection({ control }: BasicInfoSectionProps) {
  return (
    <SectionCard
      title="Basic information"
      description="Core details extracted from your documents. Edit anything that looks wrong."
    >
      <Stack spacing={2}>
        <FormTextField name="full_name" control={control} label="Full name" />
        <FormTextField
          name="contact_email"
          control={control}
          label="Contact email"
          type="email"
          rules={{
            pattern: {
              value: /^[^@\s]+@[^@\s]+\.[^@\s]+$/,
              message: 'Enter a valid email address'
            }
          }}
        />
        <FormTextField
          name="location"
          control={control}
          label="Location"
          hint="City, region, or country"
        />
        <FormTextField name="language_preference" control={control} label="Language preference" />
        <FormTextField
          name="yoe"
          control={control}
          label="Years of experience"
          type="number"
          numeric
          rules={{
            min: { value: 0, message: 'Years of experience cannot be negative' }
          }}
        />
        <FormCheckbox
          name="requires_sponsorship"
          control={control}
          label="Requires sponsorship to work"
        />
      </Stack>
    </SectionCard>
  );
}
