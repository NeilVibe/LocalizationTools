---
phase: 62-tm-auto-update-pipeline
plan: 01
subsystem: database
tags: [faiss, hnsw, idmap2, embedding, model2vec, thread-safety, tm]

# Dependency graph
requires: []
provides:
  - "FAISSManager IDMap2 support (create_idmap_index, add_with_ids, remove_ids, convert_to_idmap)"
  - "ThreadSafeIndex class for concurrent FAISS access"
  - "InlineTMUpdater service for per-entry FAISS+hash CRUD"
  - "get_inline_updater() cached factory function"
affects: [62-02, 63-performance-instrumentation]

# Tech tracking
tech-stack:
  added: []
  patterns: [IndexIDMap2-FlatIP-wrapper, thread-safe-index-rlock, inline-updater-lazy-load]

key-files:
  created:
    - server/tools/ldm/indexing/inline_updater.py
  modified:
    - server/tools/shared/faiss_manager.py
    - server/tools/shared/__init__.py

key-decisions:
  - "Used IndexFlatIP instead of IndexHNSWFlat as IDMap2 sub-index because HNSW does not support remove_ids"
  - "IDSelectorBatch for remove_ids (IDSelectorArray not compatible with IDMap2)"

patterns-established:
  - "IDMap2(FlatIP) pattern: exact inner-product search with add/remove by ID"
  - "ThreadSafeIndex with RLock for concurrent FAISS operations"
  - "InlineTMUpdater lazy-load pattern: engine+index+lookups loaded on first use"

requirements-completed: [TMAU-01, TMAU-02, TMAU-03]

# Metrics
duration: 5min
completed: 2026-03-23
---

# Phase 62 Plan 01: FAISS IDMap2 Extensions + InlineTMUpdater Summary

**FAISSManager extended with IndexIDMap2(FlatIP) for ID-based add/remove, plus InlineTMUpdater service for synchronous per-entry FAISS + hash PKL updates**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-23T05:17:37Z
- **Completed:** 2026-03-23T05:22:09Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Extended FAISSManager with 4 new methods (create_idmap_index, add_with_ids, remove_ids, convert_to_idmap) without touching existing methods
- Created ThreadSafeIndex class with RLock for concurrent FAISS access
- Built InlineTMUpdater service with add_entry, update_entry, remove_entry, and add_entries_batch
- Hash PKL update logic faithfully mirrors sync_manager._incremental_sync patterns

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend FAISSManager with IDMap2 and thread-safe operations** - `37cca82f` (feat)
2. **Task 2: Create InlineTMUpdater service** - `4d90c55e` (feat)

## Files Created/Modified
- `server/tools/shared/faiss_manager.py` - Added create_idmap_index, add_with_ids, remove_ids, convert_to_idmap classmethods + ThreadSafeIndex class
- `server/tools/shared/__init__.py` - Exported ThreadSafeIndex
- `server/tools/ldm/indexing/inline_updater.py` - New InlineTMUpdater service with CRUD operations, batch support, lazy-loading, caching

## Decisions Made
- Used IndexFlatIP instead of IndexHNSWFlat as IDMap2 sub-index because HNSW does not support remove_ids. For typical TM sizes (<100K entries), FlatIP provides adequate search speed with full add/remove support.
- Used IDSelectorBatch for remove_ids (IDSelectorArray was not compatible with IDMap2 in this FAISS version)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IndexHNSWFlat does not support remove_ids**
- **Found during:** Task 1 (FAISSManager IDMap2 extension)
- **Issue:** Plan specified IndexIDMap2(IndexHNSWFlat) but HNSW indexes cannot remove vectors -- remove_ids raises RuntimeError
- **Fix:** Used IndexFlatIP as the sub-index instead. Exact inner product search, fully supports add_with_ids and remove_ids.
- **Files modified:** server/tools/shared/faiss_manager.py
- **Verification:** Full add/remove cycle verified in Python REPL
- **Committed in:** 37cca82f (Task 1 commit)

**2. [Rule 1 - Bug] IDSelectorArray incompatible with IDMap2**
- **Found during:** Task 1 (FAISSManager IDMap2 extension)
- **Issue:** IDSelectorArray did not work for remove_ids on IDMap2 indexes
- **Fix:** Switched to IDSelectorBatch which works correctly
- **Files modified:** server/tools/shared/faiss_manager.py
- **Verification:** remove_ids returns correct count, ntotal decrements properly
- **Committed in:** 37cca82f (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes were necessary for correctness. IndexFlatIP provides equivalent functionality for the target use case. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FAISSManager IDMap2 API ready for plan 62-02 to wire into TM CRUD route handlers
- InlineTMUpdater provides the complete add/update/remove interface
- ThreadSafeIndex ensures concurrent HTTP requests can safely modify the index
- Existing HNSW indexes will be auto-migrated to IDMap2 on first load via convert_to_idmap

## Self-Check: PASSED

- All created files verified on disk (3/3)
- All commit hashes verified in git log (2/2)

---
*Phase: 62-tm-auto-update-pipeline*
*Completed: 2026-03-23*
