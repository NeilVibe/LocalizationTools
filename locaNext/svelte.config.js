import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),

  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
      precompress: false,
      strict: true
    }),
    prerender: {
      entries: ['*']
    },
    // CRITICAL: Use relative paths for Electron's file:// protocol
    // Without this, paths like /_app/ resolve to C:/_app/ on Windows
    // NOTE: base must be empty, Vite handles the actual asset base path
    paths: {
      relative: true
    }
  }
};

export default config;
