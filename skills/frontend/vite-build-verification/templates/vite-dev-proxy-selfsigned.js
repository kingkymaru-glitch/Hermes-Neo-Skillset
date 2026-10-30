// Known-good Vite dev proxy for a LAN / self-signed-HTTPS backend.
// Drops into vite.config.js. The app MUST request the same-origin path
// (`/s22-api/...`) — not the raw backend URL — for the proxy to carry traffic.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// import cesium from 'vite-plugin-cesium'   // if your app uses Cesium/Resium

const S22_PROXY_TARGET = 'https://192.168.0.84:8080' // self-signed LAN backend

export default defineConfig({
  plugins: [react() /*, cesium() */],
  server: {
    proxy: {
      // Any request to /s22-api/* is rewritten (prefix stripped) and forwarded
      // to the backend. changeOrigin + secure:false defeat the self-signed cert
      // and host-header mismatch; the browser only ever sees same-origin /s22-api.
      '/s22-api': {
        target: S22_PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/s22-api/, ''),
      },
    },
  },
  // OPTIONAL: also proxy in `vite preview` if the built app must reach the backend.
  // preview: { proxy: { '/s22-api': { target: S22_PROXY_TARGET, changeOrigin: true, secure: false, rewrite: (p) => p.replace(/^\/s22-api/, '') } } },
})
