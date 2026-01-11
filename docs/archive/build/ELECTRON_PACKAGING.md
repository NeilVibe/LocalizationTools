# Electron Packaging: Path Structure Guide

**Created:** 2025-12-15 | **Reason:** ENOENT bug in v25.1214.2235

---

## Critical: Dev vs Production Paths Are DIFFERENT

This is the #1 cause of "works in dev, breaks in production" bugs.

### The Bug That Bit Us

**v25.1214.2235 failed with:**
```
spawn C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\tools\python\python.exe ENOENT
```

**Why?** Code looked for `tools/python/python.exe` at app root, but electron-builder puts `extraResources` in `resources/` folder.

---

## Path Structure Comparison

### Development Mode (npm run electron:dev)

```
locaNext/
├── electron/
│   ├── main.js          ← Entry point
│   └── preload.js
├── src/                  ← Svelte app
├── node_modules/
└── package.json

../server/               ← Server at sibling level
../tools/                ← Tools at sibling level
```

**In dev, `app.getAppPath()` returns:** `/path/to/locaNext`
**Server path:** `../server` (relative to locaNext)

### Production Mode (installed .exe)

```
C:\Program Files\LocaNext\
├── LocaNext.exe          ← Main executable
├── resources/
│   ├── app.asar          ← Bundled Electron app
│   ├── server/           ← extraResources: server → resources/server
│   └── tools/            ← extraResources: tools → resources/tools
│       └── python/
│           └── python.exe
└── models/               ← Downloaded post-install (NOT in resources)
```

**In prod, `app.getAppPath()` returns:** `C:\Program Files\LocaNext\resources\app.asar`
**Server path:** `resources/server` (NOT `../server`)

---

## The Fix: Use resourcesPath for extraResources

### electron/main.js

```javascript
function getPaths() {
  const isDev = !app.isPackaged;

  if (isDev) {
    // Development: paths relative to locaNext folder
    const appRoot = path.join(__dirname, '..');
    return {
      projectRoot: path.join(appRoot, '..'),
      serverPath: path.join(appRoot, '..', 'server'),
      pythonToolsPath: path.join(appRoot, '..', 'tools'),
      pythonExe: path.join(appRoot, '..', 'tools', 'python', 'python.exe'),
      modelsPath: path.join(appRoot, '..', 'models')
    };
  } else {
    // Production: extraResources are in resources/ folder
    const resourcesPath = path.join(app.getAppPath(), '..');  // ← CRITICAL
    const appRoot = path.join(resourcesPath, '..');
    return {
      projectRoot: appRoot,
      serverPath: path.join(resourcesPath, 'server'),           // resources/server
      pythonToolsPath: path.join(resourcesPath, 'tools'),       // resources/tools
      pythonExe: path.join(resourcesPath, 'tools', 'python', 'python.exe'),
      modelsPath: path.join(appRoot, 'models')  // models at app root (downloaded post-install)
    };
  }
}
```

---

## extraResources in package.json

```json
{
  "build": {
    "extraResources": [
      { "from": "../server", "to": "server" },
      { "from": "../tools", "to": "tools" }
    ]
  }
}
```

**This means:**
- `../server` → copied to `resources/server` (NOT `Playground/server`)
- `../tools` → copied to `resources/tools` (NOT `Playground/tools`)

---

## Path Resolution Cheat Sheet

| What | Dev Path | Prod Path |
|------|----------|-----------|
| `app.getAppPath()` | `/path/to/locaNext` | `C:\...\resources\app.asar` |
| `app.isPackaged` | `false` | `true` |
| Server | `../server` | `resources/server` |
| Python | `../tools/python/python.exe` | `resources/tools/python/python.exe` |
| Models | `../models` | `Playground/models` (at app root) |

---

## Testing Checklist

### Before Release

1. **Build installer:** `npm run build:win` or CI/CD
2. **Install on clean machine** (or Playground folder)
3. **Check paths exist:**
   ```powershell
   # In installed folder
   dir resources\server
   dir resources\tools\python
   ```
4. **Run app and check logs:**
   ```
   %APPDATA%\LocaNext\logs\
   ```
5. **Verify no ENOENT errors**

### Common ENOENT Causes

| Error | Cause | Fix |
|-------|-------|-----|
| `spawn python.exe ENOENT` | Wrong pythonExe path | Use `resourcesPath` not `appRoot` |
| `Cannot find server/main.py` | Wrong serverPath | Use `resourcesPath` not `appRoot` |
| `Model not found` | Looking in wrong place | Models at `appRoot/models`, not `resourcesPath/models` |

---

## Why Models Are Different

Models are NOT in `extraResources` because:
1. They're large (447MB)
2. They're downloaded post-install by first-run setup
3. User may delete and re-download

**So models go to app root (`C:\Program Files\LocaNext\models\`), not `resources/`.**

---

## Debugging Tips

### Add Path Logging

In `main.js`:
```javascript
const paths = getPaths();
logger.info('Resolved paths:', {
  isDev: !app.isPackaged,
  appPath: app.getAppPath(),
  ...paths
});
```

### Check Before Spawn

```javascript
if (!fs.existsSync(paths.pythonExe)) {
  logger.error('Python not found at:', paths.pythonExe);
  logger.error('Expected structure:', fs.readdirSync(path.dirname(paths.pythonExe)));
}
```

---

## Incident Log

| Date | Version | Bug | Root Cause |
|------|---------|-----|------------|
| 2025-12-14 | v25.1214.2235 | ENOENT python.exe | Used `appRoot/tools` instead of `resourcesPath/tools` |

---

*Critical documentation created after first successful build failed on install.*
