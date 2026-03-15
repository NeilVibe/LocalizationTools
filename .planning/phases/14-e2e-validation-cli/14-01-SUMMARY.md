---
phase: 14-e2e-validation-cli
plan: 01
subsystem: cli
tags: [cli, merge, export, gamedev, requests, base64]

requires:
  - phase: 09-translator-merge
    provides: TranslatorMergeService POST /api/ldm/files/{id}/merge
  - phase: 10-export
    provides: ExportService GET /api/ldm/files/{id}/download
  - phase: 12-gamedev-merge
    provides: GameDevMergeService POST /api/ldm/files/{id}/gamedev-merge
provides:
  - CLI merge command (cascade/strict/fuzzy/strorigin_only modes)
  - CLI gamedev-merge command with base64 XML output saving
  - CLI export command (xml/xlsx/txt with status_filter)
  - CLI detect command (translator vs gamedev file type)
  - Unit tests for all 4 CLI commands
affects: [14-e2e-validation-cli]

tech-stack:
  added: []
  patterns: [sys.argv flag parsing for CLI commands, requests.get for binary download]

key-files:
  created:
    - tests/unit/ldm/test_cli_commands.py
  modified:
    - scripts/locanext_cli.py

key-decisions:
  - "Used requests.get directly for export (binary response) instead of api() helper (JSON)"
  - "Base64 decode for gamedev-merge output_xml matches server encoding pattern"
  - "sys.argv flag parsing (not argparse) to match existing CLI style"

patterns-established:
  - "CLI command pattern: function per command, api() for JSON, requests.get for binary"

requirements-completed: [CLI-01, CLI-02, CLI-03]

duration: 3min
completed: 2026-03-15
---

# Phase 14 Plan 01: CLI Merge/Export/Detect Commands Summary

**4 CLI commands (merge, gamedev-merge, export, detect) with sys.argv routing and 9 unit tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T07:14:59Z
- **Completed:** 2026-03-15T07:18:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Extended locanext_cli.py with merge, gamedev-merge, export, and detect commands
- All commands call correct API endpoints with proper payloads
- Export saves binary file to disk, gamedev-merge decodes base64 XML output
- 9 unit tests with mocked HTTP calls all passing

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `905d567f` (test)
2. **Task 1 GREEN: Implementation** - `81cd2c21` (feat)

## Files Created/Modified
- `scripts/locanext_cli.py` - Added cmd_merge, cmd_gamedev_merge, cmd_export, cmd_detect + CLI routing
- `tests/unit/ldm/test_cli_commands.py` - 9 unit tests covering all 4 commands

## Decisions Made
- Used `requests.get` directly for export command since response is binary/streaming, not JSON
- Base64 decode for gamedev-merge output XML to match server-side encoding
- Kept sys.argv manual parsing (not argparse) to maintain consistency with existing CLI style
- cmd_detect defaults file_type to "translator" when not present (backward compatibility)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI toolkit complete with all merge/export/detect commands
- Ready for Plan 02 (E2E validation tests)

---
*Phase: 14-e2e-validation-cli*
*Completed: 2026-03-15*
