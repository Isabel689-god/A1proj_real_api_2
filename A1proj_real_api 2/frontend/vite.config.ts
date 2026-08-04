import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: [
      {
        find: /^element-plus$/,
        replacement: fileURLToPath(new URL('./node_modules/element-plus/lib/index.js', import.meta.url)),
      },
    ],
  },
  server: {
    proxy: {
      '/dashboard/overview': 'http://127.0.0.1:8000',
      '/kg': 'http://127.0.0.1:8000',
      '/knowledge': 'http://127.0.0.1:8000',
      '/user': 'http://127.0.0.1:8000',
      '/chat': 'http://127.0.0.1:8000',
      '/monitor': 'http://127.0.0.1:8000',
      '/animation': 'http://127.0.0.1:8000',
      '/maintenance': 'http://127.0.0.1:8000',
    },
  },
})
