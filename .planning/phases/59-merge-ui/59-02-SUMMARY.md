---
phase: 59-merge-ui
plan: 02
subsystem: ui
tags: [svelte5, carbon, modal, toolbar, context-menu, merge, custom-event]

# Dependency graph
requires:
  - phase: 59-merge-ui/01
    provides: MergeModal.svelte component with $bindable(open), projectId, multiLanguage, folderPath props
provides:
  - Toolbar Merge button in +layout.svelte header (always visible when project selected)
  - Folder right-click "Merge Folder to LOCDEV" context menu entry in FilesPage.svelte
  - Custom event bridge (merge-folder-to-locdev) between FilesPage and +layout.svelte
affects: [59-merge-ui/03, integration-testing]

# Tech tracking
tech-stack:
  added: []
  patterns: [window CustomEvent for cross-component communication avoiding deep prop threading]

key-files:
  created: []
  modified:
    - locaNext/src/routes/+layout.svelte
    - locaNext/src/lib/components/pages/FilesPage.svelte

key-decisions:
  - "Custom event (merge-folder-to-locdev) instead of prop threading through 3 component layers"
  - "Merge button placed between Tasks and SyncStatusPanel in toolbar"
  - "Context menu merge entry placed outside canModifyStructure block (merge writes to external LOCDEV)"

patterns-established:
  - "Window CustomEvent pattern for deep component-to-layout communication"

requirements-completed: [UI-01, UI-02]

# Metrics
duration: 3min
completed: 2026-03-22
---

# Phase 59 Plan 02: Merge UI Entry Points Summary

**Toolbar Merge button + folder right-click "Merge Folder to LOCDEV" context menu wired to MergeModal via custom event bridge**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-22T17:43:32Z
- **Completed:** 2026-03-22T17:46:37Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Toolbar Merge button in header area, disabled when no project selected, opens MergeModal in single-project mode
- Folder right-click context menu "Merge Folder to LOCDEV" entry opens MergeModal in multi-language mode with folder path pre-filled
- Custom event bridge avoids threading callback props through +layout -> LDM -> FilesPage (3 layers)
- svelte-check passes with 0 errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add toolbar merge button and MergeModal instance to +layout.svelte** - `460f5255` (feat)
2. **Task 2: Add Merge Folder to LOCDEV to folder right-click context menu** - `05b85438` (feat)

## Files Created/Modified
- `locaNext/src/routes/+layout.svelte` - Import MergeModal, Merge icon; add state vars, openMerge/openMergeFolder functions, toolbar button, modal instance, event listener
- `locaNext/src/lib/components/pages/FilesPage.svelte` - Add openMergeFolderToLocdev handler and context menu entry in folder block

## Decisions Made
- Used window CustomEvent (merge-folder-to-locdev) instead of prop threading through LDM component layer -- cleaner, avoids modifying LDM.svelte
- Placed merge context menu entry outside canModifyStructure block since merge writes to external LOCDEV path, not project structure
- Placed toolbar button between Tasks and SyncStatusPanel, styled like Tasks button for consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both entry points wired and verified with svelte-check
- MergeModal from Plan 01 is fully connected
- Ready for Plan 03 (integration testing / final polish)

---
*Phase: 59-merge-ui*
*Completed: 2026-03-22*
