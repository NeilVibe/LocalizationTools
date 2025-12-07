# Build Troubleshooting Guide

## CRITICAL RULE: NEVER REBUILD WITHOUT PROOF

**NEVER trigger a new build without PROVING you have fixed a REAL issue.**

Before triggering ANY rebuild:
1. Read the ACTUAL build log from the failed run
2. Identify the SPECIFIC error message
3. Make a code change that addresses that EXACT error
4. Document what you changed and WHY

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

**Cause:** electron-builder's winCodeSign module tries to create symlinks, which requires admin privileges on Windows.

**Fix:** Disable code signing with `CSC_IDENTITY_AUTO_DISCOVERY: "false"` (prevents winCodeSign from running).

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

## History of Build Fixes

| Date | Error | Root Cause | Fix |
|------|-------|------------|-----|
| 2025-12-07 | `Env WIN_CSC_LINK is not correct` | Empty string treated as file path | Remove WIN_CSC_LINK and CSC_LINK |
| 2025-12-07 | `Cannot create symbolic link` | winCodeSign symlinks need admin | Use CSC_IDENTITY_AUTO_DISCOVERY |

---

*Last updated: 2025-12-07*
