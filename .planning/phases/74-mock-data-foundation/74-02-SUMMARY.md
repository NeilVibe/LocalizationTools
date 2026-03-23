---
phase: 74-mock-data-foundation
plan: 02
subsystem: testing
tags: [japanese, xml, language-data, perforce-paths, mock-data, lxml, pytest]

# Dependency graph
requires:
  - phase: 74-01
    provides: "Valid DDS textures and WEM audio stubs in Perforce-mapped paths"
provides:
  - "Japanese language data XML with 100 StringIds matching KOR/ENG"
  - "Comprehensive test suite validating all MOCK-09 through MOCK-12 requirements"
  - "13 tests covering DDS validity, WEM audio, 3-language parity, XML data, Perforce path resolution"
affects: [mega-index, language-data-upload, perforce-path-service, media-preview]

# Tech tracking
tech-stack:
  added: []
  patterns: [Perforce-path-aligned test constants, cross-language fixture validation]

key-files:
  created:
    - tests/fixtures/mock_gamedata/loc/languagedata_JPN.xml
  modified:
    - tests/unit/test_mock_media_stubs.py

key-decisions:
  - "Kept TEXTURES_DIR for PNG fallback alongside new DDS_DIR for Perforce path"
  - "StrOrigin and Str both set to Japanese text (same pattern as KOR file)"

patterns-established:
  - "Test constants mirror PerforcePathService.configure_for_mock_gamedata() keys exactly"
  - "Cross-language validation: same filenames/StringIds across all language variants"

requirements-completed: [MOCK-12, MOCK-09, MOCK-10, MOCK-11]

# Metrics
duration: 4min
completed: 2026-03-24
---

# Phase 74 Plan 02: Japanese Language Data + Perforce Path Tests Summary

**Japanese XML with 100 StringIds + 13 tests validating DDS/WEM/XML at correct Perforce-mapped paths**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T18:13:38Z
- **Completed:** 2026-03-23T18:17:44Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created languagedata_JPN.xml with contextually appropriate Japanese translations for all 100 StringIds
- Fixed test constants from wrong paths (textures/, audio/) to correct Perforce-mapped paths (texture/image/, sound/windows/*)
- Added TestLanguageData class validating EN/KR/JP existence, StringId matching, and br-tag encoding
- Added TestPerforcePathResolution class validating all 11 PerforcePathService template directories
- All 13 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Japanese language data XML** - `a8cefe63` (feat)
2. **Task 2: Fix and expand test_mock_media_stubs.py** - `df18ae3c` (feat)

## Files Created/Modified
- `tests/fixtures/mock_gamedata/loc/languagedata_JPN.xml` - Japanese translations for all 100 StringIds (CHAR, ITEM, SKILL, GIMMICK, KNOW, DLG)
- `tests/unit/test_mock_media_stubs.py` - Rewritten with correct Perforce paths, 5 test classes, 13 test methods

## Decisions Made
- Kept TEXTURES_DIR as separate constant for PNG fallback path (used by thumbnail endpoint) alongside new DDS_DIR
- Set both StrOrigin and Str to Japanese text, matching KOR file pattern
- Used contextually appropriate RPG Japanese (archaic speech for elder characters, casual for assassin)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all language data contains real Japanese translations, all tests validate real files.

## Next Phase Readiness
- EN/KR/JP language data complete (MOCK-12 met)
- All 11 PerforcePathService template directories verified (MOCK-09 met)
- DDS and WEM files validated at correct paths (MOCK-10, MOCK-11 met)
- Ready for language data upload E2E testing and mega index integration

---
*Phase: 74-mock-data-foundation*
*Completed: 2026-03-24*
