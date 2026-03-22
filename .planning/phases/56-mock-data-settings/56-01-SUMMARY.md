---
phase: 56-mock-data-settings
plan: 01
subsystem: database
tags: [sqlite, mock-data, cli, language-detection, offline]

requires: []
provides:
  - "scripts/setup_mock_data.py CLI for creating mock platform/projects/folders"
  - "detect_language_from_name() function for project language auto-detection"
  - "validate_loc_path() function for languagedata file validation (.txt/.xml/.xlsx)"
  - "ensure_tables() for idempotent SQLite schema creation"
affects: [56-02-settings-ui, 57-transfer-adapter, 58-merge-api]

tech-stack:
  added: []
  patterns:
    - "Standalone CLI scripts using sync sqlite3 (not async aiosqlite)"
    - "Language suffix detection via rsplit + lookup map"
    - "FK-safe table wipe order: rows -> files -> folders -> projects -> platforms"

key-files:
  created:
    - scripts/setup_mock_data.py
    - tests/test_mock_data.py
  modified: []

key-decisions:
  - "Used sync sqlite3 directly instead of ORM — standalone script needs no server dependencies"
  - "ensure_tables() built into wipe_and_create() for zero-setup experience"
  - "validate_loc_path globs languagedata_*.* to accept all formats (txt/xml/xlsx)"

patterns-established:
  - "CLI mock scripts use argparse with required --confirm-wipe flag for safety"
  - "Language detection via LANGUAGE_SUFFIX_MAP dict with rsplit('_', 1) parsing"

requirements-completed: [MOCK-01, MOCK-02, MOCK-03, MOCK-04]

duration: 3min
completed: 2026-03-22
---

# Phase 56 Plan 01: Mock Data CLI Summary

**Standalone CLI script creating 3 mock projects with language auto-detection and languagedata validation for offline transfer demo**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-22T14:45:17Z
- **Completed:** 2026-03-22T14:48:43Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- CLI script `setup_mock_data.py` creates 1 platform, 3 projects, 2 folders in SQLite
- Language detection maps 15 suffix codes (FRE, ENG, MULTI, etc.) to display names
- LOC PATH validation accepts .txt, .xml, .xlsx languagedata files (MOCK-04 compatibility)
- Script is idempotent — safe to run multiple times with --confirm-wipe
- ensure_tables() auto-creates schema if offline.db doesn't exist

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `1095d889` (test)
2. **Task 1 GREEN: Implementation + tests passing** - `d06e1118` (feat)
3. **Task 2: Verify against real offline.db** - no code changes (verification only)

_TDD approach: RED (12 failing tests) -> GREEN (all 12 pass)_

## Files Created/Modified
- `scripts/setup_mock_data.py` - CLI mock data setup with language detection, LOC PATH validation, ensure_tables
- `tests/test_mock_data.py` - 12 test cases covering detection, wipe/create, folders, CLI flags, path validation

## Decisions Made
- Used sync sqlite3 instead of ORM — standalone script with zero server dependencies
- Built ensure_tables() directly into wipe_and_create() so script works even without existing DB
- validate_loc_path uses languagedata_*.* glob to accept all file formats per MOCK-04

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed subprocess test using sys.executable instead of 'python'**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** WSL2 environment has python3 not python — subprocess test failed with FileNotFoundError
- **Fix:** Changed test to use sys.executable for portable Python binary resolution
- **Files modified:** tests/test_mock_data.py
- **Verification:** All 12 tests pass
- **Committed in:** d06e1118 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor portability fix, no scope creep.

## Issues Encountered
None beyond the python/python3 binary name issue (auto-fixed above).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- offline.db populated with mock data, ready for Settings UI (56-02)
- detect_language_from_name() available for import by transfer adapter (Phase 57)
- validate_loc_path() ready for LOC PATH settings validation

---
*Phase: 56-mock-data-settings*
*Completed: 2026-03-22*
