# Auto-Update System

**Last Updated:** 2025-12-27 | **Status:** WORKING | **Verified:** Build 408-409

---

## How It Works

```
LocaNext.exe (Build 408)                    Gitea Server
       │                                         │
       │  1. Check for updates                   │
       │──────────────────────────────────────►  │
       │     GET /releases/download/latest/      │
       │         latest.yml                      │
       │                                         │
       │  2. Compare versions                    │
       │◄──────────────────────────────────────  │
       │     version: 25.1227.2331 (Build 409)   │
       │                                         │
       │  3. If newer → Download .exe            │
       │──────────────────────────────────────►  │
       │                                         │
       │  4. Install on next restart             │
       └─────────────────────────────────────────┘
```

---

## Configuration

**File:** `locaNext/electron/updater.js`

```javascript
// Default: Gitea (internal server)
const UPDATE_SERVER = process.env.UPDATE_SERVER || 'gitea';
const GITEA_URL = process.env.GITEA_URL || 'http://172.28.150.120:3000';

autoUpdaterConfig = {
  provider: 'generic',
  url: `${GITEA_URL}/neilvibe/LocaNext/releases/download/latest`,
};
```

**URL checked:** `http://172.28.150.120:3000/neilvibe/LocaNext/releases/download/latest/latest.yml`

---

## The ESM Bug Fix (Build 408)

**File:** `locaNext/electron/main.js`

### Before (Broken)

```javascript
const { autoUpdater: updater } = await import('electron-updater');
autoUpdater = updater;  // updater = undefined!!!
```

**Why broken:** `electron-updater` is CommonJS. When ESM imports CJS, it wraps in `{ default: module }`. Destructuring `{ autoUpdater }` gets `undefined`.

### After (Fixed)

```javascript
const electronUpdater = await import('electron-updater');
autoUpdater = electronUpdater.default?.autoUpdater || electronUpdater.autoUpdater;
```

**Why works:** Import whole module, then access `.default.autoUpdater` (ESM wrapper) or `.autoUpdater` (direct).

**Reference:** https://github.com/electron-userland/electron-builder/issues/7976

---

## First-Run Flag Location

**File:** `locaNext/electron/first-run-setup.js`

### Problem

NSIS installer deletes old installation during updates. Flag file in install folder gets deleted.

### Solution

Store flag in `%APPDATA%\LocaNext\` which survives installations.

```javascript
function getFlagFilePath() {
  const appDataPath = app.getPath('userData');  // %APPDATA%/LocaNext
  return path.join(appDataPath, 'first_run_complete.flag');
}
```

---

## Log Messages

Check these in `logs/locanext_app.log`:

| Log | Meaning |
|-----|---------|
| `electron-updater loaded successfully {"hasAutoUpdater":true}` | ESM fix works |
| `Auto-updater check {"autoUpdaterLoaded":true}` | Updater initialized |
| `Setting up auto-updater {"config":{...}}` | Config applied |
| `Update available {"version":"X.X.X"}` | Newer version detected |
| `Update downloaded {"version":"X.X.X"}` | Ready to install |

---

## Testing Auto-Update

### Prerequisites

1. Build N installed on Playground
2. Build N+1 available on Gitea

### Steps

```bash
# 1. Check installed version
cat "/mnt/c/.../Playground/LocaNext/resources/version.json"

# 2. Check Gitea latest version
curl -s "http://172.28.150.120:3000/neilvibe/LocaNext/releases/download/latest/latest.yml" | head -3

# 3. Launch app
powershell.exe -c "Start-Process 'C:\...\LocaNext.exe'"

# 4. Check logs for update detection
grep -E "(Update available|Update downloaded)" /mnt/c/.../logs/locanext_app.log
```

---

## CI/CD Integration

The build workflow automatically:

1. Creates release with version tag (e.g., `v25.1227.2331`)
2. Uploads `latest.yml` + `.exe` + `.blockmap`
3. Updates `latest` tag to point to new release

**Workflow file:** `.gitea/workflows/build.yml`

---

## Troubleshooting

### No update detected

1. Check Gitea has newer version: `curl .../latest/latest.yml`
2. Check logs for `hasAutoUpdater: true`
3. If `hasAutoUpdater: false` → ESM bug not fixed

### First-run shows every launch

1. Check `%APPDATA%\LocaNext\first_run_complete.flag` exists
2. If missing after update → flag location not fixed

### Update downloads but won't install

1. Check Windows Defender isn't blocking
2. Check app has write permission to install folder

---

## Version History

| Build | Change |
|-------|--------|
| 405 | First-run flag moved to AppData |
| 407 | Debug logging added |
| 408 | ESM import fix for electron-updater |
| 409 | Verified auto-update working |

---

*Auto-update system verified working 2025-12-27*
