# Phase 3: TM Workflow - Research

**Researched:** 2026-03-14
**Domain:** Translation Memory management, semantic matching, tree UI, word-level diff
**Confidence:** HIGH

## Summary

Phase 3 builds the TM workflow on a foundation that is substantially already in place. The backend has a complete TM repository interface (TMRepository with 20+ methods), TM assignment system (platform/project/folder hierarchy), 5-tier cascade search (TMSearcher with hash, FAISS, n-gram tiers), and Model2Vec embedding engine. The frontend has TMExplorerTree (drag-drop, activation, context menu), TMManager (CRUD modal), TMPage (explorer grid), TMQAPanel (side panel with TM matches), and GridPage (VirtualGrid + side panel). The critical gap is: the TM tree does NOT auto-mirror file explorer structure on upload, the side panel shows raw percentage tags without color coding or word-level diff, there is no per-file leverage statistics display, and the tree/explorer styling is functional but not polished.

The user's additional context specifies that the right panel should evolve into a tabbed interface (TM | Image | Audio | AI Context) with toggle on/off capability. The TM tab should show matches with color-coded percentages and word-level diff highlighting. QuickTranslate merge patterns (StringID+StrOrigin+Desc, match types like strict, fuzzy, strorigin_only) inform the export workflow but the primary concern for Phase 3 is the live TM lookup display, not the merge/export engine.

**Primary recommendation:** Enhance existing components (TMQAPanel becomes tabbed right panel, TMExplorerTree gets auto-mirror trigger, add word-diff utility and leverage API) rather than building anything from scratch. All backend infrastructure exists.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TM-01 | TM tree auto-mirrors file explorer folder structure when files are uploaded | Backend has TMRepository.assign() and file upload routes. Need to add auto-create-TM-and-assign hook in file upload flow |
| TM-02 | User can assign TMs to folders/files through the mirrored tree | TMExplorerTree already has drag-drop assignment + assignTM(). TMRepository.assign() with AssignmentTarget works. Just needs polish |
| TM-03 | TM lookup shows match percentages with color coding (100%=green, fuzzy=yellow, no-match=red) | TMSearcher.search() returns score + match_type. TMQAPanel shows Tag with raw percentage. Need color-coding logic + word-diff |
| TM-04 | TM leverage statistics displayed per file | TMSearcher.search_batch() exists. Need new API endpoint for batch leverage computation and UI display |
| TM-05 | Model2Vec-based semantic matching | Already implemented: EmbeddingEngine with Model2Vec default, FAISS indexes, TMSearcher 5-tier cascade |
| UI-02 | File explorer tree view polished with professional appearance | ExplorerGrid exists in FilesPage but no tree view yet. Need CSS polish for Windows Explorer style |
| UI-03 | TM explorer tree view polished with assignment UI | TMExplorerTree exists with full functionality. Needs CSS polish to match Phase 2 grid quality |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Model2Vec (potion-multilingual-128M) | 256-dim | Semantic embeddings for fuzzy matching | DEPLOYED, working |
| FAISS | IndexHNSWFlat | Vector similarity search | DEPLOYED, working |
| Carbon Components Svelte | current | UI components (Tag, Button, Modal) | DEPLOYED |
| Svelte 5 | Runes | Frontend framework | DEPLOYED |
| FastAPI | current | Backend API | DEPLOYED |

### Supporting (New for Phase 3)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| diff-match-patch (JS) | Word-level diff highlighting | TM match display in right panel |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| diff-match-patch | Custom char-level diff | diff-match-patch is battle-tested, handles CJK correctly, and is 3KB gzipped |
| External diff lib | Inline word-diff function | For simple source-vs-TM-source diffs, a custom function comparing word arrays may suffice and avoid a dependency |

**Recommendation:** Use a lightweight custom word-diff function (split by whitespace/CJK chars, compare arrays) since the diff is only source-to-source comparison for TM matches. This avoids adding a dependency for a simple operation. If Korean word boundaries prove tricky, fall back to diff-match-patch.

## Architecture Patterns

### Existing Architecture (What We Build On)

