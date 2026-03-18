<script>
  /**
   * CommandPalette - Global Ctrl+K entity search modal (Phase 40)
   *
   * Glassmorphism overlay with debounced search against dictionary-lookup API.
   * Arrow keys navigate results, Enter navigates to Codex, Escape closes.
   */
  import { onDestroy } from "svelte";
  import { api } from "$lib/api/client.js";
  import { goToCodex } from "$lib/stores/navigation.js";
  import { currentApp, currentView } from "$lib/stores/app.js";
  import { fly, fade } from "svelte/transition";
  import { cubicOut } from "svelte/easing";
  import { Search, Close } from "carbon-icons-svelte";

  // Svelte 5 Runes state
  let isOpen = $state(false);
  let query = $state('');
  let results = $state([]);
  let selectedIndex = $state(0);
  let isSearching = $state(false);

  // Refs
  let inputRef = $state(null);
  let debounceTimer = null; // NOT $state — used only in $effect, not rendered

  onDestroy(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
  });

  // Keyboard shortcut: Ctrl+K / Cmd+K
  $effect(() => {
    function handleKeydown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) {
          closeModal();
        } else {
          openModal();
        }
        return;
      }

      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        closeModal();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
      } else if (e.key === 'Enter' && results.length > 0) {
        e.preventDefault();
        selectResult(results[selectedIndex]);
      }
    }

    document.addEventListener('keydown', handleKeydown);
    return () => document.removeEventListener('keydown', handleKeydown);
  });

  // Debounced search on query change
  $effect(() => {
    const q = query; // track only query
    // Use untracked timeout to avoid effect_update_depth_exceeded
    if (debounceTimer) clearTimeout(debounceTimer);

    if (!q || q.trim().length === 0) {
      // Direct assignments outside async are fine since query is the only tracked dep
      results = [];
      selectedIndex = 0;
      isSearching = false;
      return;
    }

    isSearching = true;
    const timer = setTimeout(async () => {
      try {
        const response = await api.request('/api/ldm/gamedata/dictionary-lookup', {
          method: 'POST',
          body: JSON.stringify({ text: q.trim(), top_k: 8, threshold: 0.3 })
        });
        // Only update if query hasn't changed during fetch
        if (query === q) {
          results = response.results || [];
          selectedIndex = 0;
        }
      } catch {
        if (query === q) results = [];
      } finally {
        if (query === q) isSearching = false;
      }
    }, 200);
    debounceTimer = timer;
  });

  function openModal() {
    isOpen = true;
    // Focus input after DOM update
    requestAnimationFrame(() => {
      inputRef?.focus();
    });
  }

  function closeModal() {
    isOpen = false;
    query = '';
    results = [];
    selectedIndex = 0;
    isSearching = false;
    if (debounceTimer) clearTimeout(debounceTimer);
    // Restore focus to main content for keyboard accessibility
    requestAnimationFrame(() => {
      const main = document.querySelector('[role="main"]') || document.querySelector('main');
      main?.focus();
    });
  }

  function selectResult(result) {
    if (!result) return;
    // Navigate to Codex with search query
    currentApp.set('ldm');
    currentView.set('app');
    goToCodex(result.source);
    closeModal();
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  }

  function getMatchBadgeClass(matchType) {
    switch (matchType) {
      case 'exact': return 'badge-exact';
      case 'similar': return 'badge-similar';
      case 'fuzzy': return 'badge-fuzzy';
      default: return '';
    }
  }
</script>

