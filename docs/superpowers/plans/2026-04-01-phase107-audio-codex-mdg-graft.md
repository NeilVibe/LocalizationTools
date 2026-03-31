# Phase 107: Audio Codex MDG Full Graft — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat-list AudioCodexPage with a full MDG-style 3-panel layout (Export Tree | Result Grid | Audio Player) with exact MDG feature parity.

**Architecture:** State lives in AudioCodexPage (orchestrator). Three child components are stateless, props-driven. A hidden `<audio>` element is controlled programmatically for progress bar. Backend codex routes get `language` query parameter for multi-language audio folder switching.

**Tech Stack:** Svelte 5 (runes), Carbon Components/Icons, FastAPI, MegaIndex D10/D11/D20/D21/C4/C5

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `locaNext/vite.config.js` | Add codex audio stream proxy |
| Modify | `server/tools/ldm/routes/codex_audio.py` | Add `language` param to stream/list/detail endpoints |
| Create | `locaNext/src/lib/components/ldm/AudioExportTree.svelte` | Left panel: category hierarchy sidebar |
| Create | `locaNext/src/lib/components/ldm/AudioResultGrid.svelte` | Center panel: EventName/KOR/ENG grid with play/stop + arrow nav |
| Create | `locaNext/src/lib/components/ldm/AudioPlayerPanel.svelte` | Right panel: player + progress + scripts + metadata |
| Rewrite | `locaNext/src/lib/components/ldm/AudioCodexPage.svelte` | Orchestrator: 3-panel layout, state management, hidden audio element (**keep in `pages/` — this is wrong path, see note**) |
| Rewrite | `locaNext/src/lib/components/pages/AudioCodexPage.svelte` | ← This is the actual path. REWRITE this file. |
| Delete | `locaNext/src/lib/components/ldm/AudioCodexDetail.svelte` | Replaced by AudioPlayerPanel |

**Note:** AudioCodexPage lives at `locaNext/src/lib/components/pages/AudioCodexPage.svelte`, NOT in `ldm/`. New child components go in `ldm/` following existing pattern.

---

## Wave 1: Bug Fixes + Backend (Plan 1)

### Task 1: Vite Proxy Fix

**Files:**
- Modify: `locaNext/vite.config.js`

- [ ] **Step 1: Add codex audio stream proxy**

In `locaNext/vite.config.js`, add a second proxy entry inside the `proxy` object:

```javascript
proxy: {
  // Proxy audio streams to avoid ORB (Opaque Resource Blocking) on cross-origin media
  '/api/ldm/mapdata/audio/stream': {
    target: 'http://localhost:8888',
    changeOrigin: true,
  },
  '/api/ldm/codex/audio/stream': {
    target: 'http://localhost:8888',
    changeOrigin: true,
  },
},
```

- [ ] **Step 2: Verify proxy config is valid**

Run: `cd locaNext && node -e "const c = require('./vite.config.js'); console.log('OK');" 2>&1 || echo "vite.config.js uses ESM, check manually"`

Open `locaNext/vite.config.js` and visually confirm both proxy entries exist.

- [ ] **Step 3: Commit**

```bash
git add locaNext/vite.config.js
git commit -m "fix: add Vite proxy for codex audio stream (ORB bypass)"
```

---

### Task 2: Backend Language Support on Codex Routes

**Files:**
- Modify: `server/tools/ldm/routes/codex_audio.py`

The `get_audio_path_by_event_for_lang(event_name, file_language)` method already exists in `mega_index_api.py`. We just need to wire the `language` query parameter into the codex routes.

- [ ] **Step 1: Add language param to `_build_audio_card` helper**

Replace the `_build_audio_card` function (lines 45-56) with:

```python
def _build_audio_card(event_name: str, mega, language: str = "eng") -> AudioCardResponse:
    """Build an AudioCardResponse from MegaIndex lookups."""
    event_lower = event_name.lower()
    return AudioCardResponse(
        event_name=event_name,
        string_id=mega.event_to_stringid_lookup(event_name),
        script_kr=mega.get_script_kr(event_name),
        script_eng=mega.get_script_eng(event_name),
        export_path=mega.event_to_export_path.get(event_lower),
        has_wem=mega.get_audio_path_by_event_for_lang(event_name, language) is not None,
        xml_order=mega.event_to_xml_order.get(event_lower),
    )
```

- [ ] **Step 2: Add language param to stream endpoint**

Replace the `stream_audio` function (lines 149-179) with:

