---
phase: 051-contextual-intelligence-qa-engine
plan: 01
subsystem: qa-engine
tags: [ahocorasick, glossary, entity-detection, category-mapper, lxml, xml-parsing]

# Dependency graph
requires:
  - phase: 05-visual-polish-and-integration
    provides: MapDataService singleton pattern, qa_helpers utilities
provides:
  - GlossaryService singleton with AC automaton for O(n) entity detection
  - XML extraction methods for character, item, region game data
  - Glossary filter with QuickSearch proven defaults
  - TwoTierCategoryMapper for string type classification
  - Mock gamedata XML fixtures (5 characters, 5 items, 3 regions)
affects: [051-02, 051-03, 051-04, 051-05, qa-engine, context-service]

# Tech tracking
tech-stack:
  added: [pyahocorasick (AC automaton), lxml (XML recovery parser)]
  patterns: [singleton service with lazy init, AC automaton + is_isolated boundary check, two-tier category mapping]

key-files:
  created:
    - server/tools/ldm/services/glossary_service.py
    - server/tools/ldm/services/category_mapper.py
    - tests/unit/ldm/test_glossary_service.py
    - tests/unit/ldm/test_category_mapper.py
    - tests/fixtures/mock_gamedata/characterinfo_sample.xml
    - tests/fixtures/mock_gamedata/iteminfo_sample.xml
    - tests/fixtures/mock_gamedata/regioninfo_sample.xml
  modified: []

key-decisions:
  - "Entity index keyed by term name (not numeric ID) for direct lookup"
  - "Glossary filter uses QuickSearch defaults: min_occ=2, max_len=25, filter_sentences=True"
  - "AC automaton built once at initialization, reused across all detection calls"
  - "lxml recovery mode for robust XML parsing of potentially malformed game data"

patterns-established:
  - "GlossaryService singleton: build_from_entity_names() + detect_entities() + extract_*_glossary()"
  - "TwoTierCategoryMapper: Tier1 STORY (dialog/sequencer) -> Tier2 GAME_DATA (priority keywords) -> fallback Other"
  - "Word boundary check via is_isolated() prevents Korean compound false matches in AC detection"

requirements-completed: [CTX-05, CTX-06, CTX-09, CTX-10]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 5.1 Plan 01: Glossary + Category Mapper Summary

**Aho-Corasick glossary service with XML entity extraction, word boundary detection, and two-tier category mapping ported from QuickSearch/QuickCheck**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T14:22:42Z
- **Completed:** 2026-03-14T14:27:45Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- GlossaryService singleton builds AC automaton from game data XML for O(n) entity detection
- Word boundary check (is_isolated) prevents Korean compound word false matches
- Glossary filter applies proven QuickSearch defaults (min_occ=2, max_len=25, no sentences/punctuation)
- TwoTierCategoryMapper correctly classifies strings using STORY + GAME_DATA tiers
- 37 unit tests covering AC building, detection, XML extraction, filtering, and category mapping

## Task Commits

Each task was committed atomically:

1. **Task 1: GlossaryService with AC automaton and mock game data fixtures** - `65e72730` (feat)
2. **Task 2: TwoTierCategoryMapper for string type classification** - `3b5c2339` (feat, from prior execution)

## Files Created/Modified
- `server/tools/ldm/services/glossary_service.py` - GlossaryService singleton: AC automaton, XML extraction, glossary filter
- `server/tools/ldm/services/category_mapper.py` - TwoTierCategoryMapper: two-tier string classification
- `tests/unit/ldm/test_glossary_service.py` - 22 tests for glossary service
- `tests/unit/ldm/test_category_mapper.py` - 15 tests for category mapper
- `tests/fixtures/mock_gamedata/characterinfo_sample.xml` - 5 mock character entries
- `tests/fixtures/mock_gamedata/iteminfo_sample.xml` - 5 mock item entries
- `tests/fixtures/mock_gamedata/regioninfo_sample.xml` - 3 mock region entries

## Decisions Made
- Entity index keyed by term name (not numeric ID) for direct O(1) lookup by detected term
- Glossary filter uses QuickSearch proven defaults (min_occ=2, max_len=25, filter_sentences=True)
- AC automaton built once at service initialization, not per-request (avoids 50-200ms rebuild)
- lxml recovery mode for XML parsing (handles malformed game data gracefully)

## Deviations from Plan

None - plan executed exactly as written. Task 2 category_mapper was found already committed from a prior plan execution (051-04) but with identical content.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GlossaryService ready for QA Engine (Plan 02) to use for Term Check with pre-built automaton
- CategoryMapper ready for context service (Plan 03) to use for string classification
- Entity detection ready for ContextTab (Plan 05) to wire into frontend

---
*Phase: 051-contextual-intelligence-qa-engine*
*Completed: 2026-03-14*
