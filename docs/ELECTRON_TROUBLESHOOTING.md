# Electron Troubleshooting Guide

**Last Updated:** 2025-12-05
**Purpose:** Debug protocol for Electron desktop app issues

---

## Quick Debug Protocol

```
1. KILL app cleanly: taskkill /F /IM LocaNext.exe
2. CLEAR logs: rm -f logs/*.log
3. LAUNCH app fresh
4. CHECK logs: cat logs/locanext_app.log | tail -60
5. IDENTIFY errors in [Renderer ERROR] lines
6. FIX source code
7. COPY to Windows: cp file /mnt/c/Users/.../resources/app/...
8. REPEAT until clean
```

---

## Common Issues & Fixes

### 1. Black Screen (Frontend Not Rendering)

**Symptoms:**
- App window opens but shows black/blank screen
- Logs show "Main window ready and visible" but user sees nothing
- Backend works, health check passes

**Root Causes Found (2025-12-05):**

#### Cause A: Preload Script ES Module Error
```
[Renderer] PRELOAD ERROR | SyntaxError: Cannot use import statement outside a module
```

**Fix:** Convert preload.js from ES modules to CommonJS:
```javascript
// WRONG (ES Modules - doesn't work in sandboxed preload)
import { contextBridge, ipcRenderer } from 'electron';

// CORRECT (CommonJS - required for sandbox)
const { contextBridge, ipcRenderer } = require('electron');
```

**Why:** Electron's sandboxed preload scripts don't support ES modules.

#### Cause B: SvelteKit Absolute Paths
```
[Renderer ERROR] | Failed to fetch dynamically imported module: file:///C:/_app/immutable/entry/start.xxx.js
```

**Fix:** Post-process build output to use relative paths:
```bash
# In build/index.html, change:
# href="/_app/..." → href="./_app/..."
# import("/_app/...") → import("./_app/...")

cd locaNext/build
sed -i 's|href="/_app/|href="./_app/|g; s|import("/_app/|import("./_app/|g; s|href="/favicon|href="./favicon|g' index.html
```

**Why:** Electron uses `file://` protocol. Absolute paths like `/_app/` resolve to `C:/_app/` on Windows, which doesn't exist.

---

### 2. Missing Preload API (appendLog)

**Symptoms:**
```
[Renderer ERROR] | TypeError: window.electron.appendLog is not a function
```

**Root Cause:** Frontend logger calls `window.electron.appendLog()` but preload.js doesn't expose it.

**Fix:** Add to `preload.js`:
```javascript
// In contextBridge.exposeInMainWorld('electron', {...})
appendLog: (params) => ipcRenderer.invoke('append-log', params)
```

And add IPC handler to `main.js`:
```javascript
ipcMain.handle('append-log', async (event, { logPath, message }) => {
  const fullPath = path.join(paths.projectRoot, logPath);
  const logDir = path.dirname(fullPath);
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  fs.appendFileSync(fullPath, message + '\n', 'utf8');
  return { success: true };
});
```

---

### 3. Database Table Not Found

**Symptoms:**
```
sqlite3.OperationalError: no such table: users
```

**Root Cause:** `dependencies.py` creates engine but doesn't call `create_all()` to make tables.

**Fix:** In `server/utils/dependencies.py`, add table creation:
```python
from server.database.db_setup import initialize_database as init_db_tables

def initialize_database():
    global _engine, _session_maker
    if _engine is None:
        _engine = create_database_engine(...)
        _session_maker = get_session_maker(_engine)
        # CREATE TABLES!
        init_db_tables(_engine)
```

---

### 4. Backend Health Check Timeout

**Symptoms:**
```
Backend not ready after 30 seconds
Health check failed - never received response
```

**Root Causes:**

#### Cause A: localhost vs 127.0.0.1
Windows may resolve `localhost` to IPv6 (`::1`) while Python binds to IPv4 (`127.0.0.1`).

**Fix:** Use `127.0.0.1` explicitly everywhere:
```javascript
// In main.js
const BACKEND_URL = 'http://127.0.0.1:8888';
```

#### Cause B: Python Firewall Popup
If Python binds to `0.0.0.0`, Windows shows firewall popup blocking startup.

**Fix:** Bind to `127.0.0.1` only:
```python
# In server/main.py
uvicorn.run(app, host="127.0.0.1", port=8888)
```

---

### 3. Preload Errors

