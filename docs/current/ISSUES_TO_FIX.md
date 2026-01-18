# Issues To Fix

**Last Updated:** 2026-01-18 (Session 53) | **Build:** 497 | **Open:** 4

---

## Quick Summary

| Status | Count |
|--------|-------|
| **OPEN** | 4 |
| **FIXED/CLOSED** | 137 |

---

## OPEN ISSUES

### TECH-DEBT-001: AsyncSessionWrapper Should Be aiosqlite ⚠️ HIGH

- **Severity:** HIGH (architectural debt)
- **Component:** `server/utils/dependencies.py:33-143`

**Problem:** SQLite wrapper fakes async - blocks event loop. Should use true `aiosqlite`.

**Impact:** Performance issues under load, GIL blocking.

---

### BUG-042: Trash Bin Cannot Be Accessed ⚠️ LOW

- **Severity:** LOW (works in DEV mode)
- **Status:** NEEDS WINDOWS TESTING

**Problem:** Clicking Trash Bin does nothing on Windows Electron app. Works fine in DEV mode.

---

### IMPROVE-001: Unify First-Run Setup with Launcher UI ⚠️ LOW

- **Severity:** LOW (UX polish)
- **Components:** `electron/first-run-setup.js`, `src/lib/components/Launcher.svelte`

**Problem:** Two separate UIs for launcher and first-run setup. Could unify for consistent UX.

---

### DOCS-001: Documentation Files Too Large ⚠️ LOW

- **Severity:** LOW (affects Claude context)

**Problem:** Some docs exceed token limits.

| File | Lines | Target |
|------|-------|--------|
| `ISSUES_TO_FIX.md` | ~200 | ✅ FIXED |
| `OFFLINE_ONLINE_MODE.md` | 1660 | < 1000 |

---

## RECENTLY FIXED (Session 53)

### BUILD-001: Slim Installer ✅ FIXED

- **Fixed:** Build 497
- **Problem:** Installer 594MB → Target 150MB
- **Solution:** Created `requirements-build.txt`, fixed cache hash
- **Result:** **174 MB** installer (71% smaller)

### UI-113, BUG-044, UI-114 ✅ FIXED (Session 50-51)

| Issue | Fix |
|-------|-----|
| UI-113 | Edit mode right-click menu with colors |
| BUG-044 | File search localStorage key fix |
| UI-114 | Toast notification positioning |

### BUG-043: Offline Folder Creation ✅ FIXED (Session 50)

- **Fix:** Added `**/*.sql` to extraResources

### PATCH-001/002: Patch Updater ✅ FIXED (Session 48)

- **Fix:** Use Electron `net` module + `original-fs`

---

## Historical Issues

See `docs/archive/history/ISSUES_ARCHIVE.md` for 130+ resolved issues from Sessions 1-47.
