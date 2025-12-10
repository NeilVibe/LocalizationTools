<script>
  // DEBUG: This should log immediately when the module loads
  console.log("[DEBUG] +page.svelte module loading...");

  import { currentApp, currentView } from "$lib/stores/app.js";
  import XLSTransfer from "$lib/components/apps/XLSTransfer.svelte";
  import QuickSearch from "$lib/components/apps/QuickSearch.svelte";
  import KRSimilar from "$lib/components/apps/KRSimilar.svelte";
  import LDM from "$lib/components/apps/LDM.svelte";
  import TaskManager from "$lib/components/TaskManager.svelte";
  // Welcome component removed - LDM is now the default app
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  console.log("[DEBUG] +page.svelte imports complete");

  // SvelteKit page props (consumed to silence unused warnings)
  export let data;
  export let form;
  export let params;
  // Consume props to avoid unused warnings
  $: void data;
  $: void form;
  $: void params;

  import { get } from 'svelte/store';

  // DEBUG: Expose page's view of stores for testing (set immediately, not in onMount)
  // Use get() since this runs during initialization, not in reactive context
  if (typeof window !== 'undefined') {
    window.pageDebug = {
      getStoreValues: () => ({
        currentApp: get(currentApp),
        currentView: get(currentView)
      }),
      setApp: (appId) => {
        currentApp.set(appId);
        currentView.set('app');
        return { success: true, app: appId };
      }
    };
    console.log("[DEBUG] window.pageDebug exposed immediately");
  }

  // Use reactive statements for logging (the actual rendering uses $store syntax)
  $: console.log("[DEBUG] View changed:", $currentView);
  $: console.log("[DEBUG] App changed:", $currentApp);
  $: logger.info("Navigation state", { view: $currentView, app: $currentApp });

  onMount(() => {
    console.log("[DEBUG] +page.svelte onMount");
    logger.component("+page.svelte", "mounted");
    logger.info("Page state", { view: $currentView, app: $currentApp });
  });
</script>

<div class="main-container">
  {#if $currentView === 'tasks'}
    <TaskManager />
  {:else if $currentApp === 'xlstransfer'}
    <XLSTransfer />
  {:else if $currentApp === 'quicksearch'}
    <QuickSearch />
  {:else if $currentApp === 'krsimilar'}
    <KRSimilar />
  {:else}
    <!-- LDM is the default app - no Welcome page needed -->
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
