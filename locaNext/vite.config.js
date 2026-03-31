import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  // CRITICAL: Use relative paths for Electron's file:// protocol
  // Without this, paths like /_app/ resolve to C:/_app/ on Windows
  base: './',
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      // Proxy audio streams to avoid ORB (Opaque Resource Blocking) on cross-origin media
      '/api/ldm/mapdata/audio/stream': {
        target: 'http://localhost:8888',
        changeOrigin: true,
      },
      '/api/ldm/codex/audio/stream': {
        target: 'http://localhost:8888',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ['carbon-components-svelte', 'carbon-icons-svelte']
  }
});
