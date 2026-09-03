import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          // m3e-* 是 @m3e/web 的 Web Components，不作为 Vue 组件解析
          isCustomElement: tag => tag.startsWith('m3e-'),
        },
      },
    }),
    vuetify({ autoImport: true }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      }
    }
  }
})
