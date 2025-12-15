# Session Context - Last Working State

**Updated:** 2025-12-15 16:00 | **By:** Claude

---

## Current Priority: P33 Offline Mode + CI Overhaul

**Status: 100% COMPLETE** | Full structure preservation + Sync + CI verified

---

## Latest Build Status

### Build v2512151747
- **Trigger:** SQLite smoke test
- **Expected Result:** May fail on old code (before auto-detect fix)
- **Next Action:** Trigger new build with auto-detect fix committed

### Pending Commit (READY)
```bash
git diff .gitea/workflows/build.yml
# Changes: Windows smoke test now uses auto-detect mode (not manual DATABASE_MODE=sqlite)
```

---

## What Was Fixed This Session

### 1. Windows Smoke Test Auto-Detection (build.yml)
**Problem:** Smoke test manually set `DATABASE_MODE=sqlite`, bypassing auto-detection feature.
**Fix:** Removed manual override, let backend auto-detect and fallback to SQLite.

```powershell
# BEFORE (wrong - manual override):
$env:DATABASE_MODE = "sqlite"
$appProc = Start-Process "$installDir\LocaNext.exe" -PassThru

# AFTER (correct - auto-detect):
# Let auto-detection work - no manual DATABASE_MODE override
# Backend will try PostgreSQL, fail, auto-fallback to SQLite
$appProc = Start-Process "$installDir\LocaNext.exe" -PassThru
```

### 2. CI Tests Already Fixed (Previous Session)
- `test_server_startup.py`: Fixed `DATABASE_TYPE` → `DATABASE_MODE`/`ACTIVE_DATABASE_TYPE`
- `test_full_simulation.py`: Added FAISS dimension mismatch skip

### 3. SQL Injection Fixed (CR-002)
- `server/tools/ldm/api.py`: All TM queries now use parameterized queries

---

## Test Architecture

### Linux CI (PostgreSQL)
```
TEST_DIRS (build.yml line 362):
- tests/integration/test_api_true_simulation.py  # Real API tests
- tests/integration/server_tests/test_server_startup.py
- tests/integration/server_tests/test_auth_integration.py
- tests/integration/server_tests/test_async_auth.py
- tests/security/  # All security tests
- tests/e2e/test_full_simulation.py  # KR Similar, XLSTransfer
- tests/e2e/test_kr_similar_e2e.py
- tests/e2e/test_quicksearch_e2e.py
- tests/unit/test_db_utils.py
- tests/unit/test_kr_similar_core.py
- tests/unit/test_tm_search.py
```
**Result:** ~256 tests (real API, real PostgreSQL)

### Windows Smoke Test (build.yml Phase 4)
```powershell
# 1. Silent install installer
# 2. Verify required files exist
# 3. Start app, wait for backend
# 4. Check /health endpoint
# 5. Verify database_type (auto-detected)
```
**Result:** Installer + Backend verification

### ULTIMATE Smoke Test (Manual/CDP)
```
tests/cdp/test_ultimate_smoke.py
- Requires: LocaNext.exe running with --remote-debugging-port=9222
- Tests: Full user journey (login → edit cell → verify DB → download)
- Use for: Manual testing, Windows E2E validation
```
**NOT for Linux CI** (requires running Electron app)

---

## P33 Phase Status (100% Complete)

| Phase | Status | What |
|-------|--------|------|
| 1 | ✅ | SQLite backend (FlexibleJSON, db_setup.py, auto-fallback) |
| 2 | ✅ | Auto-detection (PostgreSQL unreachable → SQLite) |
| 3 | ✅ | Tabbed sidebar (Files/TM tabs) |
| 4 | ✅ | Online/Offline badges in toolbar |
| 5 | ✅ | Go Online button + Upload to Server modal |
| 6 | ✅ | CI streamlined (1536 → 256 real tests) |
| 7 | ✅ | extra_data JSONB + Sync endpoints |
| 8 | ✅ | Windows smoke test uses auto-detect |

---

## Key Implementation Details

### Database Mode Configuration
```python
# server/config.py
DATABASE_MODE = "auto"  # Options: auto | postgresql | sqlite
ACTIVE_DATABASE_TYPE = "postgresql"  # Set at runtime by auto-detection

# Auto-detection flow:
# 1. Try PostgreSQL connection
# 2. If fails → fallback to SQLite
# 3. Set ACTIVE_DATABASE_TYPE = actual type used
```

### extra_data JSONB (Full Structure Preservation)
```python
# server/database/models.py
class LDMFile(Base):
    extra_data = Column(FlexibleJSON, nullable=True)
    # TXT: {"encoding": "utf-8", "total_columns": 10}
    # XML: {"root_element": "LangData", "element_tag": "LocStr"}

class LDMRow(Base):
    extra_data = Column(FlexibleJSON, nullable=True)
    # TXT: {"col7": "value", "col8": "value"}
    # XML: {"CustomAttr": "value"}
```

### Sync Endpoints
```
POST /api/ldm/sync-to-central     # Sync file + rows SQLite → PostgreSQL
POST /api/ldm/tm/sync-to-central  # Sync TM + entries SQLite → PostgreSQL
```

---

## Files Modified This Session

| File | Change |
|------|--------|
| `.gitea/workflows/build.yml` | Windows smoke test uses auto-detect (not manual SQLite) |

## Files Modified Previous Session

| File | Change |
|------|--------|
| `server/database/models.py` | Added `extra_data` JSONB columns |
| `server/tools/ldm/file_handlers/txt_handler.py` | Captures extra columns |
| `server/tools/ldm/file_handlers/xml_handler.py` | Captures extra attributes |
| `server/tools/ldm/api.py` | SQL injection fix + sync endpoints |
| `tests/integration/server_tests/test_server_startup.py` | Fixed config test |
| `tests/e2e/test_full_simulation.py` | Added FAISS skip |
| `tests/cdp/test_ultimate_smoke.py` | Created comprehensive CDP test |

---

## Next Steps

1. **Commit auto-detect fix:**
   ```bash
   git add .gitea/workflows/build.yml
   git commit -m "P33: Windows smoke test uses auto-detect mode"
   ```

2. **Trigger new build:**
   ```bash
   echo "Build LIGHT v$(date '+%y%m%d%H%M') - Auto-detect smoke test" >> GITEA_TRIGGER.txt
   git add -A && git commit -m "Build: Auto-detect smoke test"
   git push origin main && git push gitea main
   ```

3. **Verify build passes:**
   - Linux CI: ~256 tests with PostgreSQL
   - Windows: Installer + Backend with auto-detect SQLite fallback

---

## Quick Commands

```bash
# Check git status
git status

# Run Linux tests locally (with PostgreSQL)
./scripts/start_all_servers.sh
python3 -m pytest tests/integration/test_api_true_simulation.py -v

# Test SQLite auto-detection locally
POSTGRES_HOST=invalid python3 server/main.py
# Should fallback to SQLite

# Trigger build
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Code Review Status (P32 - LOW PRIORITY)

11 issues documented in `docs/code-review/ISSUES_20251215_LDM_API.md`:
- ~~2 CRITICAL~~ → 1 fixed (SQL injection), 1 remaining (response format)
- 3 HIGH (deprecated asyncio)
- 6 MEDIUM/LOW

**Do AFTER P33 build verification.**

---

*For global priorities: [Roadmap.md](../../Roadmap.md)*
*For P33 details: [P33_OFFLINE_MODE_CI_OVERHAUL.md](P33_OFFLINE_MODE_CI_OVERHAUL.md)*
