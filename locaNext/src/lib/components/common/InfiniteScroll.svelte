<script>
  /**
   * InfiniteScroll — IntersectionObserver sentinel that fires onloadmore
   * when scrolled near, with $effect cleanup.
   */
  let { onloadmore, loading = false, hasMore = true, loadingSnippet = undefined } = $props();

  let sentinel = $state(null);

  $effect(() => {
    if (!sentinel || !hasMore || loading) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !loading && hasMore) {
          onloadmore();
        }
      },
      { rootMargin: '200px' }
    );

    observer.observe(sentinel);

    return () => observer.disconnect();
  });
</script>

{#if hasMore}
  <div bind:this={sentinel} aria-hidden="true" class="infinite-scroll-sentinel"></div>
{/if}

{#if loading}
  {#if loadingSnippet}
    {@render loadingSnippet()}
  {/if}
{/if}

<style>
  .infinite-scroll-sentinel {
    min-height: 1px;
    width: 100%;
  }
</style>