```python
@router.get("/stream/{event_name}")
async def stream_audio(
    event_name: str,
    language: str = Query(default="eng", description="Audio language folder (eng/kor/zho-cn)"),
):
    """Stream WAV audio for an event_name.

    Looks up WEM path via MegaIndex D10 (language-aware), converts WEM -> WAV
    via MediaConverter, and returns the WAV file.
    Unauthenticated for <audio> element compatibility.
    """
    mega = get_mega_index()
    wem_path = mega.get_audio_path_by_event_for_lang(event_name, language)

    if wem_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"No audio found for event '{event_name}' (language={language})",
        )

    # If the path is already a WAV file, serve it directly
    if wem_path.suffix.lower() == ".wav" and wem_path.exists():
        return FileResponse(str(wem_path), media_type="audio/wav")

    # Convert Windows path to WSL path, then WEM -> WAV
    wsl_path = convert_to_wsl_path(str(wem_path))
    converter = get_media_converter()

    wav_path = await asyncio.to_thread(
        converter.convert_wem_to_wav, Path(wsl_path)
    )
    if wav_path is None:
        raise HTTPException(status_code=500, detail="Audio conversion failed")

    return FileResponse(str(wav_path), media_type="audio/wav")
```

- [ ] **Step 3: Add language param to list endpoint**

In the `list_audio` function (line 228), add the `language` parameter:

```python
@router.get("/", response_model=AudioListResponse)
async def list_audio(
    category: Optional[str] = Query(None, description="Filter by D20 export_path prefix"),
    q: Optional[str] = Query(None, description="Search across event_name, script, stringid"),
    language: str = Query(default="eng", description="Audio language folder (eng/kor/zho-cn)"),
    current_user: dict = Depends(get_current_active_user_async),
):
```

And change line 288 to pass language:

```python
items = [_build_audio_card(ev, mega, language=language) for ev in all_events]
```

- [ ] **Step 4: Add language param to detail endpoint**

In the `get_audio_detail` function (line 182), add language parameter:

```python
@router.get("/{event_name}", response_model=AudioDetailResponse)
async def get_audio_detail(
    event_name: str,
    language: str = Query(default="eng", description="Audio language folder (eng/kor/zho-cn)"),
    current_user: dict = Depends(get_current_active_user_async),
):
```

And update the wem_path lookup (line 206) and stream_url (line 218):

```python
        wem_path = mega.get_audio_path_by_event_for_lang(event_name, language)
        has_wem = wem_path is not None

        return AudioDetailResponse(
            event_name=event_name,
            string_id=string_id,
            script_kr=mega.get_script_kr(event_name),
            script_eng=mega.get_script_eng(event_name),
            export_path=mega.event_to_export_path.get(event_lower),
            has_wem=has_wem,
            xml_order=mega.event_to_xml_order.get(event_lower),
            wem_path=str(wem_path) if wem_path else None,
            stream_url=f"/api/ldm/codex/audio/stream/{event_name}?language={language}" if has_wem else None,
        )
```

- [ ] **Step 5: Verify backend starts**

Run: `cd /home/neil1988/LocalizationTools && DEV_MODE=true timeout 10 python3 -c "from server.tools.ldm.routes.codex_audio import router; print('OK: codex_audio routes import successfully')"`

Expected: `OK: codex_audio routes import successfully`

- [ ] **Step 6: Commit**

```bash
git add server/tools/ldm/routes/codex_audio.py
git commit -m "feat: add language param to codex audio routes (eng/kor/zho-cn)"
```

---

## Wave 1: AudioExportTree Component (Plan 2)

### Task 3: Create AudioExportTree.svelte

**Files:**
- Create: `locaNext/src/lib/components/ldm/AudioExportTree.svelte`

This is the left panel — a hierarchical category tree extracted from the current AudioCodexPage sidebar, enhanced to match MDG's `export_tree.py` exactly.

- [ ] **Step 1: Create the component**

Create `locaNext/src/lib/components/ldm/AudioExportTree.svelte`:

```svelte
<script>
  /**
   * AudioExportTree.svelte - Category hierarchy sidebar for Audio Codex
   *
   * MDG-exact behavior: hierarchical export_path tree with collapsible nodes,
   * count badges, auto-expand first 2 levels. Props-driven, stateless.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { ChevronRight, ChevronDown } from "carbon-icons-svelte";

  let {
    categories = [],
    activeCategory = null,
    totalEvents = 0,
    onselect = () => {},
  } = $props();

  // Track expanded nodes — auto-expand first 2 levels on mount
  let expandedPaths = $state(new Set());
  let initialized = $state(false);

  $effect(() => {
    if (categories.length > 0 && !initialized) {
      const paths = new Set();
      for (const cat of categories) {
        paths.add(cat.full_path);
        if (cat.children) {
          for (const child of cat.children) {
            paths.add(child.full_path);
          }
        }
      }
      expandedPaths = paths;
      initialized = true;
    }
  });

  function toggleExpand(fullPath, event) {
    event.stopPropagation();
    const next = new Set(expandedPaths);
    if (next.has(fullPath)) {
      next.delete(fullPath);
    } else {
      next.add(fullPath);
    }
    expandedPaths = next;
  }

  function selectCat(fullPath) {
    onselect(fullPath);
  }
</script>

<aside class="export-tree" aria-label="Audio categories">
  <div class="tree-header">
    <span class="tree-title">Categories</span>
  </div>

  <!-- All root node -->
  <button
    class="tree-node depth-0"
    class:active={activeCategory === null}
    onclick={() => selectCat(null)}
    aria-label="All audio entries ({totalEvents})"
  >
    <span class="tree-spacer"></span>
    <span class="tree-name">All</span>
    <span class="tree-count">{totalEvents}</span>
  </button>

  <!-- Recursive tree rendering (3 levels max like MDG) -->
  {#each categories as cat (cat.full_path)}
    {@const expanded = expandedPaths.has(cat.full_path)}
    {@const hasKids = cat.children && cat.children.length > 0}
    <button
      class="tree-node depth-0"
      class:active={activeCategory === cat.full_path}
      onclick={() => selectCat(cat.full_path)}
    >
      {#if hasKids}
        <span
          class="tree-toggle"
          role="button"
          tabindex="0"
          onclick={(e) => toggleExpand(cat.full_path, e)}
          onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(cat.full_path, e); } }}
        >
          {#if expanded}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
        </span>
      {:else}
        <span class="tree-spacer"></span>
      {/if}
      <span class="tree-name">{cat.name}</span>
      <span class="tree-count">{cat.count}</span>
    </button>

    {#if expanded && hasKids}
      {#each cat.children as child (child.full_path)}
        {@const childExpanded = expandedPaths.has(child.full_path)}
        {@const childHasKids = child.children && child.children.length > 0}
        <button
          class="tree-node depth-1"
          class:active={activeCategory === child.full_path}
          onclick={() => selectCat(child.full_path)}
        >
          {#if childHasKids}
            <span
              class="tree-toggle"
              role="button"
              tabindex="0"
              onclick={(e) => toggleExpand(child.full_path, e)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(child.full_path, e); } }}
            >
              {#if childExpanded}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
            </span>
          {:else}
            <span class="tree-spacer"></span>
          {/if}
          <span class="tree-name">{child.name}</span>
          <span class="tree-count">{child.count}</span>
        </button>

        {#if childExpanded && childHasKids}
          {#each child.children as grandchild (grandchild.full_path)}
            <button
              class="tree-node depth-2"
              class:active={activeCategory === grandchild.full_path}
              onclick={() => selectCat(grandchild.full_path)}
            >
              <span class="tree-spacer"></span>
              <span class="tree-name">{grandchild.name}</span>
              <span class="tree-count">{grandchild.count}</span>
            </button>
          {/each}
        {/if}
      {/each}
    {/if}
  {/each}
</aside>

<style>
  .export-tree {
    width: 250px;
    flex-shrink: 0;
    border-right: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }

  .tree-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .tree-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .tree-node {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    padding: 8px 12px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    cursor: pointer;
    text-align: left;
    transition: all 0.12s;
    border-left: 3px solid transparent;
  }

  .tree-node.depth-0 { padding-left: 12px; }
  .tree-node.depth-1 { padding-left: 28px; }
  .tree-node.depth-2 { padding-left: 44px; }

  .tree-node:hover { background: var(--cds-layer-hover-01); color: var(--cds-text-01); }
  .tree-node:focus { outline: 2px solid var(--cds-focus); outline-offset: -2px; }
  .tree-node.active {
    background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.1));
    color: var(--cds-text-01);
    border-left-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 500;
  }

  .tree-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--cds-text-03);
    cursor: pointer;
    flex-shrink: 0;
    width: 18px;
    height: 18px;
  }

  .tree-toggle:hover { color: var(--cds-text-01); }

  .tree-spacer {
    display: inline-block;
    width: 18px;
    flex-shrink: 0;
  }

  .tree-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tree-count {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
    flex-shrink: 0;
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add locaNext/src/lib/components/ldm/AudioExportTree.svelte
git commit -m "feat: AudioExportTree component (MDG-exact category hierarchy)"
```

---

## Wave 1: AudioPlayerPanel Component (Plan 3)

### Task 4: Create AudioPlayerPanel.svelte

**Files:**
- Create: `locaNext/src/lib/components/ldm/AudioPlayerPanel.svelte`

