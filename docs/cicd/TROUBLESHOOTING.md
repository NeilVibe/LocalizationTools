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
