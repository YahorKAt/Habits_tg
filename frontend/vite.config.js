import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  },
  build: {
    // Оптимизация сборки
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'recharts': ['recharts'],
          'date-fns': ['date-fns']
        }
      }
    },
    // Увеличиваем лимит предупреждений о размере чанков
    chunkSizeWarningLimit: 1000
  },
  optimizeDeps: {
    // Предварительная оптимизация зависимостей
    include: ['react', 'react-dom', 'date-fns']
  }
})