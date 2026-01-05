<script>
  // Svelte 5: Props with children slot
  let {
    title = '',
    icon = null,
    stat = null,
    label = '',
    expanded = false,
    highlight = false,
    children
  } = $props();

  // Svelte 5: Local reactive state for expanded
  let isExpanded = $state(expanded);

  function toggleExpand() {
    isExpanded = !isExpanded;
  }
</script>

<div class="expandable-card" class:highlight class:expanded={isExpanded}>
  <button class="card-header" onclick={toggleExpand}>
    <div class="header-content">
      {#if icon}
        <div class="card-icon">
          <svelte:component this={icon} size={24} />
        </div>
      {/if}
      <div class="header-info">
        {#if stat !== null}
          <div class="stat-value">{stat}</div>
        {/if}
        <div class="stat-label">{label || title}</div>
      </div>
    </div>
    <div class="expand-indicator" class:rotated={isExpanded}>
      ▼
    </div>
  </button>

  {#if isExpanded}
    <div class="card-body">
      {@render children()}
    </div>
  {/if}
</div>

<style>
  .expandable-card {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    transition: all 0.2s;
    overflow: hidden;
  }

  .expandable-card:hover {
    border-color: #4589ff;
    box-shadow: 0 2px 8px rgba(69, 137, 255, 0.2);
  }

  .expandable-card.highlight {
    border-color: #4589ff;
    background: linear-gradient(135deg, #262626 0%, #2d2d2d 100%);
  }

  .expandable-card.expanded {
    border-color: #78a9ff;
  }

  .card-header {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px;
    background: transparent;
    border: none;
    cursor: pointer;
    color: inherit;
    text-align: left;
  }

  .card-header:hover {
    background: rgba(69, 137, 255, 0.05);
  }

  .header-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .card-icon {
    color: #4589ff;
    display: flex;
    align-items: center;
  }

  .expandable-card.highlight .card-icon {
    color: #ffb000;
  }

  .header-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f4f4f4;
  }

  .stat-label {
    font-size: 0.875rem;
    color: #c6c6c6;
  }

  .expand-indicator {
    color: #8d8d8d;
    font-size: 0.75rem;
    transition: transform 0.2s;
    margin-right: 4px;
  }

  .expand-indicator.rotated {
    transform: rotate(180deg);
  }

  .card-body {
    padding: 0 20px 20px 20px;
    animation: slideDown 0.2s ease-out;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
