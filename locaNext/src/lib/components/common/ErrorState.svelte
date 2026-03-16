<script>
  /**
   * ErrorState — Error message display with optional retry button.
   * Uses Carbon WarningAlt icon and Button.
   */
  import { Button } from "carbon-components-svelte";
  import { WarningAlt, Renew } from "carbon-icons-svelte";

  let { message = "Something went wrong", onretry = undefined } = $props();
</script>

<div class="error-state">
  <div class="error-state__icon">
    <WarningAlt size={32} />
  </div>
  <p class="error-state__message">{message}</p>
  {#if onretry}
    <Button kind="ghost" size="small" icon={Renew} onclick={onretry}>Retry</Button>
  {/if}
</div>

<style>
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 2rem;
    text-align: center;
  }

  .error-state__icon {
    color: var(--cds-support-01, #fa4d56);
  }

  .error-state__message {
    font-size: 0.875rem;
    color: var(--cds-text-01);
    margin: 0;
    max-width: 320px;
  }
</style>