```
GridPage.svelte
  |-- VirtualGrid.svelte (translation grid)
  |-- TMQAPanel.svelte (right side panel - TM + QA)
       |-- TM Matches section
       |-- QA Issues section

FilesPage.svelte
  |-- ExplorerGrid.svelte (Windows Explorer style)
  |-- Breadcrumb.svelte

TMPage.svelte
  |-- TMExplorerGrid.svelte (TM list/grid)

TMExplorerTree.svelte (tree view, used in older LDM layout)
```

### Target Architecture (Phase 3 Changes)

```
GridPage.svelte
  |-- VirtualGrid.svelte (unchanged)
  |-- RightPanel.svelte (NEW - replaces TMQAPanel)
       |-- TabBar: [TM] [Image] [Audio] [AI Context]
       |-- TMTab.svelte (enhanced TM matches with color + diff)
       |    |-- Color-coded percentage badges
       |    |-- Word-level diff highlighting
       |    |-- Leverage stats bar
       |-- ImageTab.svelte (placeholder for Phase 5)
       |-- AudioTab.svelte (placeholder for Phase 5)
       |-- AIContextTab.svelte (placeholder for Phase 5.1)

FilesPage.svelte (polish CSS)
  |-- ExplorerGrid.svelte (polish CSS)

TMPage.svelte (enhance)
  |-- TMExplorerTree.svelte (enhanced with auto-mirror)
  |-- TMExplorerGrid.svelte (polish CSS)
```

### Pattern 1: TM Auto-Mirror on File Upload
**What:** When files are uploaded to a folder, automatically create a TM for that folder (if none exists) and assign it
**When to use:** File upload route (server/tools/ldm/routes/files.py)
**Implementation:**
```python
# In the file upload handler, after successful file creation:
async def _auto_mirror_tm(folder_id: int, project_id: int, tm_repo: TMRepository):
    """Create and assign TM if folder has no active TM."""
    existing = await tm_repo.get_for_scope(folder_id=folder_id)
    if not existing:
        folder_name = ...  # Get from folder repo
        tm = await tm_repo.create(
            name=f"TM - {folder_name}",
            source_lang="ko",
            target_lang="en"
        )
        target = AssignmentTarget(folder_id=folder_id)
        await tm_repo.assign(tm["id"], target)
        await tm_repo.activate(tm["id"])
```

### Pattern 2: Color-Coded TM Match Percentages
**What:** Map match scores to colors using the project's established color system
**When to use:** TMTab component when displaying matches
**Implementation:**
```javascript
// Color bands matching project conventions (from Phase 2 decisions):
function getMatchColor(score) {
    if (score >= 1.0) return { color: '#24a148', label: 'Exact' };      // Green (confirmed)
    if (score >= 0.92) return { color: '#c6a300', label: 'High Fuzzy' }; // Yellow (draft)
    if (score >= 0.75) return { color: '#ff832b', label: 'Fuzzy' };      // Orange
    return { color: '#da1e28', label: 'Low' };                           // Red (error)
}
```

### Pattern 3: Word-Level Diff for TM Display
**What:** Highlight differences between the current source text and the TM match source text
**When to use:** TMTab when showing fuzzy matches (score < 1.0)
**Implementation:**
```javascript
// Simple word-level diff for source comparison
function computeWordDiff(original, match) {
    const origWords = tokenize(original);
    const matchWords = tokenize(match);
    // Use longest common subsequence to find unchanged words
    // Mark added/removed words with spans
    return { original: markedOriginal, match: markedMatch };
}

function tokenize(text) {
    // Split on whitespace AND between CJK characters
    return text.match(/[\u3000-\u9fff\uac00-\ud7af]|[^\s\u3000-\u9fff\uac00-\ud7af]+/g) || [];
}
```

### Pattern 4: Leverage Statistics API
**What:** Compute per-file TM match statistics (exact%, fuzzy%, new%)
**When to use:** File explorer and grid header
**Implementation:**
```python
# New endpoint: GET /api/ldm/files/{file_id}/leverage
# Uses TMSearcher.search_batch() to process all rows
@router.get("/files/{file_id}/leverage")
async def get_file_leverage(file_id: int, ...):
    rows = await row_repo.get_all(file_id)
    sources = [r["source"] for r in rows]
    results = searcher.search_batch(sources)
    stats = {
        "exact": sum(1 for r in results if r["perfect_match"]),
        "fuzzy": sum(1 for r in results if not r["perfect_match"] and r["results"]),
        "new": sum(1 for r in results if not r["results"]),
        "total": len(rows)
    }
    return stats
```

