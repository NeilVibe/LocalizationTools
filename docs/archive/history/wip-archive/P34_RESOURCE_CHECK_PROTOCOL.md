# P34: Resource Check Protocol

**Purpose:** Document resource zombies, parasites, and establish cleanup protocols
**Created:** 2025-12-16
**Status:** Investigation Complete - Implementation Pending

---

## Executive Summary

Investigation of system resource consumption revealed multiple zombie processes consuming ~14+ GB RAM, primarily from:
1. **External projects** with auto-starting services (2.4GB+ from WebTranslator alone)
2. **Gitea systemd services** auto-starting on boot
3. **Manual dev server startups** that persist after sessions

This document establishes a resource monitoring protocol and remediation plan.

---

## Zombie Identification

### External to LocaNext (NOT our codebase)

| Process | Source | Memory | CPU | Root Cause |
|---------|--------|--------|-----|------------|
| **Gunicorn x3** | `/home/neil1988/WebTranslator` | ~2.4 GB | Low | `webtranslator.service` (disabled but ran) |
| **Nest.js x2** | `/home/neil1988/CityEmpire/backend` | ~600 MB | Low | Manual `npm run dev` never stopped |
| **Gitea** | `/home/neil1988/gitea` | 260 MB | 36% | `gitea.service` ENABLED (auto-start) |

### Systemd Services Found

```
/etc/systemd/system/gitea.service         - ENABLED (auto-starts)
/etc/systemd/system/gitea-runner.service  - ENABLED (auto-starts)
/etc/systemd/system/webtranslator.service - disabled but was running
```

---

## LocaNext Issues Found

### ISSUE-R01: stop_all_servers.sh Incomplete Cleanup

**File:** `scripts/stop_all_servers.sh`

**Problem:** Script only kills processes on ports 8888, 3000, 5175. Does NOT:
- Kill orphan Vite processes on other ports (5173, 5174)
- Kill any Node processes left from `npm run dev`
- Detect leftover Python processes

**Current Code:**
```bash
declare -A SERVERS=(
    [8888]="Backend API"
    [3000]="Gitea"
    [5175]="Admin Dashboard"
)
```

**Missing Ports:**
- 5173 (locaNext Vite dev)
- 5174 (adminDashboard default)

---

### ISSUE-R02: Admin Dashboard Port Mismatch

**Problem:** Port configuration inconsistency

| Location | Port |
|----------|------|
| `adminDashboard/package.json` | 5174 |
| `scripts/start_all_servers.sh` | 5175 |
| `scripts/check_servers.sh` | 5175 |
| `scripts/stop_all_servers.sh` | 5175 |

**Risk:** If user runs `cd adminDashboard && npm run dev`, it starts on 5174. Scripts check/stop 5175.

---

### ISSUE-R03: No Zombie Detection Script

**Problem:** No script exists to detect and report resource zombies.

**Need:** A script that:
1. Lists all processes owned by user
2. Identifies common dev zombies (node, python, gunicorn, gitea)
3. Shows memory usage
4. Offers cleanup options

---

### ISSUE-R04: Gitea Auto-Start May Not Be Desired

**Problem:** Gitea services are enabled and auto-start on WSL/system boot.

**Commands to check:**
```bash
systemctl is-enabled gitea.service         # enabled
systemctl is-enabled gitea-runner.service  # enabled
```

**Impact:** 260MB+ RAM + continuous CPU usage even when not doing CI/CD work.

**User Decision Required:** Keep auto-start or disable?

---

### ISSUE-R05: No WebSocket Cleanup on Server Shutdown

**File:** `server/main.py` lifespan handler

**Problem:** The shutdown sequence disconnects Redis but doesn't explicitly close WebSocket connections.

**Current shutdown code (lines 104-113):**
```python
# === SHUTDOWN ===
logger.info("Server shutting down...")

# Disconnect Redis cache
try:
    await cache.disconnect()
except Exception as e:
    logger.warning(f"Redis disconnect error: {e}")

logger.success("Server shutdown complete")
```

**Missing:** No `socket_manager.disconnect_all()` or similar.

---

### ISSUE-R06: No Resource Monitoring Documentation

**Problem:** No documentation exists for:
- Expected memory usage per component
- How to identify resource leaks
- Regular cleanup procedures

---

## Clean Codebase Confirmation

**LocaNext server code is clean:**
- No subprocess spawning in server code
- No background daemons launched
- Proper lifespan management with asynccontextmanager
- Celery tasks defined but not auto-running (requires Celery Beat)

