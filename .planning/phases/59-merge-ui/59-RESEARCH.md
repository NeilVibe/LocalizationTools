# Phase 59: Merge UI - Research

**Researched:** 2026-03-23
**Domain:** Svelte 5 UI (Carbon Components), SSE streaming, multi-step modal
**Confidence:** HIGH

## Summary

Phase 59 builds the frontend merge modal and its two entry points (toolbar button + folder right-click context menu). The backend merge API is already complete (Phase 58) with POST /api/merge/preview (sync dry-run) and POST /api/merge/execute (SSE streaming). The frontend must consume these APIs through a single-page modal with four phases: configure, preview, execute, done.

The codebase already has established patterns for modals (Carbon `<Modal>` with `$bindable(open)`, Svelte 5 Runes), context menus (custom HTML-based menus in FilesPage.svelte with item-type switching), and toolbar buttons (GridPage.svelte uses Carbon `<Button kind="ghost">` in toolbar-right). SSE is the one genuinely new pattern -- no frontend EventSource usage exists yet, so this will be the first SSE consumer in the project.

**Primary recommendation:** Build MergeModal.svelte as a standalone component in `locaNext/src/lib/components/ldm/`, wire it into +layout.svelte (like ProjectSettingsModal), and add entry points in FilesPage.svelte (context menu) and +layout.svelte (toolbar area near Settings). Use native `EventSource` for SSE consumption since the execute endpoint uses sse-starlette which is fully compatible.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | "Merge to LOCDEV" button in main toolbar near Export actions | Toolbar area in +layout.svelte between nav tabs and Settings dropdown; or in GridPage.svelte toolbar-right |
| UI-02 | Right-click folder context menu "Merge Folder to LOCDEV" | FilesPage.svelte already has folder context menu block (line 2575), add new button before delete |
| UI-03 | Single-page merge modal with target LOCDEV folder picker, match type radios, scope toggle | Carbon Modal size="lg", RadioButtonGroup, Toggle components; phase-driven $state |
| UI-04 | Category filter toggle visible only for StringID mode | Conditional render with `{#if matchMode === 'stringid_only'}`, Carbon Toggle |
| UI-05 | Dry-run preview panel shows file/entry counts and overwrite warnings | POST /api/merge/preview returns MergePreviewResponse with all needed fields |
| UI-06 | Progress display during merge execution | POST /api/merge/execute SSE stream; native EventSource; progress/log/complete/error events |
| UI-07 | Summary report shown on completion with matched/skipped/overwritten counts | "complete" SSE event contains full JSON result dict |
| UI-08 | Language auto-detected from project and shown as badge in modal header | selectedProject.name parsing (project_FRE -> French); Carbon Tag component |
| UI-09 | Multi-language mode shows detected languages with file counts before merge | Preview response has `scan` and `per_language` fields for multi-language mode |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| carbon-components-svelte | (project installed) | Modal, Button, RadioButtonGroup, Toggle, Tag, ProgressBar, InlineNotification | Already used in ALL project modals |
| carbon-icons-svelte | (project installed) | Merge, Flash, Document, ArrowLeft icons | Already used in FilesPage.svelte (Merge icon imported) |
| svelte 5 | (project installed) | $state, $derived, $effect, $props, $bindable | Mandatory per CLAUDE.md |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Native EventSource API | Browser built-in | SSE stream consumption | Execute phase -- connect to POST /api/merge/execute SSE endpoint |
| $lib/utils/api.js | Project utility | getApiBase(), getAuthHeaders(), apiPost() | All API calls from the modal |
| $lib/stores/projectSettings.js | Phase 56 store | getProjectSettings(projectId) for LOC PATH and EXPORT PATH | Pre-fill modal paths from stored settings |
| $lib/stores/navigation.js | Project store | selectedProject writable store | Get current project ID and name for auto-detection |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native EventSource | fetch + ReadableStream | EventSource handles reconnection automatically but only supports GET; however, we need POST -- use fetch with getReader() instead |

**IMPORTANT NOTE on SSE with POST:** The merge execute endpoint is `POST /api/merge/execute`. Native `EventSource` only supports GET requests. The project uses `sse-starlette` which returns an `EventSourceResponse`. The frontend MUST use `fetch()` with response body streaming (`response.body.getReader()`) and manual SSE parsing, NOT native `EventSource`. This is the standard pattern for POST-based SSE endpoints.

