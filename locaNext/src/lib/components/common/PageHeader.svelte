<script>
  /**
   * PageHeader — Consistent page title bar with icon + action slot.
   * Uses v3.3 design tokens from app.css.
   */
  let { icon: Icon = undefined, title, children } = $props();
</script>

<header class="page-header">
  <div class="page-header__left">
    {#if Icon}
      <Icon size={20} />
    {/if}
    <h1>{title}</h1>
  </div>
  {#if children}
    <div class="page-header__actions">
      {@render children()}
    </div>
  {/if}
</header>

<style>
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: var(--page-header-height);
    padding: var(--page-header-padding);
    background: var(--cds-layer-01);
    border-bottom: var(--panel-border);
    flex-shrink: 0;
  }

  .page-header__left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--cds-text-01);
  }

  .page-header__left h1 {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--cds-text-01);
    margin: 0;
    line-height: 1;
  }

  .page-header__actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
</style>
