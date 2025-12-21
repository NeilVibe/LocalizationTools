# P36: Honest Coverage Assessment

**Created:** 2025-12-21 | **Purpose:** Double-check what's tested vs missing

---

## Coverage Matrix

| Area | Covered? | Test Files | Notes |
|------|----------|------------|-------|
| **TM Upload** | YES | test_e2e_1_tm_upload.py | StringID + Standard |
| **TM Building/Index** | YES | test_e2e_2_pkl_index.py | PKL index creation |
| **TM Search** | YES | test_e2e_3_tm_search.py, test_tm_search.py | Tier1 + Tier2 |
| **Pretranslation** | YES | test_e2e_4_pretranslate.py | Multiple modes |
| **File Upload** | PARTIAL | e2e tests | Excel parsing tested, raw upload less |
| **File Building** | YES | test_production_workflows_e2e.py | Dictionary creation |
| **Embeddings General** | YES | test_kr_similar_embeddings.py | Module tests |
| **Model2Vec** | WEAK | test_e2e_tm_faiss_real.py | Only 1 file mentions it |
| **Qwen** | YES | test_qwen_*.py (3 files) | Korean accuracy, validation |
| **Dashboard** | YES | test_dashboard_api.py | Stats endpoints |
| **DB** | YES | test_db_utils.py, test_database_connectivity.py | Connectivity, utils |
| **Server Logs** | YES | test_remote_logging.py, test_audit_logging.py | Remote + audit |
| **KR Similar** | YES | test_kr_similar_*.py (4+ files) | Core, embeddings, e2e |
| **QuickSearch** | YES | test_quicksearch_*.py (6 files) | Full coverage |
| **XLS Transfer** | YES | test_xlstransfer_*.py (3+ files) | Core, e2e |

---

## GAPS IDENTIFIED

### CRITICAL (Missing or Weak)

| Area | Issue | Priority |
|------|-------|----------|
| **Model2Vec vs Qwen Toggle** | No test for switching engines | HIGH |
| **File Upload API** | Direct upload endpoint not tested | HIGH |
| **Large File Handling** | No test for 10MB+ files | HIGH |
| **Performance Benchmarks** | Zero performance tests | HIGH |

### MEDIUM (Incomplete)

| Area | Issue | Priority |
|------|-------|----------|
| **TM Sync** | Unit tested, not integration | MEDIUM |
| **FAISS Rebuild** | Index rebuild not explicitly tested | MEDIUM |
| **Concurrent Access** | No multi-user test | MEDIUM |
| **Error Recovery** | DB disconnect recovery not tested | MEDIUM |

### LOW (Nice to Have)

| Area | Issue | Priority |
|------|-------|----------|
| **UI Visual Tests** | CDP tests exist but limited | LOW |
| **Memory Usage** | No memory leak tests | LOW |
| **Stress Tests** | No 1000+ concurrent test | LOW |

---

## Detailed Gap Analysis

### 1. Model2Vec vs Qwen Toggle

**What's missing:**
- No test that toggles between Model2Vec and Qwen
- No test comparing results between engines
- Fast/Deep toggle in LDM not tested

**Proposed tests:**
```python
def test_toggle_model2vec_to_qwen():
    # Switch from Model2Vec to Qwen, verify results still work

def test_embedding_engine_consistency():
    # Same query should return similar results regardless of engine
```

### 2. File Upload API

**What's tested:**
- Excel parsing (in tools tests)
- Dictionary creation from parsed data

**What's missing:**
- Direct file upload to /api/upload endpoint
- Large file upload (>10MB)
- Invalid file rejection
- Progress tracking during upload

**Proposed tests:**
```python
def test_upload_valid_excel():
    # POST /api/upload with Excel file

def test_upload_large_file():
    # 10MB+ file upload

def test_upload_invalid_format():
    # Should reject non-Excel files
```

### 3. Performance Benchmarks

