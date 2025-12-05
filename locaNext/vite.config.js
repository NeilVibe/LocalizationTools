import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  // CRITICAL: Use relative paths for Electron's file:// protocol
  // Without this, paths like /_app/ resolve to C:/_app/ on Windows
  base: './',
  server: {
    port: 5173,
    strictPort: true
  },
  optimizeDeps: {
    include: ['carbon-components-svelte', 'carbon-icons-svelte']
  }
});
