# CI/CD Troubleshooting Guide

## CRITICAL: NEVER RESTART

**Restarting does NOT solve issues.** ALWAYS follow this workflow:

1. **STOP** everything (cancel builds, stop services)
2. **CLEAN** resources (kill zombie processes)
3. **INVESTIGATE** root cause (check logs, find the actual problem)
4. **FIX** the actual issue
5. Only **THEN** start fresh

**NEVER restart the runner while a build is in progress.** This will cause Gitea to spin at 700% CPU trying to communicate with a disconnected runner.

---

## Checking Logs

### Live Logs (While Running) - USE CURL

```bash
# Get latest run number
curl -s "http://172.28.150.120:3000/neilvibe/LocaNext/actions" | grep -oE 'actions/runs/[0-9]+' | head -1
# Output: actions/runs/346

# Stream live logs (replace 346 with run number, job 0=trigger, 1=tests, 2=windows)
curl -s "http://172.28.150.120:3000/neilvibe/LocaNext/actions/runs/346/jobs/1/logs" | tail -50

# Filter for test results only
curl -s "http://172.28.150.120:3000/neilvibe/LocaNext/actions/runs/346/jobs/1/logs" | grep -E "(PASSED|FAILED|passed|failed)" | tail -30
```

### Quick Build Status Check

```bash
# One-liner: Check latest build status
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 1')
r = c.fetchone()
STATUS = {0:'UNKNOWN', 1:'SUCCESS', 2:'FAILURE', 3:'CANCELLED', 4:'SKIPPED', 5:'WAITING', 6:'RUNNING', 7:'BLOCKED'}
print(f'Run {r[0]}: {STATUS.get(r[1], r[1])} - {r[2]}')"
# CRITICAL: 6=RUNNING means build is still in progress - WAIT!
```

### Last Fail Log (After Completion) - USE DISK

**NOT curl** - read from disk on the runner machine:

```bash
# SSH to runner and find latest log
ssh neil1988@localhost "ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -3"

# Read the log file (replace <folder> with actual folder name)
ssh neil1988@localhost "cat ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log | grep -E 'FAILED|Error|assert' | tail -50"

# Or just get the last failure line
ssh neil1988@localhost "cat ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log | grep FAILED | tail -1"
```

### Quick Reference

| Need | Method |
|------|--------|
| Build still running? | `curl` live logs |
| Build finished, find last fail? | `ssh` + disk logs |

---

## Gitea API Token (Release Management)

The `GITEA_TOKEN` is required for managing releases via API (cleanup, mock releases for testing, etc.).

### Token Location

The token is stored in `~/.bashrc`:

```bash
# Load token
source ~/.bashrc
echo $GITEA_TOKEN
```

### Creating a New Token

If token is missing or expired:

1. Go to: http://172.28.150.120:3000/user/settings/applications
2. Click "Generate New Token"
3. Name: `release-manager` (or any name)
4. Permissions: Select "write:repository"
5. Click "Generate Token"
6. Add to `~/.bashrc`:
   ```bash
   echo 'export GITEA_TOKEN="your_token_here"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Release Manager Script

Use the release manager script for common operations:

```bash
# List all releases
./scripts/release_manager.sh list

# Cleanup old releases (keeps latest + current version)
./scripts/release_manager.sh cleanup

# Create mock release for auto-update testing
./scripts/release_manager.sh mock-update