Right panel — replaces AudioCodexDetail. Shows player with progress bar, Play/Stop/Prev/Next controls, KOR/ENG scripts, metadata.

- [ ] **Step 1: Create the component**

Create `locaNext/src/lib/components/ldm/AudioPlayerPanel.svelte`:

```svelte
<script>
  /**
   * AudioPlayerPanel.svelte - Audio player right panel for Audio Codex
   *
   * MDG-exact: event header + progress bar + Play/Stop/Prev/Next controls
   * + KOR/ENG script panels + metadata. Props-driven, stateless.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { Music, SkipBackFilled, SkipForwardFilled, PlayFilledAlt, StopFilledAlt } from "carbon-icons-svelte";

  let {
    audio = null,
    playing = false,
    currentTime = 0,
    duration = 0,
    onplay = () => {},
    onstop = () => {},
    onprev = () => {},
    onnext = () => {},
    onseek = () => {},
  } = $props();

  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  function handleProgressClick(event) {
    if (!duration) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    onseek(ratio * duration);
  }

  let progressPercent = $derived(
    duration > 0 ? (currentTime / duration) * 100 : 0
  );
</script>

<div class="player-panel">
  {#if audio}
    <!-- Event name header -->
    <div class="panel-header">
      <Music size={18} />
      <span class="event-name">{audio.event_name}</span>
      {#if duration > 0}
        <span class="duration-badge">{formatTime(duration)}</span>
      {/if}
    </div>

    <!-- Progress bar -->
    {#if audio.has_wem}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="progress-bar" onclick={handleProgressClick}>
        <div class="progress-fill" style="width: {progressPercent}%"></div>
        <div class="progress-thumb" style="left: {progressPercent}%"></div>
      </div>
      <div class="time-display">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    {/if}

    <!-- Controls -->
    <div class="controls">
      <button class="ctrl-btn" onclick={onprev} aria-label="Previous">
        <SkipBackFilled size={20} />
      </button>

      {#if playing}
        <button class="ctrl-btn primary stop" onclick={onstop} aria-label="Stop">
          <StopFilledAlt size={24} />
        </button>
      {:else}
        <button
          class="ctrl-btn primary"
          onclick={onplay}
          disabled={!audio.has_wem}
          aria-label="Play"
        >
          <PlayFilledAlt size={24} />
        </button>
      {/if}

      <button class="ctrl-btn" onclick={onnext} aria-label="Next">
        <SkipForwardFilled size={20} />
      </button>
    </div>

    <!-- KOR Script -->
    {#if audio.script_kr}
      <div class="script-section">
        <span class="section-label">Korean Script</span>
        <p class="script-text kr">{audio.script_kr}</p>
      </div>
    {/if}

    <!-- ENG Script -->
    {#if audio.script_eng}
      <div class="script-section">
        <span class="section-label">English Script</span>
        <p class="script-text eng">{audio.script_eng}</p>
      </div>
    {/if}

    <!-- Metadata -->
    <div class="meta-section">
      <span class="section-label">Details</span>
      {#if audio.string_id}
        <div class="meta-row">
          <span class="meta-label">StringId</span>
          <span class="meta-value">{audio.string_id}</span>
        </div>
      {/if}
      {#if audio.export_path}
        <div class="meta-row">
          <span class="meta-label">Category</span>
          <span class="meta-value">{audio.export_path}</span>
        </div>
      {/if}
      {#if audio.wem_path}
        <div class="meta-row">
          <span class="meta-label">WEM Path</span>
          <span class="meta-value mono">{audio.wem_path}</span>
        </div>
      {/if}
      {#if audio.xml_order != null}
        <div class="meta-row">
          <span class="meta-label">XML Order</span>
          <span class="meta-value">{audio.xml_order}</span>
        </div>
      {/if}
    </div>
  {:else}
    <div class="empty-state">
      <Music size={32} />
      <p>Select an audio entry to see details</p>
    </div>
  {/if}
</div>

<style>
  .player-panel {
    width: 350px;
    flex-shrink: 0;
    border-left: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--cds-text-01);
  }

  .event-name {
    font-size: 0.9375rem;
    font-weight: 600;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .duration-badge {
    font-size: 0.6875rem;
    padding: 2px 8px;
    border-radius: 8px;
    background: var(--cds-layer-02);
    color: var(--cds-text-03);
    flex-shrink: 0;
  }

  /* Progress bar */
  .progress-bar {
    height: 6px;
    background: var(--cds-layer-02);
    border-radius: 3px;
    position: relative;
    cursor: pointer;
  }

  .progress-fill {
    height: 100%;
    background: var(--cds-interactive-01, #0f62fe);
    border-radius: 3px;
    transition: width 0.1s linear;
  }

  .progress-thumb {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--cds-interactive-01, #0f62fe);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    transition: left 0.1s linear;
  }

  .time-display {
    display: flex;
    justify-content: space-between;
    font-size: 0.6875rem;
    color: var(--cds-text-03);
  }

  /* Controls */
  .controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 8px 0;
  }

  .ctrl-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    cursor: pointer;
    padding: 6px;
    border-radius: 50%;
    transition: all 0.15s;
  }

  .ctrl-btn:hover { color: var(--cds-text-01); background: var(--cds-layer-hover-01); }
  .ctrl-btn:focus { outline: 2px solid var(--cds-focus); outline-offset: 1px; }
  .ctrl-btn:disabled { color: var(--cds-disabled-03); cursor: not-allowed; }

  .ctrl-btn.primary {
    width: 44px;
    height: 44px;
    background: var(--cds-interactive-01, #0f62fe);
    color: var(--cds-text-on-color, #fff);
  }

  .ctrl-btn.primary:hover { background: var(--cds-hover-primary, #0353e9); }
  .ctrl-btn.primary:disabled { background: var(--cds-disabled-02); color: var(--cds-disabled-03); }

  .ctrl-btn.primary.stop {
    background: var(--cds-support-error, #da1e28);
  }

  .ctrl-btn.primary.stop:hover { background: var(--cds-hover-danger, #b81921); }

  /* Scripts */
  .script-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .section-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .script-text {
    margin: 0;
    line-height: 1.6;
    white-space: pre-line;
  }

  .script-text.kr { font-size: 0.9375rem; color: var(--cds-text-01); }
  .script-text.eng { font-size: 0.8125rem; color: var(--cds-text-02); }

  /* Metadata */
  .meta-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .meta-row {
    display: flex;
    gap: 12px;
    font-size: 0.8125rem;
  }

  .meta-label {
    color: var(--cds-text-03);
    min-width: 80px;
    flex-shrink: 0;
    font-weight: 500;
  }

  .meta-value {
    color: var(--cds-text-01);
    word-break: break-all;
  }

  .meta-value.mono {
    font-family: monospace;
    font-size: 0.75rem;
  }

  /* Empty state */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 48px 16px;
    color: var(--cds-text-03);
    text-align: center;
  }

  .empty-state p {
    font-size: 0.875rem;
    margin: 0;
    color: var(--cds-text-02);
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add locaNext/src/lib/components/ldm/AudioPlayerPanel.svelte
git commit -m "feat: AudioPlayerPanel component (MDG-exact player + scripts + metadata)"
```

