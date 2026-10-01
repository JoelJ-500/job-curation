import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useFieldArray, type Control } from 'react-hook-form';
import { FormTextField } from '../../../components/common/FormFields';
import RepeatableSection from '../../../components/common/RepeatableSection';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

interface ExperienceSectionProps {
  control: Control<UserProfile>;
}

export default function ExperienceSection({ control }: ExperienceSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'experiences' });

  return (
    <SectionCard
      title="Experience"
      description="Roles and projects. Each role can have several highlight bullets."
    >
      <RepeatableSection
        rows={fields}
        addLabel="Add experience"
        removeLabel="Remove experience"
        emptyText="No experience added yet."
        onAdd={() =>
          append({
            company_or_org: '',
            role: '',
            start_date: '',
            end_date: '',
            sort_order: fields.length,
            highlights: ['']
          })
        }
        onRemove={remove}
        renderRow={(index) => <ExperienceCard control={control} index={index} />}
      />
    </SectionCard>
  );
}

interface ExperienceCardProps {
  control: Control<UserProfile>;
  index: number;
}

function ExperienceCard({ control, index }: ExperienceCardProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    // react-hook-form's FieldArrayPath type only models top-level arrays, so the
    // nested highlights path is asserted here. Runtime behaviour is unaffected.
    name: `experiences.${index}.highlights` as any
  });

  return (
    <Stack spacing={2} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <FormTextField
          name={`experiences.${index}.company_or_org`}
          control={control}
          label="Company / organization"
          fullWidth
        />
        <FormTextField
          name={`experiences.${index}.role`}
          control={control}
          label="Role"
          fullWidth
        />
      </Stack>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <FormTextField
          name={`experiences.${index}.start_date`}
          control={control}
          label="Start date"
          type="date"
          fullWidth
        />
        <FormTextField
          name={`experiences.${index}.end_date`}
          control={control}
          label="End date"
          type="date"
          hint="Leave blank if current"
          fullWidth
        />
      </Stack>
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Highlights
        </Typography>
        <RepeatableSection
          rows={fields}
          addLabel="Add highlight"
          removeLabel="Remove highlight"
          emptyText="No highlights yet."
          onAdd={() => append('')}
          onRemove={remove}
          renderRow={(highlightIndex) => (
            <FormTextField
              name={`experiences.${index}.highlights.${highlightIndex}`}
              control={control}
              label={`Highlight ${highlightIndex + 1}`}
              multiline
              minRows={2}
              fullWidth
            />
          )}
        />
      </Box>
    </Stack>
  );
}