# Restore real version after testing
./scripts/release_manager.sh restore
```

### Manual API Commands

```bash
# List releases
curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases" \
  -H "Authorization: token $GITEA_TOKEN" | python3 -c "import sys,json; [print(f\"{r['id']}: {r['tag_name']}\") for r in json.load(sys.stdin)]"

# Delete a release
curl -s -X DELETE "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases/RELEASE_ID" \
  -H "Authorization: token $GITEA_TOKEN"

# Upload asset to release
curl -s -X POST "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases/RELEASE_ID/assets?name=FILE_NAME" \
  -H "Authorization: token $GITEA_TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @/path/to/file
```

---

### Windows Build Logs

Windows builds run on a separate runner. Check these logs for Windows-specific failures:

```bash
# Find Windows build logs (usually "fe" folder for Windows job)
ssh neil1988@localhost "ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -5"

# Check specific folder for Windows errors
ssh neil1988@localhost "cat ~/gitea/data/actions_log/neilvibe/LocaNext/fe/*.log | grep -E 'FAILED|Error|Traceback' | tail -20"
```

Common Windows errors:
- `AssertionError: A version must be provided for OpenAPI` → VERSION import failing
- `Server import test FAILED` → Check embedded Python path issues

---

## Runner Startup Issues

### Linux Runner Fails to Start (Random)

**Symptom:**
```bash
./scripts/gitea_control.sh start
# [ERROR] Failed to start Linux Runner
```

**Cause:** Race condition - runner tries to connect before Gitea HTTP is ready.

**Solution (Already Fixed):**
The `gitea_control.sh` now includes `wait_for_gitea_http()` function that waits up to 15 seconds for Gitea's HTTP endpoint (port 3000) to be ready before starting runners.

**Key Insight:**
- `systemctl is-active gitea` = process started (immediate)
- `curl http://localhost:3000` = HTTP accepting connections (2-5 seconds delay)

**If it still fails:**
```bash
# Check runner log
tail /tmp/act_runner.log

# Manual retry
./scripts/gitea_control.sh stop
sleep 5
./scripts/gitea_control.sh start
```

### Windows Runner Not Starting

**Symptom:** Build hangs at "Windows Installer" stage forever.

**Cause:** Windows Runner service not running.

**Solution:**
```bash
./scripts/gitea_control.sh status  # Check if Windows Runner shows as Running
./scripts/gitea_control.sh start   # Start all components including Windows Runner
```

---

## TROUBLESHOOT Mode

Checkpoint system for iterative test fixing.

### Trigger

```bash
echo "TROUBLESHOOT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "TROUBLESHOOT" && git push gitea main
```

### WINDOWS_BUILD Checkpoint

**Location:** `/home/neil1988/.locanext_checkpoint`

If Linux tests pass but Windows build fails:
1. Windows build automatically saves `WINDOWS_BUILD` to checkpoint at start
2. If Windows build fails, checkpoint remains
3. Next TROUBLESHOOT detects `WINDOWS_BUILD`:
   - Skips 900+ pytest tests (already passed)
   - Still runs security audits (fast, ~1-2 min)
   - Windows build runs immediately after
4. When Windows build succeeds, checkpoint is cleared

**Create WINDOWS_BUILD checkpoint manually:**
```bash
echo "WINDOWS_BUILD" > /home/neil1988/.locanext_checkpoint
```

**Clear checkpoint:**
```bash
rm /home/neil1988/.locanext_checkpoint
```

**⚠️ Known Issue:** Auto-clear from Windows doesn't work (WSL path access issue). After Windows build succeeds, manually clear the checkpoint:
```bash
rm /home/neil1988/.locanext_checkpoint
```

This prevents re-running 900+ tests when only Windows is failing.

### Checkpoint Types

**Two checkpoint modes:**

| Type | Content | Effect |
|------|---------|--------|
| Test list | `tests/unit/test_foo.py::test_bar`... | Resume from specific test |
| WINDOWS_BUILD | `WINDOWS_BUILD` | Skip all tests, run Windows build |

### How It Works

1. First run: Collects all tests, runs from beginning
2. On test failure: Saves remaining tests to checkpoint
3. Next run: Resumes from checkpoint
4. On all tests pass → Windows build starts
5. Windows build saves `WINDOWS_BUILD` to checkpoint
6. If Windows fails: Next run skips tests, retries Windows
7. On Windows success: Checkpoint cleared

### Commands

```bash
# Check checkpoint
cat /home/neil1988/.locanext_checkpoint

# Clear checkpoint (restart from beginning)
rm /home/neil1988/.locanext_checkpoint

# Force Windows build (skip tests)
echo "WINDOWS_BUILD" > /home/neil1988/.locanext_checkpoint
```

### Recreate Checkpoint from Last Fail

If checkpoint is lost, recreate it from the last failed test:

```bash
# 1. Collect all tests into a file
cd /path/to/project
python3 -m pytest --collect-only -q 2>/dev/null | grep "::" > /tmp/all_tests.txt

# 2. Find position of last failed test
grep -n "test_name_here" /tmp/all_tests.txt
# Example output: 689:tests/integration/test_file.py::TestClass::test_name_here

# 3. Create checkpoint from that position
tail -n +689 /tmp/all_tests.txt > ~/.locanext_checkpoint

# 4. Verify
wc -l ~/.locanext_checkpoint  # Shows remaining test count
head -1 ~/.locanext_checkpoint  # Shows starting test
```

**Example:**
```bash
# Last fail was test_get_announcements
grep -n "test_get_announcements" /tmp/all_tests.txt
# Output: 689:tests/integration/server_tests/test_api_endpoints.py::TestVersionEndpoint::test_get_announcements

# Create checkpoint starting from test 689
tail -n +689 /tmp/all_tests.txt > ~/.locanext_checkpoint
# Now TROUBLESHOOT will resume from test 689
```

---

## Autonomous TROUBLESHOOT Loop

When Claude runs TROUBLESHOOT mode autonomously:

### Loop Protocol

```
1. TRIGGER
   echo "TROUBLESHOOT" >> GITEA_TRIGGER.txt
   git add -A && git commit -m "Fix: <description>" && git push gitea main

2. WAIT (~30-40 sec for tests to start)
   sleep 40

3. CHECK LIVE LOGS
   curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/<N>/jobs/1/logs" | tail -80

4. ANALYZE
   - If "All tests passed! Checkpoint cleared" → DONE
   - If FAILED → Read error, identify fix

5. FIX
   - Edit the failing file
   - Go back to step 1

6. REPEAT until all pass
```

### Key Commands for Claude

```bash
# Get latest run number
curl -s "http://localhost:3000/neilvibe/LocaNext/actions" | grep -oP 'runs/\d+' | head -1

# Check test progress (filter PASSED/FAILED)
curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/<N>/jobs/1/logs" | grep -E "(PASSED|FAILED|remaining|passed|failed)" | tail -40

# Quick status
curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/<N>/jobs/1/logs" | tail -20
```

### Common Test Fixes

| Pattern | Fix |
|---------|-----|
| `assert 401 in [200, 403, 404]` | Add 401 to expected codes |
| `MultipleResultsFound` | Use `.first()` instead of `.scalar_one_or_none()` |
| `column must appear in GROUP BY` | Use variable for column expression |
| SQLite test using in-memory | Change to PostgreSQL with env vars |

---

## Common Errors

| Error | Fix |
|-------|-----|
| `round(double precision, integer) does not exist` | Cast to Numeric: `func.round(cast(x, Numeric), 2)` |
| `Cannot create symbolic link` | Add `sign: false` to package.json |
| `No module named 'X'` | Add to requirements.txt |
| Server hangs at "Loading XLSTransfer..." | Lazy import issue (see below) |

### Server Startup Hang / CI Timeout (Lazy Import) - RECURRING ISSUE!

**⚠️ THIS IS A RECURRING BUG - CHECK THIS FIRST WHEN CI TIMES OUT!**

**Symptom:** CI build fails with server startup timeout (30s exceeded). Log shows server stuck at one of:
```
QuickSearch API initialized
```
or
```
Loading XLSTransfer core module...
```

**Root Cause:** Eager import of `sentence_transformers` at module level. This loads PyTorch (3-30s depending on environment).

**Impact:**
| Environment | Import Time | CI Result |
|-------------|-------------|-----------|
| Local (cached) | 3s | Usually OK |
| CI (first run) | 30+s | ❌ TIMEOUT |

**Detection Command:**
```bash
# Find eager imports (should return NOTHING at module scope)
grep -rn "^from sentence_transformers\|^import torch\|^from torch" server/ --include="*.py"

# Check try-blocks at module level
grep -rn "try:" -A3 server/ --include="*.py" | grep "sentence_transformers\|torch"
```

**Bad Pattern:**
```python
# ❌ WRONG - Module level import (blocks startup!)
try:
    from sentence_transformers import SentenceTransformer
    import torch
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
```

**Good Pattern:**
```python
# ✅ CORRECT - Lazy import
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
    import torch

_models_available: Optional[bool] = None

def _check_models_available() -> bool:
    """Lazy check - cached after first call."""
    global _models_available
    if _models_available is None:
        try:
            import sentence_transformers
            import torch
            _models_available = True
        except ImportError:
            _models_available = False
    return _models_available

class MyManager:
    def _ensure_model_loaded(self):
        # LAZY IMPORT: Only when actually needed
        from sentence_transformers import SentenceTransformer
        import torch
        self.model = SentenceTransformer(MODEL_NAME)
```

**Files to watch:**
- `server/tools/kr_similar/embeddings.py` ← Fixed Build 300
- `server/tools/xlstransfer/translation.py`
- `server/tools/xlstransfer/process_operation.py`
- `server/tools/xlstransfer/translate_file.py`
- `server/tools/shared/embedding_engine.py`

**History of occurrences:**
| Build | File | Fix Date |
|-------|------|----------|
| 300 | `kr_similar/embeddings.py` | 2025-12-18 |
| 298 | `xlstransfer/*.py` | 2025-12-17 |

**Full documentation:** `docs/development/CODING_STANDARDS.md` → Pitfall #1

---

## Known Issue: Async Event Loop Test Isolation

### Problem: `got Future attached to a different loop`

**Test:** `test_get_announcements` (and any test using async db after 100+ prior tests)

**Symptoms:**
- Test PASSES when run in isolation or as first test
- Test FAILS when run after many other tests (test #128+)
- Error: `RuntimeError: Task ... got Future attached to a different loop`

**Root Cause:**
The `_async_session_maker` in `server/utils/dependencies.py` is tied to an event loop at initialization time. When pytest's TestClient runs many tests, the event loop state can become corrupted. The session maker remains tied to the old loop while tests run in a new context.

**Pattern Observed:**
| Run Type | test_get_announcements | Why |
|----------|------------------------|-----|
| TROUBLESHOOT (first test) | ✅ PASSES | Fresh event loop, no pollution |
| NORMAL (test #128) | ❌ FAILS | 127 prior tests corrupted loop state |

**Workaround (TROUBLESHOOT mode):**
Create checkpoint to run the failing test first:
```bash
# Find test position
python3 -m pytest --collect-only -qq 2>/dev/null | grep "::" > /tmp/all_tests.txt
grep -n "test_get_announcements" /tmp/all_tests.txt

# Create checkpoint (replace 128 with actual line number)
tail -n +128 /tmp/all_tests.txt > ~/.locanext_checkpoint

# Trigger TROUBLESHOOT
echo "TROUBLESHOOT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "TROUBLESHOOT" && git push gitea main
```

**Permanent Fix Options:**
1. Use sync db session for simple public endpoints (recommended)
2. Add pytest fixture to reinitialize async engine between test modules
3. Skip affected tests in full test suite, run separately

**Affected Endpoints:**
- `/api/announcements` - ✅ FIXED (now uses sync `Depends(get_db)`)

**DO NOT USE** `Depends(get_async_db)` - this makes the problem WORSE.

**Fix Applied (2025-12-13):**
Changed `/api/announcements` from async to sync db session in `server/main.py`.
This simple endpoint doesn't need async - sync is simpler and avoids event loop issues.

---

## Test Isolation Pattern: "Works in TROUBLESHOOT, Fails in Normal"

### The Pattern

Many CI failures follow this pattern:
- ✅ Test PASSES when run in isolation (TROUBLESHOOT with checkpoint)
- ❌ Test FAILS when run after 100+ other tests (normal build)

**Root cause:** State pollution from prior tests.

### How to Identify

1. Test fails in normal build
2. Create checkpoint, run TROUBLESHOOT → test passes
3. **This means:** Prior tests are polluting state

### How to Fix (MANDATORY)

**DO NOT** just make the test pass in isolation. Ask:
> "Why does this fail after 100+ tests but pass when first?"

Common causes and fixes:

| Polluted State | Example | Fix |
|---------------|---------|-----|
| Event loop | Async session tied to old loop | Use sync db instead |
| Rate limiting | Too many failed logins | Skip rate limiting when `DEV_MODE=true` (CI starts server with this) |
| Database state | Prior tests left data | Filter by unique test identifiers |
| Global variables | Module-level cache | Reset in fixture |
| Connection pools | Exhausted connections | Proper cleanup in fixtures |

### Rate Limiting Fix (Applied 2025-12-14)

**Problem:** `test_dashboard_api.py` tests fail with "Too many failed login attempts" after 100+ tests.

**Root Cause:** Tests before accumulated failed logins in audit log, triggering rate limit.

**Fix:** Skip rate limiting when `DEV_MODE=true` or in pytest environment.

Files changed:
- `server/api/auth_async.py` - Added `skip_rate_limit` check
- `.gitea/workflows/build.yml` - Server starts with `DEV_MODE=true`

### Verification (MANDATORY)

Before committing a fix, verify it works for NORMAL builds:
```bash
# Run the failing test AFTER many other tests
python3 -m pytest tests/path/to/earlier_tests.py tests/path/to/failing_test.py -v

# Or run the entire test file
python3 -m pytest tests/integration/server_tests/test_file.py -v
```

If it only passes in isolation, the fix is incomplete.

---

## Check Job Status via Database (When Logs Are Missing)

When log files haven't appeared yet or you need to check if jobs are running/waiting/blocked:

### Query Job Status Directly

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/neil1988/gitea/data/gitea.db')
cursor = conn.cursor()

# Get latest runs
cursor.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 5')
print('Recent runs:')
for row in cursor.fetchall():
    status_map = {1: 'success', 2: 'failure', 3: 'cancelled', 4: 'skipped'}
    print(f'  Run {row[0]}: {status_map.get(row[1], f\"status={row[1]}\")} - {row[2]}')
conn.close()
"
```

### Check Individual Job Status

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/neil1988/gitea/data/gitea.db')
cursor = conn.cursor()

# Replace 346 with your run ID
run_id = 346
cursor.execute('SELECT name, status, started, stopped FROM action_run_job WHERE run_id = ?', (run_id,))
print(f'Jobs for run {run_id}:')
for job in cursor.fetchall():
    status_map = {1: 'success', 2: 'failure', 4: 'skipped'}
    has_run = 'completed' if job[3] else ('running' if job[2] else 'waiting')
    print(f'  {job[0]}: {status_map.get(job[1], f\"status={job[1]}\")} ({has_run})')
conn.close()
"
```

### When to Use This

| Scenario | Use |
|----------|-----|
| Log file not appearing | Check if job is queued/running |
| Windows build status unclear | Check if job completed |
| Run seems stuck | Verify job state in database |

### Status Values

| Run Status | Meaning |
|------------|---------|
| 1 | Success / In Progress |
| 2 | Failure |
| 3 | Cancelled |
| 4 | Skipped |

| Job Status | Meaning |
|------------|---------|
| 1 | Success |
| 2 | Failure |
| 4 | Skipped |

**Tip:** Check `started` and `stopped` timestamps - if both exist, job completed.

---

## BUILD TIMEOUT ALERT PROTOCOL (CRITICAL!)

**⚠️ Normal STAGE times - MEMORIZE THESE:**

| Stage | Normal Time | STUCK if > | Action |
|-------|-------------|------------|--------|
| Trigger job | <1 min | 2 min | Check runner |
| Tests (pytest) | 5-10 min | 10 min | Check RAM, kill if >8GB |
| Windows build | 5-15 min | 20 min | Check Windows runner |

**Key: Monitor per-STAGE, not total build!**

### Per-Stage Monitoring

```bash
# GET CURRENT STAGE AND TIME
python3 -c "
import sqlite3, time
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('''
    SELECT j.name, j.status, j.started
    FROM action_run_job j
    WHERE j.run_id = (SELECT MAX(id) FROM action_run)
    AND j.status = 6  -- RUNNING
''')
r = c.fetchone()
if r:
    elapsed = int(time.time()) - r[2] if r[2] else 0
    print(f'Stage: {r[0][:30]}')
    print(f'Time: {elapsed//60} min {elapsed%60} sec')
    if 'Tests' in r[0] and elapsed > 600:
        print('⚠️ ALERT: Tests stuck >10 min!')
    elif 'Windows' in r[0] and elapsed > 1200:
        print('⚠️ ALERT: Windows stuck >20 min!')
else:
    print('No running stage')"
```

### ASSESSMENT Protocol (When Stage is STUCK)

```
1. CHECK RAM: free -h
   - Tests: should be <5GB
   - If >8GB → pytest is STUCK → pkill -f pytest

2. CHECK PROCESS: ps aux | grep -E 'pytest|electron-builder'
   - Is process using CPU? (good)
   - Is process using 0% CPU but high MEM? (stuck)

3. CHECK LOGS: curl live logs or check disk
   - Any error messages?
   - Is progress % increasing?

4. DECISION:
   - Progress increasing + RAM normal → wait
   - Progress stuck OR RAM >8GB → KILL and investigate
```

### Quick Alert Commands

```bash
# Check if build is stuck (ran > 10 min)
python3 -c "
import sqlite3, time
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, started FROM action_run ORDER BY id DESC LIMIT 1')
r = c.fetchone()
elapsed = int(time.time()) - r[2] if r[2] else 0
if r[1] == 6 and elapsed > 600:  # RUN for >10 min
    print(f'⚠️ ALERT: Run {r[0]} stuck for {elapsed//60} min!')
else:
    print(f'Run {r[0]}: OK ({elapsed//60} min elapsed)')"

# Kill stuck pytest
pkill -f "pytest tests/"

# Force-fail stuck build (via database)
# UPDATE action_run SET status=2 WHERE id=XXX
```

### What NOT to Do

| ❌ WRONG | ✅ RIGHT |
|----------|----------|
| Wait indefinitely | Set timeout alerts at 5, 10, 15 min |
| Keep polling "is it done?" | Kill process if stuck |
| Let failed builds run | Push fixes immediately, don't wait |
| Ignore RAM usage | Monitor: <5GB normal, >8GB = problem |

---

## Quick Diagnosis

```
BUILD FAILED
     ↓
1. curl live logs (see above)
2. Find error message
3. Fix code
4. Push and retrigger
```

---

---

## Gitea Version Upgrade Issues

### Issue: Gitea 1.25.x Requires zstd for Action Logs

**Discovery Date:** 2025-12-26 | **Affected Versions:** 1.25.x+

**Symptoms:**
- Build runs but shows FAILURE instantly
- Task steps show status=FAILURE with log_length=0
- Gitea log shows: `dbfs open "actions_log/.../XXX.log.zst": file does not exist`
- 500 Internal Server Error when accessing logs via web

**Root Cause:**
Gitea 1.25.x changed action log storage to use zstd compression (`.log.zst` files), but the `zstd` binary was not installed on the system.

**Effective Debug Steps (Use These Exact Commands):**

```bash
# STEP 1: Check latest runs in database (NOT curl - database is truth)
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title, started, stopped FROM action_run ORDER BY id DESC LIMIT 3')
for r in c.fetchall():
    status_map = {0: 'UNKNOWN', 1: 'SUCCESS', 2: 'FAILURE', 3: 'CANCELLED', 4: 'SKIPPED', 5: 'WAITING', 6: 'RUNNING'}
    print(f'Run {r[0]}: {status_map.get(r[1], r[1])} - {r[2][:50]}')"

# STEP 2: Check Gitea's main log for errors (NOT /tmp/gitea.log)
tail -50 /home/neil1988/gitea/log/gitea.log | grep -E "(error|Error|Warning|cannot|does not exist)"

# STEP 3: Check task step details for failed run
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, name, status, log_length FROM action_task_step WHERE task_id=(SELECT MAX(id) FROM action_task)')
for r in c.fetchall():
    print(f'Step {r[0]}: {r[1]}, status={r[2]}, log_length={r[3]}')"

# STEP 4: Verify zstd is installed
which zstd && zstd --version
# If missing: sudo apt-get install -y zstd
```

**Fix:**
```bash
sudo apt-get update && sudo apt-get install -y zstd
```

**After Fix - Clean Restart (REQUIRED):**
```bash
# 1. Stop runner first
pkill -f "act_runner"

# 2. Stop Gitea
pkill -f "gitea web"

# 3. Wait for clean shutdown
sleep 3

# 4. Verify clean state
ps aux | grep -E "(gitea|act_runner)" | grep -v grep  # Should be empty

# 5. Start Gitea with GOGC=200
cd /home/neil1988/gitea && GOGC=200 GITEA_WORK_DIR="/home/neil1988/gitea" nohup ./gitea web > /tmp/gitea.log 2>&1 &

# 6. Wait for Gitea to initialize
sleep 5

# 7. Start runner
cd /home/neil1988/gitea && nohup ./act_runner daemon --config runner_config.yaml > /tmp/act_runner.log 2>&1 &

# 8. Retrigger build
echo "Build NNN: Verify fix" >> /path/to/GITEA_TRIGGER.txt
git add -A && git commit -m "Build NNN: Verify fix" && git push gitea main
```

**Verification:**
```bash
# Check if .zst files are being created
find /home/neil1988/gitea/data/actions_log/neilvibe/LocaNext/ -name "*.zst" -mmin -5
# Should show recent .zst files

# Verify logs accessible via curl (no 500 error)
curl -s "http://172.28.150.120:3000/neilvibe/LocaNext/actions/runs/XXX/jobs/0/logs" | head -10
# Should show log content, not HTML error page
```

---

## ⚠️ CLAUDE CONFUSION TRAP: Git Log ≠ CI/CD Builds

**This is a documented pitfall - Claude has made this mistake before!**

### The Mistake

When asked "did we build today?" or "is there a new build?", Claude incorrectly checks:

| ❌ WRONG | Why It's Wrong |
|----------|----------------|
| `git log --since="today"` | Shows commits, NOT builds. Builds run on Gitea, not local git. |
| `ls -lt *.exe` | File timestamps show when file was COPIED, not when build RAN |
| `stat LocaNext_latest.exe` | Same problem - file modification time ≠ build time |

### The Correct Approach

**ALWAYS check the database - it's the source of truth:**

```bash
# Check recent builds (CORRECT WAY)
python3 -c "
import sqlite3
from datetime import datetime
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title, started FROM action_run ORDER BY id DESC LIMIT 5')
status_map = {0: 'UNK', 1: 'OK', 2: 'FAIL', 3: 'CANCEL', 4: 'SKIP', 5: 'WAIT', 6: 'RUN'}
for r in c.fetchall():
    when = datetime.fromtimestamp(r[3]).strftime('%b %d %H:%M') if r[3] else 'N/A'
    print(f'Run {r[0]}: {status_map.get(r[1], r[1]):6} | {when} | {r[2][:45]}')"
```

### Why This Matters

- **Git commits** = code changes pushed to repo
- **CI/CD builds** = automated jobs that compile, test, and package
- A commit triggers a build, but they are SEPARATE events
- Multiple builds can run from one commit (retries, manual triggers)
- Builds have their own IDs, timestamps, and status in the database

### Quick Reference

| Question | Check This |
|----------|-----------|
| "Any new builds?" | Database: `action_run` table |
| "Any new commits?" | Git: `git log --oneline -5` |
| "Is Playground up to date?" | Compare: Playground install time vs latest successful build time |

---

## ⚠️ CLAUDE CONFUSION TRAP #2: Date Filtering Pitfall

**Another documented pitfall - Claude has made this mistake too!**

### The Mistake

When checking for "today's" activity, Claude uses strict date filters:

```bash
# ❌ WRONG - This misses recent work!
git log --since="2025-12-27"   # Returns nothing at 2 AM on Dec 27
```

**Problem:** If it's 2 AM on Dec 27 and work happened at 11 PM on Dec 26, the filter excludes it. Claude then wrongly concludes "no activity today."

### The Correct Approach

**NEVER use date filters. Always show recent activity by count:**

```bash
# ✅ CORRECT - Show last N commits regardless of date
git log --oneline -10

# ✅ CORRECT - Show commits with timestamps for context
git log --oneline --format="%h | %ci | %s" -10
```

### Why This Matters

- Users work late nights - "today" spans midnight
- Work sessions don't follow calendar dates
- A commit at 11:53 PM is "today's work" even if technically yesterday
- Empty result from date filter ≠ no activity

### The Chain Reaction of Wrong Conclusions

```
❌ git log --since="today" returns empty
    ↓
❌ Claude concludes "no commits today"
    ↓
❌ Claude assumes "no builds either"
    ↓
❌ Claude tells user "Playground is up to date"
    ↓
❌ User confused - they KNOW they worked today!
```

### Rule: When Asked "Any Recent Activity?"

1. **First:** `git log --oneline -10` (no date filter)
2. **Then:** Database query for builds
3. **Compare:** Timestamps to understand what's recent
4. **Never:** Assume empty filtered result = no activity

---

## ⚡ EFFECTIVE CI/CD DEBUGGING (CRITICAL - READ FIRST)

**For Claude Code agents - AVOID these time-wasters, get straight to the meat:**

### Common Mistakes That Waste Time

| ❌ WRONG | ✅ CORRECT | Why |
|----------|-----------|-----|
| `tail /tmp/gitea.log` | `tail /home/neil1988/gitea/log/gitea.log` | /tmp may be empty or stale |
| `curl .../jobs/0/logs` (for debugging) | Query database directly | curl returns 500 if storage broken |
| `grep -r "error"` everywhere | Check specific log files first | Too many false positives |
| Restart immediately | Stop → Clean → Investigate → Fix → Start | Restart masks the real issue |
| Check old log folders | `ls -lt` to find NEWEST folder | Old folders have old irrelevant logs |

### The 60-Second Debug Path

**ALWAYS do these in order:**

```bash
# 1. PROCESSES (5 sec) - Are services even running?
ps aux | grep -E "(gitea|act_runner)" | grep -v grep

# 2. DATABASE (10 sec) - What's the REAL status?
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 3')
status_map = {0:'UNK', 1:'OK', 2:'FAIL', 3:'CANCEL', 4:'SKIP', 5:'WAIT', 6:'RUN'}
for r in c.fetchall(): print(f'{r[0]}: {status_map.get(r[1], r[1])} - {r[2][:40]}')"

# 3. ERRORS (15 sec) - What went wrong?
tail -30 /home/neil1988/gitea/log/gitea.log | grep -iE "(error|fail|cannot|does not)"

# 4. RUNNER (5 sec) - Is runner picking up jobs?
tail -10 /tmp/act_runner.log
```

**If run is FAILURE with no logs (log_length=0):**
```bash
# Check for storage/dependency issues
grep "dbfs\|zstd\|file does not exist" /home/neil1988/gitea/log/gitea.log | tail -5
```

### Quick Decision Tree

```
Run status WAITING?
  → Check runner: cat /tmp/act_runner.log | tail -10
  → If "declared successfully" but no tasks: wait 30s (polling interval)

Run status FAILURE, log_length=0?
  → Storage/dependency issue
  → Check: which zstd (must be installed for Gitea 1.25+)
  → Check: grep "file does not exist" gitea.log

Run status FAILURE, has logs?
  → Normal failure - read the logs
  → curl .../jobs/X/logs or check disk: ls -lt actions_log/

500 errors on curl?
  → DON'T keep retrying curl
  → Check gitea.log for the actual error
```

---

## Effective CI/CD Debugging Protocol

### Phase 1: Identify State (30 seconds)

```bash
# 1. Check process state
ps aux | grep -E "(gitea|act_runner)" | grep -v grep

# 2. Get latest runs from database (source of truth)
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 3')
status_map = {0: 'UNKNOWN', 1: 'SUCCESS', 2: 'FAILURE', 3: 'CANCELLED', 4: 'SKIPPED', 5: 'WAITING', 6: 'RUNNING'}
for r in c.fetchall():
    print(f'Run {r[0]}: {status_map.get(r[1], r[1])} - {r[2][:50]}')"
```

### Phase 2: Check Errors (30 seconds)

```bash
# Main Gitea log (NOT /tmp/gitea.log which may be empty)
tail -30 /home/neil1988/gitea/log/gitea.log | grep -E "(error|Error|Warning|cannot|failed|500)"

# Runner log
cat /tmp/act_runner.log | tail -20
```

### Phase 3: Deep Dive into Specific Run

```bash
# Get jobs for a specific run (replace XXX with run ID)
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, name, status FROM action_run_job WHERE run_id=XXX')
status_map = {0: 'UNKNOWN', 1: 'SUCCESS', 2: 'FAILURE', 3: 'CANCELLED', 4: 'SKIPPED', 5: 'WAITING', 6: 'RUNNING', 7: 'BLOCKED'}
for r in c.fetchall():
    print(f'Job {r[0]}: {r[1]}, status={status_map.get(r[2], r[2])}')"
```

### Key Rules for Effective Debugging

| DO | DON'T |
|----|-------|
| Check database directly (source of truth) | Rely solely on curl (can return 500s) |
| Check /home/neil1988/gitea/log/gitea.log | Check only /tmp/gitea.log (may be empty) |
| Stop runner BEFORE stopping Gitea | Kill Gitea while runner is mid-job |
| Clean restart with 3s+ delays | Rapid restart without cleanup |
| Verify fix with new build trigger | Assume fix worked without test |

### Common Issues Quick Reference

| Symptom | Likely Cause | Check Command |
|---------|--------------|---------------|
| Run WAITING forever | Runner not connected | `cat /tmp/act_runner.log` |
| Run FAILURE with log_length=0 | Missing dependency (zstd) | `which zstd` |
| 500 errors on log access | Storage issue | Check gitea.log for "dbfs" errors |
| Runner "declared successfully" but no jobs | Labels mismatch | Check workflow runs-on vs runner labels |

---

## Cleanup: Remove Stale Ephemeral Runners

Ephemeral runners accumulate in database. Clean them periodically:

```bash
python3 -c "
import sqlite3
import time
for attempt in range(3):
    try:
        c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db', timeout=10)
        c.execute('PRAGMA busy_timeout = 5000')
        cursor = c.cursor()
        cursor.execute(\"DELETE FROM action_runner WHERE name LIKE '%ephemeral%'\")
        c.commit()
        print(f'Deleted {cursor.rowcount} ephemeral runners')
        break
    except sqlite3.OperationalError as e:
        print(f'Attempt {attempt+1}: {e}')
        time.sleep(2)"
```

---

## ⚠️ CLAUDE CONFUSION TRAP #3: Checking Runner Status

**Another documented pitfall - Claude tried the wrong approach!**

### The Mistake

When checking if builds are running, Claude incorrectly tries:

| ❌ WRONG | Why It's Wrong |
|----------|----------------|
| `find /mnt/c -name "runner.db"` | Slow, searches all of C: drive |
| `Get-Service gitea-runner` via PowerShell | Service may not be a Windows service |
| `curl` the Gitea API | Requires authentication token |
| `ls /home/neil1988/gitea-runner/runner.db` | Wrong path |

### The Correct Approach

**ALWAYS use the documented SQL command:**

```bash
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 5')
status_map = {0:'UNK', 1:'OK', 2:'FAIL', 3:'CANCEL', 4:'SKIP', 5:'WAIT', 6:'RUN'}
for r in c.fetchall(): print(f'{r[0]}: {status_map.get(r[1], r[1])} - {r[2][:50]}')"
```

**Key points:**
- Database path: `/home/neil1988/gitea/data/gitea.db`
- This shows build status directly from source of truth
- No authentication, curl, or complex paths needed

### Rule: When Asked "Is the Build Running?"

1. **Use SQL** - Query the database directly
2. **Database is truth** - Not curl, not file timestamps, not PowerShell
3. **READ THE DOCS** - TROUBLESHOOTING.md has the exact commands

---

*Last updated: 2025-12-27*