---

## Wave 2: Result Grid + Page Rewrite (Plan 4)

### Task 5: Create AudioResultGrid.svelte

**Files:**
- Create: `locaNext/src/lib/components/ldm/AudioResultGrid.svelte`

Center panel — table-style grid with EventName | KOR | ENG columns, play/stop per row, arrow key navigation, selected row highlight.

- [ ] **Step 1: Create the component**

Create `locaNext/src/lib/components/ldm/AudioResultGrid.svelte`:

```svelte
<script>
  /**
   * AudioResultGrid.svelte - Center panel result grid for Audio Codex
   *
   * MDG-exact: EventName | KOR Script | ENG Script with play/stop button,
   * arrow key navigation, selected row highlight, has_wem indicator.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { PlayFilledAlt, StopFilledAlt } from "carbon-icons-svelte";

  let {
    items = [],
    selectedEvent = null,
    playingEvent = null,
    onselect = () => {},
    onplay = () => {},
    onstop = () => {},
  } = $props();

  let gridRef = $state(null);

  function handleRowClick(eventName) {
    onselect(eventName);
  }

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
      // Scroll into view
      const row = gridRef?.querySelector(`[data-event="${CSS.escape(nextEvent)}"]`);
      row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  function truncate(text, maxLen = 60) {
    if (!text) return "";
    return text.length > maxLen ? text.slice(0, maxLen) + "..." : text;
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="result-grid"
  role="grid"
  aria-label="Audio entries"
  bind:this={gridRef}
  tabindex="0"
  onkeydown={handleKeyDown}
>
  <!-- Header -->
  <div class="grid-header" role="row">
    <span class="col col-play"></span>
    <span class="col col-event" role="columnheader">EventName</span>
    <span class="col col-kr" role="columnheader">KOR Script</span>
    <span class="col col-eng" role="columnheader">ENG Script</span>
  </div>

  <!-- Rows -->
  <div class="grid-body">
    {#each items as item (item.event_name)}
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <div
        class="grid-row"
        class:selected={selectedEvent === item.event_name}
        class:playing={playingEvent === item.event_name}
        role="row"
        data-event={item.event_name}
        onclick={() => handleRowClick(item.event_name)}
        onkeydown={(e) => { if (e.key === "Enter") handleRowClick(item.event_name); }}
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
        <span class="col col-event">
          <span class="wem-dot" class:has-wem={item.has_wem}></span>
          <span class="event-text">{item.event_name}</span>
        </span>

        <!-- KOR Script -->
        <span class="col col-kr">{truncate(item.script_kr)}</span>

        <!-- ENG Script -->
        <span class="col col-eng">{truncate(item.script_eng)}</span>
      </div>
    {/each}

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

  .result-grid:focus-within {
    outline: none;
  }

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
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    cursor: pointer;
    transition: background 0.1s;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .grid-row:hover { background: var(--cds-layer-hover-01); }
  .grid-row.selected { background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.1)); color: var(--cds-text-01); }
  .grid-row.playing { background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.08)); }

  .col { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .col-play { width: 40px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
  .col-event { width: 200px; flex-shrink: 0; display: flex; align-items: center; gap: 6px; font-family: monospace; font-size: 0.75rem; }
  .col-kr { flex: 1; min-width: 0; color: var(--cds-text-01); }
  .col-eng { flex: 1; min-width: 0; color: var(--cds-text-03); font-size: 0.75rem; }

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
```

