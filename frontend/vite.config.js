import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    build: { outDir: '../backend/dist', emptyOutDir: true },
    server: { 
      port: 5173, 
      proxy: { 
        '/api': env.VITE_API_URL || 'http://localhost:8001', 
        '/uploads': env.VITE_UPLOADS_URL || 'http://localhost:8001' 
      } 
    }
  }
})
