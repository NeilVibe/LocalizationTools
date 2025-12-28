# Session Context

**Updated:** 2025-12-28 14:00 | **Build:** 412 (FAILED) | **Status:** PRIORITY 1 - ASYNC EVENT LOOP FIX

---

## PRIORITY 1: Async Event Loop Test Failures (BLOCKING)

### Problem

Build 412 failed due to **async event loop pollution** - tests fail when run after 100+ other tests:

```
RuntimeError: Task got Future attached to a different loop
```

**Failing tests:**
- `test_submit_logs_with_auth`
- `test_start_session`
- `test_get_latest_version`

**Root cause:** `_async_session_maker` in `server/utils/dependencies.py` gets tied to an event loop at initialization. After 100+ tests, the loop state is corrupted.

### Full Plan of Action

#### Phase 1: Understand the Problem (30 min)

1. **Read the code:**
   - `server/utils/dependencies.py` - Find `_async_session_maker` and how it's initialized
   - `server/main.py` - Check how async sessions are used
   - Failing test files in `tests/integration/server_tests/`

2. **Understand the pattern:**
   - Why does it work in isolation but fail after 100+ tests?
   - What creates new event loops during test runs?
   - How does pytest-asyncio handle event loops?

#### Phase 2: Research Solutions (30 min)

3. **Check existing fixes:**
   - Per TROUBLESHOOTING.md, `/api/announcements` was fixed by switching to sync db
   - Look at how that fix was done

4. **Identify all affected endpoints:**
   - Grep for `Depends(get_async_db)` in all route files
   - Identify which can be safely switched to sync

#### Phase 3: Implement Fix (1-2 hours)

**Option A: Convert to Sync (Recommended for simple endpoints)**
```python
# BEFORE (async - causes issues)
@router.get("/logs")
async def get_logs(db: AsyncSession = Depends(get_async_db)):
    ...

# AFTER (sync - stable)
@router.get("/logs")
def get_logs(db: Session = Depends(get_db)):
    ...
```

**Option B: Reset async engine between test modules**
```python
# In conftest.py
@pytest.fixture(autouse=True, scope="module")
def reset_async_engine():
    from server.utils.dependencies import reset_async_session_maker
    reset_async_session_maker()
    yield
```

**Option C: Use separate event loop per test**
```python
# pytest.ini or conftest.py
[tool:pytest]
asyncio_mode = auto
```

5. **For each failing endpoint:**
   - Assess if it needs async (most don't)
   - If not, convert to sync
   - If yes, implement Option B or C

#### Phase 4: Test the Fix (30 min)

6. **Run tests locally:**
   ```bash
   python3 -m pytest tests/integration/server_tests/test_api_endpoints.py -v
   ```

7. **Run full test suite to verify no regressions:**
   ```bash
   python3 -m pytest tests/ -v --tb=short
   ```

#### Phase 5: Deploy and Verify (15 min)

8. **Push and trigger build:**
   ```bash
   echo "Build 413: Fix async event loop test failures" >> GITEA_TRIGGER.txt
   git add -A && git commit -m "Fix: Async event loop test isolation"
   git push origin main && git push gitea main
   ```

9. **Monitor with timeout protocol:**
   - Stage timeout: Tests = 10 min max
   - RAM: Should be <5GB

### Files to Modify

| File | Change |
|------|--------|
| `server/utils/dependencies.py` | Add reset function or fix session maker |
| `server/api/*.py` | Convert simple endpoints to sync |
| `tests/conftest.py` | Add event loop reset fixture if needed |

### Success Criteria

- [ ] All 3 failing tests pass
- [ ] Full test suite passes (1000+ tests)
- [ ] No new test failures introduced
- [ ] Build completes in <15 min

---

## Completed This Session

### Build 411-412 Fixes

| Item | Status |
|------|--------|
| UI-077 mocked tests broken | ✅ FIXED (3 tests updated) |
| Confusion #21 documented | ✅ DONE (infinite wait issue) |
| BUILD TIMEOUT PROTOCOL added | ✅ DONE (per-stage monitoring) |

### Documentation Updated

- `TROUBLESHOOTING.md` - Added BUILD TIMEOUT ALERT PROTOCOL
- `CONFUSION_HISTORY.md` - Added Confusion #21 (infinite wait)

---

## Quick Reference

### Check Build Status (SQL)
```bash
python3 -c "
import sqlite3, time
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, started FROM action_run ORDER BY id DESC LIMIT 1')
r = c.fetchone()
elapsed = int(time.time()) - r[2] if r[2] else 0
status_map = {1: 'SUCCESS', 2: 'FAILURE', 6: 'RUNNING'}
print(f'Run {r[0]}: {status_map.get(r[1], r[1])} | {elapsed//60}m')"
```

### Per-Stage Monitoring
```bash
python3 -c "
import sqlite3, time
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('''SELECT name, status, started FROM action_run_job
    WHERE run_id=(SELECT MAX(id) FROM action_run) AND status=6''')
r = c.fetchone()
if r:
    elapsed = int(time.time()) - r[2]
    print(f'{r[0][:30]}: {elapsed//60}m')
    if elapsed > 600: print('⚠️ STUCK!')"
```

---

*PRIORITY 1: Fix async event loop before next build*
