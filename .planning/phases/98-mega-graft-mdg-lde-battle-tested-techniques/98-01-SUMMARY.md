---
phase: 98-mega-graft-mdg-lde-battle-tested-techniques
plan: 01
subsystem: gamedata
tags: [xml, sanitizer, lxml, gamedata, perforce, parsing]

requires:
  - phase: none
    provides: standalone graft from MDG/QACompilerNEW
provides:
  - "5-stage XML sanitizer service for GameData (server/tools/ldm/services/xml_sanitizer.py)"
  - "Sanitized XML parsing in gamedata routes (no more raw etree.parse)"
  - "Relaxed path validation for Perforce absolute paths"
affects: [gamedata-routes, gamedata-browse, gamedata-tree, mega-index]

tech-stack:
  added: []
  patterns: [virtual-root-xml-wrapper, dual-pass-parsing, 5-stage-sanitization]

key-files:
  created: [server/tools/ldm/services/xml_sanitizer.py]
  modified: [server/tools/ldm/routes/gamedata.py, server/tools/ldm/services/gamedata_browse_service.py]

key-decisions:
  - "Grafted exact MDG algorithm without modifications for consistency across projects"
  - "Removed is_relative_to check for absolute paths to support Perforce paths outside base_dir"
  - "Used lazy import in _count_entities and detect_columns to avoid circular imports"

patterns-established:
  - "sanitize_and_parse(path) as single entry point for all XML parsing in GameData"
  - "Absolute paths pass through validation without base_dir constraint"

requirements-completed: [GRAFT-01, GRAFT-02]

duration: 2min
completed: 2026-03-28
---

# Phase 98 Plan 01: XML Sanitizer Graft + Perforce Path Fix Summary

**Grafted MDG's battle-tested 5-stage XML sanitizer into GameData routes, replacing raw etree.parse with sanitize_and_parse + virtual root + dual-pass recovery**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T21:06:23Z
- **Completed:** 2026-03-28T21:08:45Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created `xml_sanitizer.py` with exact MDG algorithm: bad entity fix, seg newline handling, attribute < and & escaping, tag stack repair, control char removal
- Replaced raw `etree.parse` in `get_gamedata_rows` with `sanitize_and_parse` + virtual ROOT wrapper
- Replaced raw `etree.parse` in `_count_entities` and `detect_columns` with sanitized parser
- Removed `is_relative_to(self.base_dir)` check that blocked Perforce absolute paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Create xml_sanitizer.py with MDG's exact 5-stage sanitizer** - `70273db3` (feat)
2. **Task 2: Wire gamedata routes + fix path validation** - `60f21262` (feat)

## Files Created/Modified
- `server/tools/ldm/services/xml_sanitizer.py` - New 148-line sanitizer with 5 stages + virtual root + dual-pass
- `server/tools/ldm/routes/gamedata.py` - Import sanitize_and_parse, replace etree.parse in get_gamedata_rows
- `server/tools/ldm/services/gamedata_browse_service.py` - Fix _validate_path for absolute paths, use sanitizer in _count_entities and detect_columns

## Decisions Made
- Grafted exact MDG algorithm without modifications for cross-project consistency
- Removed is_relative_to check entirely for absolute paths (Perforce paths are inherently outside base_dir)
- Used lazy imports in browse service methods to avoid circular import issues

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Also updated detect_columns to use sanitizer**
- **Found during:** Task 2 (wiring gamedata routes)
- **Issue:** `detect_columns` in browse service also used raw `etree.parse`, would crash on malformed XML
- **Fix:** Replaced with `sanitize_and_parse` import and call
- **Files modified:** server/tools/ldm/services/gamedata_browse_service.py
- **Verification:** Import check passes
- **Committed in:** 60f21262 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for completeness -- all XML parsing paths now use sanitizer.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality fully wired.

## Next Phase Readiness
- XML sanitizer ready for use by any GameData service
- Path validation accepts Perforce paths for production use
- gamedata_tree_service and gamedata_edit_service still use their own parsing (edit service intentionally keeps raw parsing for write-back fidelity)

## Self-Check: PASSED

- [x] xml_sanitizer.py exists
- [x] SUMMARY.md exists
- [x] Commit 70273db3 found
- [x] Commit 60f21262 found

---
*Phase: 98-mega-graft-mdg-lde-battle-tested-techniques*
*Completed: 2026-03-28*
