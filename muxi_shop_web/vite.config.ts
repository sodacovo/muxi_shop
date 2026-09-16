import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // 代理所有 API 请求到 Django 后端
      '/user': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/goods': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/cart': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/order': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/address': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/comment': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/pay': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/main_menu': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/sub_menu': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/seckill': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // WebSocket 代理
      '/ws': {
        target: 'ws://127.0.0.1:8666',
        ws: true,
      },
    },
  },
})
