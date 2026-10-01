import { useFieldArray, type Control } from 'react-hook-form';
import { FormTextField } from '../../../components/common/FormFields';
import RepeatableSection from '../../../components/common/RepeatableSection';
import SectionCard from '../../../components/common/SectionCard';
import type { UserProfile } from '../../../types/profile';

interface RolesSectionProps {
  control: Control<UserProfile>;
}

export default function RolesSection({ control }: RolesSectionProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'roles' });

  return (
    <SectionCard
      title="Roles"
      description="Job titles the curator should search for on your behalf."
    >
      <RepeatableSection
        rows={fields}
        addLabel="Add role"
        removeLabel="Remove role"
        emptyText="No roles added yet."
        onAdd={() => append({ name: '' })}
        onRemove={remove}
        renderRow={(index) => (
          <FormTextField
            name={`roles.${index}.name`}
            control={control}
            label="Role"
            fullWidth
          />
        )}
      />
    </SectionCard>
  );
}
