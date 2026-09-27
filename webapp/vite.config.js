import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite config — dev server on :5173 (allowed by backend CORS)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      // Proxy API calls to the FastAPI backend during dev
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        // Required: the exam-progress WebSocket (/api/exams/{id}/progress)
        // goes through this same path. Without ws:true the upgrade request is
        // not proxied and the app silently falls back to 2s polling.
        ws: true,
      },
    },
  },
  preview: {
    host: true,
    proxy: {
      // Proxy API calls to the FastAPI backend when served via `vite preview` (prod container)
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        // Same as above: without ws:true, real-time progress is broken in the
        // Docker deployment and the UI degrades to polling.
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