## Architecture Patterns

### Recommended Project Structure
```
locaNext/src/lib/components/
├── ldm/
│   └── MergeModal.svelte          # Main merge modal (all 4 phases)
├── pages/
│   └── FilesPage.svelte           # Add context menu entry (modify)
└── (root)/
    └── +layout.svelte             # Add toolbar button + modal instance (modify)
```

### Pattern 1: Phase-Driven Modal State Machine
**What:** Single modal component with internal phase state controlling what's visible
**When to use:** Multi-step workflows within a single modal (configure -> preview -> execute -> done)
**Example:**
```svelte
// Based on project patterns (ProjectSettingsModal, PretranslateModal)
<script>
  let { open = $bindable(false), projectId = null, projectName = '', multiLanguage = false, folderPath = '' } = $props();

  // Phase state machine
  let phase = $state('configure'); // 'configure' | 'preview' | 'execute' | 'done'

  // Configure state
  let matchMode = $state('strict');
  let onlyUntranslated = $state(false);
  let stringidAllCategories = $state(false);

  // Preview state
  let previewResult = $state(null);
  let previewLoading = $state(false);
  let previewError = $state('');

  // Execute state
  let progressMessages = $state([]);
  let executing = $state(false);

  // Done state
  let mergeResult = $state(null);

  // Derived
  let showCategoryFilter = $derived(matchMode === 'stringid_only');

  // Reset on open
  $effect(() => {
    if (open) {
      phase = 'configure';
      previewResult = null;
      progressMessages = [];
      mergeResult = null;
    }
  });
</script>

<Modal bind:open size="lg" passiveModal={phase === 'execute'}>
  {#if phase === 'configure'}
    <!-- match type radios, scope toggle, category filter -->
  {:else if phase === 'preview'}
    <!-- dry-run results table -->
  {:else if phase === 'execute'}
    <!-- progress messages, progress bar -->
  {:else if phase === 'done'}
    <!-- summary report -->
  {/if}
</Modal>
```

### Pattern 2: Modal Wiring (from +layout.svelte)
**What:** Modal component instantiated in layout, triggered by state variable
**When to use:** All project modals follow this pattern
**Example:**
```svelte
// In +layout.svelte (following ProjectSettingsModal pattern, line 510)
import MergeModal from "$lib/components/ldm/MergeModal.svelte";

let showMergeModal = $state(false);
let mergeMultiLanguage = $state(false);
let mergeFolderPath = $state('');

function openMerge() {
  if (!$selectedProject) return;
  mergeMultiLanguage = false;
  mergeFolderPath = '';
  showMergeModal = true;
}

// In template:
<MergeModal
  bind:open={showMergeModal}
  projectId={$selectedProject?.id}
  projectName={$selectedProject?.name || ''}
  multiLanguage={mergeMultiLanguage}
  folderPath={mergeFolderPath}
/>
```

### Pattern 3: Context Menu Entry (from FilesPage.svelte)
**What:** Add menu item to existing folder right-click menu
**When to use:** FilesPage.svelte line 2575 has `{:else if contextMenuItem.type === 'folder'}` block
**Example:**
```svelte
// Inside the folder context menu block (after "New Subfolder", before divider+delete)
<div class="context-menu-divider"></div>
<button class="context-menu-item" onclick={openMergeFolderToLocdev}>
  <Merge size={16} /> Merge Folder to LOCDEV
</button>
```

### Pattern 4: SSE Consumption via Fetch + ReadableStream
**What:** POST to SSE endpoint, parse response as event stream
**When to use:** Execute phase of merge modal
**Example:**
```javascript
async function executeMerge(body) {
  const API_BASE = getApiBase();
  const response = await fetch(`${API_BASE}/api/merge/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify(body)
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventType = line.slice(7).trim();
        // Next 'data:' line has the payload
      } else if (line.startsWith('data: ')) {
        const data = line.slice(6);
        // Handle based on current eventType
      }
    }
  }
}
```

### Pattern 5: Language Auto-Detection from Project Name
**What:** Parse project name suffix to determine language
**When to use:** Badge display in modal header (UI-08)
**Example:**
```javascript
// Based on MOCK-02 pattern: project_FRE -> French
const LANGUAGE_MAP = {
  'FRE': 'French', 'ENG': 'English', 'GER': 'German',
  'SPA': 'Spanish', 'ITA': 'Italian', 'JPN': 'Japanese',
  'KOR': 'Korean', 'CHN': 'Chinese', 'RUS': 'Russian',
  'POR': 'Portuguese', 'TUR': 'Turkish', 'ARA': 'Arabic'
};

