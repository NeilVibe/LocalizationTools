---
phase: 62-tm-auto-update-pipeline
verified: 2026-03-23T07:00:00Z
status: human_needed
score: 8/8 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 7/8
  gaps_closed:
    - "Tier 4 line-embedding FAISS not persisted by _persist() — _persist() now writes line.index via FAISSManager.build_index and also persists line.npy and line_mapping.pkl, with stale-file cleanup when no line embeddings remain"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Add TM entry then immediately search for a fragment of that entry's source text"
    expected: "New entry appears in search results at Tier 1, 2, or 3 (not just Tier 4). Confirm search latency is under 100ms."
    why_human: "Cannot verify end-to-end latency or UI refresh behavior programmatically without a running server"
  - test: "Upload a TM file, then search for an entry from it"
    expected: "Entries searchable immediately after upload response returns (batch indexing ran inline, not in background)"
    why_human: "Batch indexing path uses asyncio.to_thread; needs live server to confirm entries are indexed before response"
  - test: "Edit a TM entry's source text from 'Hello world' to 'Goodbye world', then search for 'Hello world'"
    expected: "Old entry no longer appears in search results; 'Goodbye world' version does"
    why_human: "Requires live data and running server to confirm _remove_from_whole_lookup correctly purges the old hash key"
---

# Phase 62: TM Auto-Update Pipeline Verification Report

**Phase Goal:** Users get a fully automatic TM flow where every add/edit immediately updates embeddings and FAISS index -- search always returns current results with zero manual intervention
**Verified:** 2026-03-23T07:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plan 62-03 executed)

---

## Re-verification Summary

Previous verification (2026-03-23T05:30:54Z) found 1 gap:

- **Tier 4 line-embedding FAISS not persisted:** `_persist()` wrote `whole.index` but never wrote `line.index` or `line.npy`. Tier 4 search would remain stale for inline-added entries until a full background sync ran.

Plan 62-03 was executed to close this gap. The fix has been verified in the codebase.

**Gap closure confirmed:** `_persist()` at lines 546-592 of `inline_updater.py` now:
1. Writes `line.npy` (line embeddings array) — line 573
2. Calls `FAISSManager.build_index(self._line_embeddings, path=.../faiss/line.index, normalize=True)` to rebuild the positional FAISS index — lines 576-580
3. Cleans up stale `line.index` and `line.npy` when no line embeddings remain — lines 583-588
4. Always writes `line_mapping.pkl` (even when empty, to prevent searcher loading stale data) — lines 591-592

All 4 of these writes were absent in the previous version. No regressions detected on the 7 previously-passing items.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | FAISSManager supports ID-based add and remove operations on HNSW indexes | VERIFIED | `create_idmap_index`, `add_with_ids`, `remove_ids` all present and substantive in `faiss_manager.py`; uses IndexIDMap2(FlatIP) with IDSelectorBatch |
| 2 | InlineTMUpdater can encode a single entry and add it to FAISS + hash lookups in one synchronous call | VERIFIED | `add_entry()` — encode, normalize, `_ts_index.add_with_ids()`, `_add_to_whole_lookup()`, `_add_to_line_lookup()`, `_add_to_line_embeddings()`, `_persist()` all in one call |
| 3 | InlineTMUpdater can remove an old vector and add a new one for edit operations | VERIFIED | `update_entry()` — IDSelectorBatch remove, hash cleanup, line embedding removal, new encode+add, persist |
| 4 | InlineTMUpdater can remove a vector for delete operations | VERIFIED | `remove_entry()` — IDSelectorBatch remove, hash cleanup, line embedding removal, mapping removal, persist |
| 5 | Concurrent access to the FAISS index is thread-safe via a lock | VERIFIED | `ThreadSafeIndex` class with `threading.RLock()`, guards `add_with_ids`, `remove_ids`, `search` |
| 6 | Adding a TM entry via POST /tm/{id}/entries updates FAISS index inline before response returns | VERIFIED | `tm_entries.py` — `get_inline_updater(tm_id)` + `updater.add_entry()` called before `return`; fallback to background sync on exception |
| 7 | Editing and deleting TM entries update FAISS inline before response returns | VERIFIED | `update_tm_entry` and `delete_tm_entry` both call inline updater before return; `_get_entry_by_id` helper fetches old source_text for clean hash removal |
| 8 | Searching for a just-added/edited term returns the updated entry in results without page reload (all tiers) | VERIFIED | `_persist()` now writes `whole.index`, `whole_lookup.pkl`, `line_lookup.pkl`, `whole_mapping.pkl`, `whole.npy`, `line.npy`, `line.index`, `line_mapping.pkl`. All 4 search tiers are consistent after each inline operation. |

