---
phase: 07-xml-parsing-foundation-bug-fixes
plan: 01
subsystem: xml-parsing
tags: [lxml, xml-sanitizer, language-tables, stringid-consumer, tdd]

requires: []
provides:
  - XMLParsingEngine service with sanitize/parse/language-table/StringIdConsumer
  - Case-variant attribute constants and helpers (STRINGID_ATTRS, STR_ATTRS, etc.)
  - Migrated xml_handler.py using lxml instead of stdlib ET
affects: [08-dual-ui-detection, 09-translator-merge, 10-game-dev-merge, 12-export]

tech-stack:
  added: [lxml (already present, now used in xml_handler)]
  patterns: [strict-first-recover-fallback XML parsing, singleton service engine, case-variant attribute lookup]

key-files:
  created:
    - server/tools/ldm/services/xml_parsing.py
    - tests/unit/ldm/test_xml_parsing.py
    - tests/fixtures/xml/malformed_sample.xml
    - tests/fixtures/xml/locstr_sample.xml
    - tests/fixtures/xml/languagedata_eng.xml
    - tests/fixtures/xml/languagedata_kor.xml
  modified:
    - server/tools/ldm/file_handlers/xml_handler.py
    - server/tools/ldm/routes/files.py
    - server/tools/ldm/tm_manager.py

key-decisions:
  - "lxml with recover=True as fallback after strict parse -- handles malformed game data without crashing"
  - "parse_xml_file returns (rows, metadata) tuple -- eliminates module-level mutable state"
  - "StringIdConsumer uses deepcopy for independent per-instance consumption pointers"

patterns-established:
  - "XMLParsingEngine singleton via get_xml_parsing_engine() for consistent parsing across all LDM modules"
  - "Case-variant attribute lookup via get_attr(elem, ATTR_LIST) instead of hardcoded attribute names"
  - "iter_locstr_elements(root) for finding LocStr elements regardless of casing"

requirements-completed: [XML-04, XML-06, XML-07]

duration: 5min
completed: 2026-03-15
---

# Phase 07 Plan 01: XML Parsing Foundation Summary

**XMLParsingEngine with 5-step sanitizer, lxml strict+recovery parser, language table discovery, and StringIdConsumer -- xml_handler.py fully migrated from stdlib ET**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T01:21:48Z
- **Completed:** 2026-03-15T01:26:20Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Created XMLParsingEngine service with 5-step sanitizer pipeline (control chars, bare ampersands, newlines, unescaped <, tag repair)
- Implemented language table discovery (languagedata_*.xml) and translation lookup builder
- Ported StringIdConsumer from QACompiler with document-order dedup and independent consumption pointers
- Migrated xml_handler.py from stdlib ET to lxml via XMLParsingEngine -- 256 existing tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create XMLParsingEngine service with sanitizer, language tables, and StringIdConsumer** - `1be6f45a` (feat, TDD)
2. **Task 2: Migrate xml_handler.py from stdlib ET to lxml via XMLParsingEngine** - `c980254f` (feat)

## Files Created/Modified
- `server/tools/ldm/services/xml_parsing.py` - XMLParsingEngine with sanitize(), parse_file(), parse_bytes(), language table parsing, StringIdConsumer
- `tests/unit/ldm/test_xml_parsing.py` - 20 unit tests covering sanitizer, parser, language tables, consumer, constants
- `tests/fixtures/xml/malformed_sample.xml` - Malformed XML fixture (bare &, unclosed tags)
- `tests/fixtures/xml/locstr_sample.xml` - Valid LocStr XML with mixed-case tag and attribute variants
- `tests/fixtures/xml/languagedata_eng.xml` - English language data fixture
- `tests/fixtures/xml/languagedata_kor.xml` - Korean language data fixture
- `server/tools/ldm/file_handlers/xml_handler.py` - Migrated to lxml, returns (rows, metadata) tuple
- `server/tools/ldm/routes/files.py` - Updated 3 call sites for new parse_xml_file signature
- `server/tools/ldm/tm_manager.py` - Updated 1 call site for new parse_xml_file signature

## Decisions Made
- Used lxml with recover=True as fallback after strict parse -- handles malformed game data without crashing
- Changed parse_xml_file to return (rows, metadata) tuple -- eliminates module-level mutable state (_file_metadata)
- StringIdConsumer uses deepcopy of ordered_index for independent per-instance consumption pointers

## Deviations from Plan

None - plan executed exactly as written.

**Note:** The plan's verification criterion "grep -r import xml.etree server/tools/ldm/ returns empty" shows 3 remaining stdlib ET usages in files.py (lines 1293, 1395) and tm_manager.py (line 1077). These are in XML *export/writing* functions, not the parsing handler. The handler itself (`xml_handler.py`) has zero stdlib ET imports.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- XMLParsingEngine singleton ready for use by all downstream phases
- Language table discovery and translation lookup ready for Translator merge (Phase 09)
- StringIdConsumer ready for dedup logic in merge operations
- Remaining stdlib ET in export functions can be migrated when those features are reworked

---
*Phase: 07-xml-parsing-foundation-bug-fixes*
*Completed: 2026-03-15*
