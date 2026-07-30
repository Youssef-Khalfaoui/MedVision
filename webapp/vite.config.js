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
      },
      '/ws': {
        target: 'ws://localhost:8003',
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
      },
      '/ws': {
        target: 'ws://backend:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
