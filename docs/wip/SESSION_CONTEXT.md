# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-22 17:35 | **Build:** 339 | **Next:** 340

---

## CURRENT STATE

### Build 339: FULL SUCCESS ✅

| Job | Status | Details |
|-----|--------|---------|
| Check Build Trigger | ✅ | Mode: official |
| Safety Checks | ✅ | 830 passed, 34 skipped |
| Windows Installer | ✅ | 7 minutes, installer created |

### Code Coverage: 46%

| Component | Coverage | Target | Priority |
|-----------|----------|--------|----------|
| **LDM API** | 22% | 75% | **CRITICAL** |
| tm_indexer | 59% | 80% | HIGH |
| tm_manager | 29% | 70% | HIGH |
| pretranslate | 35% | 70% | HIGH |
| XLSTransfer | 6-21% | - | LOW (battle-tested) |

**Details:** [P36_COVERAGE_GAPS.md](P36_COVERAGE_GAPS.md)

---

## IN PROGRESS: LDM API Tests

### Test File Created: `tests/integration/test_ldm_api.py`

- **36 tests** covering: Projects, Folders, TM, TM Entries, Search, Rows, Files
- Uses `requests` library (not TestClient) due to async session conflicts
- Requires running server: `RUN_API_TESTS=1 pytest tests/integration/test_ldm_api.py`

---

## P37: LDM REFACTORING - WIRING COMPLETE

**Full plan:** [P37_LDM_REFACTORING.md](P37_LDM_REFACTORING.md)

### Structure Created

```
server/tools/ldm/
├── api.py                 # 3144 lines - LEGACY (preserved for reference)
├── router.py              # New aggregator - NOW ACTIVE (44 endpoints)
├── schemas/               # 9 files - COMPLETE
│   ├── common.py, project.py, folder.py, file.py
│   ├── row.py, tm.py, pretranslate.py, sync.py, settings.py
├── routes/                # 14 files - ALL MIGRATED
│   ├── health.py          ~30 lines
│   ├── projects.py        ~95 lines
│   ├── folders.py         ~90 lines
│   ├── settings.py        ~92 lines
│   ├── tm_linking.py      ~188 lines
│   ├── tm_crud.py         ~250 lines
│   ├── tm_search.py       ~208 lines
│   ├── tm_entries.py      ~488 lines (6 endpoints)
│   ├── tm_indexes.py      ~329 lines (4 endpoints)
│   ├── rows.py            ~352 lines (3 endpoints)
│   ├── files.py           ~632 lines (6 endpoints + 3 helpers)
│   ├── pretranslate.py    ~142 lines
│   └── sync.py            ~257 lines (2 endpoints)
├── services/              # 2 files - stubs
├── indexing/              # 4 files - stubs
├── helpers/               # 3 files - partial
└── file_handlers/         # UNCHANGED
```

### Progress

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Schemas | **COMPLETE** | 9 files created |
| 2. Routes structure | **COMPLETE** | 14 files created |
| 2b. Route migration | **COMPLETE** | All 14 routes migrated |
| 3. Services | PENDING | tm_manager.py split (1133 lines) |
| 4. Indexing | PENDING | tm_indexer.py split (2105 lines) |
| 5. Router wiring | **COMPLETE** | main.py now uses router.py |
| 6. Cleanup | PENDING | Delete api.py duplicate code |

### Tests: 983 passed, 51 skipped (no regressions)

---

## WHAT'S NEXT

### Priority 1: LDM API Tests (22% → 75%)

Test file ready. Need to run with server to verify coverage improvement.

### Priority 2: TM Indexer Tests (59% → 80%)

Data integrity critical. Functions: `build_indexes()`, `sync()`, `compute_diff()`, `search()`

### Don't Bother

- **XLSTransfer** - Battle-tested monolith code
- **LDM API Refactoring** - Works, tests first

---

## RECENT FIXES

| Build | Fix |
|-------|-----|
| 339 | Renamed `test_*` to `run_*` in standalone script (pytest fixture error) |
| 338 | Added `is_confirmed` to `bulk_copy_tm_entries()` |
| 337 | ROOT CAUSE: `compute_diff()` missing string_id + `indexed_at` not set |

---

## CI DEBUGGING

### Check Build Status (Quick)

```bash
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 1')
r = c.fetchone()
print(f'Run {r[0]}: {\"SUCCESS\" if r[1]==1 else \"FAILURE\"} - {r[2]}')"
```

### Check Job Status

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/neil1988/gitea/data/gitea.db')
c = conn.cursor()
c.execute('SELECT name, status, stopped FROM action_run_job WHERE run_id = (SELECT MAX(id) FROM action_run)')
for job in c.fetchall():
    status = 'SUCCESS' if job[1] == 1 else 'FAILURE' if job[1] == 2 else f'status={job[1]}'
    done = '✅' if job[2] else '⏳'
    print(f'{done} {job[0]}: {status}')"
```

### Find Latest Log

```bash
ls -lt /home/neil1988/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -3
```

### Autonomous Debug Loop

```
1. Analyze failure in logs
2. Fix the code
3. Commit & push: git add -A && git commit -m "Build N: Fix X" && git push origin main && git push gitea main
4. Trigger: echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Trigger" && git push origin main && git push gitea main
5. Sleep 5 min: sleep 300
6. Check status (use commands above)
7. If failing → GOTO step 1
```

---

## KEY DOCS

| Doc | Purpose |
|-----|---------|
| [Roadmap.md](../../Roadmap.md) | Strategic priorities |
| [P36_COVERAGE_GAPS.md](P36_COVERAGE_GAPS.md) | Coverage analysis & test plan |
| [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Open bugs (currently 0) |
| [TROUBLESHOOTING.md](../cicd/TROUBLESHOOTING.md) | CI debug techniques |

---

*Session: P37 Router Wiring COMPLETE - main.py now uses modular router.py (44 endpoints via 13 sub-routers). Legacy api.py preserved for reference. Tests: 983 passed. Next: split bloated files (tm_indexer.py 2105 lines, tm_manager.py 1133 lines) or proceed to testing.*