function detectLanguage(projectName) {
  if (!projectName) return null;
  const suffix = projectName.split('_').pop()?.toUpperCase();
  return LANGUAGE_MAP[suffix] || suffix || null;
}
```

### Anti-Patterns to Avoid
- **Multiple modals for one workflow:** Do NOT create separate modals for configure/preview/execute. Use a single modal with phase state.
- **Svelte 4 patterns:** No `export let`, no `$:`, no `createEventDispatcher`. Use `$props()`, `$derived`, callback props.
- **Native EventSource for POST:** EventSource only supports GET. Use fetch + ReadableStream for SSE from POST endpoints.
- **Hardcoding paths:** Always read from projectSettings store (getProjectSettings). LOC PATH and EXPORT PATH are per-project in localStorage.
- **Blocking UI during merge:** The execute phase must stream progress. Never await the entire merge synchronously.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal chrome | Custom overlay/dialog | Carbon `<Modal>` | Already used in 13 modals in the project |
| Radio buttons | Custom toggle buttons | Carbon `<RadioButtonGroup>` / `<RadioButton>` | Consistent styling, accessibility |
| Progress display | Custom progress bar | Carbon `<ProgressBar>` | Used in PretranslateModal already |
| Notifications | Custom toast/alert | Carbon `<InlineNotification>` | Used in ProjectSettingsModal already |
| Context menu | New context menu system | Existing HTML-based menu in FilesPage.svelte | 400+ lines of working context menu code exists |
| SSE event parsing | npm sse library | Fetch + manual line parsing | Simple enough (~20 lines), avoids dependency |
| Path settings retrieval | Custom localStorage | `getProjectSettings()` from projectSettings.js | Already built in Phase 56 |

## Common Pitfalls

### Pitfall 1: SSE POST vs GET Confusion
**What goes wrong:** Using `new EventSource(url)` for a POST endpoint -- it silently sends GET, returns 405
**Why it happens:** EventSource API only supports GET requests
**How to avoid:** Use `fetch()` with `response.body.getReader()` and parse SSE lines manually
**Warning signs:** 405 Method Not Allowed or empty response body

### Pitfall 2: Merge Guard (409 Conflict)
**What goes wrong:** User clicks "Execute" twice, second request returns 409
**Why it happens:** Backend has `_merge_in_progress` guard (merge.py line 80)
**How to avoid:** Disable execute button during execution, handle 409 response gracefully
**Warning signs:** "A merge is already in progress" error in console

### Pitfall 3: Missing Path Configuration
**What goes wrong:** User opens merge modal but LOC PATH / EXPORT PATH not configured
**Why it happens:** Settings are per-project in localStorage, may not be set yet
**How to avoid:** Check `getProjectSettings(projectId)` on modal open, show clear error/redirect to Project Settings
**Warning signs:** Empty path fields, 422 validation errors from backend

### Pitfall 4: Right-Click Context Menu Known Bug
**What goes wrong:** Right-click on file explorer may not work
**Why it happens:** Known deferred bug in STATE.md: "Fix right-click context menu on file explorer panel"
**How to avoid:** The context menu CODE works (verified in ExplorerGrid.svelte -- oncontextmenu handlers exist and dispatch events properly). The "bug" may be about specific scenarios. Test the folder right-click path specifically during implementation.
**Warning signs:** Context menu doesn't appear on right-click

### Pitfall 5: Modal Size for Content Volume
**What goes wrong:** Modal too small to show preview results table and progress log
**Why it happens:** Using `size="sm"` (like other modals) when merge modal needs more space
**How to avoid:** Use `size="lg"` for the merge modal to fit all four phases comfortably
**Warning signs:** Scroll bars inside modal, cramped layout

### Pitfall 6: SSE Buffer Incomplete Lines
**What goes wrong:** SSE events split across chunks, partial lines parsed incorrectly
**Why it happens:** ReadableStream chunks don't align with SSE event boundaries
**How to avoid:** Maintain a buffer, only process complete lines (split by `\n`, keep last partial)
**Warning signs:** JSON parse errors, truncated event data

### Pitfall 7: Modal Open State After Merge
**What goes wrong:** Modal closes during execution (user clicks outside), merge continues silently
**Why it happens:** Carbon Modal default behavior allows closing via backdrop click
**How to avoid:** Set `passiveModal={true}` during execute phase (disables close button) OR handle the `onclose` event to warn user
**Warning signs:** Merge completes but user never sees summary

## Code Examples

### Carbon Modal with Svelte 5 Runes (Project Pattern)
```svelte
// Source: locaNext/src/lib/components/ProjectSettingsModal.svelte
import { Modal, TextInput, Button, InlineNotification } from "carbon-components-svelte";

