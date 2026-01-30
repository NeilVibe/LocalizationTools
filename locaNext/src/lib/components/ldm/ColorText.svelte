<script>
  /**
   * ColorText Component
   *
   * Renders text with color tags displayed in actual colors.
   * Example: <PAColor0xffe9bd23>text<PAOldColor> renders "text" in gold.
   */

  import { parseColorTags, hasColorTags } from '$lib/utils/colorParser.js';

  // Svelte 5: Use $props() instead of export let
  let { text = '', className = '' } = $props();

  // Svelte 5: Use $derived for reactive computations
  let segments = $derived(hasColorTags(text) ? parseColorTags(text) : null);
</script>

{#if segments}
  <span class="color-text {className}">
    {#each segments as segment}
      {#if segment.color}
        <span class="colored-segment" style="color: {segment.color}">{segment.text}</span>
      {:else}
        <span class="plain-segment">{segment.text}</span>
      {/if}
    {/each}
  </span>
{:else}
  <span class="color-text {className}">{text}</span>
{/if}

<style>
  .color-text {
    display: inline;
  }

  .colored-segment {
    /* Color is applied via inline style */
  }

  .plain-segment {
    /* Inherits parent color */
  }
</style>