**Completely missing.** Need:
```python
def test_api_latency_under_200ms():
def test_embedding_speed_100_per_sec():
def test_search_speed_under_100ms():
def test_concurrent_50_requests():
```

---

## What IS Well Covered

### TM Pipeline (GOOD)
```
Upload → Parse → Index → Search → Pretranslate
  ✅       ✅       ✅       ✅         ✅
```

### Tools (GOOD)
```
KR Similar:   ✅ Core, Embeddings, E2E
QuickSearch:  ✅ Dictionary, Parser, Searcher, E2E
XLS Transfer: ✅ Core, Modules, E2E
```

### Security (GOOD)
```
JWT:    ✅ test_jwt_security.py
CORS:   ✅ test_cors_config.py
IP:     ✅ test_ip_filter.py
Audit:  ✅ test_audit_logging.py
```

### Auth (GOOD)
```
Password:  ✅ Hash, verify
Sessions:  ✅ Create, expire
Users:     ✅ CRUD, permissions
```

---

## Updated Test Count

| Category | Existing | Gaps | New Needed |
|----------|----------|------|------------|
| Processing (TM) | 46 | Model2Vec toggle | +2 |
| API | 54 | File upload, large file | +4 |
| Performance | 0 | Everything | +7 |
| Security | 40 | SQL injection, XSS | +3 |
| Integration | 150 | Concurrent, recovery | +3 |
| **TOTAL** | ~516 | | **+19** |

---

## Summary: Honest Assessment

**What's GREAT:**
- TM pipeline fully tested
- All 3 tools (KR Similar, QuickSearch, XLS Transfer) well tested
- Security basics covered
- Auth flow tested
- Dashboard API tested

**What's MISSING:**
1. Model2Vec ↔ Qwen toggle (CRITICAL)
2. Direct file upload API (CRITICAL)
3. Performance benchmarks (CRITICAL)
4. Large file handling (HIGH)
5. Concurrent access (MEDIUM)

**Action Required:**
- Create ~19 new tests to fill gaps
- Most critical: Performance + File upload + Engine toggle

---

---

## Additional Areas Checked

### DB Sync / Offline-Online (GOOD COVERAGE)

| Test | File | Status |
|------|------|--------|
| Fresh build inserts | test_tm_sync.py | YES |
| No changes unchanged | test_tm_sync.py | YES |
| New entry insert | test_tm_sync.py | YES |
| Removed entry delete | test_tm_sync.py | YES |
| Changed target update | test_tm_sync.py | YES |
| Mixed operations | test_tm_sync.py | YES |
| PostgreSQL connection | test_database_connectivity.py | YES |
| SQLite fallback | test_database_connectivity.py | YES |
| Go online transition | test_database_connectivity.py | YES |
| Connection status | test_database_connectivity.py | YES |
| Can sync check | test_database_connectivity.py | YES |

**Verdict: WELL COVERED**

### Path / Folder Creation (GOOD COVERAGE)

| Test | File | Status |
|------|------|--------|
| Default path init | test_quicksearch_dictionary.py | YES |
| Custom path init | test_quicksearch_dictionary.py | YES |
| Directory creation | test_quicksearch_dictionary.py | YES |
| Path format | test_quicksearch_dictionary.py | YES |
| Creates dirs | test_quicksearch_dictionary.py | YES |

### File Handler (EXCELLENT COVERAGE - 40+ tests!)

| Test | File | Status |
|------|------|--------|
| File size calculation | test_utils_file_handler.py | YES |
| File hash (MD5, SHA256) | test_utils_file_handler.py | YES |
| Temp copy creation | test_utils_file_handler.py | YES |
| Safe delete | test_utils_file_handler.py | YES |
| Output path handling | test_utils_file_handler.py | YES |
| File validation | test_utils_file_handler.py | YES |
| Extension validation | test_utils_file_handler.py | YES |
| Safe filename | test_utils_file_handler.py | YES |
| Long name truncation | test_utils_file_handler.py | YES |
| Directory counting | test_utils_file_handler.py | YES |
| Temp file manager | test_utils_file_handler.py | YES |
| Complete workflow | test_utils_file_handler.py | YES |

