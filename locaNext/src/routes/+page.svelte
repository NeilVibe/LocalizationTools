<script>
  // DEBUG: This should log immediately when the module loads
  console.log("[DEBUG] +page.svelte module loading...");

  import { currentApp, currentView } from "$lib/stores/app.js";
  import XLSTransfer from "$lib/components/apps/XLSTransfer.svelte";
  import QuickSearch from "$lib/components/apps/QuickSearch.svelte";
  import KRSimilar from "$lib/components/apps/KRSimilar.svelte";
  import LDM from "$lib/components/apps/LDM.svelte";
  import TaskManager from "$lib/components/TaskManager.svelte";
  import Welcome from "$lib/components/Welcome.svelte";
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

  let view;
  let app;

  console.log("[DEBUG] +page.svelte subscribing to stores");

  currentView.subscribe(value => {
    view = value;
    console.log("[DEBUG] View changed:", view);
    logger.info("View changed", { view });
  });

  currentApp.subscribe(value => {
    app = value;
    console.log("[DEBUG] App changed:", app);
    logger.info("App changed", { app });
  });

  onMount(() => {
    console.log("[DEBUG] +page.svelte onMount");
    logger.component("+page.svelte", "mounted");
    logger.info("Page state", { view, app });
  });
</script>

<div class="main-container">
  {#if view === 'tasks'}
    <TaskManager />
  {:else if view === 'app'}
    {#if app === 'xlstransfer'}
      <XLSTransfer />
    {:else if app === 'quicksearch'}
      <QuickSearch />
    {:else if app === 'krsimilar'}
      <KRSimilar />
    {:else if app === 'ldm'}
      <LDM />
    {:else}
      <Welcome />
    {/if}
  {:else}
    <Welcome />
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
