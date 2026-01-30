<script>
  import { Tag } from "carbon-components-svelte";
  import { View } from "carbon-icons-svelte";
  import { fileViewers, viewerCount, ldmConnected } from "$lib/stores/ldm.js";
  import { user } from "$lib/stores/app.js";

  // UI-042/UI-045: Simplified presence bar - just "X viewing" with hover tooltip
  // Build viewer list for tooltip - filter out invalid usernames
  // Filter out: undefined, null, empty, "Unknown", "?", "LOCAL"
  const isValidUsername = (name) => {
    if (!name) return false;
    const invalid = ["Unknown", "?", "LOCAL", "undefined", "null", ""];
    return !invalid.includes(name);
  };

  // Svelte 5: Use $derived instead of $: for reactive computations
  let viewerNames = $derived(
    $fileViewers
      .map(v => v.username || v.user_id || "")
      .filter(isValidUsername)
  );

  // Get current user's display name with robust fallback
  let currentUsername = $derived(
    isValidUsername($user?.username)
      ? $user.username
      : ($user?.user_id && isValidUsername($user.user_id) ? $user.user_id : "You")
  );

  // If no valid viewers from WebSocket, show current user
  let viewerList = $derived(
    viewerNames.length > 0 ? viewerNames.join(", ") : currentUsername
  );
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