**Verdict: EXCELLENT COVERAGE**

---

## Remaining Gaps (Updated)

### CRITICAL

| Gap | Priority | Notes |
|-----|----------|-------|
| Model2Vec ↔ Qwen toggle | CRITICAL | No engine switching test |
| Performance benchmarks | CRITICAL | Zero performance tests |
| Large file upload (10MB+) | HIGH | Not tested |

### MEDIUM

| Gap | Priority | Notes |
|-----|----------|-------|
| Windows-specific path | MEDIUM | Cross-platform path handling |
| Concurrent DB access | MEDIUM | Multi-user sync |

### What We DON'T Need (Already Covered)

- ~~Offline/Online sync~~ → COVERED in test_database_connectivity.py
- ~~SQLite fallback~~ → COVERED
- ~~TM sync logic~~ → COVERED in test_tm_sync.py (17 tests!)
- ~~Path creation~~ → COVERED in test_quicksearch_dictionary.py
- ~~File handling~~ → COVERED in test_utils_file_handler.py (40+ tests!)
- ~~Safe filenames~~ → COVERED
- ~~Temp file cleanup~~ → COVERED

---

## Final Gap Count

| Category | Existing | Still Missing |
|----------|----------|---------------|
| DB/Sync | 17+ | 0 |
| Paths/Files | 45+ | 2 (Windows-specific) |
| Performance | 0 | 7 |
| Engine Toggle | 0 | 2 |
| Large Files | 0 | 2 |
| **TOTAL NEW NEEDED** | | **~13** |

---

## LDM/File Viewer Workflow Gaps (NEW SECTION)

### Cell State Machine (PARTIALLY IMPLEMENTED)

**Expected State Transitions:**
```
┌─────────────────────────────────────────────────────────────┐
│                    CELL STATE MACHINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐    Edit     ┌────────────┐                  │
│   │  EMPTY   │ ─────────→  │  PENDING   │  ✅ WORKS        │
│   │(no text) │             │ (has text) │                  │
│   └──────────┘             └─────┬──────┘                  │
│                                  │                          │
│                      Ctrl+T      │      Ctrl+S              │
│                   ┌──────────────┼───────────────┐          │
│                   ▼              │               ▼          │
│            ┌────────────┐        │       ┌────────────┐     │
│            │ TRANSLATED │        │       │  REVIEWED  │     │
│            │  (Ctrl+T)  │ ✅     │       │  (Ctrl+S)  │ ✅  │
│            └──────┬─────┘        │       └──────┬─────┘     │
│                   │              │              │           │
│                   └──────────────┴──────────────┘           │
│                                  │                          │
│                                  ▼                          │
│                        ┌─────────────────┐                  │
│                        │ AUTO-SYNC TO TM │  ❌ NOT          │
│                        │ (if TM active)  │  IMPLEMENTED!    │
│                        └─────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Status values in API:
- "pending" (edited but not confirmed)
- "translated" (Ctrl+T - translation only)
- "reviewed" (Ctrl+S - confirmed/reviewed)
```

### ⚠️ FEATURE GAP: Auto-Add to TM on Confirm

**This is NOT just a missing test - the FEATURE is not implemented!**

**Current Flow (what happens now):**
```
Cell edit (Ctrl+S) → update_row() → Save to DB → WebSocket broadcast → DONE
                                                                    ↑
                                                          STOPS HERE!
```

**Expected Flow (what SHOULD happen):**
```
Cell edit (Ctrl+S) → update_row() → Save to DB → WebSocket broadcast
                                  ↓
                   if status='reviewed' AND linked_tm exists:
                                  ↓
                   Add entry to TM → Trigger _auto_sync_tm_indexes
```

