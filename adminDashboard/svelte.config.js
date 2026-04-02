import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),

  kit: {
    adapter: adapter({
      fallback: 'index.html'
    }),
    paths: {
      // When bundled, served from FastAPI at /dashboard/
      // In dev mode (npm run dev), this is ignored (uses root /)
      base: process.env.DASHBOARD_BASE_PATH || ''
    }
  }
};

export default config;
