# Architecture Patterns: Demo-Ready CAT Tool

**Domain:** Desktop CAT tool / game localization management platform
**Researched:** 2026-03-14

## Recommended Architecture

The existing architecture (Repository pattern, DB Factory, 3-mode detection) is sound and does not need redesign. This document focuses on UI architecture patterns needed for the demo-ready milestone.

### Component Boundaries (UI Focus)

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **TranslationGrid** | Core editor: source/target columns, virtual scrolling, cell editing | TM Panel, Status Bar, Search |
| **TMPanel** | Shows TM matches for selected segment, glossary terms, concordance results | TranslationGrid (selected segment), TM API |
| **FileExplorer** | Platform > Project > Folder > File navigation tree | TranslationGrid (file selection), Upload API |
| **TMExplorerTree** | TM management: create, assign, activate, browse TM entries | TM API, TMPanel (active TMs) |
| **SearchBar** | Find/replace across segments, concordance search trigger | TranslationGrid (highlight + navigate), TM API (concordance) |
| **QAPanel** | Run QA checks, display results, navigate to errors | TranslationGrid (error navigation), QA API |
| **StatusBar** | Segment count, translation progress, current TM info | TranslationGrid, TMPanel |
| **LeverageStats** | File analysis: match percentage breakdown | TM API, File data |

### Data Flow

```
User navigates to segment
        |
        v
TranslationGrid ──(selected source text)──> TMPanel
        |                                       |
        |                                       v
        |                              TM API: search_exact() + search_similar()
        |                                       |
        |                                       v
        |                              TMPanel shows: 100% matches, fuzzy matches
        |                              with diff highlighting and percentages
        |
        v
User edits target text
        |
        v
TranslationGrid ──(optimistic update)──> UI shows change instantly
        |
        v
Row API: update_row() ──> Repository ──> SQLite or PostgreSQL
        |
        v
Success: keep change / Failure: revert + show error toast
```

## Patterns to Follow

### Pattern 1: Optimistic UI with Revert (Already Mandated)
**What:** UI updates instantly on user action. Background API call. Revert on failure.
**When:** Every write operation (edit cell, confirm segment, assign TM).
**Example:**
```svelte
let segments = $state([]);
let pendingEdits = $state(new Map());

async function saveEdit(segmentId, newTarget) {
    const oldTarget = segments.find(s => s.id === segmentId).target;
    // Optimistic: update immediately
    segments.find(s => s.id === segmentId).target = newTarget;
    pendingEdits.set(segmentId, true);

    try {
        await api.updateRow(segmentId, { target: newTarget });
    } catch (e) {
        // Revert on failure
        segments.find(s => s.id === segmentId).target = oldTarget;
        showToast('Save failed', 'error');
    } finally {
        pendingEdits.delete(segmentId);
    }
}
```

### Pattern 2: Virtual Scrolling for Grid
**What:** Only render visible rows (~50-100) in the translation grid. Track scroll position. Load rows as user scrolls.
**When:** Any file with more than 200 segments.
**Why:** 10,000+ DOM rows will destroy performance. This is the single most important performance pattern.

### Pattern 3: Selected-Segment-Driven Panels
**What:** All side panels (TM matches, glossary, QA) react to which segment is currently selected in the grid. Single source of truth: `selectedSegmentId`.
**When:** Always. This is the CAT tool interaction model that every professional tool uses.
**Example:**
```svelte
let selectedSegmentId = $state(null);
let selectedSource = $derived(
    segments.find(s => s.id === selectedSegmentId)?.source ?? ''
);

// TMPanel auto-searches when selectedSource changes
$effect(() => {
    if (selectedSource) {
        searchTM(selectedSource);
    }
});
```

### Pattern 4: Debounced Search
**What:** Search triggers after 300ms of no typing, not on every keystroke.
**When:** Concordance search, filter-by-text, find/replace.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Full Re-render on Cell Edit
**What:** Editing one cell causes the entire grid to re-render.
**Why bad:** Visible flicker, lost scroll position, performance degradation.
**Instead:** Key each row by segment ID. Update only the changed cell's reactive state.

### Anti-Pattern 2: Fetching All TM Entries on Page Load
**What:** Loading all TM entries (could be 100K+) into memory when opening a file.
**Why bad:** Memory explosion, slow initial load.
**Instead:** Search TM on-demand per selected segment. Paginate TM browser. Use FAISS index for search, not full scan.

### Anti-Pattern 3: Mode-Specific UI Code
**What:** `if (offlineMode) { ... } else { ... }` scattered throughout components.
**Why bad:** Defeats the purpose of the repository abstraction layer.
**Instead:** Components call the same API endpoints. The backend routes to the correct repository. UI should not know or care which mode it is in (except for showing a mode indicator in the status bar).

## Scalability Considerations

| Concern | At 100 segments | At 10K segments | At 100K segments |
|---------|-----------------|-----------------|-------------------|
| Grid rendering | Direct DOM, no virtual scroll needed | Virtual scrolling mandatory | Virtual scrolling + chunked loading |
| TM search | Instant (in-memory) | FAISS index lookup (<100ms) | FAISS index lookup (<200ms) |
| File upload | Instant parsing | 1-3s parsing acceptable | Background parsing with progress bar |
| Export | Instant | 1-3s acceptable | Background export with progress bar |

## Sources

- LocaNext ARCHITECTURE_SUMMARY.md — Repository pattern, 3-mode detection, optimistic UI mandate
- [memoQ editor docs](https://docs.memoq.com/current/en/Concepts/concepts-translation-memories.html) — segment-driven TM panel pattern
- [Smartcat editor overview](https://help.smartcat.com/1539449-editor-functionalities-overview/) — CAT panel layout, toolbar, editing area separation