**Code Location:** `server/tools/ldm/api.py:728-798` (`update_row` function)

**What's Missing in Code:**
1. Check `LDMActiveTM` table for linked TM (file_id or project_id)
2. If `status='reviewed'` and TM linked → call `tm_manager.add_entry()`
3. Trigger `_auto_sync_tm_indexes(tm_id, user_id)` background task

**Related Tables:**
- `LDMActiveTM` - Links TMs to projects/files (EXISTS, not used in update_row)
- `LDMTMEntry` - TM entries (add_entry exists but not called)

### What IS Implemented vs What's Missing

| Feature | Status | Location |
|---------|--------|----------|
| Cell status: pending → translated (auto) | ✅ WORKS | api.py:757-759 |
| Cell status: manual set any status | ✅ WORKS | api.py:761-762 |
| Edit history tracking | ✅ WORKS | api.py:767-776 |
| WebSocket broadcast on update | ✅ WORKS | api.py:781-794 |
| TM entry confirm/unconfirm | ✅ WORKS | api.py:1395-1452 |
| TM auto-sync after TM entry edit | ✅ WORKS | api.py:1943-1981 |
| File → TM conversion (manual) | ✅ WORKS | api.py:2195-2282 |
| LDMActiveTM link table | ✅ EXISTS | models.py:853-888 |
| **Auto-add to TM on cell confirm** | ❌ **NOT IMPLEMENTED** | - |
| **Check linked TM on row update** | ❌ **NOT IMPLEMENTED** | - |

**What's NOT Tested (some are feature gaps):**
| Test | Gap | Priority | Notes |
|------|-----|----------|-------|
| Cell empty → pending transition | NO TEST | HIGH | Feature works |
| Cell pending → translated (Ctrl+T) | PARTIAL (CDP) | HIGH | Feature works |
| Cell pending → reviewed (Ctrl+S) | PARTIAL (CDP) | HIGH | Feature works |
| **Auto-add to TM on confirm** | **FEATURE GAP** | **CRITICAL** | **NOT IMPLEMENTED** |
| TM index auto-rebuild after confirm | FEATURE GAP | HIGH | Depends on above |
| Cell state persists after reload | NO TEST | HIGH | Feature works |

### File Viewer Workflow (PARTIAL)

**Expected Flow:**
```
1. Upload File → Parse → Display cells
2. Edit cell (double-click) → Enter text
3. Ctrl+T or Ctrl+S → Status changes
4. If TM linked: Auto-add entry to TM
5. TM index auto-rebuilds in background
```

**What's Covered vs Missing:**

| Step | Covered? | Notes |
|------|----------|-------|
| File upload | YES | e2e tests ✓ |
| File parsing | YES | unit tests ✓ |
| Cell display | PARTIAL | CDP smoke test only |
| Cell edit modal | PARTIAL | test_edit_keyboard.js tests keys |
| Status change API | NO | Endpoint exists but no test |
| Auto-add to TM | NO | `_auto_sync_tm_indexes` not tested |
| TM rebuild trigger | NO | Background task not verified |

### TM Editing Workflow (NOT TESTED)

**What should be tested:**
| Scenario | Covered? | Priority |
|----------|----------|----------|
| Edit TM entry text | NO | HIGH |
| Delete TM entry | NO | HIGH |
| TM entry edit triggers index rebuild | NO | HIGH |
| Bulk TM operations | NO | MEDIUM |
| TM entry history/audit | NO | LOW |

### Explorer State Management (NOT TESTED)

**File Explorer State:**
| State | Covered? | Notes |
|-------|----------|-------|
| Selected project persists | NO | After refresh |
| Selected file persists | NO | After refresh |
| Expanded folders persist | NO | Tree state |
| Scroll position persists | NO | After tab switch |

