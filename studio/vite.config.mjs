import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  base: process.env.VITE_DEMO_MODE === 'true' ? '/SyncShot/' : '/',
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:4310' },
  },
  build: {
    rollupOptions: {
      input: {
        studio: fileURLToPath(new URL('./index.html', import.meta.url)),
        jobs: fileURLToPath(new URL('./angular/index.html', import.meta.url)),
      },
    },
  },
});
