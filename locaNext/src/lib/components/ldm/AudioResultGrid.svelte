<script>
  /**
   * AudioResultGrid.svelte - Center panel result grid for Audio Codex
   *
   * Battle-tested patterns from language data grid:
   * - Virtual scroll for 100K+ rows (only visible rows in DOM)
   * - Content-aware row heights (auto-size based on text length)
   * - Column resize bars (drag between columns)
   * - $state.raw-compatible (items from parent via props)
   *
   * MDG-exact: EventName | KOR Script | ENG Script with play/stop button,
   * arrow key navigation, selected row highlight, has_wem indicator.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { PlayFilledAlt, StopFilledAlt } from "carbon-icons-svelte";
  import { onDestroy } from "svelte";

  const MIN_ROW_HEIGHT = 37;
  const OVERSCAN = 10;
  const CHAR_PER_LINE = 40; // Estimated chars per line for height calculation
  const LINE_HEIGHT = 18; // px per line of text
  const ROW_PADDING = 18; // vertical padding in row

  let {
    items = [],
    selectedEvent = null,
    playingEvent = null,
    onselect = () => {},
    onplay = () => {},
    onstop = () => {},
  } = $props();

  let scrollContainer = $state(null);
  let scrollTop = $state(0);
  let containerHeight = $state(600);
  let containerWidth = $state(800);

  // Column widths (percentage of flex space for KOR/ENG, fixed px for others)
  let eventColWidth = $state(200); // px
  let krWidthPercent = $state(50); // % of remaining flex space

  // Column resize state
  let isResizing = $state(false);
  let resizeColumn = $state(null);
  let resizeStartX = $state(0);
  let resizeStartValue = $state(0);

  // ── Content-aware row heights (same pattern as language data grid) ──
  // Estimate height based on longest text in KOR/ENG columns
  function estimateRowHeight(item) {
    const krLen = item.script_kr?.length || 0;
    const engLen = item.script_eng?.length || 0;
    const maxLen = Math.max(krLen, engLen);

    if (maxLen <= CHAR_PER_LINE) return MIN_ROW_HEIGHT;

    const lines = Math.ceil(maxLen / CHAR_PER_LINE);
    return Math.max(MIN_ROW_HEIGHT, lines * LINE_HEIGHT + ROW_PADDING);
  }

  // Build cumulative height array (computed once when items change)
  let cumHeights = $derived.by(() => {
    const arr = new Float64Array(items.length + 1);
    arr[0] = 0;
    for (let i = 0; i < items.length; i++) {
      arr[i + 1] = arr[i] + estimateRowHeight(items[i]);
    }
    return arr;
  });

  let totalHeight = $derived(items.length > 0 ? cumHeights[items.length] : 0);

  // Binary search for row at scroll position
  function findRowAtPosition(pos) {
    let lo = 0, hi = items.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >>> 1;
      if (cumHeights[mid + 1] <= pos) lo = mid + 1;
      else if (cumHeights[mid] > pos) hi = mid - 1;
      else return mid;
    }
    return Math.min(lo, items.length - 1);
  }

  let startIndex = $derived(Math.max(0, findRowAtPosition(scrollTop) - OVERSCAN));
  let endIndex = $derived(
    Math.min(items.length, findRowAtPosition(scrollTop + containerHeight) + OVERSCAN + 1)
  );
  let visibleItems = $derived(items.slice(startIndex, endIndex));
  let offsetY = $derived(items.length > 0 ? cumHeights[startIndex] : 0);

  function handleScroll() {
    if (scrollContainer) {
      scrollTop = scrollContainer.scrollTop;
    }
  }

  // Measure container on mount and resize
  $effect(() => {
    if (!scrollContainer) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerHeight = entry.contentRect.height;
        containerWidth = entry.contentRect.width;
      }
    });
    observer.observe(scrollContainer);
    return () => observer.disconnect();
  });

  // ── Column resize handlers (same pattern as CellRenderer) ──
  function startResize(column, event) {
    event.preventDefault();
    isResizing = true;
    resizeColumn = column;
    resizeStartX = event.clientX;
    if (column === 'event') {
      resizeStartValue = eventColWidth;
    } else if (column === 'kr') {
      resizeStartValue = krWidthPercent;
    }
    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
  }

  function handleResize(event) {
    if (!isResizing) return;
    const deltaX = event.clientX - resizeStartX;

    if (resizeColumn === 'event') {
      eventColWidth = Math.max(100, Math.min(400, resizeStartValue + deltaX));
    } else if (resizeColumn === 'kr') {
      const flexWidth = containerWidth - 40 - eventColWidth - 24; // play + event + padding
      const deltaPercent = (deltaX / flexWidth) * 100;
      krWidthPercent = Math.max(20, Math.min(80, resizeStartValue + deltaPercent));
    }
  }

  function stopResize() {
    isResizing = false;
    resizeColumn = null;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
  }

  // ── Row interaction ──
  function handlePlayClick(eventName, event) {
    event.stopPropagation();
    if (playingEvent === eventName) {
      onstop();
    } else {
      onplay(eventName);
    }
  }

  function handleKeyDown(event) {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    event.preventDefault();

    const currentIndex = items.findIndex((i) => i.event_name === selectedEvent);
    let nextIndex;

    if (event.key === "ArrowUp") {
      nextIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
    } else {
      nextIndex = currentIndex >= items.length - 1 ? 0 : currentIndex + 1;
    }

    const nextEvent = items[nextIndex]?.event_name;
    if (nextEvent) {
      onselect(nextEvent);
      scrollToIndex(nextIndex);
    }
  }

  function scrollToIndex(index) {
    if (!scrollContainer || index < 0 || index >= items.length) return;
    const rowTop = cumHeights[index];
    const rowBottom = cumHeights[index + 1];
    const viewTop = scrollContainer.scrollTop;
    const viewBottom = viewTop + containerHeight;

    if (rowTop < viewTop) {
      scrollContainer.scrollTop = rowTop;
    } else if (rowBottom > viewBottom) {
      scrollContainer.scrollTop = rowBottom - containerHeight;
    }
  }

  // Compute flex widths for columns
  let krFlexStyle = $derived(`flex: 0 0 ${krWidthPercent}%`);
  let engFlexStyle = $derived(`flex: 0 0 ${100 - krWidthPercent}%`);

  // Cleanup document listeners on unmount (if user navigates away mid-resize)
  onDestroy(() => {
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
  });
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="result-grid"
  class:resizing={isResizing}
  role="grid"
  aria-label="Audio entries ({items.length} total)"
  tabindex="0"
  onkeydown={handleKeyDown}
>
  <!-- Header with resize bars -->
  <div class="grid-header" role="row">
    <span class="col col-play"></span>
    <span class="col col-event" role="columnheader" style="width: {eventColWidth}px">
      EventName
    </span>
    <!-- Resize bar: EventName ↔ KOR -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <span class="resize-bar" onmousedown={(e) => startResize('event', e)}></span>
    <span class="col col-kr" role="columnheader" style={krFlexStyle}>
      KOR Script
    </span>
    <!-- Resize bar: KOR ↔ ENG -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <span class="resize-bar" onmousedown={(e) => startResize('kr', e)}></span>
    <span class="col col-eng" role="columnheader" style={engFlexStyle}>
      ENG Script
    </span>
  </div>

  <!-- Virtual scroll container -->
  <div
    class="grid-body"
    bind:this={scrollContainer}
    onscroll={handleScroll}
  >
    <!-- Total height spacer -->
    <div style="height: {totalHeight}px; position: relative;">
      <!-- Visible rows positioned absolutely -->
      <div style="position: absolute; top: {offsetY}px; left: 0; right: 0;">
        {#each visibleItems as item (item.event_name)}
          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <div
            class="grid-row"
            class:selected={selectedEvent === item.event_name}
            class:playing={playingEvent === item.event_name}
            role="row"
            style="height: {estimateRowHeight(item)}px"
            data-event={item.event_name}
            onclick={() => onselect(item.event_name)}
            onkeydown={(e) => { if (e.key === "Enter") onselect(item.event_name); }}
          >
            <!-- Play/Stop button -->
            <span class="col col-play">
              <button
                class="play-btn"
                class:is-playing={playingEvent === item.event_name}
                onclick={(e) => handlePlayClick(item.event_name, e)}
                disabled={!item.has_wem}
                aria-label={playingEvent === item.event_name ? "Stop" : "Play"}
              >
                {#if playingEvent === item.event_name}
                  <StopFilledAlt size={16} />
                {:else}
                  <PlayFilledAlt size={16} />
                {/if}
              </button>
            </span>

            <!-- Event name + wem dot -->
            <span class="col col-event" style="width: {eventColWidth}px">
              <span class="wem-dot" class:has-wem={item.has_wem}></span>
              <span class="event-text">{item.event_name}</span>
            </span>

            <!-- KOR Script (auto-wrap for content-aware height) -->
            <span class="col col-kr col-text" style={krFlexStyle}>
              {item.script_kr || ""}
            </span>

            <!-- ENG Script (auto-wrap for content-aware height) -->
            <span class="col col-eng col-text" style={engFlexStyle}>
              {item.script_eng || ""}
            </span>
          </div>
        {/each}
      </div>
    </div>

    {#if items.length === 0}
      <div class="no-results">No audio entries found</div>
    {/if}
  </div>
</div>

<style>
  .result-grid {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
    outline: none;
  }

  .result-grid.resizing { cursor: col-resize; user-select: none; }

  .grid-header {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    background: var(--cds-layer-02);
    border-bottom: 2px solid var(--cds-border-subtle-01);
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    flex-shrink: 0;
  }

  .grid-body {
    flex: 1;
    overflow-y: auto;
  }

  .grid-row {
    display: flex;
    align-items: flex-start;
    padding: 8px 12px;
    min-height: 37px;
    box-sizing: border-box;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    cursor: pointer;
    transition: background 0.1s;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .grid-row:hover { background: var(--cds-layer-hover-01); }
  .grid-row.selected { background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.1)); color: var(--cds-text-01); }
  .grid-row.playing { background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.08)); }

  .col { overflow: hidden; text-overflow: ellipsis; }
  .col-play { width: 40px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; padding-top: 2px; }
  .col-event { flex-shrink: 0; display: flex; align-items: center; gap: 6px; font-family: monospace; font-size: 0.75rem; white-space: nowrap; }
  .col-kr { min-width: 0; color: var(--cds-text-01); }
  .col-eng { min-width: 0; color: var(--cds-text-03); font-size: 0.75rem; }

  /* Content-aware text columns: wrap instead of truncate */
  .col-text {
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.4;
    padding: 0 8px;
    overflow: hidden;
  }

  /* Resize bars between columns */
  .resize-bar {
    width: 4px;
    flex-shrink: 0;
    cursor: col-resize;
    background: transparent;
    transition: background 0.15s;
    align-self: stretch;
    margin: 0 1px;
  }

  .resize-bar:hover { background: var(--cds-interactive-01, #0f62fe); }
  .resize-bar:active { background: var(--cds-interactive-01, #0f62fe); }

  .play-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: none;
    background: var(--cds-interactive-01, #0f62fe);
    color: var(--cds-text-on-color, #fff);
    cursor: pointer;
    transition: all 0.15s;
  }

  .play-btn:hover { background: var(--cds-hover-primary, #0353e9); }
  .play-btn:disabled { background: var(--cds-disabled-02); color: var(--cds-disabled-03); cursor: not-allowed; }
  .play-btn.is-playing { background: var(--cds-support-error, #da1e28); }
  .play-btn.is-playing:hover { background: var(--cds-hover-danger, #b81921); }

  .wem-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--cds-text-03);
    flex-shrink: 0;
  }

  .wem-dot.has-wem { background: var(--cds-support-success, #24a148); }

  .event-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .no-results {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 16px;
    color: var(--cds-text-03);
    font-size: 0.875rem;
  }
</style>
