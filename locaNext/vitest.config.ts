import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';

export default defineConfig({
  plugins: [sveltekit(), svelteTesting()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest-setup.js'],
    include: ['tests/**/*.test.{js,mjs,ts}', 'tests/**/*.svelte.test.ts'],
    exclude: ['tests/**/*.spec.*', 'node_modules/**'],
    coverage: {
      provider: 'v8',
      include: [
        'src/lib/utils/tagDetector.js',
        // Future plans will add:
        // 'src/lib/utils/statusColors.ts',
        // 'src/lib/components/ldm/TagText.svelte',
      ],
      reporter: ['text', 'html'],
      thresholds: {
        statements: 80,
        branches: 70,
        functions: 80,
        lines: 80,
      },
    },
  },
});
