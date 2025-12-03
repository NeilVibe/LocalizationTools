<script>
  import { currentApp, currentView } from "$lib/stores/app.js";
  import XLSTransfer from "$lib/components/apps/XLSTransfer.svelte";
  import QuickSearch from "$lib/components/apps/QuickSearch.svelte";
  import TaskManager from "$lib/components/TaskManager.svelte";
  import Welcome from "$lib/components/Welcome.svelte";

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

  currentView.subscribe(value => {
    view = value;
  });

  currentApp.subscribe(value => {
    app = value;
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
