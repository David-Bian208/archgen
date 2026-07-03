import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3014,
    host: '0.0.0.0',
    strictPort: false,
    watch: {
      usePolling: true,
      interval: 1000,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8941',
        changeOrigin: true,
        // SSE 端点不做任何响应处理，直接透传
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req) => {
            if (req.url?.includes('/generate_slots')) {
              // SSE: 不缓冲，直接透传
              proxyRes.headers['content-type'] = 'text/event-stream'
              proxyRes.headers['cache-control'] = 'no-cache'
              proxyRes.headers['connection'] = 'keep-alive'
            }
          })
        },
      }
    }
  }
})