- [ ] **Step 2: Commit**

```bash
git add locaNext/src/lib/components/ldm/AudioResultGrid.svelte
git commit -m "feat: AudioResultGrid component (MDG-exact grid + arrow nav)"
```

---

### Task 6: Rewrite AudioCodexPage.svelte (orchestrator)

**Files:**
- Rewrite: `locaNext/src/lib/components/pages/AudioCodexPage.svelte`
- Delete: `locaNext/src/lib/components/ldm/AudioCodexDetail.svelte`

This is the orchestrator that wires all 3 child components together with state management, hidden audio element, and language selector.

- [ ] **Step 1: Rewrite AudioCodexPage.svelte**

Replace the entire content of `locaNext/src/lib/components/pages/AudioCodexPage.svelte` with:

```svelte
<script>
  /**
   * AudioCodexPage.svelte - Audio Codex MDG-style 3-panel layout
   *
   * Orchestrator: owns all state, wires AudioExportTree (left),
   * AudioResultGrid (center), AudioPlayerPanel (right).
   * Hidden <audio> element for programmatic playback + progress bar.
   *
   * Phase 107: Audio Codex MDG Graft
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Music, Search } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import AudioExportTree from "$lib/components/ldm/AudioExportTree.svelte";
  import AudioResultGrid from "$lib/components/ldm/AudioResultGrid.svelte";
  import AudioPlayerPanel from "$lib/components/ldm/AudioPlayerPanel.svelte";
  import { onMount, onDestroy } from "svelte";

  const API_BASE = getApiBase();

  // ── State ──
  let categories = $state([]);
  let allItems = $state([]);
  let activeCategory = $state(null);
  let searchQuery = $state("");
  let selectedEvent = $state(null);
  let selectedAudio = $state(null);
  let playingEvent = $state(null);
  let selectedLanguage = $state("eng");
  let currentTime = $state(0);
  let duration = $state(0);
  let totalEvents = $state(0);
  let loadingCategories = $state(true);
  let loadingList = $state(true);
  let apiError = $state(null);

  // Hidden audio element ref
  let audioEl = $state(null);
  let rafId = null;

  // ── Derived: client-side filtered items ──
  let filteredItems = $derived.by(() => {
    return allItems.filter((item) => {
      if (activeCategory && item.export_path && !item.export_path.startsWith(activeCategory)) return false;
      if (activeCategory && !item.export_path) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = `${item.event_name || ""} ${item.script_kr || ""} ${item.script_eng || ""} ${item.string_id || ""}`.toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });
  });

  // ── Audio progress loop ──
  function startProgressLoop() {
    function tick() {
      if (audioEl && !audioEl.paused) {
        currentTime = audioEl.currentTime;
        duration = audioEl.duration || 0;
        rafId = requestAnimationFrame(tick);
      }
    }
    rafId = requestAnimationFrame(tick);
  }

  function stopProgressLoop() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  // ── API calls ──
  async function fetchCategories() {
    loadingCategories = true;
    apiError = null;
    try {
      const res = await fetch(`${API_BASE}/api/ldm/codex/audio/categories`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      categories = data.categories || [];
      totalEvents = data.total_events || 0;
      logger.info("Audio Codex categories loaded", { count: categories.length, totalEvents });
    } catch (err) {
      logger.error("Failed to fetch audio categories", { error: err.message });
      apiError = "Audio Codex unavailable — ensure gamedata folder is configured";
    } finally {
      loadingCategories = false;
    }
  }

  async function fetchAllItems() {
    loadingList = true;
    try {
      const res = await fetch(`${API_BASE}/api/ldm/codex/audio?language=${selectedLanguage}`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      allItems = data.items || [];
      logger.info("Audio Codex bulk loaded", { total: allItems.length, language: selectedLanguage });
    } catch (err) {
      logger.error("Failed to fetch audio items", { error: err.message });
      apiError = "Failed to load audio entries";
    } finally {
      loadingList = false;
    }
  }

  async function fetchAudioDetail(eventName) {
    try {
      const res = await fetch(
        `${API_BASE}/api/ldm/codex/audio/${encodeURIComponent(eventName)}?language=${selectedLanguage}`,
        { headers: getAuthHeaders() }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      selectedAudio = await res.json();
    } catch (err) {
      logger.error("Failed to fetch audio detail", { error: err.message, eventName });
    }
  }

  // ── Handlers ──
  function handleCategorySelect(fullPath) {
    activeCategory = fullPath;
  }

  function handleRowSelect(eventName) {
    selectedEvent = eventName;
    fetchAudioDetail(eventName);
  }

  function handlePlay(eventName) {
    // If a different event, select it first
    if (eventName && eventName !== selectedEvent) {
      selectedEvent = eventName;
      fetchAudioDetail(eventName);
    }
    const target = eventName || selectedEvent;
    if (!target) return;

    playingEvent = target;
    if (audioEl) {
      audioEl.src = `${API_BASE}/api/ldm/codex/audio/stream/${encodeURIComponent(target)}?language=${selectedLanguage}&v=${Date.now()}`;
      audioEl.load();
      audioEl.play().catch((err) => {
        logger.error("Audio play failed", { error: err.message });
        playingEvent = null;
      });
      startProgressLoop();
    }
  }

  function handleStop() {
    if (audioEl) {
      audioEl.pause();
      audioEl.currentTime = 0;
    }
    playingEvent = null;
    currentTime = 0;
    stopProgressLoop();
  }

  function handleSeek(time) {
    if (audioEl) {
      audioEl.currentTime = time;
      currentTime = time;
    }
  }

  function handlePrev() {
    const idx = filteredItems.findIndex((i) => i.event_name === selectedEvent);
    const prevIdx = idx <= 0 ? filteredItems.length - 1 : idx - 1;
    const prev = filteredItems[prevIdx];
    if (prev) {
      handleStop();
      handleRowSelect(prev.event_name);
    }
  }

  function handleNext() {
    const idx = filteredItems.findIndex((i) => i.event_name === selectedEvent);
    const nextIdx = idx >= filteredItems.length - 1 ? 0 : idx + 1;
    const next = filteredItems[nextIdx];
    if (next) {
      handleStop();
      handleRowSelect(next.event_name);
    }
  }

  function handleAudioEnded() {
    playingEvent = null;
    currentTime = 0;
    duration = 0;
    stopProgressLoop();
  }

  function handleLanguageChange(event) {
    const lang = event.target.value;
    selectedLanguage = lang;
    handleStop();
    selectedAudio = null;
    selectedEvent = null;
    fetchAllItems();
  }

  onMount(() => {
    fetchCategories();
    fetchAllItems();
  });

  onDestroy(() => {
    stopProgressLoop();
    if (audioEl) {
      audioEl.pause();
      audioEl.src = "";
    }
  });
</script>

<!-- Hidden audio element for programmatic control -->
<audio
  bind:this={audioEl}
  preload="auto"
  onended={handleAudioEnded}
  onerror={() => { playingEvent = null; stopProgressLoop(); }}
  ondurationchange={() => { if (audioEl) duration = audioEl.duration || 0; }}
></audio>

<div class="audio-codex-page">
  <!-- Header -->
  <div class="page-header-bar">
    <PageHeader icon={Music} title="Audio Codex" />
    <div class="header-controls">
      <!-- Language selector -->
      <div class="lang-select">
        <label for="audio-lang">Language:</label>
        <select id="audio-lang" value={selectedLanguage} onchange={handleLanguageChange}>
          <option value="eng">English (US)</option>
          <option value="kor">Korean</option>
          <option value="zho-cn">Chinese (PRC)</option>
        </select>
      </div>

      <!-- Search bar -->
      <div class="search-wrapper">
        <Search size={16} />
        <input
          type="search"
          placeholder="Search event name, script, StringId..."
          bind:value={searchQuery}
          class="search-input"
          aria-label="Search audio entries"
        />
        <span class="result-count">{filteredItems.length}</span>
      </div>
    </div>
  </div>

  {#if apiError}
    <div class="state-container">
      <ErrorState message={apiError} onretry={() => { fetchCategories(); fetchAllItems(); }} />
    </div>
  {:else if loadingCategories}
    <div class="state-container">
      <InlineLoading description="Loading audio categories..." />
    </div>
  {:else}
    <div class="three-panel">
      <!-- LEFT: Export Tree -->
      <AudioExportTree
        {categories}
        {activeCategory}
        {totalEvents}
        onselect={handleCategorySelect}
      />

      <!-- CENTER: Result Grid -->
      {#if loadingList}
        <div class="loading-center">
          <InlineLoading description="Loading audio entries..." />
        </div>
      {:else}
        <AudioResultGrid
          items={filteredItems}
          {selectedEvent}
          {playingEvent}
          onselect={handleRowSelect}
          onplay={handlePlay}
          onstop={handleStop}
        />
      {/if}

      <!-- RIGHT: Audio Player Panel -->
      <AudioPlayerPanel
        audio={selectedAudio}
        playing={playingEvent != null}
        {currentTime}
        {duration}
        onplay={() => handlePlay(selectedEvent)}
        onstop={handleStop}
        onprev={handlePrev}
        onnext={handleNext}
        onseek={handleSeek}
      />
    </div>
  {/if}
</div>

<style>
  .audio-codex-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .page-header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-right: 16px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .lang-select {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .lang-select label { font-weight: 500; white-space: nowrap; }

  .lang-select select {
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    padding: 4px 8px;
  }

  .search-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-03);
    min-width: 280px;
  }

  .search-wrapper:focus-within {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
  }

  .search-input {
    flex: 1;
    border: none;
    background: transparent;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    outline: none;
  }

  .search-input::placeholder { color: var(--cds-text-03); }

  .result-count {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
  }

  .state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 32px;
  }

  .three-panel {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .loading-center {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
```

