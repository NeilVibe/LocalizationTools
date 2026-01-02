# Advanced Search Feature

**Created:** 2025-12-28 | **Updated:** 2026-01-02 | **Priority:** P5 | **Status:** ✅ IMPLEMENTED

---

## Goal

Add search mode options to VirtualGrid search bar:
- **Contain** (default) - text contains search term
- **Exact** - exact match only
- **Not Contain** - exclude rows containing term
- **Fuzzy** - semantic search using Model2Vec embeddings

---

## Search Fields

| Field | Available | Notes |
|-------|-----------|-------|
| StringID | YES | Unique identifier |
| Source | YES | Korean text |
| Target | YES | Translated text |
| Reference | YES | From reference file |
| Metadata | FUTURE | Extensible for future fields |

---

## Implementation Plan

### Step 1: UI - Add Search Mode Dropdown

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte`

```svelte
<!-- Add dropdown next to search bar -->
<Dropdown
  size="sm"
  selectedId={searchMode}
  items={searchModeOptions}
  on:select={handleSearchModeChange}
/>
```

**Options:**
```javascript
const searchModeOptions = [
  { id: "contain", text: "Contains" },
  { id: "exact", text: "Exact Match" },
  { id: "not_contain", text: "Does Not Contain" },
  { id: "fuzzy", text: "Fuzzy (Semantic)" }
];
```

### Step 2: UI - Add Search Field Selector

**Multi-select checkboxes or dropdown:**
```javascript
const searchFieldOptions = [
  { id: "string_id", text: "StringID", default: true },
  { id: "source", text: "Source", default: true },
  { id: "target", text: "Target", default: true }
];
```

### Step 3: Backend - Extend Search API

**File:** `server/tools/ldm/routes/rows.py`

**Current endpoint:** `GET /api/ldm/files/{file_id}/rows?search=term`

**New params:**
- `search_mode`: contain | exact | not_contain | fuzzy
- `search_fields`: comma-separated list (string_id,source,target)

**Example:**
```
GET /api/ldm/files/123/rows?search=hello&search_mode=fuzzy&search_fields=source,target
```

### Step 4: Fuzzy Search Integration

Use existing Model2Vec (potion-multilingual-128M) for semantic search:

1. Encode search term to vector
2. Compare with row embeddings
3. Return rows above similarity threshold

**Existing code:** `server/tools/ldm/indexing/` has Model2Vec setup

---

## Files to Modify

| File | Changes |
|------|---------|
| `VirtualGrid.svelte` | Add search mode dropdown, field selector |
| `routes/rows.py` | Handle search_mode and search_fields params |
| `tm_manager.py` | Add fuzzy search using Model2Vec |

---

## Test Plan

| Test | Description |
|------|-------------|
| Contain | Search "hello" finds "hello world" |
| Exact | Search "hello" does NOT find "hello world" |
| Not Contain | Search "test" excludes all rows with "test" |
| Fuzzy | Search "greeting" finds "hello", "bonjour", "hi" |
| Field Filter | Search only in StringID, not source/target |

---

## Notes

- Fuzzy search uses Model2Vec (fast, ~29K sentences/sec)
- NOT using Qwen for search (too slow for real-time)
- Color tags should be stripped before search matching

---

---

## Implementation Notes (Session 15)

**Frontend (VirtualGrid.svelte):**
- Added `searchMode` state: contain, exact, not_contain, fuzzy
- Added `searchFields` state: array of string_id, source, target
- **New UI (Session 16):** Combined search control with settings popover
  - Mode indicator button with icon (⊃ = Contains, = = Exact, ≠ = Excludes, ≈ = Similar)
  - Click to open settings popover with mode grid + field toggles
  - Cleaner, more compact design
- API calls include `search_mode` and `search_fields` params

**Backend (rows.py):**
- Added `search_mode` and `search_fields` query params
- Exact: `func.lower(column) == func.lower(search)`
- Not contain: `~column.ilike(pattern)` with AND logic
- Contain/Fuzzy: `column.ilike(pattern)` with OR logic

**Fuzzy (IMPLEMENTED - Session 16):**
- Uses PostgreSQL pg_trgm extension for trigram similarity
- Threshold: 0.3 (configurable in rows.py)
- Results ordered by similarity score
- Falls back to ILIKE (contain mode) on SQLite

---

*Implemented 2026-01-02 by Claude*
