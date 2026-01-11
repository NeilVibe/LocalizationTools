# ALERT-001: Gitea Resource Crisis

**Date:** 2025-12-28 13:02 KST | **Severity:** CRITICAL | **Status:** RESOLVED

---

## CLAUDE'S MISTAKES (Root Cause Analysis)

### Mistake 1: Pushed Without Checking Gitea State
```
Commit 4a58409: "Trigger: Verify UI-062 fix"
Pushed at: 2025-12-28 12:36
```
I pushed to Gitea WITHOUT verifying:
- Gitea service was healthy
- No zombie processes existed
- System had sufficient resources

### Mistake 2: Did Not Follow Gitea Protocol
The correct protocol (from CLAUDE.md) is:
```
1. START:  sudo systemctl start gitea
2. COMMIT: git add -A && git commit -m "Build XXX: ..."
3. PUSH:   git push origin main && git push gitea main
4. STOP:   sudo systemctl stop gitea
```

I did NOT follow step 4 (STOP) in previous sessions, leaving Gitea running.

### Mistake 3: Zombie From Dec 27 Never Cleaned
```
PID 859420 started: Dec 27 (manually with ./gitea web)
Never killed until: Dec 28 13:02
```
The zombie was created in a previous session when I started Gitea manually instead of using systemd.

### Mistake 4: THE REAL PROBLEM - CI Runs on Same Machine

**Root Cause:** The `locanext-runner` runs on the SAME WSL instance as:
- Gitea server
- PostgreSQL
- LanguageTool (1GB)
- Claude session
- Everything else

When CI Run 410 triggered, pytest ran LOCALLY and consumed 36.5GB:

```
Same WSL instance (39GB total RAM):
├── Gitea server        (~300MB)
├── PostgreSQL          (~200MB)
├── LanguageTool        (~1GB)
├── Claude session      (~600MB)
├── act_runner          (~50MB)
└── pytest (CI Run 410) ← ATE 36.5GB!
                         ↓
                    SYSTEM STARVED
```

**Why tests consumed so much:**
- Unit tests: 29 files
- Integration tests: loading database fixtures
- E2E tests: loading models (Qwen 2.3GB)
- No memory limit on runner
- Running in parallel (`-n 4`)

**This is the ARCHITECTURAL FLAW:**
CI should run on SEPARATE machine (Windows runner exists but not used for all tests)

---

## What Happened

### Symptom
- System lag/freeze
- Gitea in crash loop (restart counter: 72)
- API responding 200 but service failing

### Root Causes Found

#### Issue 1: Zombie Gitea Process
| PID | Started | Problem |
|-----|---------|---------|
| 859420 | Dec 27 | OLD process still running, holding port 3000 |
| 914553 | Dec 28 12:56 | NEW systemd process couldn't bind port |

**Cause:** Gitea was started manually (outside systemd) on Dec 27 and never killed. When systemd tried to restart, port 3000 was already in use.

**Fix:** `kill -9 859420` then `sudo systemctl start gitea`

#### Issue 2: Runaway Pytest Process (MEMORY KILLER)
| Metric | Value |
|--------|-------|
| PID | 913123 |
| Memory | **93% (36.5GB of 39GB!)** |
| CPU | 72.9% |
| Free RAM | Only 280MB |
| Load Average | 5.45 |

**What it was:**
```
python3.11 -m pytest tests/unit/ --deselect=... -v --tb=short --no-cov
```

**Cause:** CI Action Run 410 ("Trigger: Verify UI-062 fix") started at 12:36:39 and ran tests that consumed all memory.

**Fix:** `kill -9 913123`

---

## Database Evidence

### Action Run 410 (The Culprit)
```
Run 410: status=6 (running/stuck)
Created: 2025-12-28 12:36:39
Started: 2025-12-28 12:36:47
Stopped: N/A (never finished - killed)
Title: "Trigger: Verify UI-062 fix"
```

### Previous Successful Runs
```
Run 409: status=1 (success), 2025-12-27 23:31-23:44 (13 min)
Run 408: status=1 (success), 2025-12-27 23:09-23:21 (12 min)
Run 407: status=1 (success), 2025-12-27 22:34-22:47 (13 min)
```

---

## Timeline Reconstruction

```
Dec 27 (sometime)
  └─ Gitea started manually with ./gitea web (PID 859420)
  └─ This process held port 3000

Dec 27 23:44
  └─ Build 409 completed successfully

Dec 28 12:36
  └─ Action Run 410 triggered ("Verify UI-062 fix")
  └─ pytest process started (PID 913123)
  └─ Memory consumption began spiraling

Dec 28 12:54-12:56
  └─ Something triggered systemd restart
  └─ Gitea service tried to start but port 3000 blocked
  └─ Entered crash loop (72 restarts!)
  └─ Old zombie (859420) still holding port

Dec 28 13:00
  └─ System lag severe
  └─ pytest at 93% memory, 72.9% CPU
  └─ Only 280MB RAM free

Dec 28 13:02
  └─ Zombie Gitea killed (859420)
  └─ Runaway pytest killed (913123)
  └─ Fresh Gitea started via systemd
```

---

## Prevention Rules

### Rule 1: Never Start Gitea Manually
```bash
# WRONG - creates zombie
cd /home/neil1988/gitea && ./gitea web

# RIGHT - use systemd
sudo systemctl start gitea
sudo systemctl stop gitea
```

### Rule 2: Always Check for Zombies Before Starting
```bash
# Check before starting
ps aux | grep gitea | grep -v grep

# If zombie found, kill it first
kill -9 <PID>

# Then start via systemd
sudo systemctl start gitea
```

### Rule 3: Monitor CI Runs for Resource Usage
```bash
# Check if any pytest is eating memory
ps aux --sort=-%mem | head -5

# Kill runaway processes
kill -9 <PID>
```

### Rule 4: Check Load Before Triggering Builds
```bash
# Check system load
uptime
free -h

# If load > 3 or memory < 2GB, wait
```

---

## Quick Recovery Commands

```bash
# Full recovery sequence
sudo systemctl stop gitea
ps aux | grep gitea | grep -v grep  # Find zombies
kill -9 <zombie_pids>
ps aux --sort=-%mem | head -5       # Find memory hogs
kill -9 <hog_pids>
sudo systemctl start gitea
free -h                             # Verify memory freed
```

---

## Related Issues

- **DOC-001:** Install vs Update confusion (same session)
- **Confusion #16:** INSTALL vs UPDATE documentation gap

---

*Alert documented for future reference*
