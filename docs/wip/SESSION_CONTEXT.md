# Session Context - Claude Handoff Document

**Updated:** 2025-12-16 12:45 KST | **Build:** 290 (FAILED - Windows build)

---

## TL;DR FOR NEXT SESSION

**CRITICAL: 7 consecutive build failures since Build 284 (Svelte 5 migration)**

| Build | Status | Time | What Failed |
|-------|--------|------|-------------|
| 290 | ❌ | 5m7s | Tests pass, Windows build fails |
| 289 | ❌ | 5m31s | Tests pass, Windows build fails |
| 288 | ❌ | 23m4s | Unit tests dropped DB tables |
| 287 | ❌ | 2m29s | Server crash |
| 286 | ❌ | 13m | Windows build |
| 285 | ❌ | - | Windows build |
| 284 | ❌ | - | P35 Svelte 5 (broke something) |
| **283** | ✅ | 22m | **LAST PASSING BUILD** |

**What We Fixed:**
1. ✅ Test isolation - unit tests use SQLite, don't drop CI database
2. ✅ Test bloat - Gitea runs ~273 tests in 5 min (not 1000+ in 23 min)
3. ✅ Connectivity tests included - `test_database_connectivity.py` (26 tests)

**What's Still Broken:**
- ❌ **Windows build step** - Tests pass but Windows installer build fails
- This has been broken since Build 284 (Svelte 5 migration)
- Need to check Windows runner or diagnose Windows build errors

**What To Do Next:**
1. **Check Windows runner** - Is it running? Check in browser: http://localhost:3000/neilvibe/LocaNext/actions/runs/290
2. **View build logs** - See what error occurs in Windows build step
3. **Compare to Build 283** - What changed that broke Windows build?

**Quick Commands:**
```bash
# Check build status in browser
open http://localhost:3000/neilvibe/LocaNext/actions/runs/290

# Check servers
./scripts/check_servers.sh

# Run connectivity tests locally
python3 -m pytest tests/integration/test_database_connectivity.py -v --no-cov

# Run db_utils tests (now use SQLite)
python3 -m pytest tests/unit/test_db_utils.py -v --no-cov
```

---

## CURRENT STATE

### Build 290 Status (Latest)
- **Triggered:** 2025-12-16 12:04 KST
- **Runtime:** 5m7s (optimized from 23 min)
- **Linux Tests:** ✅ PASSED (~273 tests)
- **Windows Build:** ❌ FAILED
- **Overall:** ❌ FAILED
- **URL:** http://localhost:3000/neilvibe/LocaNext/actions/runs/290

### Build Failure Pattern
Since Build 284 (Svelte 5 migration), ALL builds fail at Windows step. Tests pass but Windows build breaks. This suggests the Windows runner may be down OR something in the Svelte 5 changes broke the Electron build.

### App Status
```
LocaNext v25.1216.1210
├── Backend:     ✅ PostgreSQL + SQLite offline
├── Frontend:    ✅ Electron 39 + Svelte 5 (runes migrated)
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── CI/CD:       ✅ ~273 tests, ~5 min runtime (optimized!)
├── Offline:     ✅ Auto-fallback + indicator (needs prod test)
├── Installer:   ✅ Fixes in code (BUG-009, BUG-010)
└── Tests:       ✅ Fixed isolation (SQLite for unit tests)
```

### Test Configuration
| Test Type | Database | Status |
|-----------|----------|--------|
| Integration tests | CI PostgreSQL (via API) | ✅ Working |
| Unit tests (db_utils) | SQLite in-memory | ✅ 24 pass |
| Unit tests (models) | SQLite in-memory | ⏭️ 33 skipped (need JSONB) |
| Connectivity tests | CI PostgreSQL | ✅ 26 pass |

---

## ISSUES FIXED THIS SESSION

### Build 287/288 Failure (Test Isolation)
- **Symptom:** Server crashed with `relation "users" does not exist` after ~16 minutes
- **Root Cause:** Unit tests dropped all PostgreSQL tables during cleanup
- **Fix:** Unit tests now use SQLite in-memory, isolated from CI database
- **Files Changed:**
  - `tests/unit/test_db_utils.py` - Use SQLite, simplified fixture
  - `tests/unit/test_server/test_models.py` - Use SQLite (tests skipped)

### Build 288 Slow Runtime (Test Bloat)
- **Symptom:** Tests took 23 minutes instead of ~5 minutes
- **Root Cause:** Gitea CI was running 1000+ tests (entire directories) instead of ~273 (specific files)
- **Cause:** Commit 2d9c658 changed `TEST_DIRS` to include entire `tests/unit/` directory
- **Fix:** Changed Gitea workflow back to specific test files
- **Files Changed:**
  - `.gitea/workflows/build.yml` - Use specific test files instead of directories

### Build 287 Initial Crash (before test fix)
- **Symptom:** Server died after "Initialized XLSTransfer API"
- **Diagnosis:** Intermittent issue, resolved after adding debug logging
- **Files Changed:**
  - `server/api/xlstransfer_async.py` - Added verbose module loading logs

---

## FILES MODIFIED THIS SESSION

```
tests/unit/test_db_utils.py           # Fixed: Always use SQLite
tests/unit/test_server/test_models.py # Fixed: Always use SQLite
server/api/xlstransfer_async.py       # Added debug logging
.gitea/workflows/build.yml            # Fixed: Use specific test files
GITEA_TRIGGER.txt                     # Build triggers
docs/wip/SESSION_CONTEXT.md           # This file
docs/wip/ISSUES_TO_FIX.md             # Issue tracking
```

---

## PRODUCTION TESTING CHECKLIST

**Before deploying to production, verify:**

1. **Offline Mode:**
   - [ ] Disconnect PostgreSQL, verify SQLite fallback
   - [ ] Check Online/Offline indicator shows correct state
   - [ ] Test "Go Online" button reconnects

2. **Installer:**
   - [ ] Run installer on fresh Windows machine
   - [ ] Verify first-run setup creates data directories
   - [ ] Verify auto-login works in offline mode

3. **All 4 Tools:**
   - [ ] XLSTransfer loads files
   - [ ] QuickSearch searches dictionaries
   - [ ] KR Similar finds similar strings
   - [ ] LDM opens and edits files

---

## ARCHITECTURE NOTES

### Database Connection Flow
```
Server Start
    │
    ├─ DATABASE_MODE=auto (default)
    │
    ├─ check_postgresql_reachable(timeout=3s)
    │      │
    │      ├─ Reachable → Use PostgreSQL
    │      │
    │      └─ Unreachable → Fall back to SQLite
    │
    └─ Set config.ACTIVE_DATABASE_TYPE
```

### CI Test Isolation (NEW)
```
CI Environment
    │
    ├─ Server (PostgreSQL locanext_ci_test)
    │      └─ Stays running during all tests
    │
    ├─ Integration Tests (via API)
    │      └─ Call server endpoints, don't touch DB directly
    │
    └─ Unit Tests (SQLite in-memory)
           └─ Isolated, don't affect server database
```

---

*Last updated by Claude - Build 290*
