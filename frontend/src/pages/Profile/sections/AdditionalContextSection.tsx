import { useFieldArray, type Control } from 'react-hook-form';
import { FormTextField } from '../../../components/common/FormFields';
import RepeatableSection from '../../../components/common/RepeatableSection';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

interface AdditionalContextSectionProps {
  control: Control<UserProfile>;
}

export default function AdditionalContextSection({ control }: AdditionalContextSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'additional_context' });

  return (
    <SectionCard
      title="Additional context"
      description="Awards, publications, portfolio highlights, and anything else worth surfacing."
    >
      <RepeatableSection
        rows={fields}
        addLabel="Add entry"
        removeLabel="Remove entry"
        emptyText="No additional context yet."
        onAdd={() => append({ entry: '' })}
        onRemove={remove}
        renderRow={(index) => (
          <FormTextField
            name={`additional_context.${index}.entry`}
            control={control}
            label="Entry"
            multiline
            minRows={2}
            fullWidth
          />
        )}
      />
    </SectionCard>
  );
}
