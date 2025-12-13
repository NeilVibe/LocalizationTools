# CI/CD Troubleshooting Guide

## Checking Logs

### Live Logs (While Running) - USE CURL

```bash
# Get latest run number
curl -s "http://localhost:3000/neilvibe/LocaNext/actions" | grep -oP 'runs/\d+' | head -1

# Stream live logs (replace 221 with run number)
curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/221/jobs/1/logs" | tail -50

# Filter for test results only
curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/221/jobs/1/logs" | grep -E "(PASSED|FAILED|remaining)" | tail -30
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
| `got Future attached to a different loop` | Use `Depends(get_async_db)` not `async for` |
| `Cannot create symbolic link` | Add `sign: false` to package.json |
| `No module named 'X'` | Add to requirements.txt |

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

*Last updated: 2025-12-13*