### Pattern 5: Tabbed Right Panel
**What:** Replace the current TMQAPanel with a tabbed interface
**When to use:** GridPage right panel
**Implementation:**
```svelte
<!-- RightPanel.svelte -->
<script>
    let activeTab = $state('tm');
    const tabs = [
        { id: 'tm', label: 'TM', icon: DataBase },
        { id: 'image', label: 'Image', icon: Image },
        { id: 'audio', label: 'Audio', icon: Music },
        { id: 'context', label: 'AI Context', icon: MachineLearning }
    ];
</script>

<div class="right-panel">
    <div class="tab-bar">
        {#each tabs as tab (tab.id)}
            <button class:active={activeTab === tab.id}
                    onclick={() => activeTab = tab.id}>
                <svelte:component this={tab.icon} size={14} />
                {tab.label}
            </button>
        {/each}
    </div>
    <div class="tab-content">
        {#if activeTab === 'tm'}
            <TMTab {selectedRow} {tmMatches} {tmLoading} />
        {:else if activeTab === 'image'}
            <div class="placeholder">Coming in Phase 5</div>
        {:else if activeTab === 'audio'}
            <div class="placeholder">Coming in Phase 5</div>
        {:else if activeTab === 'context'}
            <div class="placeholder">Coming in Phase 5.1</div>
        {/if}
    </div>
</div>
```

### Anti-Patterns to Avoid
- **Building a new TM backend:** The 5-tier cascade TMSearcher is already built and tested. Do NOT rewrite it.
- **Using pg_trgm for offline:** SQLite does not have pg_trgm. The TMSearcher with FAISS already handles this correctly for both modes.
- **Adding Qwen dependency:** MEMORY.md is explicit: "Model2Vec ONLY -- no Qwen until further notice."
- **Rebuilding tree from scratch:** TMExplorerTree.svelte is 1120 lines with drag-drop, multi-select, context menu. Polish it, don't replace it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TM search cascade | Custom search algorithm | TMSearcher 5-tier cascade (server/tools/ldm/indexing/searcher.py) | Already handles hash, FAISS, n-gram with proper thresholds |
| Embedding generation | Custom encoder | EmbeddingEngine (server/tools/shared/embedding_engine.py) | Already abstracts Model2Vec vs Qwen with lazy loading |
| TM CRUD | Direct DB queries | TMRepository interface (server/repositories/interfaces/tm_repository.py) | 20+ methods, works for both SQLite and PostgreSQL |
| TM assignment hierarchy | Custom scope resolution | get_active_for_file() in TMRepository | Already resolves folder -> project -> platform inheritance |
| Tree component | Custom tree from scratch | TMExplorerTree.svelte | 1120 lines with drag-drop, multi-select, context menu |
| File explorer | Custom file browser | ExplorerGrid.svelte + FilesPage.svelte | Full Windows Explorer clone already working |

**Key insight:** Phase 3 is 80% enhancement of existing code and 20% new functionality (auto-mirror trigger, color-coded percentages, word-diff, leverage stats, tabbed panel).

## Common Pitfalls

### Pitfall 1: TM Index Not Built After Auto-Mirror Create
**What goes wrong:** Auto-created TM has no FAISS index, so TMSearcher returns nothing
**Why it happens:** Creating a TM does not build indexes automatically; they need entries first
**How to avoid:** The auto-mirror creates an EMPTY TM. Indexes build when entries are added (via _auto_sync_tm_indexes background task). The TM is useful immediately for manual entry collection via confirm-and-add-to-TM flow.
**Warning signs:** TM shows "pending" status, search returns no results

### Pitfall 2: CJK Word-Level Diff Tokenization
**What goes wrong:** Korean/Japanese/Chinese text has no spaces, so word-level diff shows entire text as changed
**Why it happens:** Naive split-by-whitespace fails for CJK
**How to avoid:** Tokenizer must treat each CJK character as a separate token. The regex `[\u3000-\u9fff\uac00-\ud7af]|[^\s\u3000-\u9fff\uac00-\ud7af]+` handles this.
**Warning signs:** Diff shows entire Korean sentence highlighted as different when only one syllable changed

