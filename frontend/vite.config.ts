import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// D-013: /api 요청은 백엔드(127.0.0.1:8000)로 넘긴다. CORS 는 쓰지 않는다.
const apiProxy = {
  '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
}

export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
})
