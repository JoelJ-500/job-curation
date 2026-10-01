import Stack from '@mui/material/Stack';
import { useFieldArray, type Control } from 'react-hook-form';
import {
  FormTextField,
  type SelectOption
} from '../../../components/common/FormFields';
import RepeatableSection from '../../../components/common/RepeatableSection';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

const SKILL_TYPES: SelectOption[] = [
  { value: '', label: 'Unspecified' },
  { value: 'prog_language', label: 'Programming language' },
  { value: 'framework', label: 'Framework' },
  { value: 'tool', label: 'Tool' },
  { value: 'methodology', label: 'Methodology' },
  { value: 'other', label: 'Other' }
];

interface SkillsSectionProps {
  control: Control<UserProfile>;
}

export default function SkillsSection({ control }: SkillsSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'skills' });

  return (
    <SectionCard
      title="Skills"
      description="Tools, languages, frameworks, and methodologies you can be matched on."
    >
      <RepeatableSection
        rows={fields}
        addLabel="Add skill"
        removeLabel="Remove skill"
        emptyText="No skills added yet."
        onAdd={() => append({ name: '', type: '' })}
        onRemove={remove}
        renderRow={(index) => (
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <FormTextField name={`skills.${index}.name`} control={control} label="Skill" fullWidth />
            <FormTextField
              name={`skills.${index}.type`}
              control={control}
              label="Type"
              options={SKILL_TYPES}
              fullWidth
            />
          </Stack>
        )}
      />
    </SectionCard>
  );
}
