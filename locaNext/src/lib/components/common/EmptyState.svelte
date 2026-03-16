<script>
  /**
   * EmptyState — Centered icon + headline + description + optional CTA button.
   * Uses Carbon Button for the CTA.
   */
  import { Button } from "carbon-components-svelte";

  let { icon: Icon = undefined, headline, description = undefined, ctaLabel = undefined, onaction = undefined } = $props();
</script>

<div class="empty-state">
  {#if Icon}
    <div class="empty-state__icon">
      <svelte:component this={Icon} size={48} />
    </div>
  {/if}
  <p class="empty-state__headline">{headline}</p>
  {#if description}
    <p class="empty-state__description">{description}</p>
  {/if}
  {#if ctaLabel && onaction}
    <Button kind="tertiary" size="small" on:click={onaction}>{ctaLabel}</Button>
  {/if}
</div>

<style>
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 3rem 1rem;
    text-align: center;
  }

  .empty-state__icon {
    color: var(--cds-text-03);
  }

  .empty-state__headline {
    font-size: 1rem;
    font-weight: 500;
    color: var(--cds-text-01);
    margin: 0;
  }

  .empty-state__description {
    font-size: 0.875rem;
    color: var(--cds-text-03);
    margin: 0;
    max-width: 320px;
  }
</style>