**The zombies are all from EXTERNAL sources.**

---

## Recommended Fixes

### Quick Fix: Disable External Auto-Starts

```bash
# Disable Gitea auto-start (run when not needed)
sudo systemctl disable gitea.service
sudo systemctl disable gitea-runner.service

# Stop current Gitea processes
sudo systemctl stop gitea.service gitea-runner.service

# Or use stop script
./scripts/stop_all_servers.sh
```

### Script Enhancement: Resource Check Script

Create `scripts/check_resources.sh`:
```bash
#!/bin/bash
# Resource zombie detector

echo "=== Resource Check ==="

echo -e "\n--- Node.js processes ---"
pgrep -a node || echo "None"

echo -e "\n--- Python processes ---"
pgrep -af python | grep -v "grep" || echo "None"

echo -e "\n--- Ports in use ---"
ss -tlnp 2>/dev/null | grep -E ":(3000|5001|5173|5174|5175|8888)" || echo "None"

echo -e "\n--- High memory processes (>100MB) ---"
ps aux --sort=-%mem | head -20 | awk '$6 > 100000 {print $11, $6/1024"MB"}'

echo -e "\n--- Systemd services (user) ---"
systemctl list-units --type=service --state=running | grep -E "gitea|web" || echo "None"
```

### Script Enhancement: Nuclear Cleanup

Create `scripts/kill_all_dev.sh`:
```bash
#!/bin/bash
# Kill ALL dev processes (use with caution)

echo "Killing all Node.js processes..."
pkill -f node || true

echo "Killing Python on common dev ports..."
for port in 5001 8888; do
    kill $(lsof -t -i:$port) 2>/dev/null || true
done

echo "Stopping Gitea..."
sudo systemctl stop gitea gitea-runner 2>/dev/null || true

echo "Done. Run './scripts/check_servers.sh' to verify."
```

---

## Action Items

| ID | Task | Priority | Status |
|----|------|----------|--------|
| R01 | Update stop_all_servers.sh to include all dev ports | Medium | Pending |
| R02 | Fix admin dashboard port mismatch | Low | Pending |
| R03 | Create check_resources.sh script | High | Pending |
| R04 | Document Gitea auto-start decision | Medium | User Decision |
| R05 | Add WebSocket cleanup to shutdown | Low | Pending |
| R06 | Create resource monitoring doc | Low | Pending |

---

## Prevention Protocol

### Daily Development Start
```bash
# 1. Check for zombies
./scripts/check_resources.sh

# 2. If zombies found, clean up
./scripts/kill_all_dev.sh  # or manual cleanup

# 3. Start only what you need
./scripts/start_all_servers.sh
```

### End of Day
```bash
# Stop all servers
./scripts/stop_all_servers.sh

# Verify cleanup
./scripts/check_resources.sh
```

### Weekly
- Review WSL memory with `free -h`
- Check for new zombie types
- Review systemd services

---

## Technical Details

### WebTranslator Service (The 2.4GB Zombie)

**Service file:** `/etc/systemd/system/webtranslator.service`
```ini
[Unit]
Description=Web Translator Gunicorn service
After=network.target

[Service]
User=neil1988
Group=neil1988
WorkingDirectory=/home/neil1988/WebTranslator
Environment="PATH=/home/neil1988/WebTranslator/venv/bin"
ExecStart=/home/neil1988/WebTranslator/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5001 --timeout 1800 --graceful-timeout 300 --keep-alive 65 --max-requests 1000 --max-requests-jitter 50 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**Why 2.4GB?** 3 workers x ~800MB each = 2.4GB. Each Gunicorn worker forks the entire Python process.

### Gitea Service

**Service file:** `/etc/systemd/system/gitea.service`
```ini
[Unit]
Description=Gitea Git Server
After=network.target

[Service]
Type=simple
User=neil1988
WorkingDirectory=/home/neil1988/gitea
ExecStart=/home/neil1988/gitea/gitea web
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

**Why auto-starts?** `WantedBy=multi-user.target` + enabled = starts on boot.

---

## Related Documents

- [SERVER_MANAGEMENT.md](../development/SERVER_MANAGEMENT.md) - Server start/stop procedures
- [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) - Known bugs (not resource-related)
- [P33_OFFLINE_MODE_CI_OVERHAUL.md](P33_OFFLINE_MODE_CI_OVERHAUL.md) - CI/CD setup (uses Gitea)

---

*Created: 2025-12-16 | Investigation by Claude Code*
