import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import commonjs from 'vite-plugin-commonjs'
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    uni(),
  commonjs(),
  ],
  optimizeDeps: {
    include: ['uview-plus'],
  },
  server: {
    proxy: {
      '/api': {
        target: 'https://jkyhobdhqqah.sealoshzh.site',
        changeOrigin: true,
        secure: true,
      },
    },
  },
})
