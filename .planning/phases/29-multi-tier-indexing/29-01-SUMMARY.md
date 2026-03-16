---
phase: 29-multi-tier-indexing
plan: 01
subsystem: indexing
tags: [faiss, ahocorasick, model2vec, hnsw, hashtable, cascade-search, gamedata]

# Dependency graph
requires:
  - phase: 28-hierarchical-tree-ui
    provides: "TreeNode schema, EDITABLE_ATTRS mapping, folder tree loading"
provides:
  - "GameDataIndexer: hash + FAISS + AC indexes from TreeNode entities"
  - "GameDataSearcher: 6-tier cascade search (AC, hash, FAISS, ngram)"
  - "Pydantic schemas for index API (build, search, status)"
affects: [29-02-api-endpoints, 29-03-frontend-integration, 30-context-intelligence]

# Tech tracking
tech-stack:
  added: []
  patterns: [in-memory-faiss, br-tag-line-splitting, key-strkey-indexing, ac-entity-detection]

key-files:
  created:
    - server/tools/ldm/indexing/gamedata_indexer.py
    - server/tools/ldm/indexing/gamedata_searcher.py
    - tests/unit/ldm/test_gamedata_indexer.py
    - tests/unit/ldm/test_gamedata_searcher.py
  modified:
    - server/tools/ldm/schemas/gamedata.py

key-decisions:
  - "FAISSManager.build_index with path=None for in-memory indexes (no disk persistence)"
  - "AC automaton stores (idx, name, node_id, tag) tuple for direct entity detection"
  - "Whole lookup indexes 3 keys per entity: name, Key attr, StrKey attr (IDX-01)"
  - "normalize_newlines_universal converts br-tags to \\n before line splitting"

patterns-established:
  - "GameDataIndexer singleton via get_gamedata_indexer() -- same pattern as GlossaryService"
  - "6-tier cascade: AC detect -> whole hash -> whole FAISS -> line hash -> line FAISS -> ngram"
  - "Entity extraction walks TreeNode hierarchy using EDITABLE_ATTRS mapping"

requirements-completed: [IDX-01, IDX-02, IDX-03, IDX-04]

# Metrics
duration: 5min
completed: 2026-03-16
---

# Phase 29 Plan 01: GameDataIndexer + GameDataSearcher Summary

**Multi-tier indexing engine with hashtable (O(1) name/Key/StrKey lookup), FAISS HNSW (semantic), Aho-Corasick (entity detection), and 6-tier cascade search adapted from TMIndexer/TMSearcher**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-16T08:19:24Z
- **Completed:** 2026-03-16T08:25:07Z
- **Tasks:** 2 (TDD: RED/GREEN each)
- **Files modified:** 5

## Accomplishments
- GameDataIndexer builds 5 index structures from TreeNode entities: whole hash, line hash (br-tag split), whole FAISS, line FAISS, AC automaton
- Whole hashtable indexes entity names AND Key/StrKey attributes for O(1) lookup (IDX-01)
- GameDataSearcher performs 6-tier cascade with gamedata-specific result schema (entity_name, node_id, tag, file_path)
- AC entity detection with is_isolated() word boundary checking (from GlossaryService pattern)
- 31 unit tests all passing (17 indexer + 14 searcher)

## Task Commits

Each task was committed atomically (TDD RED + GREEN):

1. **Task 1: GameDataIndexer** - `03a14898` (test: RED) + `c1649d81` (feat: GREEN)
2. **Task 2: GameDataSearcher** - `684662b1` (test: RED) + `d79dabc7` (feat: GREEN)

## Files Created/Modified
- `server/tools/ldm/indexing/gamedata_indexer.py` - In-memory multi-tier index builder (hash, FAISS, AC)
- `server/tools/ldm/indexing/gamedata_searcher.py` - 6-tier cascade search engine
- `server/tools/ldm/schemas/gamedata.py` - Added IndexBuild/Search/Status Pydantic schemas
- `tests/unit/ldm/test_gamedata_indexer.py` - 17 unit tests for indexer
- `tests/unit/ldm/test_gamedata_searcher.py` - 14 unit tests for searcher

## Decisions Made
- Used FAISSManager.build_index(path=None) for in-memory indexes -- avoids disk I/O since gamedata indexes are rebuilt on each folder load
- AC automaton stores full entity metadata (idx, name, node_id, tag) to avoid secondary lookup during detection
- Whole lookup indexes 3 separate keys per entity (name, Key, StrKey) to satisfy IDX-01 exact lookup requirement
- normalize_newlines_universal used for both indexing and search to ensure br-tag text matches correctly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GameDataIndexer and GameDataSearcher are fully functional with unit tests
- Plan 02 will wire these to API endpoints and validate performance (<3s for 5000+ entities)
- Plan 03 will integrate into the frontend (auto-index on folder load, search bar, AC highlights)

## Self-Check: PASSED

All files verified present. All 4 commits verified in git log. All acceptance criteria grep checks passed. 31/31 tests passing.

---
*Phase: 29-multi-tier-indexing*
*Completed: 2026-03-16*
