<script>
  import { Tag } from "carbon-components-svelte";
  import { View } from "carbon-icons-svelte";
  import { fileViewers, viewerCount, ldmConnected } from "$lib/stores/ldm.js";
  import { user } from "$lib/stores/app.js";

  // UI-042: Simplified presence bar - just "X viewing" with hover tooltip
  // Build viewer list for tooltip - filter out undefined/empty usernames
  $: viewerNames = $fileViewers
    .map(v => v.username || v.user_id || "Unknown")
    .filter(name => name && name !== "Unknown");

  // If no viewers from WebSocket yet, show current user
  $: viewerList = viewerNames.length > 0
    ? viewerNames.join(", ")
    : ($user?.username || "You");
</script>

<!-- UI-042: Simplified - just "X viewing" with hover tooltip showing viewer names -->
<div class="presence-bar" class:connected={$ldmConnected}>
  <div class="presence-indicator" title={viewerList}>
    <View size={16} />
    <span class="viewer-count">{$viewerCount || 1}</span>
    <span class="label">viewing</span>
  </div>

  {#if !$ldmConnected}
    <Tag type="outline" size="sm">Offline</Tag>
  {/if}
</div>

<style>
  /* UI-042: Simplified presence bar - just text with hover tooltip */
  .presence-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    opacity: 0.7;
    transition: opacity 0.2s;
  }

  .presence-bar.connected {
    opacity: 1;
  }

  .presence-indicator {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    cursor: help;
  }

  .viewer-count {
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .label {
    color: var(--cds-text-02);
  }
</style>