**TM Explorer State:**
| State | Covered? | Notes |
|-------|----------|-------|
| Selected TM persists | NO | After refresh |
| TM status display (pending/ready) | YES | UI-047 fixed |
| TM filter state persists | NO | After reload |

---

## Summary: All Gaps Combined

### CRITICAL (Must Have for QA)

| # | Gap | Category | Notes |
|---|-----|----------|-------|
| 1 | Auto-add to TM on cell confirm | LDM Workflow | `_auto_sync_tm_indexes` |
| 2 | Cell state transitions | LDM Workflow | pending→translated→reviewed |
| 3 | Performance benchmarks | Performance | 0 tests exist |
| 4 | Model2Vec ↔ Qwen toggle | Processing | No engine switch test |

### HIGH (Should Have)

| # | Gap | Category | Notes |
|---|-----|----------|-------|
| 5 | TM entry editing | TM Workflow | No edit tests |
| 6 | TM index rebuild trigger | TM Workflow | Background task |
| 7 | Large file upload (10MB+) | API | Not tested |
| 8 | Cell state persistence | LDM State | After reload |
| 9 | SQL injection prevention | Security | SEC-011 |
| 10 | XSS prevention | Security | SEC-012 |

### MEDIUM (Nice to Have)

| # | Gap | Category | Notes |
|---|-----|----------|-------|
| 11 | Explorer state persistence | UI State | File/TM explorers |
| 12 | Concurrent DB access | Integration | Multi-user |
| 13 | Connection pool stress | DB | DB-009 |
| 14 | Windows-specific paths | Cross-platform | Path handling |

---

## New Tests Needed: Complete List

### LDM Workflow Tests (NEW - 8 tests)

```python
# tests/blocks/processing/test_ldm_workflow.py

def test_cell_empty_to_pending():
    """Empty cell → edit → status becomes 'pending'"""

def test_cell_pending_to_translated():
    """Cell with text + Ctrl+T → status becomes 'translated'"""

def test_cell_pending_to_reviewed():
    """Cell with text + Ctrl+S → status becomes 'reviewed'"""

def test_auto_add_to_tm_on_confirm():
    """Confirmed cell auto-adds to linked TM"""

def test_tm_index_rebuild_after_confirm():
    """TM FAISS index rebuilds after new entry"""

def test_cell_state_persists_after_reload():
    """Cell states saved to DB and restored"""

def test_tm_entry_edit():
    """Edit existing TM entry"""

def test_tm_entry_delete():
    """Delete TM entry and verify index update"""
```

### Performance Tests (7 tests)

```python
# tests/performance/test_benchmarks.py

def test_api_health_under_50ms():
def test_login_under_200ms():
def test_tm_search_1k_under_100ms():
def test_tm_search_100k_under_500ms():
def test_embedding_speed_100_per_sec():
def test_file_upload_10mb_under_5s():
def test_concurrent_50_requests():
```

### Security Tests (3 tests)

```python
# tests/blocks/security/test_injection.py

def test_sql_injection_prevention():
def test_xss_prevention_in_responses():
def test_sensitive_data_not_logged():
```

### State Management Tests (4 tests)

```python
# tests/blocks/ui/test_state_persistence.py

def test_file_explorer_selected_project_persists():
def test_file_explorer_expanded_folders_persist():
def test_tm_explorer_selected_tm_persists():
def test_tm_explorer_filter_state_persists():
```

---

## Final Gap Count (Updated)

| Category | Existing | Still Missing | Priority |
|----------|----------|---------------|----------|
| LDM Workflow | 0 | 8 | CRITICAL |
| Performance | 0 | 7 | CRITICAL |
| Security | 40 | 3 | HIGH |
| UI State | 0 | 4 | MEDIUM |
| Engine Toggle | 0 | 2 | HIGH |
| Large Files | 0 | 2 | HIGH |
| **TOTAL NEW NEEDED** | | **~26** | |

---

*P36 Coverage Gaps | Updated Assessment | 2025-12-21*
