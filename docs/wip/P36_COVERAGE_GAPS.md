# P36: Code Coverage Assessment

**Created:** 2025-12-21 | **Last Run:** 2025-12-22 | **Overall Coverage:** 46%

---

## ACTUAL COVERAGE (pytest --cov, 2025-12-22)

### Summary

| Metric | Value |
|--------|-------|
| **Total Coverage** | 46.07% |
| **Goal** | 80% minimum, 90% target |
| **Tests Passed** | 1071 |
| **Lines Covered** | 5,349 / 11,610 |

### By Component (Actual Numbers)

#### ✅ EXCELLENT (90%+)
| File | Coverage | Notes |
|------|----------|-------|
| kr_similar/core.py | 100% | Battle-tested |
| database/models.py | 94% | Data models |
| quicksearch/dictionary.py | 91% | Well tested |
| audit_logger.py | 92% | Security logging |
| client/file_handler.py | 90% | File utils |
| client_config.py | 90% | Config handling |

#### ⚠️ NEEDS WORK (50-80%)
| File | Coverage | Lines Missing | Priority |
|------|----------|---------------|----------|
| config.py | 84% | 39 | LOW |
| main.py | 77% | 42 | MEDIUM |
| kr_similar/searcher.py | 70% | 70 | MEDIUM |
| kr_similar/embeddings.py | 62% | 95 | MEDIUM |
| quicksearch/qa_tools.py | 66% | 146 | LOW |
| tm_indexer.py | 59% | 312 | HIGH |
| db_setup.py | 57% | 93 | MEDIUM |
| db_utils.py | 57% | 105 | MEDIUM |

#### ❌ CRITICAL GAPS (<50%)
| File | Coverage | Lines Missing | Priority |
|------|----------|---------------|----------|
| **ldm/api.py** | 22% | 897 | **CRITICAL** |
| ldm/websocket.py | 20% | 146 | HIGH |
| ldm/tm_manager.py | 29% | 251 | HIGH |
| ldm/pretranslate.py | 35% | 136 | HIGH |
| xlstransfer/process_operation.py | 6% | 379 | LOW* |
| xlstransfer/embeddings.py | 10% | 280 | LOW* |
| xlstransfer/excel_utils.py | 12% | 141 | LOW* |
| xlstransfer/translation.py | 19% | 83 | LOW* |
| api/xlstransfer_async.py | 21% | 269 | LOW* |

*LOW priority because XLSTransfer is battle-tested from original monolith

---

## HONEST ASSESSMENT

### What ACTUALLY Needs Tests (Priority Order)

1. **LDM API (22% → target 75%)**
   - 1153 lines, only 256 covered
   - This is the main LDM tool - NEW code, user data
   - ~600 lines need tests

2. **tm_indexer.py (59% → target 80%)**
   - TM sync, FAISS indexing - data integrity critical
   - ~200 lines need tests

3. **tm_manager.py (29% → target 70%)**
   - TM CRUD operations
   - ~150 lines need tests

4. **pretranslate.py (35% → target 70%)**
   - Core pretranslation logic
   - ~100 lines need tests

### What's FINE As-Is

| Component | Why No More Tests Needed |
|-----------|-------------------------|
| **XLSTransfer** (6-21%) | Ported from battle-tested monolith. If it matches original, it works. |
| **kr_similar/core.py** (100%) | Already perfect |
| **quicksearch/** (66-91%) | Good enough, stable code |
| **models.py** (94%) | Mostly data definitions |

### Realistic Target

| Component | Current | Target | Why |
|-----------|---------|--------|-----|
| LDM API | 22% | 75% | New code, user-facing |
| tm_indexer | 59% | 80% | Data integrity |
| tm_manager | 29% | 70% | CRUD operations |
| pretranslate | 35% | 70% | Core feature |
| **Overall** | 46% | 70% | Achievable, meaningful |

**Note:** 100% is not the goal. 70-80% on critical paths with meaningful tests is better than 100% with meaningless coverage padding.

---

## GAPS IDENTIFIED

### CRITICAL (Must Fix)

| Area | Issue | Priority |
|------|-------|----------|
| **LDM API endpoints** | 22% coverage on 1153 lines | CRITICAL |
| **TM sync operations** | Integration tests weak | HIGH |
| **Pretranslation flow** | End-to-end not fully tested | HIGH |

### MEDIUM (Should Fix)

| Area | Issue | Priority |
|------|-------|----------|
| **Model2Vec vs Qwen Toggle** | No test for switching engines | MEDIUM |
| **File Upload API** | Direct upload endpoint not tested | MEDIUM |
| **WebSocket handlers** | 20% coverage | MEDIUM |
| **FAISS Rebuild** | Index rebuild not explicitly tested | MEDIUM |

### LOW (Nice to Have)

| Area | Issue | Priority |
|------|-------|----------|
| **Performance Benchmarks** | Zero performance tests | LOW |
| **Large File Handling** | No test for 10MB+ files | LOW |
| **Concurrent Access** | No multi-user test | LOW |
| **Memory Usage** | No memory leak tests | LOW |

---

## TEST PLAN

### Phase 1: LDM API (Priority CRITICAL)

Target: 22% → 75% coverage

**Endpoints to test:**
```
POST /ldm/projects - Create project
GET /ldm/projects - List projects
POST /ldm/files/upload - Upload file
GET /ldm/files/{id}/rows - Get rows
PUT /ldm/rows/{id} - Update row (Ctrl+S flow)
POST /ldm/tm - Create TM
POST /ldm/tm/{id}/entries - Add TM entry
POST /ldm/tm/{id}/sync - Sync TM indexes
GET /ldm/tm/{id}/search - Search TM
POST /ldm/pretranslate - Run pretranslation
```

**Approach:** Integration tests with TestClient, real database

### Phase 2: TM Indexer (Priority HIGH)

Target: 59% → 80% coverage

**Functions to test:**
- `build_indexes()` - FAISS index creation
- `sync()` - TM synchronization
- `compute_diff()` - Change detection
- `search()` - Vector search

### Phase 3: TM Manager (Priority HIGH)

Target: 29% → 70% coverage

**Functions to test:**
- `create_tm()` - TM creation
- `add_entry()` - Entry addition
- `update_entry()` - Entry modification
- `delete_entry()` - Entry removal
- `get_entries()` - Entry retrieval

---

## What We DON'T Need to Test Extensively

### XLSTransfer (Battle-Tested)

The XLSTransfer code is ported directly from the original monolith scripts that have been used in production for years. If the code matches the original:

- `simple_number_replace()` - PROVEN
- `clean_text()` - PROVEN
- `adapt_structure()` - PROVEN
- Excel parsing - PROVEN

**Recommendation:** Keep existing smoke tests. Don't chase coverage here.

### WebSocket Handlers

Hard to test automatically, visual verification during CDP tests is sufficient.

---

*P36 Coverage Assessment | Actual Data from pytest --cov | 2025-12-22*
