# Gitea Safety Protocol

**Created:** 2025-12-14 | **Reason:** Gitea CPU spinout incident (706% CPU)

---

## The Incident

Gitea consumed 706% CPU (7 cores) because:

**ROOT CAUSE: systemd service with `Restart=always`**

```
/etc/systemd/system/gitea-runner.service
Restart=always
RestartSec=5
restart counter: 506  ← RESTARTED 506 TIMES!
```

The runner kept restarting every 5 seconds, polling Gitea constantly even with NO build running.

Contributing factors:
1. Rapid API calls to delete releases/tags
2. Two IPs polling (Windows + WSL)
3. No Gitea service running but runner kept trying to connect

---

## The Fix

### Option 1: Remove Dangerous Service (Quick Fix)
```bash
# Remove the dangerous undocumented service
sudo systemctl stop gitea-runner.service
sudo systemctl disable gitea-runner.service
sudo rm /etc/systemd/system/gitea-runner.service
sudo systemctl daemon-reload
```

Then use manual scripts: `~/gitea/start_runner.sh`

### Option 2: Safe systemd Service (RECOMMENDED)

Create a SAFE service with proper limits:

```bash
sudo tee /etc/systemd/system/gitea-runner.service << 'EOF'
[Unit]
Description=Gitea Actions Runner
After=gitea.service network.target
Requires=gitea.service
PartOf=gitea.service

[Service]
Type=simple
User=neil1988
WorkingDirectory=/home/neil1988/gitea
ExecStart=/home/neil1988/gitea/act_runner daemon
Restart=on-failure          # NOT "always"
RestartSec=30               # 30 second cooldown
StartLimitBurst=3           # Max 3 restarts in 5 min
StartLimitIntervalSec=300
CPUQuota=100%
MemoryMax=512M

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable gitea-runner.service
sudo systemctl start gitea-runner.service
```

**Full guide:** [RUNNER_SERVICE_SETUP.md](RUNNER_SERVICE_SETUP.md)

---

## Safety Rules

### 1. Before Gitea API Operations

```bash
# Check Gitea CPU before any operations
ps aux | grep gitea | grep -v grep | awk '{print "Gitea CPU: " $3 "%"}'
```

If CPU > 20%, wait or restart Gitea first.

### 2. Rate Limit API Calls

**NEVER** do rapid loops. Add delays:

```bash
# BAD - rapid fire
for id in 1 2 3 4 5; do
  curl -X DELETE ".../releases/$id"
done

# GOOD - with delay
for id in 1 2 3 4 5; do
  curl -X DELETE ".../releases/$id"
  sleep 1  # Rate limit
done
```

### 3. After Canceling a Build

Stop the act_runner to prevent polling loop:

```bash
# Find and kill act_runner
pkill -f "act_runner"

# Or gracefully
killall act_runner
```

### 4. After Any Gitea Operations

Check system health:

```bash
# Quick health check
ps aux --sort=-%cpu | head -5
```

### 5. Restart Gitea Safely

```bash
# Kill if running
pkill -f "gitea web"

# Wait
sleep 2

# Start fresh
cd ~/gitea && ./gitea web &

# Verify CPU is normal
sleep 5 && ps aux | grep gitea | grep -v grep | awk '{print "CPU: " $3 "%"}'
```

---

## Emergency: Kill Runaway Gitea

```bash
# Nuclear option
pkill -9 -f gitea

# Also kill runners
pkill -9 -f act_runner

# Check
ps aux | grep -E "gitea|act_runner" | grep -v grep
```

---

## Signs of Trouble

| Symptom | Likely Cause |
|---------|--------------|
| CPU > 50% | Runner polling loop |
| Memory climbing | Stuck webhook/action |
| FetchTask spam in logs | Runner can't find task |

---

## Resource Optimization: On-Demand Gitea

Gitea uses ~7% CPU even when idle (background tasks, Go runtime). To save resources, run Gitea only when needed:

```bash
# START Gitea + Runner (before commit/push/build)
cd ~/gitea && GOGC=200 ./gitea web > /tmp/gitea.log 2>&1 &
sleep 3 && ./act_runner daemon --config runner_config.yaml > /tmp/act_runner.log 2>&1 &

# STOP Gitea + Runner (when done)
pkill -f "act_runner" && sleep 2 && pkill -f "gitea web"
```

| When to START | When to STOP |
|---------------|--------------|
| Before `git push gitea main` | After build completes |
| Before triggering CI builds | When done pushing for the day |

---

*Documented after incident that nearly killed the user's computer.*
