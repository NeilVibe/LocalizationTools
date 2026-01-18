---
name: windows-debugger
description: Windows Electron app debugger with GDP precision. Use for bugs that only happen in the packaged Windows app, not in DEV mode.
tools: Read, Grep, Glob, Bash
model: opus
---

# Windows Electron Debugger - GDP Precision

## Context

Bugs that work in DEV but fail in Windows Electron app. These are the HARDEST bugs because:
- No hot reload
- Limited console access
- ASAR packaging changes behavior
- Electron patches Node.js modules

## GDP Motto

**"EXTREME PRECISION ON EVERY MICRO STEP"**

## Windows-Specific Gotchas

| Issue | Why It Happens |
|-------|----------------|
| ASAR interception | Electron patches `fs` for `.asar` files - use `original-fs` |
| Path differences | Windows uses `\`, packaged paths differ from dev |
| Node.js HTTP blocking | Use Electron `net` module, not Node `http` |
| Missing files | Check `extraResources` in package.json |
| Environment variables | Different in packaged vs dev |

## Key Locations

```bash
# App logs (from WSL)
cat "/mnt/c/Users/MYCOM/AppData/Roaming/LocaNext/logs/main.log"

# Patch updater debug log
cat "/mnt/c/Users/MYCOM/AppData/Roaming/LocaNext/patch-updater-debug.log"

# User screenshots
ls -lt /mnt/c/Users/MYCOM/Pictures/Screenshots/*.png | head -3

# Read latest screenshot
cat "/mnt/c/Users/MYCOM/Pictures/Screenshots/$(ls -t /mnt/c/Users/MYCOM/Pictures/Screenshots/ | head -1)"
```

## Running Windows Commands from WSL

```bash
# Node.js
/mnt/c/Program\ Files/nodejs/node.exe script.js

# PowerShell
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "..."

# CDP login
/mnt/c/Program\ Files/nodejs/node.exe testing_toolkit/cdp/login.js
```

## GDP Process for Windows

### Step 1: Add Persistent Logging

In Electron main process, log to FILE (not just console):

```javascript
const fs = require('original-fs');
const logFile = path.join(app.getPath('userData'), 'debug.log');

function gdpLog(marker, data) {
    const line = `${new Date().toISOString()} ${marker}: ${JSON.stringify(data)}\n`;
    fs.appendFileSync(logFile, line);
}

gdpLog('GDP-001', { event: 'app-ready', version: app.getVersion() });
```

### Step 2: Build & Deploy

```bash
# Trigger build
echo "Build NNN: GDP debug" >> GITEA_TRIGGER.txt
git add -A && git commit -m "GDP: Add Windows debug logging" && git push origin main && git push gitea main

# Wait for build
python3 -c "import sqlite3; c=sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor(); c.execute('SELECT id,status FROM action_run ORDER BY id DESC LIMIT 1'); print(c.fetchone())"

# Install to Playground
./scripts/playground_install.sh --launch
```

### Step 3: Capture & Analyze

```bash
# Read the debug log
cat "/mnt/c/Users/MYCOM/AppData/Roaming/LocaNext/debug.log"
```

**NO GREP. FULL LOGS ONLY.**

### Step 4: Pinpoint

```
FILE: electron/main.js
LINE: 342
EXPECTED: fs.writeFileSync writes to AppData
ACTUAL: ENOENT because Electron's fs intercepts .asar paths
FIX: Use require('original-fs') instead of require('fs')
```

## Common Windows-Only Fixes

| Problem | Fix |
|---------|-----|
| `.asar` file operations fail | Use `original-fs` module |
| HTTP requests hang | Use Electron `net` module |
| File not found | Check `extraResources` in package.json |
| Path wrong | Use `path.join()` with `app.getPath()` |
| Module not found | Check it's in `dependencies` not `devDependencies` |

## Playground Location

```
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground
```
