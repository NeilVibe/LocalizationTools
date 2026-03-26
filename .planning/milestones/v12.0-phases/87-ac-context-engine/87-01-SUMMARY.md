---
phase: 87-ac-context-engine
plan: 01
subsystem: search
tags: [ahocorasick, ngram, jaccard, korean, tm-search, context]

requires:
  - phase: 86-dual-threshold-tm-ui
    provides: "Dual threshold system (62% context, 92% pretranslation)"
provides:
  - "ContextSearcher class with 3-tier AC cascade search"
  - "AC automatons built from whole_lookup + line_lookup on TM index load"
  - "Character n-gram Jaccard fuzzy matching for Korean text"
affects: [87-02, 88-ac-context-integration]

tech-stack:
  added: [ahocorasick (already installed, newly used in indexer)]
  patterns: ["3-tier cascade: whole AC -> line AC -> char n-gram Jaccard", "space-stripped Korean n-gram extraction"]

key-files:
  created:
    - server/tools/ldm/indexing/context_searcher.py
    - tests/unit/ldm/test_context_searcher.py
  modified:
    - server/tools/ldm/indexing/indexer.py

key-decisions:
  - "AC automatons built in _build_ac_automatons() called from load_indexes(), not build_indexes() -- avoids persistence, rebuilds from existing serialized data"
  - "Jaccard uses union of n={2,3,4,5} character n-grams with space stripping for Korean"
  - "Tier ordering: whole AC first (exact substring), line AC second, fuzzy Jaccard last"

patterns-established:
  - "ContextSearcher pattern: takes indexes dict from TMIndexer.load_indexes(), reads automaton + lookup keys"
  - "Multi-n-gram Jaccard with space-stripped Korean for fuzzy matching"

requirements-completed: [ACCTX-01, ACCTX-03]

duration: 8min
completed: 2026-03-26
---

# Phase 87 Plan 01: AC Context Engine Core Summary

**3-tier AC context search engine with Aho-Corasick substring matching and char n-gram Jaccard fuzzy (62% threshold) for Korean TM text**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-26T04:12:05Z
- **Completed:** 2026-03-26T04:20:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- AC automatons built from whole_lookup + line_lookup keys when TM indexes load
- ContextSearcher class with 3-tier cascade: whole AC (score=1.0), line AC (score=1.0), char n-gram Jaccard (>=0.62)
- Multi-n-gram extraction with n={2,3,4,5} and space-stripped Korean text
- 19 unit tests covering all tiers, cascade ordering, Jaccard math, and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for AC context searcher** - `3f09651a` (test)
2. **Task 1 GREEN: AC context engine with 3-tier cascade** - `1085c523` (feat)

## Files Created/Modified
- `server/tools/ldm/indexing/context_searcher.py` - New ContextSearcher class with 3-tier cascade search
- `server/tools/ldm/indexing/indexer.py` - Added _build_ac_automatons() and AC automaton keys to load_indexes() return dict
- `tests/unit/ldm/test_context_searcher.py` - 19 unit tests for all tiers, n-gram math, edge cases

## Decisions Made
- AC automatons built in load_indexes() (not build_indexes()) to avoid additional persistence -- rebuilds from existing serialized data each load
- Jaccard uses union of n={2,3,4,5} character n-grams, matching Korean NLP research findings
- Space-stripping before n-gram extraction handles inconsistent Korean spacing in game text
- Deduplication by entry_id across tiers prevents duplicate results

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ContextSearcher ready for integration with row-select WebSocket handler (Phase 88)
- AC automatons available in indexes dict for any consumer
- Performance benchmark needed when wiring to real TM data (Plan 87-02)

## Self-Check: PASSED

- context_searcher.py: FOUND
- test_context_searcher.py: FOUND
- SUMMARY.md: FOUND
- RED commit 3f09651a: FOUND
- GREEN commit 1085c523: FOUND

---
*Phase: 87-ac-context-engine*
*Completed: 2026-03-26*
