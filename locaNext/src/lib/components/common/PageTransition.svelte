<script>
  /**
   * PageTransition.svelte - Phase 40: Crossfade page transition wrapper
   *
   * Wraps page content with a fade transition keyed on the current page.
   * When currentPage changes, the old content fades out (150ms) and new fades in (150ms)
   * for a 300ms total crossfade effect.
   *
   * Respects prefers-reduced-motion by setting duration to 0.
   */
  import { fade } from 'svelte/transition';
  import { currentPage } from '$lib/stores/navigation.js';

  let { children } = $props();

  // Respect prefers-reduced-motion
  let reducedMotion = $state(false);

  if (typeof window !== 'undefined') {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotion = mql.matches;
    mql.addEventListener('change', (e) => { reducedMotion = e.matches; });
  }

  let duration = $derived(reducedMotion ? 0 : 150);
</script>

{#key $currentPage}
  <div class="page-transition-wrapper" in:fade={{ duration }}>
    {@render children()}
  </div>
{/key}

<style>
  .page-transition-wrapper {
    width: 100%;
    height: 100%;
  }

  @media (prefers-reduced-motion: reduce) {
    .page-transition-wrapper {
      animation-duration: 0ms !important;
    }
  }
</style>
