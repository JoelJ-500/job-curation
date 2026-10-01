import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import MenuItem from '@mui/material/MenuItem';
import TextField, { type TextFieldProps } from '@mui/material/TextField';
import {
  Controller,
  type Control,
  type FieldPath,
  type FieldValues,
  type RegisterOptions
} from 'react-hook-form';

export interface SelectOption {
  value: string;
  label: string;
}

interface FormTextFieldProps<T extends FieldValues>
  extends Omit<TextFieldProps, 'name' | 'value' | 'onChange' | 'error' | 'select' | 'children'> {
  // Field names are passed as strings (including array paths such as
  // `experiences.0.company_or_org`) so the profile sections stay readable; the
  // single cast to FieldPath happens here.
  name: string;
  control: Control<T>;
  rules?: RegisterOptions<T, FieldPath<T>>;
  hint?: string;
  numeric?: boolean;
  options?: SelectOption[];
}

// A MUI TextField wired to react-hook-form via Controller. Supports select
// dropdowns and numeric inputs in one place.
export function FormTextField<T extends FieldValues>(props: FormTextFieldProps<T>) {
  const { name, control, rules, hint, numeric, options, ...textFieldProps } = props;

  return (
    <Controller
      name={name as FieldPath<T>}
      control={control}
      rules={rules}
      render={({ field, fieldState }) => (
        <TextField
          {...textFieldProps}
          name={field.name}
          inputRef={field.ref}
          value={field.value ?? ''}
          onBlur={field.onBlur}
          onChange={(event) => {
            const raw = event.target.value;
            field.onChange(numeric ? (raw === '' ? null : Number(raw)) : raw);
          }}
          select={Boolean(options)}
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message ?? hint}
          InputLabelProps={
            textFieldProps.type === 'date' || field.value ? { shrink: true } : undefined
          }
        >
          {options
            ? options.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))
            : null}
        </TextField>
      )}
    />
  );
}

interface FormCheckboxProps<T extends FieldValues> {
  name: string;
  control: Control<T>;
  label: string;
}

export function FormCheckbox<T extends FieldValues>({ name, control, label }: FormCheckboxProps<T>) {
  return (
    <Controller
      name={name as FieldPath<T>}
      control={control}
      render={({ field }) => (
        <FormControlLabel
          control={
            <Checkbox
              checked={Boolean(field.value)}
              inputRef={field.ref}
              onChange={(event) => field.onChange(event.target.checked)}
            />
          }
          label={label}
        />
      )}
    />
  );
}
