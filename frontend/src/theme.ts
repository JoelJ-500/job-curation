import { createTheme } from '@mui/material/styles';

// Single app theme, shared by every page (Profile, Settings, Dashboard).
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#2f5fde' },
    background: { default: '#f5f6f8' }
  },
  shape: { borderRadius: 8 },
  typography: {
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 }
  }
});
