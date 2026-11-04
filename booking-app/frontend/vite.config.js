import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const target = 'http://127.0.0.1:8000'
const proxy = {
  '/api': {
    target,
    changeOrigin: true,
    configure(proxyServer) {
      proxyServer.on('proxyReq', (proxyReq, req) => {
        // Translate only same-origin browser requests to the Python server's origin.
        // Foreign origins remain foreign and are rejected by its existing checks.
        if (req.headers.origin === `http://${req.headers.host}` && req.headers['sec-fetch-site'] !== 'cross-site') {
          proxyReq.setHeader('Origin', target)
        }
      })
    },
  },
}

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, strictPort: true, proxy },
  preview: { port: 4173, strictPort: true, proxy },
})