- [ ] **Step 2: Delete AudioCodexDetail.svelte**

```bash
rm locaNext/src/lib/components/ldm/AudioCodexDetail.svelte
```

- [ ] **Step 3: Verify no remaining imports of AudioCodexDetail**

Search for any remaining references:

```bash
grep -r "AudioCodexDetail" locaNext/src/ --include="*.svelte" --include="*.js" --include="*.ts"
```

Expected: No results (the only import was in AudioCodexPage which we just rewrote).

- [ ] **Step 4: Verify Svelte builds**

```bash
cd locaNext && npx svelte-check --threshold warning 2>&1 | head -30
```

Expected: No errors related to Audio components.

- [ ] **Step 5: Commit**

```bash
git add locaNext/src/lib/components/pages/AudioCodexPage.svelte \
       locaNext/src/lib/components/ldm/AudioResultGrid.svelte \
       locaNext/src/lib/components/ldm/AudioExportTree.svelte \
       locaNext/src/lib/components/ldm/AudioPlayerPanel.svelte
git rm locaNext/src/lib/components/ldm/AudioCodexDetail.svelte
git commit -m "feat: Audio Codex MDG 3-panel graft (export tree + grid + player)"
```

---

### Task 7: Verify End-to-End

- [ ] **Step 1: Test backend language parameter**

