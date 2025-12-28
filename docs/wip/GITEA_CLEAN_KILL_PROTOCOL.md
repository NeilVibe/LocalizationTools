# Gitea Clean Kill Protocol

**Priority:** P2 | **Status:** IMPLEMENTED | **Created:** 2025-12-28

---

## DANGER - READ BEFORE TOUCHING GITEA

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️  GITEA IS CRITICAL INFRASTRUCTURE - HANDLE WITH CARE ⚠️    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ONE WRONG MOVE CAN:                                            │
│  • Create ZOMBIE processes that eat CPU forever                 │
│  • Cause INFINITE LOOPS in runners                              │
│  • BREAK CI/CD completely (builds won't run)                    │
│  • Leave ORPHANED containers consuming resources                │
│  • Corrupt the Gitea database                                   │
│                                                                 │
│  ALWAYS:                                                        │
│  1. Check status BEFORE any action                              │
│  2. Use the control script (not raw commands)                   │
│  3. Wait for graceful shutdown before forcing                   │
│  4. Verify status AFTER any action                              │
│  5. Never kill during an active build (wait or let it finish)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### What Can Go Wrong

| Mistake | Consequence |
|---------|-------------|
| Kill during active build | Zombie Docker containers, stuck jobs |
| Start runner twice | Duplicate runners, race conditions |
| Kill Gitea without killing runner | Orphaned runner, can't restart |
| Force kill without graceful first | Database corruption risk |
| Restart too quickly | Port conflicts, startup failures |

### Resource Management Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│  STOP/START > RESTART                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DON'T:  restart (risky, can leave zombies)                     │
│                                                                 │
│  DO:     CLEAN STOP → wait → CLEAN START (when needed)          │
│                                                                 │
│  WHY?                                                           │
│  • Restart can leave orphaned processes                         │
│  • Stop gives clean slate, verifiable state                     │
│  • Start only when actually needed (saves resources)            │
│  • Gitea uses ~60% CPU when idle - stop when not building!      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Workflow

```
DAILY WORKFLOW:
1. Need to build?  → START
2. Build done?     → STOP
3. Not building?   → Keep STOPPED (saves CPU/RAM)

NOT RECOMMENDED:
- Leaving Gitea running 24/7
- Using "restart" command
- Starting and forgetting
```

### Safe Sequence (ALWAYS FOLLOW)

```
STOP:
1. CHECK    → ./scripts/gitea_control.sh status
2. STOP     → ./scripts/gitea_control.sh stop
3. VERIFY   → ./scripts/gitea_control.sh status (confirm stopped)

START (when needed):
1. CHECK    → ./scripts/gitea_control.sh status
2. START    → ./scripts/gitea_control.sh start
3. VERIFY   → ./scripts/gitea_control.sh status (confirm running)
4. DO WORK  → Push, build, etc.
5. STOP     → ./scripts/gitea_control.sh stop (when done!)
```

---

## TL;DR - Quick Commands

```bash
# Check status
./scripts/gitea_control.sh status

# Restart (fixes high CPU, clears state)
./scripts/gitea_control.sh restart

# Force kill if stuck
./scripts/gitea_control.sh kill

# Live monitoring
./scripts/gitea_control.sh monitor
```

---

## Problem Statement

Gitea and act_runner processes can become problematic when:
- CI builds get stuck or timeout
- Go garbage collection gets backed up (causes 50%+ CPU when idle)
- Multiple builds pile up
- Improper shutdown

**Symptoms:**
- High CPU usage (>30% when idle) - **RESTART FIXES THIS**
- High RAM usage (>8GB)
- Builds won't start
- `act_runner` processes consuming resources

---

## Full Architecture (3 Components)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CI/CD ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GITEA SERVER (WSL - 172.28.150.120:3000)                          │
│  └── Orchestrates builds, stores artifacts                         │
│  └── Managed by: systemd (gitea.service)                           │
│                                                                     │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │   LINUX RUNNER (WSL)   │    │  WINDOWS RUNNER (Native) │        │
│  ├─────────────────────────┤    ├─────────────────────────┤        │
│  │ Name: locanext-runner   │    │ Name: windows-runner     │        │
│  │ Process: act_runner     │    │ Process: act_runner_     │        │
│  │                         │    │          patched_v15.exe │        │
│  │ Labels:                 │    │                          │        │
│  │  - ubuntu-latest        │    │ Labels:                  │        │
│  │  - linux                │    │  - windows-latest        │        │
│  │                         │    │  - windows, self-hosted  │        │
│  │ Jobs: Tests (1-2)       │    │  - x64                   │        │
│  │                         │    │                          │        │
│  │ Managed by:             │    │ Jobs: Build EXE (3)      │        │
│  │  Manual daemon          │    │                          │        │
│  │                         │    │ Managed by:              │        │
│  │                         │    │  NSSM Service            │        │
│  │                         │    │  (GiteaActRunner)        │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
│                                                                     │
│  ALL MANAGED BY: ./scripts/gitea_control.sh                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

| Component | Platform | Process | Location | Managed By |
|-----------|----------|---------|----------|------------|
| **Gitea Server** | WSL | `gitea` | `/home/neil1988/gitea/` | systemd |
| **Linux Runner** | WSL | `act_runner` | `/home/neil1988/gitea/` | Manual daemon |
| **Windows Runner** | Windows | `act_runner_patched_v15.exe` | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\` | NSSM Service |

### Process Locations
```
LINUX (WSL):
  Gitea Server:    /home/neil1988/gitea/gitea
  Linux Runner:    /home/neil1988/gitea/act_runner
  Database:        /home/neil1988/gitea/data/gitea.db
  Runner Config:   /home/neil1988/gitea/runner_config.yaml

WINDOWS:
  Windows Runner:  C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner_patched_v15.exe
  Runner Config:   C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\config.yaml
  Service Name:    GiteaActRunner (via NSSM)

Control Script:    ./scripts/gitea_control.sh (manages ALL components)
```

### Check Running Services
```bash
# Check ALL components at once:
./scripts/gitea_control.sh status

# Sample output:
# === Gitea Status (Full Architecture) ===
#
# [SERVER]
# [OK] Gitea Server: Running (PID: 950902, CPU: 2.2%, MEM: 0.5%)
#
# [LINUX RUNNER]
# [OK] Linux Runner: Running (PID: 950949, CPU: 0.0%)
#
# [WINDOWS RUNNER]
# [OK] Windows Runner: Running (Service: GiteaActRunner, PID: 172560)
#
# === Latest Build ===
# Build 415: SUCCESS (92m ago)
```

### Windows Runner Details

The Windows runner uses a **patched version** (v15) that fixes PowerShell NUL byte bugs.

**Patch:** Strips `\x00` characters from `GITHUB_OUTPUT` to prevent `invalid format` errors.

**Docs:**
- Setup: `docs/deployment/WINDOWS_RUNNER_SETUP.md`
- Rebuild: `runner/README.md`

---

## Clean Kill Protocol

### Level 1: Graceful Stop (Preferred)

```bash
# Use the control script
./scripts/gitea_control.sh stop

# What it does:
# 1. pkill -SIGTERM act_runner (graceful)
# 2. Wait 3 seconds
# 3. Force kill if still running
# 4. systemctl stop gitea (graceful via systemd)
# 5. Wait 3 seconds
# 6. systemctl kill if still running
```

### Level 2: Force Kill (If Level 1 Fails)

```bash
./scripts/gitea_control.sh kill

# What it does:
# 1. pkill -9 act_runner
# 2. systemctl kill gitea
# 3. pkill -9 gitea (backup)
# 4. Stop any Docker containers
# 5. Remove stopped containers
```

### Level 3: Nuclear Option (Manual)

Only if script fails:

```bash
# Kill everything Gitea-related
sudo pkill -9 -f gitea
pkill -9 -f act_runner
pkill -9 -f "docker.*runner"

# Clean up docker
docker system prune -f

# Check for zombie processes
ps aux | grep -E "(Z|defunct)"

# Start fresh
./scripts/gitea_control.sh start
```

---

## Monitoring Protocol

### Quick Health Check

```bash
# Use the control script
./scripts/gitea_control.sh status

# Sample output:
# === Gitea Status ===
# [OK] Gitea: Running (PID: 950902, CPU: 2.2%, MEM: 0.4%)
# [OK] act_runner: Running (PID: 950949, CPU: 0.0%)
#
# === Latest Build ===
# Build 415: SUCCESS (66m ago)
```

### Live Monitoring

```bash
# Refreshes every 10 seconds
./scripts/gitea_control.sh monitor

# Shows:
# - Gitea CPU/MEM/Uptime
# - act_runner CPU/MEM/Uptime
# - Latest build status
# - WARNING if build >15 minutes
```

### Health Thresholds

| Metric | Normal | Warning | Action |
|--------|--------|---------|--------|
| **Gitea CPU** | <5% | >30% | Restart |
| **Gitea RAM** | <500MB | >2GB | Investigate |
| **Build time** | <10m | >15m | Check logs |
| **Idle CPU** | ~2% | >50% | Restart (GC issue) |

---

## Timeout Thresholds

| Stage | Max Time | Action if Exceeded |
|-------|----------|-------------------|
| Checkout | 2 min | Kill and restart |
| Dependencies | 5 min | Kill and restart |
| Tests | 10 min | Kill, investigate |
| Build | 15 min | Kill, investigate |
| **Total** | **20 min** | Force kill all |

---

## Restart Protocol

```bash
# Preferred method
./scripts/gitea_control.sh restart

# What it does:
# 1. Graceful stop of act_runner (SIGTERM)
# 2. Graceful stop of Gitea (systemctl)
# 3. Wait 2 seconds
# 4. Start Gitea via systemd
# 5. Wait 3 seconds
# 6. Start act_runner daemon
# 7. Show status

# Manual (if script fails):
sudo systemctl restart gitea
cd /home/neil1988/gitea && ./act_runner daemon --config runner_config.yaml &
```

---

## Management Script

**Location:** `./scripts/gitea_control.sh`

```bash
# Commands:
./scripts/gitea_control.sh status   # Show status + CPU/MEM
./scripts/gitea_control.sh stop     # Graceful stop
./scripts/gitea_control.sh kill     # Force kill
./scripts/gitea_control.sh start    # Start both services
./scripts/gitea_control.sh restart  # Stop then start
./scripts/gitea_control.sh monitor  # Live monitoring (10s refresh)
```

---

## Prevention Best Practices

1. **Restart periodically** - Fixes Go GC buildup (every few days or after many builds)
2. **Monitor resource usage** - Use `./scripts/gitea_control.sh status` before triggering builds
3. **Limit concurrent builds** - Only 1 build at a time
4. **Check before triggering** - If CPU >30%, restart first
5. **Don't leave builds running overnight** - Check status before leaving

---

## Lessons Learned (2025-12-28)

### Issue: 52% CPU When Idle

**Symptoms:**
- Gitea using 52.2% CPU with no running builds
- Build 415 finished 1+ hour ago
- No Docker containers running

**Root Cause:**
- Go garbage collection can get backed up after processing many builds
- The process accumulates memory pressure over time
- Not a bug, just needs periodic restart

**Fix:**
```bash
./scripts/gitea_control.sh restart
# Result: CPU dropped from 52.2% → 2.2%
```

**Prevention:**
- Restart after every 5-10 builds
- Restart if CPU >30% when idle
- Monitor with `./scripts/gitea_control.sh status`

---

## RECOVERY - When Things Go Wrong

### Symptom: Builds Won't Start

```bash
# 1. Check what's running
./scripts/gitea_control.sh status

# 2. Check for zombie/stuck processes
ps aux | grep -E "(gitea|act_runner|docker)" | grep -v grep

# 3. Force kill everything
./scripts/gitea_control.sh kill

# 4. Clean Docker
docker ps -aq | xargs -r docker rm -f
docker system prune -f

# 5. Wait 10 seconds
sleep 10

# 6. Start fresh
./scripts/gitea_control.sh start

# 7. Verify
./scripts/gitea_control.sh status
```

### Symptom: Duplicate Runners

```bash
# Check for multiple runners
pgrep -a act_runner

# If more than 1 line shows up:
pkill -9 act_runner
sleep 5
cd /home/neil1988/gitea && ./act_runner daemon --config runner_config.yaml &
```

### Symptom: Build Stuck Forever

```bash
# 1. Check current build status
python3 -c "
import sqlite3, time
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, started FROM action_run WHERE status=6')
for r in c.fetchall():
    elapsed = (int(time.time()) - r[2]) // 60
    print(f'Build {r[0]}: RUNNING for {elapsed}m')
"

# 2. If >20 minutes, it's stuck. Cancel in Gitea UI or:
# Mark as failed in database (EMERGENCY ONLY)
# sqlite3 /home/neil1988/gitea/data/gitea.db "UPDATE action_run SET status=2 WHERE id=XXX"
```

### Symptom: Port Already in Use

```bash
# Find what's using port 3000
lsof -i :3000

# Kill it
kill -9 <PID>

# Then restart
./scripts/gitea_control.sh start
```

### Nuclear Recovery (Last Resort)

```bash
# 1. Kill EVERYTHING
sudo pkill -9 gitea
pkill -9 act_runner
docker kill $(docker ps -q) 2>/dev/null
docker rm $(docker ps -aq) 2>/dev/null

# 2. Check nothing remains
ps aux | grep -E "(gitea|act_runner)" | grep -v grep
# Should be empty!

# 3. Wait
sleep 10

# 4. Start via systemd (not script)
sudo systemctl start gitea
sleep 5
cd /home/neil1988/gitea && ./act_runner daemon --config runner_config.yaml &

# 5. Verify
./scripts/gitea_control.sh status
```

---

## Windows Runner (If Applicable)

The workflow has a Windows runner job: `[self-hosted, windows, x64]`

If Windows runner exists, it runs separately on Windows, not WSL.
Linux script does NOT manage the Windows runner.

**Check Windows runner:** Look for `act_runner.exe` process in Windows Task Manager.

---

*Document created: 2025-12-28 | Status: IMPLEMENTED | Script: scripts/gitea_control.sh*
*CRITICAL: Always follow safe sequence. Never rush. Verify before and after.*