### Pitfall 3: Leverage Stats Performance
**What goes wrong:** Computing leverage for a 10K-segment file takes too long, blocking the UI
**Why it happens:** search_batch() on 10K segments with FAISS loads the model and runs 10K searches
**How to avoid:** Run leverage computation as a background task (FastAPI BackgroundTasks). Show a loading indicator. Cache results. Consider computing leverage only on demand (user clicks a button), not on every file open.
**Warning signs:** API call takes >5 seconds, UI freezes

### Pitfall 4: SQLite Mode Missing Features
**What goes wrong:** search_similar() returns empty in SQLite mode (no pg_trgm)
**Why it happens:** The TMRepository.search_similar() on SQLite returns [] by default
**How to avoid:** The TMSearcher 5-tier cascade (server/tools/ldm/indexing/searcher.py) already handles this correctly for both modes using FAISS. The /api/ldm/tm/suggest endpoint uses the old pg_trgm path. For Phase 3, ensure we use the TMSearcher cascade, not the repository's search_similar().
**Warning signs:** TM matches work online but not offline

### Pitfall 5: TMExplorerTree vs TMExplorerGrid Confusion
**What goes wrong:** Developer polishes the wrong component
**Why it happens:** TMExplorerTree.svelte (tree view with hierarchy) and TMExplorerGrid.svelte (flat grid list) serve different purposes
**How to avoid:** TMExplorerTree is the hierarchical tree (Platform > Project > Folder > TM) used for assignment. TMExplorerGrid is the flat list used in TMPage. Both need polish, but TMExplorerTree is the one relevant to TM-01/TM-02.

## Code Examples

### Existing: TMSearcher Result Format (from searcher.py)
```python
# TMSearcher.search() returns:
{
    "tier": 1,              # 1-5 (which cascade tier matched)
    "tier_name": "perfect_whole",  # or "whole_embedding", "perfect_line", etc.
    "perfect_match": True,   # exact match?
    "results": [
        {
            "entry_id": 42,
            "source_text": "원본 텍스트",
            "target_text": "Original text",
            "string_id": "STR_001",
            "score": 1.0,        # 0.0-1.0
            "match_type": "perfect_whole"  # or "whole_embedding", "ngram"
        }
    ]
}
```

### Existing: TMQAPanel TM Match Display (from TMQAPanel.svelte)
```svelte
<!-- Current: raw percentage tag -->
<Tag type="teal" size="sm">{Math.round(match.similarity * 100)}%</Tag>

<!-- Phase 3 target: color-coded with word diff -->
<Tag type={getTagType(match.similarity)} size="sm">
    {Math.round(match.similarity * 100)}%
</Tag>
{#if match.similarity < 1.0}
    <div class="word-diff">
        {@html renderWordDiff(selectedRow.source, match.source)}
    </div>
{/if}
```

