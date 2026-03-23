---
phase: 62-tm-auto-update-pipeline
plan: 02
subsystem: api
tags: [faiss, inline-update, tm-crud, batch-indexing, search-consistency]

# Dependency graph
requires:
  - phase: 62-01
    provides: "InlineTMUpdater service with add_entry, update_entry, remove_entry, add_entries_batch"
provides:
  - "Inline FAISS+hash updates on TM add/edit/delete (immediate search consistency)"
  - "Batch inline indexing on TM upload (replaces full background rebuild)"
  - "Error fallback to background sync on inline update failure"
affects: [63-performance-instrumentation]

# Tech tracking
tech-stack:
  added: []
  patterns: [inline-update-before-response, batch-upload-via-asyncio-to-thread, pre-modification-data-capture]

key-files:
  created: []
  modified:
    - server/tools/ldm/routes/tm_entries.py
    - server/tools/ldm/routes/tm_crud.py

key-decisions:
  - "Added _get_entry_by_id helper for pre-modification data capture instead of skipping old_source_text"
  - "Search consistency is automatic -- TMSearcher loads fresh indexes from disk per request, no cache invalidation needed"
  - "Upload batch indexing queries all entries from DB after insert rather than piping from TMManager"

patterns-established:
  - "Inline-update-before-response: CRUD endpoints update FAISS+hash synchronously, wrapped in try/except with background fallback"
  - "Pre-modification capture: fetch old entry data via asyncio.to_thread before DB modification for proper index cleanup"

requirements-completed: [TMAU-04, TMAU-05]

# Metrics
duration: 4min
completed: 2026-03-23
---

# Phase 62 Plan 02: Wire Inline Updates into TM CRUD Endpoints Summary

**All TM CRUD endpoints (add/edit/delete/upload) now update FAISS index and hash lookups inline before HTTP response, giving users immediate search consistency**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T05:25:22Z
- **Completed:** 2026-03-23T05:29:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Wired InlineTMUpdater into POST/PUT/DELETE endpoints in tm_entries.py with try/except fallback
- Added _get_entry_by_id async helper for pre-modification data capture (old source text for proper hash cleanup)
- Replaced background trigger_auto_indexing with batch inline add_entries_batch in upload endpoint
- Confirmed search consistency is automatic (TMSearcher loads indexes from disk per request)

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace background sync with inline updates in tm_entries.py** - `16cbe420` (feat)
2. **Task 2: Wire batch import and ensure search consistency** - `4347864f` (feat)

## Files Created/Modified
- `server/tools/ldm/routes/tm_entries.py` - Added inline updater calls for add/edit/delete with background fallback, plus _get_entry_by_id helper
- `server/tools/ldm/routes/tm_crud.py` - Replaced trigger_auto_indexing with batch inline indexing via asyncio.to_thread

## Decisions Made
- Added `_get_entry_by_id` helper using asyncio.to_thread with sync DB query rather than skipping old_source_text. This enables proper FAISS vector removal and hash cleanup on edit/delete operations.
- TMSearcher consistency is automatic -- it instantiates per-request via `TMIndexer.load_indexes()` which reads from disk. Since `InlineTMUpdater._persist()` writes to disk, no cache invalidation mechanism was needed.
- For upload batch indexing, entries are fetched from DB after insert (rather than piped from TMManager) because TMManager.upload_tm() doesn't return individual entry data.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added _get_entry_by_id helper for pre-modification data**
- **Found during:** Task 1 (tm_entries.py wiring)
- **Issue:** No `get_entry(entry_id)` method exists on TMRepository interface. Update and delete endpoints need old source_text for proper FAISS vector removal and hash cleanup.
- **Fix:** Added async helper `_get_entry_by_id()` that queries LDMTMEntry by ID via `asyncio.to_thread` with a sync DB session, returning source_text/target_text/string_id.
- **Files modified:** server/tools/ldm/routes/tm_entries.py
- **Committed in:** 16cbe420 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The helper was necessary for correct index cleanup. Plan anticipated this gap and suggested a simpler approach (skip old_source_text), but adding the helper was straightforward and provides better data consistency.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full TM CRUD pipeline is now inline: add/edit/delete = synchronous, upload = batch via thread
- Search returns fresh results immediately after any TM modification
- Background sync preserved as error fallback only
- Ready for Phase 63 performance instrumentation to measure inline update latency

## Self-Check: PASSED

- All modified files verified on disk (2/2)
- All commit hashes verified in git log (2/2)

---
*Phase: 62-tm-auto-update-pipeline*
*Completed: 2026-03-23*
