# Session Context - Last Working State

**Updated:** 2025-12-15 ~10:05 KST | **By:** Claude

---

## Current Session: P28.5 - CI/CD Infrastructure Hardening

**Status: BUILD RUNNING** | Build v25.1215.0100 (tasks 615, 616)

### Issues Found & Fixed This Session

| ID | Severity | Issue | Root Cause | Fix |
|----|----------|-------|------------|-----|
| INFRA-001 | **CRITICAL** | 706% CPU Terror | Undocumented systemd service with `Restart=always`, no limits | Safe systemd config with limits |
| INFRA-002 | HIGH | Build failed with Node.js syntax error | Systemd service ran in isolated env without NVM | Wrapper script sources NVM |
| INFRA-003 | HIGH | Server stuck at "Creating database tables..." in CI | `.env` file with `override=True` overriding CI env vars | Changed to `override=False` in server/config.py |

### CPU Terror Prevention - APPLIED ✅

Safe systemd service now running:
```ini
[Unit]
StartLimitBurst=3               # Max 3 restarts per 5 min, then STOPS
StartLimitIntervalSec=300
BindsTo=gitea.service           # Runner dies if Gitea dies

[Service]
ExecStartPre=/bin/bash -c 'curl -sf http://localhost:3000/api/v1/version || exit 1'
ExecStart=/home/neil1988/gitea/start_runner_systemd.sh  # Sources NVM for Node.js 20
Restart=on-failure              # NOT always - only restart on actual failures
RestartSec=30
```

**Verification:**
```
$ systemctl is-active gitea-runner.service
active

$ journalctl -u gitea-runner.service -n 5
Now using node v20.18.3 (npm v11.6.0)
Starting act_runner daemon...
task 615 repo is neilvibe/LocaNext
task 616 repo is neilvibe/LocaNext
```

### Key Files Created/Modified

| File | Purpose |
|------|---------|
| `~/gitea/start_runner_systemd.sh` | Wrapper script that sources NVM before starting runner |
| `/etc/systemd/system/gitea-runner.service` | Safe systemd service with restart limits |
| `server/config.py:19` | Changed `override=True` to `override=False` |

---

## Full Build Review - ALL CHECKS PASS ✅

| # | Component | Status | Details |
|---|-----------|--------|---------|
| 1 | win.target | ✅ OK | `"nsis"` |
| 2 | extraResources | ✅ OK | 4 mappings (python, server, tools, version.py) |
| 3 | Electron Paths | ✅ OK | `resourcesPath = app.getAppPath()/..` |
| 4 | dotenv override | ✅ OK | `override=False` (CI env vars win) |
| 5 | NSIS Includes | ✅ OK | 13 files bundled in repo |
| 6 | Error Dialog | ✅ OK | Exit button + setClosable(true) |
| 7 | Runner Service | ✅ OK | Active with safety limits |
| 8 | CPU Terror Prevention | ✅ OK | StartLimitBurst=3, on-failure, BindsTo |

---

## P28: CI/CD Fixed - electron-builder NSIS

**Status: COMPLETE** | First successful build: v25.1214.2235

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Build Tool** | electron-builder 26.x |
| **Installer Format** | NSIS (Nullsoft) |
| **CI/CD Primary** | Gitea Actions (self-hosted, Linux host mode) |
| **CI/CD Secondary** | GitHub Actions (cloud) |

### What Changed

| Component | Before | After |
|-----------|--------|-------|
| Installer tech | Inno Setup (skipped!) | electron-builder NSIS |
| Build output | Portable ZIP (broken) | Setup.exe installer |
| Python bundling | Missing | extraResources config |
| Config location | .iss files | package.json |

---

## Electron Path Structure (CRITICAL)

**Dev Mode:**
```
LocalizationTools/
├── server/main.py          ← serverDir = process.cwd()
├── tools/python/python.exe ← pythonDir = process.cwd()/tools/python
└── version.py
```

**Production (after install):**
```
C:\Users\X\AppData\Local\Programs\LocaNext\
├── LocaNext.exe
└── resources/
    ├── server/main.py      ← serverDir = resources/server
    ├── tools/python/       ← pythonDir = resources/tools/python
    └── version.py
```

**Key Code (electron/main.js:101):**
```javascript
const resourcesPath = path.join(app.getAppPath(), '..');  // resources/
```

---

## CI/CD Code Review - All Sessions

### Session 13 (2025-12-14)
| ID | Issue | Fix |
|----|-------|-----|
| CI-001 to CI-010 | Various NSIS, version, safety-checks issues | All fixed |

### Session 13B (2025-12-15) - Infrastructure
| ID | Issue | Fix |
|----|-------|-----|
| INFRA-001 | 706% CPU (infinite restart) | Safe systemd config with limits |
| INFRA-002 | Node.js syntax error (no NVM in systemd) | Wrapper script with NVM sourcing |
| INFRA-003 | Wrong DB in CI (dotenv override) | `override=False` in config.py |

---

## Build History (Recent)

| Run | Version | Status | Notes |
|-----|---------|--------|-------|
| #263 | v25.1214.2235 | ✅ SUCCESS | First good NSIS build |
| #264-265 | v25.1215.0035-0043 | FAILED | Node.js syntax error (systemd env) |
| #266 | v25.1215.0050 | FAILED | dotenv override (wrong DB) |
| #267 | v25.1215.0100 | ⏳ RUNNING | Full review passed + CPU fix |

---

## P29: Verification Test - PENDING

Need to verify after build #267 succeeds:
1. [ ] Download and install on Windows
2. [ ] App starts standalone
3. [ ] Embedded Python works
4. [ ] Backend server starts correctly
5. [ ] Tools (XLSTransfer, QuickSearch, etc.) work

---

## Quick Commands

```bash
# Check runner status (systemd)
sudo systemctl status gitea-runner.service
sudo journalctl -u gitea-runner.service -n 20

# Check build logs
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -5

# Trigger new build
echo "Build LIGHT v$(TZ='Asia/Seoul' date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

*For full project status, see [Roadmap.md](../../Roadmap.md)*