### Existing: Active TMs Hierarchy (from GridPage.svelte)
```javascript
// GridPage already loads active TMs for file context:
const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/active-tms`, ...);
// Returns: [{ tm_id, tm_name, scope, scope_name, priority }]
```

### Existing: Auto-Add Entry on Confirm (from GridPage.svelte)
```javascript
// When user confirms translation, entry auto-added to active TM:
async function handleConfirmTranslation(event) {
    const { rowId, source, target } = event.detail;
    if (activeTMs.length > 0 && source && target) {
        const tmId = activeTMs[0].tm_id;
        // POST to /api/ldm/tm/{tmId}/entries
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Qwen-based TM matching | Model2Vec (79x faster) | Model2Vec migration | Faster search, lighter build |
| pg_trgm only | 5-tier cascade (hash+FAISS+ngram) | TMSearcher refactor | Works offline via FAISS |
| Single TM selection | TM hierarchy (platform>project>folder) | TM assignment system | Contextual TM per file |
| Modal TM viewer | TMExplorerTree + TMPage | Phase 10 UI overhaul | Integrated tree view |

## Open Questions

1. **Auto-mirror scope: folder-level or project-level TM?**
   - What we know: The TM hierarchy supports platform, project, and folder scopes
   - What's unclear: Should auto-mirror create per-folder TMs (mirrors file structure exactly) or per-project TMs (simpler, one TM per project)?
   - Recommendation: Start with per-project TM auto-creation (simpler, covers most use cases). User can manually create folder-level TMs for fine-grained control.

2. **Leverage stats: compute on open or on demand?**
   - What we know: search_batch() can process all rows but may be slow for large files
   - What's unclear: Performance characteristics for 10K+ segments
   - Recommendation: Compute on-demand with a "Analyze" button. Cache results per file (invalidate on TM entry changes). Show loading state.

3. **Right panel tab persistence**
   - What we know: User may switch tabs frequently
   - What's unclear: Should active tab be stored in preferences? Should all tabs load content or lazy-load?
   - Recommendation: Store in preferences ($preferences), lazy-load tab content (only TM tab active in Phase 3, others show placeholder).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (E2E) + pytest (backend) |
| Config file | `locaNext/playwright.config.ts`, `tests/conftest.py` |
| Quick run command | `cd locaNext && npx playwright test --grep "tm" -x` |
| Full suite command | `cd locaNext && npx playwright test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TM-01 | TM tree auto-mirrors file structure on upload | E2E | `npx playwright test tests/tm-auto-mirror.spec.ts -x` | Wave 0 |
| TM-02 | User assigns TM via tree drag-drop | E2E | `npx playwright test tests/tm-assignment-test.spec.ts -x` | Exists (needs update) |
| TM-03 | TM matches show color-coded percentages + word diff | E2E | `npx playwright test tests/tm-color-diff.spec.ts -x` | Wave 0 |
| TM-04 | Leverage statistics per file | API + E2E | `pytest tests/api/test_leverage.py -x` | Wave 0 |
| TM-05 | Model2Vec semantic matching works | API | `pytest tests/api/test_tm_search.py -x` | Wave 0 |
| UI-02 | File explorer polished | E2E visual | `npx playwright test tests/file_explorer_crud.spec.ts -x` | Exists |
| UI-03 | TM explorer polished | E2E visual | `npx playwright test tests/tm-explorer-polish.spec.ts -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd locaNext && npx playwright test --grep "tm" -x`
- **Per wave merge:** Full Playwright suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `locaNext/tests/tm-auto-mirror.spec.ts` -- covers TM-01 (upload triggers TM creation)
- [ ] `locaNext/tests/tm-color-diff.spec.ts` -- covers TM-03 (color-coded matches, word diff display)
- [ ] `locaNext/tests/tm-explorer-polish.spec.ts` -- covers UI-03 (visual quality assertions)
- [ ] `tests/api/test_leverage.py` -- covers TM-04 (leverage stats API)
- [ ] `tests/api/test_tm_search.py` -- covers TM-05 (Model2Vec cascade search)

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of:
  - `server/repositories/interfaces/tm_repository.py` -- 20+ method TM interface
  - `server/tools/ldm/indexing/searcher.py` -- 5-tier cascade TMSearcher
  - `server/tools/shared/embedding_engine.py` -- Model2Vec/Qwen abstraction
  - `server/tools/ldm/routes/tm_assignment.py` -- TM hierarchy assignment
  - `server/tools/ldm/routes/tm_search.py` -- TM suggest/search endpoints
  - `locaNext/src/lib/components/ldm/TMExplorerTree.svelte` -- 1120-line tree component
  - `locaNext/src/lib/components/ldm/TMQAPanel.svelte` -- current right panel
  - `locaNext/src/lib/components/pages/GridPage.svelte` -- grid + side panel layout
  - `locaNext/src/lib/components/pages/FilesPage.svelte` -- file explorer page
  - `locaNext/src/lib/components/pages/TMPage.svelte` -- TM explorer page

### Secondary (MEDIUM confidence)
- QuickTranslate merge patterns from `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py`
- QuickTranslate fuzzy matching from `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/fuzzy_matching.py`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- everything is already deployed and working
- Architecture: HIGH -- direct code analysis, all components identified and read
- Pitfalls: HIGH -- based on actual code behavior (SQLite gaps, CJK tokenization, performance)
- TM auto-mirror: MEDIUM -- new feature, design choices needed (project vs folder scope)

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable codebase, no external dependencies changing)
