import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // ws: true is required for the /api/v1/ws/prices WebSocket upgrade to pass
      // through the dev server to FastAPI instead of being treated as plain HTTP.
      '/api': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
    },
  },
});