**How to capture preload errors:**
Add this to main.js in createMainWindow():
```javascript
mainWindow.webContents.on('preload-error', (event, preloadPath, error) => {
  logger.error('[Renderer] PRELOAD ERROR', {
    preloadPath,
    error: error.message,
    stack: error.stack
  });
});
```

**Common fixes:**
- Use `require()` not `import`
- Check that preload path exists
- Ensure sandbox mode is compatible

---

## Renderer Logging (Add to main.js)

Add comprehensive renderer logging to capture frontend errors:

```javascript
// ==================== RENDERER LOGGING ====================
// Capture ALL console output from the frontend (Svelte)
mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
  const levelMap = { 0: 'DEBUG', 1: 'INFO', 2: 'WARNING', 3: 'ERROR' };
  const levelName = levelMap[level] || 'LOG';
  logger.info(`[Renderer ${levelName}]`, { message, line, source: sourceId });
});

mainWindow.webContents.on('did-start-loading', () => {
  logger.info('[Renderer] Page started loading');
});

mainWindow.webContents.on('did-finish-load', () => {
  logger.success('[Renderer] Page finished loading');
});

mainWindow.webContents.on('dom-ready', () => {
  logger.info('[Renderer] DOM ready');
});

mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
  logger.error('[Renderer] FAILED TO LOAD', {
    errorCode,
    errorDescription,
    url: validatedURL
  });
});

mainWindow.webContents.on('preload-error', (event, preloadPath, error) => {
  logger.error('[Renderer] PRELOAD ERROR', {
    preloadPath,
    error: error.message,
    stack: error.stack
  });
});
```

---

## Log File Locations

| Log | Path | Contains |
|-----|------|----------|
| App Log | `logs/locanext_app.log` | Main + backend + renderer logs |
| Error Log | `logs/locanext_error.log` | Errors only |
| Backend Log | Console output from Python | Server startup, API calls |

---

## Testing Protocol

```bash
# 1. Kill all processes
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
/mnt/c/Windows/System32/taskkill.exe /F /IM python.exe

# 2. Clear old logs
rm -f "/mnt/c/Users/MYCOM/Desktop/LocaNext/logs/"*.log

# 3. Copy fixed files
cp locaNext/electron/preload.js "/mnt/c/Users/.../resources/app/electron/preload.js"
cp -r locaNext/build "/mnt/c/Users/.../resources/app/build"
cp locaNext/electron/main.js "/mnt/c/Users/.../resources/app/electron/main.js"

# 4. Launch app
/mnt/c/Windows/System32/cmd.exe /c "start C:\...\LocaNext.exe"

# 5. Wait and check logs
sleep 15
cat "/mnt/c/Users/.../Desktop/LocaNext/logs/locanext_app.log" | tail -50

# 6. Look for SUCCESS markers:
#    - "LocaNext preload script loaded" ✓
#    - "[Renderer] DOM ready" ✓
#    - "[Renderer] Page finished loading" ✓
#    - "Component: Login - mounted" ✓
```

---

## Success Indicators

When everything is working, logs should show:
```
[Renderer INFO] | {"message":"LocaNext preload script loaded"...}
[Renderer] DOM ready
[Renderer] Page finished loading
Main window ready and visible
[Renderer INFO] | {"message":"Component: Layout - mounted"...}
[Renderer INFO] | {"message":"Component: Login - mounted"...}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `electron/preload.js` | Bridge between main and renderer - MUST use CommonJS |
| `electron/main.js` | Main process, window creation, backend management |
| `build/index.html` | SvelteKit output - check for absolute vs relative paths |
| `svelte.config.js` | SvelteKit config - `paths.relative: true` helps but not complete |
| `vite.config.js` | Vite config - `base: './'` for relative assets |

---

## SvelteKit + Electron Path Fix

Since SvelteKit doesn't fully support relative paths for dynamic imports, post-process the build:

```bash
# Add to build script or run after npm run build:
cd locaNext/build
sed -i 's|href="/_app/|href="./_app/|g; s|import("/_app/|import("./_app/|g; s|href="/favicon|href="./favicon|g' index.html
```

This converts:
- `href="/_app/..."` → `href="./_app/..."`
- `import("/_app/...")` → `import("./_app/...")`
- `href="/favicon.png"` → `href="./favicon.png"`

---

*Created: 2025-12-05 after fixing black screen issue*
