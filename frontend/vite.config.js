import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const apiTarget = process.env.VITE_API_TARGET || process.env.BACKEND_URL || 'http://127.0.0.1:8000'
const frontendPort = Number(process.env.FRONTEND_PORT || process.env.VITE_FRONTEND_PORT || 5174)
const projectRoot = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/echarts')) {
            return 'echarts'
          }
          if (id.includes('node_modules/vue') || id.includes('node_modules/@vue')) {
            return 'vue-vendor'
          }
          if (id.includes('node_modules/vue-router')) {
            return 'vue-vendor'
          }
          if (id.includes('node_modules/lucide-vue-next')) {
            return 'icons'
          }
        },
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    fs: {
      allow: [projectRoot],
    },
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        // 实时分析 SSE 可能超过默认代理超时
        timeout: 0,
        proxyTimeout: 0,
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0,
      },
    },
  },
})
