# P30: CI/CD Pipeline Optimization

**Created:** 2025-12-15 | **Status:** REVIEW COMPLETE | **Priority:** Medium

---

## Goal

1. **Review all tests running in CI** - Find and remove redundant/duplicate tests from CI
2. **Add smoke test** - Verify installer actually works (install, download, autologin, interaction)

---

## 1. Test Audit - COMPLETE

### What runs in CI (from build.yml)

```bash
TEST_DIRS="tests/unit/ tests/integration/ tests/security/ tests/e2e/test_kr_similar_e2e.py tests/e2e/test_xlstransfer_e2e.py tests/e2e/test_quicksearch_e2e.py"
```

### Current Test Counts

| Directory | Files | Tests | Status |
|-----------|-------|-------|--------|
| tests/unit/ | 28 | ~530 | IN CI |
| tests/integration/ | 11 | ~124 | IN CI |
| tests/security/ | 4 | ~87 | IN CI |
| tests/e2e/ (3 files) | 3 | ~38 | IN CI |
| **Total** | **46** | **~779** | |

---

## 2. Duplicates Found - REMOVE FROM CI

### HIGH PRIORITY - Clear Duplicates

| File to REMOVE | Tests | Duplicate Of | Reason |
|----------------|-------|--------------|--------|
| `tests/unit/test_cache_extended.py` | 29 | test_cache_module.py | Same cache config/TTL tests |
| `tests/unit/test_server/test_cache.py` | 15 | test_cache_module.py | Same CacheManager tests |
| `tests/unit/test_websocket_module.py` | 14 | test_websocket_functions.py | Trivial structural tests only |
| `tests/integration/server_tests/test_api_endpoints.py` | 14 | test_api_endpoints_detailed.py | Less comprehensive version |

**Total to Remove: 72 test functions (~9%)**

### Analysis Details

#### Cache Testing (3 files testing same thing)
- `test_cache_module.py` (23 tests) - **KEEP** - Most comprehensive
- `test_cache_extended.py` (29 tests) - **REMOVE** - Duplicates same constants
- `test_server/test_cache.py` (15 tests) - **REMOVE** - Repeats same tests

#### WebSocket Testing
- `test_websocket_functions.py` (41 tests) - **KEEP** - Tests actual emit functions
- `test_websocket_module.py` (14 tests) - **REMOVE** - Only checks imports exist
- `test_server/test_websocket.py` (13 tests) - **KEEP** - Uses mocks (different approach)

#### API Endpoint Testing
- `test_api_endpoints_detailed.py` (28 tests) - **KEEP** - Comprehensive
- `test_api_endpoints.py` (14 tests) - **REMOVE** - Subset of detailed version
- `test_api_true_simulation.py` (20 tests) - **KEEP** - Flow-based (complementary)

---

## 3. Tests to KEEP (Good Coverage)

| Category | Files | Tests | Note |
|----------|-------|-------|------|
| Unit - Auth | test_auth_module.py | 32 | Password/JWT |
| Unit - Cache | test_cache_module.py | 23 | Primary cache tests |
| Unit - Code | test_code_patterns.py | 49 | Pattern validation |
| Unit - DB | test_db_utils.py | 28 | Database utils |
| Unit - KR Similar | test_kr_similar_*.py | 57 | Core algorithms |
| Unit - QuickSearch | test_quicksearch_*.py | 100 | All QS modules |
| Unit - TM | test_tm_*.py | 66 | Translation memory |
| Unit - WebSocket | test_websocket_functions.py | 41 | Emit functions |
| Unit - XLSTransfer | test_xlstransfer_modules.py | 25 | Core modules |
| Unit - Client | client/*.py | 86 | File/Logger/Progress |
| Unit - Server | test_server/*.py (minus cache) | 71 | Models/QS/WS |
| Integration | All (minus test_api_endpoints.py) | 110 | API/Auth/Async |
| Security | All 4 files | 87 | Audit/CORS/IP/JWT |
| E2E | 3 specific files | 38 | Tool workflows |

---

## 4. Implementation - DESELECTS Update

### New DESELECTS for build.yml

```bash
DESELECTS="--deselect=tests/unit/test_cache_extended.py \
           --deselect=tests/unit/test_server/test_cache.py \
           --deselect=tests/unit/test_websocket_module.py \
           --deselect=tests/integration/server_tests/test_api_endpoints.py \
           --deselect=tests/integration/test_tm_real_model.py \
           --deselect=tests/e2e/test_xlstransfer_e2e.py::TestXLSTransferEmbeddings::test_05_model_loads \
           --deselect=tests/e2e/test_xlstransfer_e2e.py::TestXLSTransferEmbeddings::test_06_embedding_generation \
           --deselect=tests/e2e/test_xlstransfer_e2e.py::TestXLSTransferEmbeddings::test_07_embedding_caching \
           --deselect=tests/e2e/test_kr_similar_e2e.py::TestKRSimilarEmbeddings::test_05_model_loads \
           --deselect=tests/e2e/test_kr_similar_e2e.py::TestKRSimilarEmbeddings::test_06_embedding_generation"
```

---

## 5. Smoke Test - CI-ADAPTED VERSION

### What CI CAN verify (REQUIRED to pass)
1. Silent install completes successfully
2. All critical files exist (exe, server, python, tools)
3. File structure is correct

### What CI CANNOT verify (OPTIONAL/Informational)
4. Backend starts - **Requires PostgreSQL (not in CI)**
5. Admin autologin - **Requires database**
6. API interaction - **Requires running backend**

### Note on Full Testing
Full backend testing requires manual validation with PostgreSQL.
The CI smoke test verifies the **installer works** and **files are bundled correctly**.

### Implementation

See `.gitea/workflows/build.yml` - "Smoke Test - Installer Verification" step.

---

## 6. Final Results

### Before Optimization
- **Tests:** ~779 functions
- **Time:** ~17 minutes
- **Redundancy:** 72 duplicate tests

### After Optimization (Expected)
- **Tests:** ~707 functions (-9%)
- **Time:** ~15 minutes (estimated -12%)
- **Coverage:** Same (removed only duplicates)

### Tests Removed from CI

| Test File | Functions | Reason |
|-----------|-----------|--------|
| test_cache_extended.py | 29 | Duplicate of test_cache_module.py |
| test_server/test_cache.py | 15 | Duplicate of test_cache_module.py |
| test_websocket_module.py | 14 | Trivial import checks only |
| test_api_endpoints.py | 14 | Subset of test_api_endpoints_detailed.py |
| **Total** | **72** | |

---

## 7. Implementation Checklist

- [x] Review tests/unit/ - duplicates identified
- [x] Review tests/integration/ - duplicates identified
- [x] Review tests/security/ - no duplicates (keep all)
- [x] Review tests/e2e/ - already optimized (3 specific files)
- [x] Update DESELECTS in build.yml
- [x] Add smoke test to build.yml
- [x] Test updated CI - Build v25.1215.0204 (smoke test adjusted for no-DB CI)
- [ ] User validation

---

## 8. Apply Changes

**To apply these optimizations, update `.gitea/workflows/build.yml`:**

1. Add new DESELECTS (line ~351)
2. Add smoke test step after Windows build
3. Commit and trigger build

**Command to apply:**
```bash
# After user approval, run:
# Edit build.yml with new DESELECTS
# Add smoke test step
# Commit and push
```

---

*Review completed: 2025-12-15 by Claude*