```bash
cd /home/neil1988/LocalizationTools && DEV_MODE=true python3 -c "
from server.tools.ldm.routes.codex_audio import router
import inspect
# Check stream_audio has language param
stream_fn = None
for route in router.routes:
    if hasattr(route, 'endpoint') and route.endpoint.__name__ == 'stream_audio':
        stream_fn = route.endpoint
        break
if stream_fn:
    sig = inspect.signature(stream_fn)
    assert 'language' in sig.parameters, 'stream_audio missing language param'
    print('OK: stream_audio has language param')
else:
    print('FAIL: stream_audio not found')
"
```

- [ ] **Step 2: Test AudioCodexPage loads in browser**

Navigate to `http://localhost:5173` in Playwright, go to Audio Codex page.
Take a screenshot to verify 3-panel layout renders.

```bash
# Use curl to verify API endpoints work
curl -s -H "Authorization: Bearer $(curl -s -X POST http://localhost:8888/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')" \
  "http://localhost:8888/api/ldm/codex/audio?language=eng" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'OK: {d[\"total\"]} audio items loaded')"
```

- [ ] **Step 3: Test language switching on stream**

```bash
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8888/api/ldm/codex/audio/stream/play_grimjaw_forge_01?language=eng"
```

Expected: `200` (or `404` if that specific event doesn't exist — the route should work without error).

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: Audio Codex end-to-end verification fixes"
```
