# Master Plan - What's Done & What's Next

**Last Updated:** 2025-12-22 | **Build:** 341 | **Next:** 342

---

## COMPLETED

### P37: Code Quality - DONE
- [x] `api.py` (3156 lines) deleted - dead code
- [x] `tm_indexer.py` (2105 lines) split into 4 modular files
- [x] Global monolith audit - NO ACTIVE MONOLITHS
- [x] All 1071 tests pass

### Infrastructure - DONE
- [x] CI/CD working (Gitea + GitHub)
- [x] Security audit completed
- [x] Schema upgrade mechanism
- [x] 0 open issues

---

## CURRENT COVERAGE

**Overall: 47%** | **Target: 70%**

### LDM Coverage (Priority)

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| `indexing/utils.py` | **100%** | 100% | DONE |
| `indexing/indexer.py` | **84%** | 90% | LOW |
| `indexing/searcher.py` | **83%** | 90% | LOW |
| `indexing/sync_manager.py` | **22%** | 70% | HIGH |
| `routes/files.py` | **11%** | 70% | HIGH |
| `routes/rows.py` | **16%** | 70% | HIGH |
| `routes/tm_entries.py` | **16%** | 70% | HIGH |
| `routes/tm_indexes.py` | **15%** | 70% | HIGH |
| `tm_manager.py` | ~30% | 70% | MEDIUM |
| `pretranslate.py` | **35%** | 70% | MEDIUM |
| `backup_service.py` | **0%** | 50% | LOW |

### Other Low Coverage

| Component | Current | Notes |
|-----------|---------|-------|
| `api/stats.py` | 12% | Admin dashboard |
| `api/rankings.py` | 13% | Admin dashboard |
| `api/admin_telemetry.py` | 14% | Admin dashboard |

---

## NEXT ACTIONS

### 1. Coverage Improvement (P36)

**Goal:** 47% → 70%

**Strategy:** Test the NEW modular code first (easy wins):

```bash
# Run with coverage
python3 -m pytest tests/ -k "ldm" --cov=server/tools/ldm --cov-report=html
```

**Priority Test Files to Create:**
1. `tests/unit/ldm/test_sync_manager.py` - sync_manager.py (22% → 70%)
2. `tests/unit/ldm/test_routes_files.py` - routes/files.py (11% → 70%)
3. `tests/unit/ldm/test_routes_rows.py` - routes/rows.py (16% → 70%)
4. `tests/unit/ldm/test_routes_tm_entries.py` - tm_entries.py (16% → 70%)

### 2. Performance (Future)

| Area | Status | Notes |
|------|--------|-------|
| FAISS HNSW | DONE | Optimized indexes |
| Model2Vec | DONE | Fast embeddings |
| Incremental sync | DONE | PERF-001 |
| Batch operations | DONE | bulk_copy_tm_entries |

### 3. CI/CD Modes (Future)

| Mode | Status |
|------|--------|
| `LIGHT` | DONE |
| `FULL` | TODO |
| `QA-LIGHT` | TODO |
| `QA-FULL` | TODO |

---

## WIP DOCS STATUS

| Doc | Status | Action |
|-----|--------|--------|
| `SESSION_CONTEXT.md` | CURRENT | Keep updated |
| `ISSUES_TO_FIX.md` | CURRENT | 0 open issues |
| `P37_LDM_REFACTORING.md` | COMPLETE | Archive soon |
| `P36_COVERAGE_GAPS.md` | ACTIVE | Use for testing |
| `P36_TEST_MAPPING.md` | REFERENCE | Keep |
| `FAISS_OPTIMIZATION_PLAN.md` | COMPLETE | Archive |
| `MODEL2VEC_BENCHMARK.md` | COMPLETE | Archive |
| `P25_LDM_UX_OVERHAUL.md` | 85% done | Continue later |
| `FEAT-001_AUTO_TM_DESIGN.md` | DESIGN | Future feature |

---

## QUICK COMMANDS

### Run Tests
```bash
# All tests
python3 -m pytest tests/ -v

# LDM only
python3 -m pytest tests/ -k "ldm" -v

# With coverage
python3 -m pytest tests/ --cov=server/tools/ldm --cov-report=html
```

### Trigger Build
```bash
echo "Build 342: Description" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build 342: Description" && git push origin main && git push gitea main
```

---

## SUMMARY

| Category | Status |
|----------|--------|
| **Code Quality** | CLEAN - No monoliths |
| **Tests** | 1071 passing |
| **Coverage** | 47% (target 70%) |
| **Performance** | Optimized |
| **Open Issues** | 0 |

**Next Priority:** Write tests for low-coverage LDM routes (11-22% → 70%)

---

*Master plan consolidating all WIP docs. Updated 2025-12-22.*
