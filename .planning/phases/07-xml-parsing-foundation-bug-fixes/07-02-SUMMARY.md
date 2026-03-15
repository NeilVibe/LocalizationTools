---
phase: 07-xml-parsing-foundation-bug-fixes
plan: 02
subsystem: xml-parsing
tags: [lxml, knowledge-table, dds-index, chain-resolution, aho-corasick, xml-parsing-engine]

# Dependency graph
requires:
  - phase: 07-01
    provides: XMLParsingEngine service with sanitize, parse_file, parse_bytes, StringIdConsumer
provides:
  - MapDataService builds real StrKey-to-image indexes from KnowledgeInfo XMLs
  - GlossaryService delegates XML parsing to centralized XMLParsingEngine
  - ContextService resolve_chain() provides step-by-step chain resolution with partial tracking
  - KnowledgeLookup dataclass for cross-service knowledge table access
  - build_knowledge_table() and build_dds_index() standalone functions
affects: [08-dual-ui, 09-translator-merge, 11-image-audio-pipeline, 13-ai-summaries]

# Tech tracking
tech-stack:
  added: []
  patterns: [knowledge-table-builder, dds-index-builder, chain-resolution-steps, wsl-path-conversion]

key-files:
  created:
    - tests/fixtures/xml/knowledgeinfo_chain.xml
  modified:
    - server/tools/ldm/services/mapdata_service.py
    - server/tools/ldm/services/glossary_service.py
    - server/tools/ldm/services/context_service.py
    - tests/unit/ldm/test_mapdata_service.py
    - tests/unit/ldm/test_glossary_service.py
    - tests/unit/ldm/test_context_service.py
    - tests/unit/ldm/test_xml_parsing.py

key-decisions:
  - "KnowledgeData elements parsed (not KnowledgeInfo tag) matching real game data structure"
  - "DDS index uses lowercase stems for case-insensitive texture name matching"
  - "Chain resolution returns partial results with step tracking instead of silent None"
  - "GlossaryService._parse_xml delegates to XMLParsingEngine singleton rather than inline lxml"

patterns-established:
  - "Chain resolution pattern: 3-step tracking with partial flag for debugging No Image issues"
  - "Knowledge table builder: standalone function accepting folder + parser for testability"
  - "WSL path conversion at service initialization boundary (not deep in parsing code)"

requirements-completed: [XML-01, XML-02, XML-03, XML-05]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 07 Plan 02: XML Service Wiring Summary

**MapDataService builds real StrKey-to-image chains from KnowledgeInfo XMLs, GlossaryService delegates to XMLParsingEngine, ContextService provides 3-step chain resolution with partial result tracking**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T01:29:32Z
- **Completed:** 2026-03-15T01:34:51Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- MapDataService.initialize() builds real indexes from KnowledgeInfo XML files via XMLParsingEngine with graceful degradation
- GlossaryService._parse_xml replaced with XMLParsingEngine delegation (centralized sanitization for all XML)
- ContextService.resolve_chain() tracks 3 resolution steps: StrKey -> KnowledgeLookup -> UITextureName -> DDS path
- Cross-reference chains resolve across multiple XML files (XML-05)
- All 274 LDM tests passing (18 new tests added)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing tests for knowledge table + DDS index** - `4cba867f` (test)
2. **Task 1 GREEN: Wire MapDataService to parse real KnowledgeInfo XMLs** - `509123bc` (feat)
3. **Task 2: Wire GlossaryService + add chain resolution to ContextService** - `a774c82e` (feat)

_Note: Task 1 followed TDD with RED/GREEN commits._

## Files Created/Modified
- `tests/fixtures/xml/knowledgeinfo_chain.xml` - 3 KnowledgeData elements for chain resolution testing
- `server/tools/ldm/services/mapdata_service.py` - KnowledgeLookup dataclass, build_knowledge_table(), build_dds_index(), _resolve_image_chains(), get_knowledge_lookup()
- `server/tools/ldm/services/glossary_service.py` - _parse_xml delegates to XMLParsingEngine, initialize() applies WSL path conversion
- `server/tools/ldm/services/context_service.py` - resolve_chain() with 3-step tracking, resolve_context_for_row() includes chain_steps
- `tests/unit/ldm/test_mapdata_service.py` - 11 new tests for knowledge table, DDS index, image chain resolution
- `tests/unit/ldm/test_glossary_service.py` - 3 new tests for XMLParsingEngine delegation and WSL paths
- `tests/unit/ldm/test_context_service.py` - 4 new tests for chain resolution (full, partial, missing, row integration)
- `tests/unit/ldm/test_xml_parsing.py` - 1 new test for cross-reference across files

## Decisions Made
- KnowledgeData elements parsed (not KnowledgeInfo tag) to match real game data XML structure
- DDS index uses lowercase stems for case-insensitive UITextureName matching
- Chain resolution returns structured dict with steps array, result, and partial flag
- GlossaryService._parse_xml kept as static method interface but delegates to singleton engine

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test needed _loaded=True for get_image_context to work**
- **Found during:** Task 1 GREEN phase
- **Issue:** Tests set up knowledge table and DDS index manually but forgot to set _loaded=True, so get_image_context returned None
- **Fix:** Added `svc._loaded = True` to test setup after _resolve_image_chains()
- **Files modified:** tests/unit/ldm/test_mapdata_service.py
- **Verification:** Tests pass correctly
- **Committed in:** 509123bc (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test setup fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three XML services (MapData, Glossary, Context) now wired to real XML data via XMLParsingEngine
- Knowledge table, DDS index, and chain resolution patterns established for downstream phases
- Phase 07 Plan 03 (bug fixes) already completed -- phase is now complete
- Ready for Phase 08 (Dual UI Detection)

---
*Phase: 07-xml-parsing-foundation-bug-fixes*
*Completed: 2026-03-15*