let { open = $bindable(false), projectId = null } = $props();
let saved = $state(false);

$effect(() => {
  if (open && projectId) {
    // Reset state on open
  }
});
```

### Context Menu Item (Project Pattern)
```svelte
// Source: locaNext/src/lib/components/pages/FilesPage.svelte (line 2575)
{:else if contextMenuItem.type === 'folder'}
  <button class="context-menu-item" onclick={() => { handleCopy(); closeMenus(); }}>Copy</button>
  <!-- Add merge entry here -->
  <button class="context-menu-item" onclick={openMergeFolderToLocdev}>
    <Merge size={16} /> Merge Folder to LOCDEV
  </button>
```

### API Call Pattern (Project Standard)
```javascript
// Source: locaNext/src/lib/utils/api.js
import { getApiBase, getAuthHeaders } from "$lib/utils/api.js";

const API_BASE = getApiBase();
const response = await fetch(`${API_BASE}/api/merge/preview`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    ...getAuthHeaders()
  },
  body: JSON.stringify({
    source_path: exportPath,
    target_path: locPath,
    export_path: exportPath,
    match_mode: matchMode,
    only_untranslated: onlyUntranslated,
    stringid_all_categories: stringidAllCategories,
    multi_language: multiLanguage
  })
});
```

### Merge API Response Shapes
```javascript
// POST /api/merge/preview response (MergePreviewResponse)
{
  files_processed: 3,
  total_corrections: 150,
  total_matched: 120,
  total_updated: 120,
  total_not_found: 30,
  total_skipped: 0,
  total_skipped_translated: 10,
  overwrite_warnings: ["file1.xml: 45 entries will be overwritten"],
  errors: [],
  // Multi-language mode only:
  per_language: { "FRE": { matched: 60 }, "ENG": { matched: 60 } },
  scan: { "FRE": { files: 2 }, "ENG": { files: 1 } }
}

// POST /api/merge/execute SSE events
// event: progress | data: "Processing file1.xml..."
// event: log      | data: {"message": "Matched 45 entries", "level": "info"}
// event: complete | data: {JSON result dict with all counters}
// event: error    | data: "Error message string"
// event: ping     | data: "keepalive"
```

### Match Mode Constants
```javascript
// Mapping to backend MATCH_MODES (server/services/transfer_adapter.py)
const MATCH_MODES = [
  { value: 'stringid_only', label: 'StringID Only', description: 'Case-insensitive, SCRIPT/ALL filter' },
  { value: 'strict', label: 'StringID + StrOrigin', description: 'Strict 2-key with nospace fallback' },
  { value: 'strorigin_filename', label: 'StrOrigin + FileName 2PASS', description: '3-tuple then 2-tuple fallback' }
];
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Svelte 4 `export let` | Svelte 5 `$props()` + `$bindable` | v3.1 migration | All 36 components migrated |
| `createEventDispatcher` | Callback props (`onX = undefined`) | v3.1 migration | Zero legacy dispatchers |
| `on:click` directive | `onclick` attribute | v3.1 migration | Svelte 5 event syntax |
| npm SSE libraries | Native fetch + ReadableStream | Current best practice | No dependency needed |

## Open Questions

1. **Toolbar Button Placement**
   - What we know: GridPage.svelte has toolbar-right with ghost buttons; +layout.svelte has top nav with Settings dropdown. The requirement says "main toolbar near Export actions."
   - What's unclear: Is "main toolbar" the GridPage toolbar (visible only when viewing a file) or the top nav bar (always visible)?
   - Recommendation: Place in +layout.svelte top nav area (always visible, like a dedicated action button between the nav tabs and Apps dropdown). This ensures the merge button is accessible from the Files page, not just when a grid is open. ALTERNATIVE: Add to the Files page header/breadcrumb area.

