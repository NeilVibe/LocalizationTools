# WSL Interop & SSH Reliability

**Status:** Working (auto-fixed by systemd service)
**Source:** CheckComputer project solutions

---

## Quick Reference

```bash
# Check interop status
ls /proc/sys/fs/binfmt_misc/WSLInterop && echo "OK" || echo "BROKEN"

# Test interop
cmd.exe /c echo "Works!"

# Manual fix (if broken, no restart needed)
sudo sh -c 'echo ":WSLInterop:M::MZ::/init:PF" > /proc/sys/fs/binfmt_misc/register'
```

---

## Problem 1: WSL Interop Breaks Randomly

**Symptom:**
```
/bin/bash: cmd.exe: cannot execute binary file: Exec format error
```

**Cause:** `WSLInterop` handler disappears from `/proc/sys/fs/binfmt_misc/`

### Solution: Systemd Auto-Fix Service

Create `/etc/systemd/system/wsl-interop-fix.service`:

```ini
[Unit]
Description=Ensure WSL Interop is registered
After=systemd-binfmt.service
Before=multi-user.target

[Service]
Type=oneshot
ExecCondition=/bin/sh -c '[ ! -f /proc/sys/fs/binfmt_misc/WSLInterop ]'
ExecStart=/bin/sh -c 'echo ":WSLInterop:M::MZ::/init:PF" > /proc/sys/fs/binfmt_misc/register'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable wsl-interop-fix.service
sudo systemctl start wsl-interop-fix.service
```

**How it works:**
- Runs at boot after `systemd-binfmt.service`
- `ExecCondition` checks if WSLInterop is missing
- If missing, registers the handler
- If already exists, skips (no-op)

### The Magic String Explained

```
:WSLInterop:M::MZ::/init:PF
```

| Part | Meaning |
|------|---------|
| `WSLInterop` | Handler name |
| `M` | Match by magic bytes |
| `MZ` | DOS/Windows executable magic bytes |
| `/init` | WSL's init handles execution |
| `PF` | Flags: Preserve argv[0], Fix binary |

---

## Problem 2: WSL Not Starting Reliably on Boot

**Symptom:** SSH not available after Windows boot

### Solution: Elegant Startup Task

Create `C:\Users\MYCOM\wsl-startup.cmd`:
```batch
@echo off
REM Elegant WSL startup - waits for systemd to fully initialize
wsl.exe -d Ubuntu2 --exec /usr/bin/systemctl is-system-running --wait
```

**Why this works:**
- `systemctl is-system-running --wait` blocks until systemd reaches stable state
- SSH and all systemd services are running when it exits

**Task Scheduler settings:**
| Setting | Value |
|---------|-------|
| Name | WSL-SSH-Startup |
| Trigger | At logon |
| Delay | 10 seconds |
| Run Level | Highest |
| Action | `C:\Users\MYCOM\wsl-startup.cmd` |

---

## Problem 3: SSH Dies While Away

### Solution: SSH Watchdog (Windows Task)

Script: `scripts/wsl_ssh_watchdog.ps1`

**Features:**
- Checks SSH every 5 minutes
- Auto-restarts WSL if SSH not responding
- Safety limit: max 3 restarts per hour (prevents death loops)

**Install as Task:**
1. Task Scheduler > Create Basic Task: "WSL SSH Watchdog"
2. Trigger: At startup + Repeat every 5 minutes
3. Action: `powershell.exe -ExecutionPolicy Bypass -File "D:\LocalizationTools\scripts\wsl_ssh_watchdog.ps1"`
4. Run whether user is logged on or not

---

## WSL Config

Ensure `/etc/wsl.conf` has:
```ini
[boot]
systemd=true

[interop]
enabled=true
appendWindowsPath=true
```

---

## Verification Commands

```bash
# Check interop service
systemctl status wsl-interop-fix.service

# Check interop working
cat /proc/sys/fs/binfmt_misc/WSLInterop

# Check SSH running
systemctl status ssh

# Test full chain
cmd.exe /c echo "Interop OK" && echo "All working!"
```

---

## Troubleshooting

### Interop still broken after boot
```bash
journalctl -u wsl-interop-fix.service
sudo systemctl start wsl-interop-fix.service
```

### SSH not starting
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

### Need to restart WSL remotely
From Windows (kills SSH connection):
```cmd
wsl --shutdown
wsl -d Ubuntu2
```

---

## Files Reference

| File | Location | Purpose |
|------|----------|---------|
| `wsl-interop-fix.service` | `/etc/systemd/system/` | Auto-fix interop at boot |
| `wsl-startup.cmd` | `C:\Users\MYCOM\` | Startup script (waits for systemd) |
| `wsl_ssh_watchdog.ps1` | `scripts/` | Keep SSH alive |
| `WSL-SSH-Startup` | Task Scheduler | Triggers startup on logon |

---

## Full Documentation

For complete details, see CheckComputer project:
- `/home/neil1988/CheckComputer/docs/WSL-AUTOSTART-AND-INTEROP-FIX.md`
- `/home/neil1988/CheckComputer/docs/WSL-WINDOWS-INTEGRATION.md`

---

*Last updated: 2025-12-19*
