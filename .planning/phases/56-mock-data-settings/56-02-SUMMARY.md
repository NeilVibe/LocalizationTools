---
phase: 56-mock-data-settings
plan: 02
subsystem: settings
tags: [fastapi, svelte5, localStorage, path-validation, wsl]

requires:
  - phase: none
    provides: standalone plan
provides:
  - "/api/settings/validate-path POST endpoint for path validation"
  - "Per-project settings store (localStorage keyed by project ID)"
  - "ProjectSettingsModal with LOC PATH and EXPORT PATH inputs"
  - "selectedProject global writable store in navigation.js"
affects: [57-transfer-adapter, 58-merge-modal, 59-merge-execution]

tech-stack:
  added: []
  patterns: ["Per-project localStorage settings with SETTINGS_PREFIX + projectId key pattern", "validate_path_logic helper separated from endpoint for testability", "Global selectedProject store synced from LDM.svelte via $effect"]

key-files:
  created:
    - server/api/settings.py
    - locaNext/src/lib/stores/projectSettings.js
    - locaNext/src/lib/components/ProjectSettingsModal.svelte
    - tests/test_path_validation.py
    - tests/test_project_settings_store.js
  modified:
    - server/main.py
    - locaNext/src/lib/stores/navigation.js
    - locaNext/src/lib/components/apps/LDM.svelte
    - locaNext/src/routes/+layout.svelte

key-decisions:
  - "Separated validate_path_logic from endpoint handler for direct unit testing without HTTP"
  - "Used languagedata_*.* glob (any extension) to support .xml, .txt, .xlsx languagedata files"
  - "selectedProject as writable store in navigation.js synced via $effect in LDM.svelte"

patterns-established:
  - "Per-project localStorage: key = locaNext_project_settings_{projectId}"
  - "Path validation: translate_wsl_path + exists + is_dir + languagedata glob"
  - "Global store sync: LDM.svelte $effect syncs local state to global writable"

requirements-completed: [SET-01, SET-02, SET-03]

duration: 7min
completed: 2026-03-22
---

# Phase 56 Plan 02: Project Settings Summary

**Backend path validation endpoint + per-project localStorage settings store + ProjectSettingsModal with LOC PATH and EXPORT PATH inputs accessible from Settings dropdown**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-22T14:45:11Z
- **Completed:** 2026-03-22T14:51:42Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Backend /api/settings/validate-path endpoint with WSL path translation, existence/directory/languagedata file checks
- Per-project settings store (getProjectSettings/setProjectSettings/clearProjectSettings) with localStorage persistence
- Global selectedProject writable store synced from LDM.svelte for layout-level access
- ProjectSettingsModal with validation feedback (success with file count, error with hints)
- 9 pytest tests + 13-assertion Node.js test all passing
- svelte-check: 0 errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create backend path validation endpoint** - `a5ba6151` (feat, TDD)
2. **Task 2: Create per-project settings store with selectedProject global store** - `fa7b9e38` (feat)
3. **Task 3: Create ProjectSettingsModal and wire into layout** - `c7c38b17` (feat)

## Files Created/Modified
- `server/api/settings.py` - Path validation endpoint with WSL translation and languagedata glob
- `server/main.py` - Register settings_api router
- `locaNext/src/lib/stores/projectSettings.js` - Per-project localStorage store
- `locaNext/src/lib/stores/navigation.js` - Added selectedProject writable store
- `locaNext/src/lib/components/apps/LDM.svelte` - $effect syncing selectedProjectId to global store
- `locaNext/src/lib/components/ProjectSettingsModal.svelte` - Modal with LOC/EXPORT PATH inputs + validation
- `locaNext/src/routes/+layout.svelte` - Project Settings dropdown item + modal rendering
- `tests/test_path_validation.py` - 9 pytest tests for path validation
- `tests/test_project_settings_store.js` - 13-assertion Node.js unit test

## Decisions Made
- Separated validate_path_logic() from the endpoint handler for direct pytest testing without HTTP/TestClient
- Used languagedata_*.* glob pattern (any extension) to support .xml, .txt, .xlsx files (MOCK-04 test123 uses .txt)
- Created selectedProject as a writable store in navigation.js instead of a new file, synced via $effect in LDM.svelte

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all data flows are wired (localStorage persistence, backend validation, store sync).

## Next Phase Readiness
- LOC PATH and EXPORT PATH are now configurable per project
- Path validation endpoint ready for merge modal to verify paths before execution
- selectedProject store available for any layout-level component needing project context

## Self-Check: PASSED

All 5 created files verified on disk. All 3 task commits verified in git log.

---
*Phase: 56-mock-data-settings*
*Completed: 2026-03-22*
