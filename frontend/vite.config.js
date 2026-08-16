import { defineConfig } from 'vite'
export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 3001,
    allowedHosts: ['n8n.algo-dynamix.ai','screen.finnverify.com','aml.finnverify.com','payments.finnverify.com'],
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/health': { target: 'http://localhost:8001', changeOrigin: true },
      '/dashboard': { target: 'http://localhost:8001', changeOrigin: true },
      '/invoices': { target: 'http://localhost:8001', changeOrigin: true },
      '/accounting': { target: 'http://localhost:8001', changeOrigin: true },
      '/auth': { target: 'http://localhost:8001', changeOrigin: true },
    }
  }
})
