import DeleteIcon from '@mui/icons-material/Delete';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useEffect, useRef, useState } from 'react';
import { profileApi } from '../../../api/profile';
import SectionCard from '../../../components/common/SectionCard';
import StatusBanner from '../../../components/common/StatusBanner';
import type { ExtractionState, UserDocument, UserProfile } from '../../../types/profile';

const POLL_INTERVAL_MS = 1000;
const MAX_POLLS = 30;

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

function formatBytes(bytes?: number | null): string {
  if (!bytes) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value < 10 && unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`;
}

interface DocumentsSectionProps {
  onExtracted: (profile: UserProfile) => void;
}

// Document upload + extraction feedback. Adding documents triggers the agent;
// the UI polls for status and refreshes the form when the run finishes.
export default function DocumentsSection({ onExtracted }: DocumentsSectionProps) {
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [state, setState] = useState<ExtractionState>('idle');
  const [message, setMessage] = useState<string | undefined>();
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    profileApi
      .listDocuments()
      .then(setDocuments)
      .catch(() => undefined);
  }, []);

  const followExtraction = async () => {
    setState('extracting');
    setMessage('Extracting your profile from the uploaded documents…');

    for (let attempt = 0; attempt < MAX_POLLS; attempt += 1) {
      await delay(POLL_INTERVAL_MS);
      const status = await profileApi.getStatus();

      if (status.state === 'done') {
        const profile = await profileApi.getProfile();
        onExtracted(profile);
        setState('done');
        setMessage('Profile updated from your documents. Review the form and save your changes.');
        return;
      }

      if (status.state === 'error') {
        setState('error');
        setMessage(status.message ?? 'Extraction failed.');
        return;
      }
    }

    setState('error');
    setMessage('Extraction is taking longer than expected.');
  };

  const handleFiles = async (fileList: FileList | null) => {
    const files = fileList ? Array.from(fileList) : [];
    if (files.length === 0) return;

    setState('uploading');
    setMessage(`Uploading ${files.length} document${files.length > 1 ? 's' : ''}…`);

    try {
      const created = await profileApi.uploadDocuments(files);
      setDocuments((previous) => [...created, ...previous]);
      await followExtraction();
    } catch (error) {
      setState('error');
      setMessage(error instanceof Error ? error.message : 'Upload failed.');
    }
  };

  const handleDelete = async (id: number) => {
    await profileApi.deleteDocument(id);
    setDocuments((previous) => previous.filter((document) => document.id !== id));
  };

  const handleRerun = async () => {
    await profileApi.startExtraction();
    await followExtraction();
  };

  const busy = state === 'uploading' || state === 'extracting';

  return (
    <SectionCard
      title="Documents"
      description="Upload resumes, notes, code files, or portfolio images. Adding documents re-runs the extraction agent."
    >
      <Stack spacing={2}>
        <StatusBanner state={state} message={message} />

        <Box
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            void handleFiles(event.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          sx={{
            border: '2px dashed',
            borderColor: dragging ? 'primary.main' : 'divider',
            borderRadius: 2,
            p: 3,
            textAlign: 'center',
            cursor: busy ? 'progress' : 'pointer',
            bgcolor: dragging ? 'action.hover' : 'transparent'
          }}
        >
          <UploadFileIcon color="primary" />
          <Typography variant="body1">Drag &amp; drop files here, or click to browse</Typography>
          <Typography variant="caption" color="text.secondary">
            PDF, DOCX, TXT, MD, images, and code files
          </Typography>
          <input
            ref={inputRef}
            type="file"
            multiple
            hidden
            onChange={(event) => {
              void handleFiles(event.target.files);
              event.target.value = '';
            }}
          />
        </Box>

        {documents.length > 0 ? (
          <List dense>
            {documents.map((document) => (
              <ListItem
                key={document.id}
                divider
                secondaryAction={
                  <IconButton
                    edge="end"
                    aria-label="Remove document"
                    onClick={() => void handleDelete(document.id)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                }
              >
                <ListItemText
                  primary={document.file_name}
                  secondary={formatBytes(document.size_bytes)}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No documents uploaded yet.
          </Typography>
        )}

        <Box>
          <Button
            variant="outlined"
            size="small"
            onClick={() => void handleRerun()}
            disabled={documents.length === 0 || busy}
          >
            Re-run extraction
          </Button>
        </Box>
      </Stack>
    </SectionCard>
  );
}
