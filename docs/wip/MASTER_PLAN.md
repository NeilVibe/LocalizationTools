# Master Plan - What's Done & What's Next

**Last Updated:** 2025-12-22 | **Build:** 343 | **Next:** 344

---

## COMPLETED

### P37: Code Quality - DONE
- [x] `api.py` (3156 lines) deleted - dead code
- [x] `tm_indexer.py` (2105 lines) split into 4 modular files
- [x] Global monolith audit - NO ACTIVE MONOLITHS
- [x] All tests pass (1068 GitHub, 950+ Gitea)

### P36: Mocked Tests - DONE
- [x] 27 mocked LDM tests created
- [x] Core routes covered (projects 98%, folders 90%, tm_entries 74%)
- [x] GitHub CI fix for clean DB environments

### Infrastructure - DONE
- [x] CI/CD working (Gitea + GitHub) - BOTH VERIFIED
- [x] Security audit completed
- [x] Schema upgrade mechanism
- [x] 0 open issues

---

## WHAT'S LEFT TO DO

### 1. Coverage Improvement (P36) - IN PROGRESS

**Overall: 47%** | **Target: 70%**

| File | Current | Target | Priority |
|------|---------|--------|----------|
| `sync_manager.py` | 22% | 70% | HIGH |
| `routes/files.py` | 11% | 70% | HIGH |
| `routes/rows.py` | 16% | 70% | HIGH |
| `routes/tm_indexes.py` | 15% | 70% | HIGH |
| `tm_manager.py` | ~30% | 70% | MEDIUM |
| `pretranslate.py` | 35% | 70% | MEDIUM |

**Strategy:** Create mocked unit tests for remaining routes.

### 2. CI/CD Modes - TODO

| Mode | Status |
|------|--------|
| `LIGHT` | DONE |
| `FULL` | TODO |
| `QA-LIGHT` | DONE |
| `QA-FULL` | TODO |

### 3. P25 LDM UX Overhaul - 85% DONE

Remaining UX improvements for LDM interface.

---

## WIP DOCS STATUS

| Doc | Status | Action |
|-----|--------|--------|
| `SESSION_CONTEXT.md` | CURRENT | Keep updated |
| `ISSUES_TO_FIX.md` | CURRENT | 0 open issues |
| `P37_LDM_REFACTORING.md` | COMPLETE | Archive |
| `P36_COVERAGE_GAPS.md` | ACTIVE | Use for testing |
| `P36_TEST_MAPPING.md` | REFERENCE | Keep |
| `FAISS_OPTIMIZATION_PLAN.md` | COMPLETE | Archive |
| `MODEL2VEC_BENCHMARK.md` | COMPLETE | Archive |
| `P25_LDM_UX_OVERHAUL.md` | 85% done | Continue later |

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
echo "Build 344: Description" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build 344: Description" && git push origin main && git push gitea main
```

---

## SUMMARY

| Category | Status |
|----------|--------|
| **Code Quality** | CLEAN - No monoliths |
| **Tests** | 1068 passing (GitHub) |
| **Coverage** | 47% (target 70%) |
| **Performance** | Optimized |
| **Open Issues** | 0 |
| **CI/CD** | Both platforms verified |

**Next Priority:** Write tests for low-coverage LDM routes (11-22% → 70%)

---

*Master plan consolidating all WIP docs. Updated 2025-12-22.*
