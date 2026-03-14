---
phase: 06-offline-demo-validation
plan: 02
subsystem: testing
tags: [sqlite, offline, mode-detection, factory-pattern, testclient, smoke-tests]

requires:
  - phase: 01-stability
    provides: "SQLite repository implementations and parity infrastructure"
provides:
  - "Mode detection validation for 3-mode factory routing (offline/server-local/postgresql)"
  - "API endpoint smoke tests proving all critical routes work in SQLite mode"
affects: [06-offline-demo-validation]

tech-stack:
  added: []
  patterns: ["FastAPI TestClient with dependency_overrides for SQLite-mode API testing", "socketio.ASGIApp.other_asgi_app for inner FastAPI app access"]

key-files:
  created:
    - tests/integration/test_offline_mode_detection.py
    - tests/integration/test_offline_api_endpoints.py
  modified: []

key-decisions:
  - "Use socketio.ASGIApp.other_asgi_app to access inner FastAPI app for TestClient (server.main wraps app in Socket.IO)"
  - "Session-scoped template DB from SQLAlchemy Base.metadata.create_all for fast per-test DB copies"
  - "Seed test data via raw SQL INSERT for row tests (qa_flag_count=0 explicit to avoid NULL)"

patterns-established:
  - "API smoke test pattern: dependency_overrides for all 9 repo factories + auth + db"

requirements-completed: [OFFL-02, OFFL-03]

duration: 12min
completed: 2026-03-15
---

# Phase 6 Plan 02: Offline Mode Detection & API Endpoint Validation Summary

**3-mode factory routing validated (27 tests) + API endpoint smoke tests in SQLite mode (21 tests) -- 48 tests total, all passing**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-14T14:58:19Z
- **Completed:** 2026-03-15T15:10:49Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- Validated _is_offline_mode header detection (OFFLINE_MODE_ prefix, JWT, empty, none, missing Bearer)
- Validated _is_server_local config detection (sqlite vs postgresql)
- Verified all 9 factory functions route to correct SQLite repos in both server_local and offline modes
- Smoke-tested 10+ API endpoints via TestClient in SQLite mode (health, platforms, projects, folders, rows, TMs, context, mapdata)
- Confirmed no 500 errors from any endpoint in SQLite mode
- Context/MapData return graceful degradation responses (not errors)

## Task Commits

Each task was committed atomically:

1. **Task 1: Mode detection logic validation** - `ba7271d1` (test)
2. **Task 2: API endpoint smoke tests in SQLite mode** - `2033ccb8` (test)

## Files Created/Modified
- `tests/integration/test_offline_mode_detection.py` - 27 tests for 3-mode detection logic and all 9 factory functions
- `tests/integration/test_offline_api_endpoints.py` - 21 API smoke tests using TestClient with SQLite dependency overrides

## Decisions Made
- Used `socketio.ASGIApp.other_asgi_app` to access inner FastAPI app (server.main wraps app in Socket.IO ASGI wrapper)
- Session-scoped template DB pattern (copy from pre-built template, same as stability/conftest.py)
- Raw SQL seed data for row tests with explicit `qa_flag_count=0` to avoid NULL validation errors

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `server.main.app` is wrapped in `socketio.ASGIApp` which doesn't expose `dependency_overrides` -- resolved by accessing `app.other_asgi_app` for the inner FastAPI instance
- SQLAlchemy `Column(Integer, default=0)` is Python-side only -- raw SQL INSERTs don't get the default, so `qa_flag_count` must be explicitly set in test seed data

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Mode detection and API layer validated for SQLite mode
- Ready for Phase 6 Plan 03 (if applicable) or phase completion

---
*Phase: 06-offline-demo-validation*
*Completed: 2026-03-15*

## Self-Check: PASSED
