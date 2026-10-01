import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import UserProfilePage from './pages/Profile/UserProfilePage';
import SettingsPage from './pages/Settings/SettingsPage';
import DashboardPage from './pages/Dashboard/DashboardPage';

// Top level app: the shell (nav) is shared by every page, and routing is already
// wired for the pages that are still to come (Settings, Dashboard).
export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Navigate to="/profile" replace />} />
          <Route path="/profile" element={<UserProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="*" element={<Navigate to="/profile" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
