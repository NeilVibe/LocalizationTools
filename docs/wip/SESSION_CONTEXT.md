# Session Context

**Updated:** 2025-12-28 14:30 | **Build:** 409 | **Status:** STABLE REVISION + DOC-001 COMPLETE

---

## DOC-001: INSTALL vs UPDATE Confusion - RESOLVED

### Critical Documentation Overhaul

**Problem:** Claude (and documentation) conflated INSTALL and UPDATE operations, causing:
- Wrong advice (telling user to "install" when app already installed)
- Wasted time (full reinstall takes 2-5 min, auto-update takes 30 sec)
- Wrong testing scenarios

**Resolution:** Complete documentation overhaul:

| Doc | Change |
|-----|--------|
| `CLAUDE.md` | Added "INSTALL vs UPDATE" section |
| `MASTER_TEST_PROTOCOL.md` | Added critical distinction section + updated Phase 4 |
| `HOW_TO_BUILD.md` | Added "After Build: INSTALL vs UPDATE" section |
| `CONFUSION_HISTORY.md` | Added Confusion #16 with full details |
| `DOC-001_INSTALL_VS_UPDATE_CONFUSION.md` | Created comprehensive reference |

---

## STABLE REVISION - 2025-12-28 (Build 409)

### 10 Fixes Completed This Session

| Issue | Description | Status |
|-------|-------------|--------|
| **UI-059** | Row selection state inconsistent | ✅ FIXED |
| **UI-062** | version.json file:// protocol error | ✅ FIXED (webRequest intercept) |
| **UI-065** | Edit icon visibility on selected | ✅ FIXED |
| **UI-074** | Missing /api/ldm/files endpoint | ✅ VERIFIED (already existed) |
| **UI-075** | Console error objects not showing | ✅ FIXED (Error serialization) |
| **UI-076** | Search bar not filtering rows | ✅ FIXED |
| **UI-077** | Duplicate names (Files/Folders/Projects/TM) | ✅ FIXED |
| **UI-078** | Color tags not rendering | ✅ FIXED |
| **UI-079** | Grid lines not visible | ✅ FIXED |
| **UI-080** | Search results empty cells | ✅ FIXED |

### Code Changes

| File | Change |
|------|--------|
| `VirtualGrid.svelte` | Search fix, grid lines, selection priority |
| `files.py` | Duplicate file name validation |
| `folders.py` | Duplicate folder name validation |
| `projects.py` | Duplicate project name validation |
| `tm_crud.py` | Duplicate TM name validation |

### Documentation Updated

| Doc | Content |
|-----|---------|
| `DEV_MODE_PROTOCOL.md` | CS-001 to CS-007 Critical Solutions, Phase 14 Debug Commands |
| `CONFUSION_HISTORY.md` | Confusions 10-16 (now includes INSTALL vs UPDATE) |
| `TERMINAL_COMMAND_GUIDE.md` | NEW - Commands + Gitea Protocol |
| `ISSUES_TO_FIX.md` | 7 issues fixed, 8 remaining |
| `DOC-001_INSTALL_VS_UPDATE_CONFUSION.md` | NEW - Critical distinction documentation |
| `CLAUDE.md` | Added INSTALL vs UPDATE section |
| `MASTER_TEST_PROTOCOL.md` | Added INSTALL vs UPDATE section + updated Phase 4 |
| `HOW_TO_BUILD.md` | Added After Build section |

---

## Gitea Protocol Followed

```
1. START:  sudo systemctl start gitea
2. COMMIT: git add -A && git commit -m "Build XXX: ..."
3. PUSH:   git push origin main && git push gitea main
4. STOP:   sudo systemctl stop gitea
```

---

## Open Issues (7 remaining - all LOW priority)

### MEDIUM (Low Priority)
- UI-063: CSS text overflow
- UI-066: Placeholder column count
- UI-067: Filter dropdown styling
- UI-068: Resize handle visibility
- UI-069: QA/Edit icon overlap

### LOW (Cosmetic)
- UI-070 to UI-073: Cosmetic issues

### NOT A BUG / BY DESIGN (Closed)
- UI-061: Routing error (handled in +error.svelte)
- UI-064: Status colors on hover (intentional)

---

*Build 409 - Stable Revision*
