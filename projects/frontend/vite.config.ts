import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    // Some crypto libraries look for global/process in browser
    'global': 'globalThis',
  }
})
