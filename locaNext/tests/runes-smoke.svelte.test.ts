import { describe, it, expect } from 'vitest';

describe('Svelte 5 runes smoke test', () => {
  it('$state is accessible in .svelte.test.ts files', () => {
    let count = $state(0);
    expect(count).toBe(0);
    count = 5;
    expect(count).toBe(5);
  });
});
