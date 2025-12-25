# Gitea Runner Service Setup

**Created:** 2025-12-15 | **Reason:** 706% CPU incident prevention

---

## CRITICAL: NEVER RESTART

**Restarting does NOT solve issues.** ALWAYS follow this workflow:

1. **STOP** everything
2. **CLEAN** resources
3. **INVESTIGATE** root cause
4. **FIX** the actual issue
5. Only **THEN** start fresh

---

## The Problem We're Solving

An undocumented systemd service with `Restart=always` caused 506 restarts and 706% CPU usage.

**Bad (what caused the incident):**
```ini
Restart=always      # Restarts infinitely even if Gitea is down
RestartSec=5        # Every 5 seconds = rapid polling = CPU death
```

---

## The Elegant Solution

Based on [Gitea official documentation](https://docs.gitea.com/usage/actions/act-runner) and [GitLab graceful shutdown practices](https://runbooks.gitlab-static.net/ci-runners/linux/graceful-shutdown/):

### Key Principles

1. **Health check before start** - Don't start runner if Gitea isn't healthy
2. **Graceful shutdown** - Finish current job before stopping (SIGQUIT)
3. **Proper dependency chain** - Runner BINDS to Gitea (stops immediately if Gitea stops)
4. **Restart limits** - Give up after 3 failures, don't spiral

---

## Step 1: Create Gitea Service (if not exists)

```bash
sudo tee /etc/systemd/system/gitea.service << 'EOF'
[Unit]
Description=Gitea Git Server
After=network.target

[Service]
Type=simple
User=neil1988
WorkingDirectory=/home/neil1988/gitea
ExecStart=/home/neil1988/gitea/gitea web

# Restart policy
Restart=on-failure
RestartSec=30
StartLimitBurst=3
StartLimitIntervalSec=300

[Install]
WantedBy=multi-user.target
EOF
```

---

## Step 2: Create Runner Service (Elegant Version)

```bash
sudo tee /etc/systemd/system/gitea-runner.service << 'EOF'
[Unit]
Description=Gitea Actions Runner
Documentation=https://docs.gitea.com/usage/actions/act-runner

# Dependency chain - CRITICAL
After=network.target gitea.service
Requires=gitea.service
# BindsTo is stronger than Requires - stops runner immediately if Gitea stops
BindsTo=gitea.service

# Health check - don't start if Gitea isn't responding
ExecStartPre=/bin/bash -c 'curl -sf http://localhost:3000/api/v1/version || exit 1'

[Service]
Type=simple
User=neil1988
WorkingDirectory=/home/neil1988/gitea
ExecStart=/home/neil1988/gitea/act_runner daemon

# Graceful shutdown - let runner finish current job
# SIGQUIT tells runner to stop accepting new jobs, finish current
KillSignal=SIGQUIT
TimeoutStopSec=3600

# Restart policy - on-failure only, with limits
Restart=on-failure
RestartSec=30
StartLimitBurst=3
StartLimitIntervalSec=300

[Install]
WantedBy=multi-user.target
EOF
```

### Why This Is Elegant (Not Band-Aid)

| Feature | Purpose |
|---------|---------|
| `BindsTo=gitea.service` | Runner stops IMMEDIATELY if Gitea stops (no orphan polling) |
| `ExecStartPre=curl` | Health check - won't even start if Gitea API is down |
| `KillSignal=SIGQUIT` | Graceful shutdown - finishes current job before stopping |
| `TimeoutStopSec=3600` | Allows up to 1 hour to finish current job |
| `Restart=on-failure` | Only restarts on crash, NOT on manual stop or Gitea down |
| `StartLimitBurst=3` | Max 3 restarts in 5 min, then gives up |

---

## Step 3: Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable gitea.service gitea-runner.service
sudo systemctl start gitea.service
# Runner starts automatically due to dependency
```

---

## Management Commands

```bash
# Check status
systemctl status gitea.service gitea-runner.service

# View logs
journalctl -u gitea-runner.service -f

# Graceful stop (finishes current job)
sudo systemctl stop gitea-runner.service

# Check health before troubleshooting
curl -sf http://localhost:3000/api/v1/version && echo "Gitea OK"

# Check restart count (should be low)
systemctl show gitea-runner.service --property=NRestarts
```

---

## How It Prevents 706% CPU

| Scenario | Old (Dangerous) | New (Safe) |
|----------|-----------------|------------|
| Gitea down | Runner keeps restarting every 5s | Runner won't start (health check fails) |
| Gitea stops | Runner keeps trying | Runner stops immediately (BindsTo) |
| Runner crashes | Restarts infinitely | Max 3 restarts, then stops |
| Manual stop | Might restart | Stays stopped (on-failure only) |
| Long-running job | Killed immediately | Gets 1 hour to finish (SIGQUIT) |

---

## Verification

```bash
# Test 1: Health check works
sudo systemctl stop gitea.service
sudo systemctl start gitea-runner.service
# Should fail with "ExecStartPre failed"

# Test 2: BindsTo works
sudo systemctl start gitea.service
sudo systemctl start gitea-runner.service
# Both running
sudo systemctl stop gitea.service
# Both should stop

# Test 3: Restart limit works
# Kill runner 4 times in 5 minutes
pkill -9 -f "act_runner daemon"
# After 3rd: "Start request repeated too quickly"
```

---

## Sources

- [Gitea Act Runner Documentation](https://docs.gitea.com/usage/actions/act-runner)
- [GitHub Issue #26205: Add systemd service example](https://github.com/go-gitea/gitea/issues/26205)
- [GitLab Runner Graceful Shutdown](https://runbooks.gitlab-static.net/ci-runners/linux/graceful-shutdown/)

---

*Created after 706% CPU incident. No resource limits needed - proper dependency management is the elegant solution.*
