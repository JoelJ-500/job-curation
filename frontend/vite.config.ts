import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server config. `/api` requests are proxied to the Python backend so the
// frontend and backend run on separate ports without CORS issues.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
