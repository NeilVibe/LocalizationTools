# Build Troubleshooting Guide

## CRITICAL RULE: NEVER REBUILD WITHOUT PROOF

**NEVER trigger a new build without PROVING you have fixed a REAL issue.**

Before triggering ANY rebuild:
1. **RUN VERSION CHECK FIRST:**
   ```bash
   python3 scripts/check_version_unified.py
   ```
   This catches 90% of build failures (stale version timestamp, mismatched versions).

2. Read the ACTUAL build log from the failed run
3. Identify the SPECIFIC error message
4. Make a code change that addresses that EXACT error
5. Document what you changed and WHY

---

## FAST LOG CHECK PROTOCOL

**Step 1: Find latest build folder**
```bash
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -3
```

**Step 2: List log files in that folder**
```bash
ls ~/gitea/data/actions_log/neilvibe/LocaNext/<FOLDER>/
```

**Step 3: Search for errors (check BOTH logs if multiple exist)**
```bash
grep -i "error\|failed\|⨯\|BLOCKED" ~/gitea/data/actions_log/neilvibe/LocaNext/<FOLDER>/*.log | head -20
```

**Step 4: Read end of log for final error**
```bash
tail -50 ~/gitea/data/actions_log/neilvibe/LocaNext/<FOLDER>/<NUMBER>.log
```

---

## COMMON BUILD FAILURES (CHECK THESE FIRST!)

### Version Timestamp Too Old (MOST COMMON!)

**Error:**
```
❌ Version timestamp TOO FAR: 2512131330 (KST) is 1.1h away from now. Max: 1h
❌ BUILD BLOCKED: Version timestamp too far from current time!
```

**Fix:**
```bash
# 1. Check what needs updating
python3 scripts/check_version_unified.py

# 2. Update version.py with suggested timestamp
# 3. Run check again to fix all files
# 4. Commit and push
```

**WRONG approaches that WASTE TIME:**
- "Let's try rebuilding and see if it works"
- Restarting runners when the actual issue is in the build script
- Triggering multiple builds hoping one will magically succeed
- Making changes without reading the error log first

---

## Common Gitea/electron-builder Errors

### 1. Code Signing Errors

**Error:**
```
⨯ Env WIN_CSC_LINK is not correct, cannot resolve: C:\...\locaNext not a file
```

**Cause:** Setting `WIN_CSC_LINK: ""` (empty string) makes electron-builder treat it as a file path.

**Fix:** Remove `WIN_CSC_LINK` and `CSC_LINK` entirely. Only use:
```yaml
env:
  CSC_IDENTITY_AUTO_DISCOVERY: "false"
```

### 2. Symlink Permission Errors (Windows)

**Error:**
```
Cannot create symbolic link : Le client ne dispose pas d'un privilege necessaire
```

**Cause:** electron-builder downloads winCodeSign binaries even when `CSC_IDENTITY_AUTO_DISCOVERY: "false"` is set. The archive contains macOS symlinks that 7-zip cannot create without admin privileges.

**Fix:** Must disable code signing BOTH in workflow AND in package.json:

1. In workflow (build.yml):
```yaml
env:
  CSC_IDENTITY_AUTO_DISCOVERY: "false"
```

2. In package.json (locaNext/package.json):
```json
"win": {
  "target": "nsis",
  "sign": false,
  "signAndEditExecutable": false
}
```

**Important:** `CSC_IDENTITY_AUTO_DISCOVERY: "false"` alone is NOT sufficient! You MUST also set `sign: false` in package.json to prevent electron-builder from downloading winCodeSign entirely.

### 3. Version Format Errors

**Error:**
```
Cannot parse version "2512072249" - must be semver format
```

**Cause:** electron-builder requires semantic versioning (X.Y.Z format).

**Fix:** Use proper semver in package.json:
```json
"version": "1.3.0"
```

---

## Debugging Workflow

1. **Find the build log:**
   ```bash
   ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -5
   # Find the hex folder (e.g., 4a = task 74 in decimal)
   cat ~/gitea/data/actions_log/neilvibe/LocaNext/4a/74.log
   ```

2. **Search for errors:**
   ```bash
   grep -i "error\|failed\|⨯" ~/gitea/data/actions_log/neilvibe/LocaNext/4a/74.log
   ```

3. **Check runner status:**
   ```bash
   # Linux runner
   tail -20 /tmp/linux_runner.log

   # Windows runner
   cat /tmp/windows_runner_output.txt
   ```

---

## Post-Install Runtime Errors

### ENOENT: Python/Server Not Found (CRITICAL!)

**Error:**
```
spawn C:\...\Playground\tools\python\python.exe ENOENT
```

**Cause:** Code looks for `extraResources` at wrong path.
- `extraResources` go to `resources/` folder, NOT app root
- Dev: `../tools/python/python.exe`
- Prod: `resources/tools/python/python.exe`

**Fix:** Use `resourcesPath` for production paths:
```javascript
// WRONG
const pythonExe = path.join(appRoot, 'tools', 'python', 'python.exe');

// RIGHT
const resourcesPath = path.join(app.getAppPath(), '..');
const pythonExe = path.join(resourcesPath, 'tools', 'python', 'python.exe');
```

**Full guide:** [ELECTRON_PACKAGING.md](ELECTRON_PACKAGING.md)

---

### First-Run Setup Fails Silently

**Symptom:** App opens but nothing works, no error shown.

**Cause:** Error dialog wasn't closable (no Exit button).

**Fix:** Added Exit button and made window closable on error:
```javascript
if (status === 'error') {
  setupWindow.setClosable(true);
}
```

---

## Post-Build Testing Protocol (MANDATORY!)

**DO NOT RELEASE WITHOUT TESTING ON CLEAN MACHINE.**

### Quick Test Checklist

1. **Install on Playground/clean folder**
2. **Check folder structure:**
   ```powershell
   dir "C:\...\Playground\resources\server"    # Should exist
   dir "C:\...\Playground\resources\tools"     # Should exist
   ```
3. **Run app and check:**
   - [ ] First-run setup starts
   - [ ] No ENOENT errors in logs
   - [ ] Error dialog has Exit button
   - [ ] Installer showed progress details

### Where to Find Logs

```powershell
# Windows logs
dir %APPDATA%\LocaNext\logs\

# Or check Event Viewer for crashes
```

---

## History of Build Fixes

| Date | Error | Root Cause | Fix |
|------|-------|------------|-----|
| 2025-12-07 | `Env WIN_CSC_LINK is not correct` | Empty string treated as file path | Remove WIN_CSC_LINK and CSC_LINK |
| 2025-12-07 | `Cannot create symbolic link` | winCodeSign downloaded even with CSC_IDENTITY_AUTO_DISCOVERY | Add `sign: false` to package.json win config |
| 2025-12-14 | `spawn python.exe ENOENT` | extraResources at `resources/` not `appRoot/` | Use `resourcesPath` for prod paths |
| 2025-12-14 | Error dialog can't close | No Exit button, `closable: false` | Add Exit button, `setClosable(true)` on error |
| 2025-12-14 | Installer shows no details | NSIS default hides details | Added `ShowInstDetails show` in nsis-includes |

---

*Last updated: 2025-12-15*
