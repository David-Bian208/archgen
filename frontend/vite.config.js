import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 支持环境变量配置 API 地址
// 本地开发：VITE_API_URL=http://localhost:8001 npm run dev
// 阿里云部署：VITE_API_URL=http://8.130.148.166:8001 npm run dev
const apiUrl = process.env.VITE_API_URL || 'http://localhost:8001'

export default defineConfig({
  plugins: [vue()],
  base: './',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: apiUrl,
        changeOrigin: true,
      },
    },
  },
})
