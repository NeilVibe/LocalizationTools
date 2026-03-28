# Bulk Load Architecture — Nuke Page-by-Page, Load Everything

> **STATUS: PLANNED. Must implement before next build.**

**Goal:** Load ALL rows on file open in ONE shot. Client-side search, filter, scroll. Zero API calls during browsing. Kill the 1,700 HTTP round trips.

**Why:** Current architecture makes 1 API call per 100 rows. A 170K row file = 1,700 HTTP calls. Each triggers async state updates, height rebuilds, reactive cascades. This causes flickering, blank rows, stale data, page resets. QuickSearch loads everything into .pkl and works instantly. We need the same approach.

---

## Architecture Change

### BEFORE (broken):
```
File open → load page 1 (100 rows) → user scrolls → load page 2 → ... → page 1700
Search → API call → clear rows → reload filtered → API call → ...
Every scroll position = new API call = async state update = potential flicker
```

### AFTER (correct):
```
File open → ONE API call → ALL 170K rows → client memory (40MB)
Search → Array.filter() in memory → instant
Scroll → read from memory array → instant
Filter → Array.filter() in memory → instant
API calls ONLY for: upload, save edit, delete
```

---

## Implementation Plan

### Task 1: Bulk rows API endpoint

**File:** `server/tools/ldm/routes/rows.py`

Add `GET /files/{file_id}/rows/all` — returns ALL rows, no pagination:

```python
@router.get("/files/{file_id}/rows/all")
async def get_all_rows(
    file_id: int,
    repo = Depends(get_row_repository),
    current_user: dict = Depends(get_current_active_user_async)
):
    rows, total = await repo.get_for_file(file_id, page=1, limit=999999)
    return {"total": total, "rows": rows}
```

### Task 2: ScrollEngine — bulk load on file open

**File:** `locaNext/src/lib/components/ldm/grid/ScrollEngine.svelte`

Replace `loadRows()` + `loadPage()` page-by-page system:

```javascript
export async function loadRows() {
    if (!fileId) return;

    grid.rows = [];
    grid.loading = true;
    grid.initialLoading = true;

    // ONE call — ALL rows
    const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows/all`, {
        headers: getAuthHeaders()
    });

    if (response.ok) {
        const data = await response.json();
        grid.total = data.total;

        // Store ALL rows in memory
        data.rows.forEach((row, i) => {
            grid.rows[i] = { ...row, id: row.id.toString() };
            rowIndexById.set(row.id.toString(), i);
        });

        grid.rowsVersion++;
        rebuildCumulativeHeights(stripColorTags);
    }

    grid.loading = false;
    grid.initialLoading = false;
}
```

Delete: `loadPage()`, `ensureRowsLoaded()`, `ensureRowsLoadedImmediate()`, `prefetchAdjacentPages()`, `loadedPages`, `loadingPages`, `PREFETCH_PAGES`, throttle logic.

`calculateVisibleRange()` stays — it still determines which rows to RENDER. But it no longer triggers page loads.

### Task 3: SearchEngine — client-side filter

**File:** `locaNext/src/lib/components/ldm/grid/SearchEngine.svelte`

Replace API-based search with in-memory filter:

```javascript
function handleSearch() {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        const term = grid.searchTerm?.trim().toLowerCase();

        if (!term) {
            // No search — show all rows
            grid.filteredRows = null; // null = use grid.rows directly
            grid.total = grid.allRows.length;
        } else {
            // Filter in memory — instant
            grid.filteredRows = grid.allRows.filter(row => {
                for (const field of grid.searchFields) {
                    if (row[field]?.toLowerCase().includes(term)) return true;
                }
                return false;
            });
            grid.total = grid.filteredRows.length;
        }

        grid.rowsVersion++;
        rebuildCumulativeHeights(stripColorTags);
    }, 150); // Shorter debounce — no API call, just memory filter
}
```

### Task 4: gridState — add allRows + filteredRows

**File:** `locaNext/src/lib/components/ldm/grid/gridState.svelte.ts`

```javascript
export const grid = $state({
    allRows: [],        // ALL rows from DB (immutable after load)
    filteredRows: null,  // null = no filter active, array = filtered subset
    rows: [],            // DISPLAY rows (= filteredRows ?? allRows)
    // ... rest unchanged
});
```

`getVisibleRows()` reads from `grid.filteredRows ?? grid.allRows`.

### Task 5: Loading indicator

Show progress during initial bulk load:
- "Loading 170,668 rows..." with progress bar
- After load: "170,668 rows loaded. Search ready."

### Task 6: File status filter — client-side

Move confirmed/unconfirmed/qa_flagged filter to client-side too.

---

## Performance Budget

| File Size | Memory | Load Time | Search Time |
|-----------|--------|-----------|-------------|
| 10K rows | ~2MB | <1s | <10ms |
| 100K rows | ~20MB | 2-3s | <50ms |
| 200K rows | ~40MB | 3-5s | <100ms |
| 500K rows | ~100MB | 5-10s | <200ms |

All acceptable for a desktop Electron app with 8GB+ RAM.

---

## What This Eliminates

- ❌ loadPage() — gone
- ❌ ensureRowsLoaded() — gone
- ❌ ensureRowsLoadedImmediate() — gone
- ❌ prefetchAdjacentPages() — gone
- ❌ loadedPages Set — gone
- ❌ loadingPages Set — gone
- ❌ ENSURE_ROWS_THROTTLE_MS — gone
- ❌ MAX_PAGES_TO_LOAD — gone
- ❌ All blank row / stale position / flicker bugs — gone
- ❌ Search API calls — gone
- ❌ Filter API calls — gone
- ❌ 1,700 HTTP round trips — gone

## What Stays

- ✅ Virtual scroll (only render visible rows)
- ✅ Cumulative heights (variable row height)
- ✅ FTS5 index (for future server-side features)
- ✅ DB indexes (for future server-side features)
- ✅ Upload/save/delete API calls
