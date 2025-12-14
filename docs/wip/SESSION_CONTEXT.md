# Session Context - Last Working State

**Updated:** 2025-12-14 ~21:30 KST | **By:** Claude

---

## P28: CI/CD Fixed - electron-builder NSIS

**Status: COMPLETE** | Replaced broken Inno Setup with native NSIS

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
   - Removed "Setup Inno Setup Path" step
   - Replaced "Compile Installer" (ZIP) with "Collect NSIS Installer"
   - Updated asset upload to use .exe
   - Removed deprecated .iss file updates

3. **.github/workflows/build-electron.yml** (CI/CD Code Review fix)
   - Synced with Gitea workflow - now uses NSIS instead of Inno Setup
   - Updated silent install flags for NSIS (`/S /D=path`)
   - Fixed verification paths for electron-builder structure (`resources/`)
   - Updated latest.yml generation to use unified version format

4. **installer/deprecated/** - Archived old .iss files

5. **LICENSE** - Added MIT license file

---

## CI/CD Code Review - Session 13 COMPLETE

### Issues Fixed

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| CI-001 | HIGH | Gitea still updated .iss files | Removed deprecated .iss updates |
| CI-002 | CRITICAL | GitHub still used Inno Setup | Synced to use NSIS |
| CI-003 | MEDIUM | NSIS install flags wrong | Fixed to `/S /D=path` |
| CI-004 | MEDIUM | File verification paths wrong | Updated for `resources/` structure |

### Both Workflows Now Sync

- Gitea (.gitea/workflows/build.yml)
- GitHub (.github/workflows/build-electron.yml)
- Both use electron-builder NSIS
- Same verification tests

---

## Next: P29 - Verification Test

Need to trigger a build and verify:
1. NSIS installer is produced
2. Download and install on Windows
3. App starts standalone
4. Embedded Python works

### Trigger Build Command

```bash
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "P28: CI/CD sync - both workflows use NSIS" && git push origin main && git push gitea main
```

---

## Quick Reference

**New build output:**
```
installer_output/LocaNext_v25.XXXX.XXXX_Light_Setup.exe
```

**Key config (locaNext/package.json):**
```json
"win": { "target": "nsis" },
"nsis": {
  "oneClick": false,
  "allowToChangeInstallationDirectory": true,
  ...
}
```

---

*For full project status, see [Roadmap.md](../../Roadmap.md)*
