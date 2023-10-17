import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '~bootstrap': resolve("node_modules/bootstrap"),
      '@': resolve("src"),
      "@client": resolve("typescript_client"),
    }
  },
  server: {
    host: "0.0.0.0",
    proxy: {
        "/api": {
            target: "http://backend:8000",
        },
    },
    watch: {
        usePolling: true,
    },
  },
})
