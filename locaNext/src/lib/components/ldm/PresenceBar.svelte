<script>
  import { Tag, Tooltip } from "carbon-components-svelte";
  import { User, UserMultiple, View } from "carbon-icons-svelte";
  import { fileViewers, viewerCount, ldmConnected } from "$lib/stores/ldm.js";

  // Get initials from username
  function getInitials(username) {
    if (!username) return "?";
    return username
      .split(/[\s._-]/)
      .map(part => part[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }

  // Get avatar color based on username
  function getAvatarColor(username) {
    const colors = [
      "#0f62fe", // Blue
      "#8a3ffc", // Purple
      "#24a148", // Green
      "#f1c21b", // Yellow
      "#fa4d56", // Red
      "#007d79", // Teal
      "#ba4e00", // Orange
    ];
    const hash = (username || "").split("").reduce((a, c) => a + c.charCodeAt(0), 0);
    return colors[hash % colors.length];
  }
</script>

<div class="presence-bar" class:connected={$ldmConnected}>
  <div class="presence-indicator">
    <View size={16} />
    <span class="viewer-count">{$viewerCount}</span>
    <span class="label">viewing</span>
  </div>

  {#if $fileViewers.length > 0}
    <div class="avatars">
      {#each $fileViewers.slice(0, 5) as viewer (viewer.user_id)}
        <Tooltip triggerText="" direction="bottom">
          <div
            class="avatar"
            style="background-color: {getAvatarColor(viewer.username)}"
          >
            {getInitials(viewer.username)}
          </div>
          <svelte:fragment slot="body">
            <p>{viewer.username}</p>
          </svelte:fragment>
        </Tooltip>
      {/each}

      {#if $fileViewers.length > 5}
        <div class="avatar more">
          +{$fileViewers.length - 5}
        </div>
      {/if}
    </div>
  {/if}

  {#if !$ldmConnected}
    <Tag type="outline" size="sm">Offline</Tag>
  {/if}
</div>

<style>
  .presence-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.25rem 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
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
  }

  .viewer-count {
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .label {
    color: var(--cds-text-02);
  }

  .avatars {
    display: flex;
    align-items: center;
    margin-left: 0.25rem;
  }

  .avatar {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.625rem;
    font-weight: 600;
    color: white;
    margin-left: -6px;
    border: 2px solid var(--cds-background);
    cursor: default;
  }

  .avatar:first-child {
    margin-left: 0;
  }

  .avatar.more {
    background: var(--cds-layer-accent-01);
    color: var(--cds-text-01);
    font-size: 0.5625rem;
  }
</style>
