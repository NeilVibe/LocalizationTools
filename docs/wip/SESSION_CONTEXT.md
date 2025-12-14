# Session Context - Last Working State

**Updated:** 2025-12-15 ~09:55 KST | **By:** Claude

---

## Current Session: P28.5 - CI/CD Infrastructure Hardening

**Status: IN PROGRESS** | Build v25.1215.0050 running

### Issues Found & Fixed This Session

| ID | Severity | Issue | Root Cause | Fix |
|----|----------|-------|------------|-----|
| INFRA-001 | **CRITICAL** | 706% CPU Terror | Undocumented systemd service with `Restart=always`, no limits | Removed; created safe service config |
| INFRA-002 | HIGH | Build failed with Node.js syntax error | Systemd service ran in isolated env without NVM | Reverted to manual `start_runner.sh` (inherits NVM) |
| INFRA-003 | HIGH | Server stuck at "Creating database tables..." in CI | `.env` file with `override=True` overriding CI env vars | Changed to `override=False` in server/config.py |

### Session 13B: CI/CD Infrastructure Review (COMPLETE)

**What happened:**
1. User reported computer overheating - 706% CPU from Gitea
2. Found undocumented systemd service restarting 506 times
3. Created proper systemd service with safeguards BUT it broke builds
4. Root cause: systemd runs in isolated environment without NVM/Node.js 20
5. Fix: Reverted to manual script, created wrapper for future systemd use
6. During testing, found `.env` override bug breaking CI database connection

**Key Files:**
- `~/gitea/start_runner.sh` - Original manual script (WORKING)
- `~/gitea/start_runner_systemd.sh` - Wrapper with NVM (READY for future use)
- `/etc/systemd/system/gitea-runner.service` - Disabled (needs wrapper)
- `server/config.py:19` - Changed `override=True` to `override=False`

### CPU Terror Prevention (PENDING APPLY after build)

Safe systemd service design:
```ini
[Unit]
StartLimitBurst=3               # Max 3 restarts...
StartLimitIntervalSec=300       # ...per 5 minutes, then STOP
BindsTo=gitea.service           # Dies if Gitea dies

[Service]
ExecStartPre=/bin/bash -c 'curl -sf http://localhost:3000/api/v1/version || exit 1'
ExecStart=/home/neil1988/gitea/start_runner_systemd.sh  # Sources NVM
Restart=on-failure              # NOT always
RestartSec=30
```

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

### Files Modified

1. **locaNext/package.json**
   - `win.target`: "dir" → "nsis"
   - Added `nsis` config block
   - Expanded `extraResources` for Python + server

2. **.gitea/workflows/build.yml**
   - Removed Inno Setup steps
   - NSIS includes bundled in repo (no downloads)
   - Fixed safety-checks conditions

3. **locaNext/electron/main/index.ts**
   - Fixed path resolution: `resourcesPath = path.join(app.getAppPath(), '..')`
   - Production: files in `resources/` folder
   - Dev: files at project root

4. **locaNext/electron/main/first-run-setup.ts**
   - Added NSIS installer details display
   - Fixed error dialog (Exit button, closable)

5. **server/config.py**
   - `override=True` → `override=False` (CI env vars take precedence)

6. **installer/nsis-includes/*.nsh** - 11 NSIS files bundled in repo

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

**Key Code (main/index.ts):**
```typescript
const resourcesPath = app.isPackaged
  ? path.join(app.getAppPath(), '..')  // resources/
  : process.cwd();                      // project root
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

| Run | Version | Status | Issue |
|-----|---------|--------|-------|
| #263 | v25.1214.2235 | ✅ SUCCESS | First good NSIS build |
| #264-265 | v25.1215.0035-0043 | FAILED | Node.js syntax error (systemd env) |
| #266 | v25.1215.0050 | RUNNING | Fixed dotenv override |

---

## P29: Verification Test - PENDING

Need to verify after successful build:
1. [ ] Download and install on Windows
2. [ ] App starts standalone
3. [ ] Embedded Python works
4. [ ] Backend server starts correctly
5. [ ] Tools (XLSTransfer, QuickSearch, etc.) work

---

## Documentation Created This Session

| Document | Purpose |
|----------|---------|
| `docs/cicd/RUNNER_SERVICE_SETUP.md` | Safe systemd service configuration |
| `docs/build/ELECTRON_PACKAGING.md` | Dev vs Prod path structure |
| `docs/troubleshooting/GITEA_SAFETY_PROTOCOL.md` | 706% CPU incident documentation |
| `docs/code-review/CODE_REVIEW_TYPES.md` | CI/CD Code vs Infrastructure review types |

---

## Quick Commands

```bash
# Check build logs
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -5
tail -50 ~/gitea/data/actions_log/neilvibe/LocaNext/XX/YYY.log

# Check runner status
tail -f /tmp/act_runner.log

# Trigger new build
echo "Build LIGHT v$(TZ='Asia/Seoul' date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

*For full project status, see [Roadmap.md](../../Roadmap.md)*
