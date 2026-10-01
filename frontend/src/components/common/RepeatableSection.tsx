import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

interface RepeatableSectionProps {
  rows: { id: string }[];
  onAdd: () => void;
  onRemove: (index: number) => void;
  addLabel: string;
  emptyText: string;
  removeLabel?: string;
  renderRow: (index: number) => ReactNode;
}

// Generic "add / remove rows" list wrapper used by every repeatable section
// (social media, skills, experience, ...).
export default function RepeatableSection({
  rows,
  onAdd,
  onRemove,
  addLabel,
  emptyText,
  removeLabel = 'Remove item',
  renderRow
}: RepeatableSectionProps) {
  return (
    <Stack spacing={2}>
      {rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {emptyText}
        </Typography>
      ) : (
        rows.map((row, index) => (
          <Stack key={row.id} direction="row" spacing={1} alignItems="flex-start">
            <Box sx={{ flexGrow: 1 }}>{renderRow(index)}</Box>
            <IconButton
              aria-label={removeLabel}
              color="error"
              size="small"
              onClick={() => onRemove(index)}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Stack>
        ))
      )}
      <Box>
        <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={onAdd}>
          {addLabel}
        </Button>
      </Box>
    </Stack>
  );
}
