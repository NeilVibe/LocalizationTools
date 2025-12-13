# CI/CD Troubleshooting Guide

**Quick fixes for common CI/CD failures**

---

## TROUBLESHOOT Mode

**Smart checkpoint system for iterative test fixing.**

### How It Works

```
TROUBLESHOOT trigger
       ↓
   Run tests
       ↓
 Test fails? ──→ Save checkpoint → Exit
       ↓              ↓
   All pass     Fix code, push
       ↓              ↓
    Done        TROUBLESHOOT again
                      ↓
                Resume at checkpoint
```

### Quick Commands

```bash
# Check checkpoint
cat ~/.locanext_checkpoint

# Check latest log (ALWAYS DO THIS FIRST)
tail -5 $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)

# Clear checkpoint manually
rm ~/.locanext_checkpoint
```

### Checkpoint Location

`/home/neil1988/.locanext_checkpoint` - Persists across CI runs (host mode).

---

## CRITICAL RULES

1. **NEVER rebuild without checking logs first.**
2. **NEVER restart services to "fix" issues.** Find root cause.

```bash
# Step 1: Find latest build
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -3

# Step 2: Check for errors
grep -i "error\|failed\|❌\|BLOCKED" ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log | head -20

# Step 3: Read the actual error
tail -50 ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/<number>.log
```

**NOTE:** Disk logs only appear AFTER job completes. For live logs, use Gitea web UI:
`http://localhost:3000/neilvibe/LocaNext/actions`

---

## Error Categories

### Category A: Version Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `Version timestamp TOO FAR` | Old version in version.py | **AUTO-FIXED** - Pipeline generates version |
| `Expected 'X', found 'Y'` in docs | Docs have old version | **WARN ONLY** - Doesn't block build |
| `Expected 'X', found 'Y'` in critical files | Version injection failed | Check pipeline logs |

### Category B: Test Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `unexpected keyword argument 'use_postgres'` | Old function signature | Remove `use_postgres` parameter |
| `No module named 'X'` | Missing dependency | Add to requirements.txt |
| `Connection refused` | Server not running | Check PostgreSQL is up |

### Category C: Build Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot create symbolic link` | Windows symlink permission | `sign: false` in package.json |
| `Cannot parse version` | Invalid semver format | Use YY.MMDD.HHMM format |
| `Env WIN_CSC_LINK is not correct` | Code signing misconfigured | Remove WIN_CSC_LINK entirely |

---

## Quick Diagnosis Flow

```
BUILD FAILED
     ↓
┌────────────────────────────────┐
│ 1. Check which job failed      │
│    - check-build-trigger?      │
│    - safety-checks?            │
│    - build-windows?            │
└────────────┬───────────────────┘
             ↓
┌────────────────────────────────┐
│ 2. Read the error message      │
│    grep "error\|failed" *.log  │
└────────────┬───────────────────┘
             ↓
┌────────────────────────────────┐
│ 3. Check this table:           │
│    - Version issue? → Cat A    │
│    - Test failed? → Cat B      │
│    - Build failed? → Cat C     │
└────────────┬───────────────────┘
             ↓
┌────────────────────────────────┐
│ 4. Apply fix from table        │
│ 5. Commit and push             │
│ 6. Verify fix in next build    │
└────────────────────────────────┘
```

---

## Job-Specific Issues

### Job 1: check-build-trigger

**Common issues:**
- No "Build LIGHT" or "Build FULL" in GITEA_TRIGGER.txt
- Malformed trigger line

**Fix:** Add proper trigger line:
```
Build LIGHT - description here
```

### Job 2: safety-checks

**Common issues:**
- Test failures
- Import errors
- Database connection errors

**Debug commands:**
```bash
# Run tests locally
python3 -m pytest tests/ -v --tb=short

# Check specific test
python3 -m pytest tests/path/to/test.py -v
```

### Job 3: build-windows

**Common issues:**
- Code signing errors
- Missing dependencies
- Path issues

**Debug:** Check Windows runner is online:
```bash
# Check runner status
cat /tmp/windows_runner_output.txt
```

---

## Version Check Details

The version check has two categories:

### Critical Files (Block Build)
- `version.py` - Source of truth
- `server/config.py` - Backend import
- `locaNext/package.json` - Electron version
- `installer/*.iss` - Installer version

### Informational Files (Warn Only)
- `README.md`
- `CLAUDE.md`
- `Roadmap.md`

If critical files mismatch → Build fails
If informational files mismatch → Warning only, build continues

---

## Historical Fixes

| Date | Error | Root Cause | Fix |
|------|-------|------------|-----|
| 2025-12-13 | `use_postgres` TypeError | Deprecated parameter | Remove from all scripts |
| 2025-12-13 | README.md version mismatch | Docs not injected by pipeline | Separate critical vs informational |
| 2025-12-13 | Version too old | Manual version updates | Pipeline auto-generates |
| 2025-12-07 | Symlink permission | winCodeSign downloaded | `sign: false` in package.json |

---

## Prevention Checklist

Before pushing code that might break CI:

- [ ] Run `python3 scripts/check_version_unified.py` locally
- [ ] Run `python3 -m pytest tests/ -v` locally
- [ ] Check for deprecated function signatures
- [ ] Verify PostgreSQL is the only database (no SQLite fallbacks)

---

*Last updated: 2025-12-13*