**Score:** 8/8 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/tools/shared/faiss_manager.py` | IDMap2 wrapper, add_with_ids, remove_ids, build_index, thread-safe index holder | VERIFIED | All methods present. `build_index` confirmed at line 247. `IndexIDMap2(FlatIP)` correctly used (HNSW does not support remove_ids). |
| `server/tools/ldm/indexing/inline_updater.py` | InlineTMUpdater with add_entry, update_entry, remove_entry, full Tier 4 persistence | VERIFIED | 612-line file (grown from 489). All public methods present. `_persist()` now writes all 8 artifacts including `line.index` and `line.npy`. |
| `server/tools/ldm/routes/tm_entries.py` | Inline index updates on add/edit/delete endpoints | VERIFIED | All 3 CRUD endpoints call `get_inline_updater`; try/except fallback preserved |
| `server/tools/ldm/routes/tm_crud.py` | Batch inline update on upload endpoint | VERIFIED | `get_inline_updater(tm_id)` + `asyncio.to_thread(updater.add_entries_batch, ...)` with fallback |
| `server/tools/ldm/indexing/searcher.py` | Fresh index loading for search consistency | VERIFIED | `TMSearcher` is per-request. `TMIndexer.load_indexes()` reads all files fresh from disk — no stale module-level cache. Now consistent for all tiers including Tier 4. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `inline_updater.py` | `faiss_manager.py` | `FAISSManager.create_idmap_index, add_with_ids, remove_ids, build_index` | WIRED | Direct import; all 4 methods called in mutation methods and `_persist()` |
| `inline_updater.py` | `embedding_engine.py` | `EmbeddingEngine.encode()` | WIRED | `get_embedding_engine(engine_name)` in `_ensure_loaded()`; `self._engine.encode()` in all mutation methods |
| `tm_entries.py` | `inline_updater.py` | `get_inline_updater(tm_id)` | WIRED | Import at line 24; called in all 3 CRUD endpoints |
| `tm_crud.py` | `inline_updater.py` | `add_entries_batch` | WIRED | Import confirmed; `updater.add_entries_batch` called via `asyncio.to_thread` |
| `_persist()` | `line.index` on disk | `FAISSManager.build_index(line_embeddings, path=.../faiss/line.index)` | WIRED | Lines 576-580 of `inline_updater.py` — previously NOT_WIRED, now WIRED |
| `searcher.py` | `line.index` on disk | `TMIndexer.load_indexes()` fresh per-request | WIRED | Searcher loads fresh from disk; inline updater now writes fresh `line.index` — full consistency achieved |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TMAU-01 | 62-01 | TM entry add triggers automatic embedding generation | SATISFIED | `add_entry()` calls `self._engine.encode()` synchronously |
| TMAU-02 | 62-01 | TM entry add triggers incremental HNSW add_items (no full rebuild) | SATISFIED | `add_entry()` calls `_ts_index.add_with_ids()` — per-entry add, no rebuild |
| TMAU-03 | 62-01 | TM entry edit triggers embedding re-computation + HNSW update | SATISFIED | `update_entry()` removes old vector, re-encodes, adds new; `remove_entry()` removes cleanly |
| TMAU-04 | 62-02 | TM batch import triggers bulk embedding + HNSW batch add | SATISFIED | `tm_crud.py` upload calls `add_entries_batch` via `asyncio.to_thread` for all entries |
| TMAU-05 | 62-02/03 | Search returns updated results immediately after add/edit (no manual refresh) | SATISFIED | All tiers now consistent. `_persist()` writes `line.index` so Tier 4 line-embedding search reflects inline-added entries immediately. |

All 5 requirement IDs (TMAU-01 through TMAU-05) are satisfied. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `inline_updater.py` | 223, 281 | `import faiss as _faiss` inside method body | Info | Lazy import inside `update_entry` and `remove_entry`. Minor inconsistency — no functional impact since `_ensure_loaded()` already loaded faiss via FAISSManager. |

The previous Blocker anti-pattern (`_persist()` not saving `line.index`) is confirmed resolved.

---

## Human Verification Required

All automated checks pass. The following items require a live server to confirm end-to-end behavior.

### 1. End-to-End Add-Then-Search (All Tiers)

**Test:** Add a new TM entry via the TM Viewer UI, then immediately search for a distinctive word from that entry's source text.
**Expected:** The new entry appears in search results without any manual index rebuild. Response time for the add endpoint should be under 500ms.
**Why human:** Cannot verify UI reactivity or end-to-end latency without a running server and browser session.

### 2. Batch Upload Index Confirmation

**Test:** Upload a TM file with 100+ entries, then immediately search for an entry from that file (without navigating away or waiting).
**Expected:** Entry is found in search results. The upload response should include `indexing_status: "completed"` (not `"scheduled"`).
**Why human:** Batch indexing runs via `asyncio.to_thread` — need live server to confirm it completes before the HTTP response for large files.

### 3. Edit Operation Hash Cleanup

**Test:** Edit a TM entry's source text from "Hello world" to "Goodbye world", then search for "Hello world".
**Expected:** Old entry no longer appears in search results; "Goodbye world" version does.
**Why human:** Requires live data and running server to confirm `_remove_from_whole_lookup` correctly purges the old hash key.

---

## Gaps Summary

No gaps remain. The single gap from the initial verification (Tier 4 line-embedding FAISS not persisted by `_persist()`) has been closed by Plan 62-03. The `_persist()` method now writes all 8 on-disk artifacts required for consistent search across all 4 tiers (whole hash, whole FAISS, line hash, line FAISS).

The phase goal — "fully automatic TM flow where every add/edit immediately updates embeddings and FAISS index, search always returns current results with zero manual intervention" — is achieved at the code level. Human verification items above confirm end-to-end behavior in a live environment.

---

_Verified: 2026-03-23T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after Plan 62-03 gap closure_
