import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const API = process.env.FCV_API_URL ?? 'http://localhost:8100'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5180,
    strictPort: true,
    proxy: {
      '/api': { target: API, changeOrigin: true, ws: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
})
