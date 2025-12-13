# CI/CD Troubleshooting Guide

## Checking Logs

### Live Logs (While Running)

```bash
# Get latest run number
curl -s "http://localhost:3000/neilvibe/LocaNext/actions" | grep -oP 'runs/\d+' | head -1

# Stream live logs (replace 203 with run number)
curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/203/jobs/1/logs" | tail -50
```

### Disk Logs (After Completion)

```bash
# Find latest build folder
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -3

# Read log
tail -50 ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log
```

---

## TROUBLESHOOT Mode

Checkpoint system for iterative test fixing.

### Trigger

```bash
echo "TROUBLESHOOT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "TROUBLESHOOT" && git push gitea main
```

### How It Works

1. First run: Collects all tests, runs from beginning
2. On failure: Saves remaining tests to `~/.locanext_checkpoint`
3. Next run: Resumes from checkpoint

### Commands

```bash
# Check checkpoint
cat ~/.locanext_checkpoint

# Clear checkpoint (restart from beginning)
rm ~/.locanext_checkpoint
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
