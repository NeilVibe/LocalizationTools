import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173,
    strictPort: true
  },
  optimizeDeps: {
    include: ['carbon-components-svelte', 'carbon-icons-svelte']
  }
});
