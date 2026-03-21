---
phase: 51-offline-production-bundle
plan: 01
subsystem: packaging
tags: [model2vec, vgmstream, electron-builder, sqlite, wal, offline]

requires:
  - phase: 50-stringid-audio-image
    provides: "Audio/Image Codex features that need bundled binaries"
provides:
  - "Model2Vec download script for offline bundling"
  - "vgmstream binary copy script for WEM audio conversion"
  - "electron-builder extraResources for Model2Vec + vgmstream"
  - "SQLite WAL mode + busy_timeout for offline reliability"
  - "4-location vgmstream path detection (PATH > Electron > project bin > server bin)"
affects: [51-02-audit-smoketest]

tech-stack:
  added: []
  patterns: ["WAL mode + busy_timeout for all SQLite connections", "LOCANEXT_RESOURCES_PATH env var for Electron bundled binaries"]

key-files:
  created:
    - tools/download_model2vec.py
    - tools/bundle_vgmstream.py
  modified:
    - locaNext/package.json
    - server/database/offline.py
    - server/database/server_sqlite.py
    - server/tools/ldm/services/media_converter.py
    - .gitignore

key-decisions:
  - "WAL mode set at connection time (not schema init only) for server_sqlite.py to cover all code paths"
  - "4-location vgmstream search order: PATH > Electron extraResources > project bin > legacy server bin"
  - "bin/vgmstream/ added to .gitignore as build artifact (copied from MapDataGenerator/tools/)"

patterns-established:
  - "LOCANEXT_RESOURCES_PATH: env var for Electron extraResources path detection"
  - "SQLite PRAGMA journal_mode=WAL + busy_timeout=10000 on every connection"

requirements-completed: [OFFLINE-01, OFFLINE-02, OFFLINE-03]

duration: 2min
completed: 2026-03-21
---

# Phase 51 Plan 01: Offline Production Bundle Packaging Summary

**Model2Vec + vgmstream bundling scripts, electron-builder extraResources config, and SQLite WAL hardening for offline-only reliability**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T13:23:51Z
- **Completed:** 2026-03-21T13:26:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created download_model2vec.py script to pre-download potion-multilingual-128M weights for offline bundling
- Created bundle_vgmstream.py script to copy vgmstream-cli.exe + 11 DLLs for WEM audio conversion
- Updated electron-builder to include Model2Vec and vgmstream in extraResources (6 entries total)
- Hardened SQLite with WAL mode + 10s busy_timeout in both offline.py and server_sqlite.py
- Added 4-location vgmstream path detection including Electron extraResources path

## Task Commits

Each task was committed atomically:

1. **Task 1: Model2Vec download script + vgmstream copy script + electron-builder config** - `63cc5aaa` (feat)
2. **Task 2: SQLite WAL hardening + vgmstream Electron path detection** - `97d6b6bf` (feat)

## Files Created/Modified
- `tools/download_model2vec.py` - Downloads potion-multilingual-128M and saves to models/Model2Vec/
- `tools/bundle_vgmstream.py` - Copies vgmstream-cli.exe + 11 DLLs to bin/vgmstream/
- `locaNext/package.json` - Added Model2Vec + vgmstream to extraResources (6 entries)
- `server/database/offline.py` - WAL mode + busy_timeout in _init_schema_sync
- `server/database/server_sqlite.py` - WAL mode + busy_timeout in sync and async connections
- `server/tools/ldm/services/media_converter.py` - 4-location vgmstream search with Electron support
- `.gitignore` - Added bin/vgmstream/ (models/Model2Vec/ already present)

## Decisions Made
- WAL mode set at connection time (not only schema init) for server_sqlite.py to cover all code paths
- 4-location vgmstream search: PATH > Electron extraResources > project bin/vgmstream/ > legacy server/bin/
- bin/vgmstream/ added to .gitignore since it contains copied binaries (build artifact)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all scripts are fully functional.

## Next Phase Readiness
- Bundling scripts ready for 51-02 audit/smoke-test plan
- SQLite WAL hardened for offline-only workloads
- electron-builder config complete with all 6 extraResources entries

---
*Phase: 51-offline-production-bundle*
*Completed: 2026-03-21*
