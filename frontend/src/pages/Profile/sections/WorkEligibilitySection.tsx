import Stack from '@mui/material/Stack';
import { useFieldArray, type Control } from 'react-hook-form';
import {
  FormTextField,
  type SelectOption
} from '../../../components/common/FormFields';
import RepeatableSection from '../../../components/common/RepeatableSection';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

const ELIGIBILITY_TYPES: SelectOption[] = [
  { value: 'citizenship', label: 'Citizenship' },
  { value: 'work_visa', label: 'Work visa' },
  { value: 'residency', label: 'Residency' }
];

interface WorkEligibilitySectionProps {
  control: Control<UserProfile>;
}

export default function WorkEligibilitySection({ control }: WorkEligibilitySectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'work_eligibility' });

  return (
    <SectionCard
      title="Work eligibility"
      description="Citizenships, work visas, and residencies you hold."
    >
      <RepeatableSection
        rows={fields}
        addLabel="Add eligibility"
        removeLabel="Remove eligibility"
        emptyText="No work eligibility added yet."
        onAdd={() => append({ country_name: '', type: 'citizenship' })}
        onRemove={remove}
        renderRow={(index) => (
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <FormTextField
              name={`work_eligibility.${index}.country_name`}
              control={control}
              label="Country"
              fullWidth
            />
            <FormTextField
              name={`work_eligibility.${index}.type`}
              control={control}
              label="Type"
              options={ELIGIBILITY_TYPES}
              fullWidth
            />
          </Stack>
        )}
      />
    </SectionCard>
  );
}