{#if isOpen}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div
    class="palette-backdrop"
    onclick={handleBackdropClick}
    transition:fade={{ duration: 150 }}
  >
    <div
      class="palette-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      transition:fly={{ y: -8, duration: 150, easing: cubicOut }}
    >
      <!-- Search Input -->
      <div class="palette-search">
        <div class="search-icon">
          <Search size={16} />
        </div>
        <input
          bind:this={inputRef}
          bind:value={query}
          type="text"
          placeholder="Search entities..."
          class="palette-input"
          aria-label="Search entities"
          autocomplete="off"
          spellcheck="false"
        />
        {#if query}
          <button class="clear-btn" onclick={() => { query = ''; inputRef?.focus(); }} aria-label="Clear search">
            <Close size={14} />
          </button>
        {/if}
      </div>

      <!-- Results -->
      <div class="palette-results" role="listbox" aria-label="Search results">
        {#if query.trim().length === 0}
          <div class="palette-empty">
            <Search size={20} />
            <span>Type to search entities...</span>
          </div>
        {:else if isSearching}
          <div class="palette-empty">
            <span>Searching...</span>
          </div>
        {:else if results.length === 0}
          <div class="palette-empty">
            <Search size={20} />
            <span>No matches found</span>
          </div>
        {:else}
          {#each results as result, i (result.source || i)}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div
              class="palette-result"
              class:selected={i === selectedIndex}
              role="option"
              tabindex="-1"
              aria-selected={i === selectedIndex}
              onclick={() => selectResult(result)}
              onmouseenter={() => { selectedIndex = i; }}
            >
              <div class="result-main">
                <span class="result-source">{result.source}</span>
                <span class="result-badge {getMatchBadgeClass(result.match_type)}">{result.match_type}</span>
              </div>
              {#if result.target}
                <div class="result-target">{result.target}</div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>

      <!-- Keyboard hints -->
      <div class="palette-hints">
        <span><kbd>↑↓</kbd> navigate</span>
        <span><kbd>↵</kbd> select</span>
        <span><kbd>esc</kbd> close</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .palette-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 9500;
    display: flex;
    justify-content: center;
    align-items: flex-start;
  }

  .palette-modal {
    margin-top: 15vh;
    max-width: 560px;
    width: 90vw;
    background: rgba(26, 26, 26, 0.95);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(212, 154, 92, 0.2);
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* Search input area */
  .palette-search {
    position: relative;
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .search-icon {
    position: absolute;
    left: 1rem;
    color: var(--cds-text-03);
    display: flex;
    align-items: center;
    pointer-events: none;
  }

  .palette-input {
    width: 100%;
    height: 48px;
    background: var(--cds-field-01);
    border: none;
    padding: 0 2.5rem 0 2.75rem;
    font-size: 1rem;
    color: var(--cds-text-01);
    outline: none;
  }

  .palette-input::placeholder {
    color: var(--cds-text-04);
  }

  .clear-btn {
    position: absolute;
    right: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--cds-text-03);
    cursor: pointer;
    opacity: 0.6;
    transition: opacity 0.15s;
  }

  .clear-btn:hover {
    opacity: 1;
  }

  /* Results list */
  .palette-results {
    max-height: 320px;
    overflow-y: auto;
    padding: 4px;
  }

  .palette-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem 1rem;
    color: var(--cds-text-03);
    font-size: 0.875rem;
  }

  .palette-result {
    padding: 0.625rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.1s;
    margin-bottom: 2px;
  }

  .palette-result:hover,
  .palette-result.selected {
    background: rgba(212, 154, 92, 0.12);
  }

  .result-main {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .result-source {
    font-weight: 500;
    color: var(--cds-text-01);
    font-size: 0.875rem;
  }

  .result-badge {
    font-size: 0.6875rem;
    padding: 2px 8px;
    border-radius: 10px;
    background: var(--cds-layer-02);
    color: var(--cds-text-03);
    flex-shrink: 0;
  }

  .result-badge.badge-exact {
    background: rgba(36, 161, 72, 0.15);
    color: #24a148;
  }

  .result-badge.badge-similar {
    background: rgba(212, 154, 92, 0.15);
    color: #d49a5c;
  }

  .result-target {
    font-size: 0.8125rem;
    color: var(--cds-text-03);
    margin-top: 2px;
    padding-left: 0;
  }

  /* Keyboard hints */
  .palette-hints {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    border-top: 1px solid var(--cds-border-subtle-01);
    font-size: 0.75rem;
    color: var(--cds-text-04);
  }

  .palette-hints kbd {
    font-family: inherit;
    font-size: 0.6875rem;
    padding: 1px 4px;
    border-radius: 3px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    color: var(--cds-text-03);
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .palette-backdrop,
    .palette-modal {
      transition: none;
    }
  }
</style>
