import Stack from '@mui/material/Stack';
import { useFieldArray, type Control } from 'react-hook-form';
import {
  FormTextField,
  type SelectOption
} from '../../../components/common/FormFields';
import RepeatableSection from '../../../components/common/RepeatableSection';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

const EDUCATION_TYPES: SelectOption[] = [
  { value: '', label: 'Unspecified' },
  { value: 'associate', label: 'Associate' },
  { value: 'bachelors', label: "Bachelor's" },
  { value: 'masters', label: "Master's" },
  { value: 'phd', label: 'PhD' },
  { value: 'diploma', label: 'Diploma' },
  { value: 'certificate', label: 'Certificate' }
];

interface EducationSectionProps {
  control: Control<UserProfile>;
}

export default function EducationSection({ control }: EducationSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'educations' });

  return (
    <SectionCard title="Education & credentials" description="Degrees, diplomas, and certifications.">
      <RepeatableSection
        rows={fields}
        addLabel="Add education"
        removeLabel="Remove education"
        emptyText="No education added yet."
        onAdd={() =>
          append({
            institution_name: '',
            credential_name: '',
            type: null,
            start_date: '',
            end_date: ''
          })
        }
        onRemove={remove}
        renderRow={(index) => (
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <FormTextField
                name={`educations.${index}.institution_name`}
                control={control}
                label="Institution"
                fullWidth
              />
              <FormTextField
                name={`educations.${index}.credential_name`}
                control={control}
                label="Credential"
                hint="e.g. Computer Science, Red Seal"
                fullWidth
              />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <FormTextField
                name={`educations.${index}.type`}
                control={control}
                label="Type"
                options={EDUCATION_TYPES}
                fullWidth
              />
              <FormTextField
                name={`educations.${index}.start_date`}
                control={control}
                label="Start date"
                type="date"
                fullWidth
              />
              <FormTextField
                name={`educations.${index}.end_date`}
                control={control}
                label="End date"
                type="date"
                hint="Leave blank if in progress"
                fullWidth
              />
            </Stack>
          </Stack>
        )}
      />
    </SectionCard>
  );
}
