import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// 개발 서버(npm run dev)에서는 /api 요청을 로컬 백엔드(uvicorn)로 전달합니다.
// 배포(nginx)에서는 nginx가 같은 역할을 합니다.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.BACKEND_URL || 'http://192.168.0.179:80', changeOrigin: true },
    },
  },
});
