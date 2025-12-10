<script>
  /**
   * Error page that handles SvelteKit routing failures in Electron.
   *
   * In Electron with file:// protocol, SvelteKit router fails because:
   * - URL is file:///C:/Users/.../index.html
   * - Router tries to match route /C:/Users/.../index.html
   * - No route matches, so "Not found" error
   *
   * This error page renders the main app content instead of an error.
   */
  import { page } from '$app/stores';
  import { currentApp, currentView } from "$lib/stores/app.js";
  import XLSTransfer from "$lib/components/apps/XLSTransfer.svelte";
  import QuickSearch from "$lib/components/apps/QuickSearch.svelte";
  import KRSimilar from "$lib/components/apps/KRSimilar.svelte";
  import LDM from "$lib/components/apps/LDM.svelte";
  import TaskManager from "$lib/components/TaskManager.svelte";
  // Welcome component removed - LDM is now the default app
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  let view;
  let app;

  currentView.subscribe(value => {
    view = value;
  });

  currentApp.subscribe(value => {
    app = value;
  });

  onMount(() => {
    logger.info("+error.svelte acting as main page (Electron file:// workaround)");
  });

  // Log the error for debugging
  $: if ($page.error) {
    console.log("[Electron] SvelteKit routing error (expected in file:// mode):", $page.error.message);
  }
</script>

<!-- Render main app content even though this is technically an error page -->
<div class="main-container">
  {#if view === 'tasks'}
    <TaskManager />
  {:else if app === 'xlstransfer'}
    <XLSTransfer />
  {:else if app === 'quicksearch'}
    <QuickSearch />
  {:else if app === 'krsimilar'}
    <KRSimilar />
  {:else}
    <!-- LDM is the default app -->
    <LDM />
  {/if}
</div>

<style>
  .main-container {
    width: 100%;
    height: 100%;
    overflow-y: auto;
    background: var(--cds-background);
  }
</style>