2. **Right-Click Bug Severity**
   - What we know: STATE.md defers "Fix right-click context menu on file explorer panel." The ExplorerGrid.svelte code properly handles oncontextmenu events.
   - What's unclear: What exactly is broken. The code path works. Might be a CSS z-index issue or event propagation problem in specific scenarios.
   - Recommendation: Proceed with implementation. Test specifically on folders. If the bug manifests, fix it as part of Plan 02 since the context menu entry depends on it.

3. **Source Path vs Export Path Semantics**
   - What we know: The merge API takes source_path, target_path, and export_path. ProjectSettings stores locPath and exportPath.
   - What's unclear: The exact mapping. For "merge to LOCDEV": source_path = exportPath (translated files), target_path = locPath (LOCDEV), export_path = exportPath.
   - Recommendation: Clarify mapping in Plan 01 configure phase. The modal should auto-fill from stored project settings and make the mapping explicit in the UI.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (browser E2E) + manual visual verification |
| Config file | testing_toolkit/DEV_MODE_PROTOCOL.md |
| Quick run command | `DEV_MODE=true python3 server/main.py` + browser verification |
| Full suite command | Manual Playwright headless test |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | Merge button visible in toolbar | manual + screenshot | Playwright screenshot | No - Wave 0 |
| UI-02 | Right-click folder shows merge option | manual + screenshot | Playwright right-click | No - Wave 0 |
| UI-03 | Modal walks through 4 phases | manual | Click-through test | No - Wave 0 |
| UI-04 | Category filter conditional visibility | manual | Toggle match mode, verify | No - Wave 0 |
| UI-05 | Preview shows counts and warnings | manual | Trigger preview with mock data | No - Wave 0 |
| UI-06 | Progress display streams updates | manual | Execute merge, watch progress | No - Wave 0 |
| UI-07 | Summary report on completion | manual | Complete merge, verify counts | No - Wave 0 |
| UI-08 | Language badge auto-detected | manual | Open modal for project_FRE | No - Wave 0 |
| UI-09 | Multi-language detected languages | manual | Right-click folder, preview | No - Wave 0 |

### Sampling Rate
- **Per task commit:** DEV mode browser check with screenshot
- **Per wave merge:** Full click-through of all 4 modal phases
- **Phase gate:** All 9 UI requirements manually verified with screenshots

### Wave 0 Gaps
- This is a UI-only phase. Manual verification via DEV mode browser + screenshots is the test approach, consistent with all prior UI phases in this project.
- No automated test infrastructure needed -- Phase 60 handles integration testing.

## Sources

### Primary (HIGH confidence)
- `locaNext/src/lib/components/ProjectSettingsModal.svelte` - Modal pattern with Svelte 5 Runes, Carbon Modal, $bindable
- `locaNext/src/lib/components/ldm/PretranslateModal.svelte` - Multi-state modal with progress display
- `locaNext/src/lib/components/pages/FilesPage.svelte` - Context menu implementation (lines 2534-2668)
- `locaNext/src/lib/components/pages/GridPage.svelte` - Toolbar pattern (lines 286-344)
- `locaNext/src/routes/+layout.svelte` - Top nav, modal wiring, Settings dropdown (lines 460-510)
- `server/api/merge.py` - Full merge API (preview + execute SSE endpoints)
- `server/services/transfer_adapter.py` - MATCH_MODES constant, transfer function signatures
- `locaNext/src/lib/stores/projectSettings.js` - getProjectSettings/setProjectSettings
- `locaNext/src/lib/stores/navigation.js` - selectedProject store
- `locaNext/src/lib/utils/api.js` - getApiBase, getAuthHeaders, apiPost utilities

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` - Tribunal decisions, right-click bug deferral
- `.planning/REQUIREMENTS.md` - UI-01 through UI-09 specifications
- `.planning/ROADMAP.md` - Phase 59 plan descriptions and success criteria

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use, verified in codebase
- Architecture: HIGH - following exact patterns from Phase 56 (ProjectSettingsModal) and existing context menu code
- Pitfalls: HIGH - identified from actual codebase analysis (SSE POST issue, merge guard, known bug)

**Research date:** 2026-03-23
**Valid until:** 2026-04-22 (30 days - stable project patterns)
