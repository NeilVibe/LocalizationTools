# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-22 11:00 | **Build:** 339 | **Next:** 340

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

## WHAT'S NEXT

### Priority 1: LDM API Tests (22% → 75%)

The main gap. 1153 lines, only 256 covered. New code handling user data.

**Endpoints needing tests:**
```
POST /ldm/projects - Create project
GET /ldm/projects - List projects
POST /ldm/files/upload - Upload file
GET /ldm/files/{id}/rows - Get rows
PUT /ldm/rows/{id} - Update row
POST /ldm/tm - Create TM
POST /ldm/tm/{id}/entries - Add TM entry
POST /ldm/tm/{id}/sync - Sync TM indexes
GET /ldm/tm/{id}/search - Search TM
POST /ldm/pretranslate - Run pretranslation
```

### Priority 2: TM Indexer Tests (59% → 80%)

Data integrity critical. Functions: `build_indexes()`, `sync()`, `compute_diff()`, `search()`

### Don't Bother: XLSTransfer

6-21% coverage but LOW priority - code ported from battle-tested monolith.

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

*Session: Build 339 passed, coverage analyzed, next is LDM API tests*
