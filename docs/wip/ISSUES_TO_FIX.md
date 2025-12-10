# Issues To Fix

**Purpose:** Track known bugs, UI issues, and improvements across LocaNext
**Last Updated:** 2025-12-11

---

## Quick Summary

| Area | Open | Fixed | Total |
|------|------|-------|-------|
| LDM UI | 0 | 5 | 5 |
| Navigation | 0 | 1 | 1 |
| General | 0 | 0 | 0 |

---

## Open Issues

*No open issues at this time.*

---

## Fixed Issues (2025-12-11)

### LDM - UI/UX Issues

#### ISSUE-001: Button Hover Tooltip Z-Index
- **Status:** [x] Fixed
- **Priority:** High
- **Fixed:** 2025-12-11
- **Component:** Global CSS (app.css)

**Problem:** Tooltip/hover bubble info was overshadowed by main content area.

**Fix Applied:**
- Added z-index 10000+ to all tooltip-related CSS classes in `app.css`
- Classes: `.bx--tooltip`, `.bx--assistive-text`, `.bx--popover-content`, etc.

---

#### ISSUE-002: File Upload Not Working
- **Status:** [x] Fixed (Partial - UI only)
- **Priority:** Critical
- **Fixed:** 2025-12-11
- **Component:** LDM FileExplorer.svelte

**Problem:** File upload showed no progress or feedback.

**Initial Fix Applied (UI):**
- Added `uploadProgress` and `uploadStatus` state variables
- Progress bar shows during upload (0-100%)
- Success/error notifications after upload
- Auto-close modal on success

**Root Cause Found:** See ISSUE-006 below.

---

#### ISSUE-006: FileUploader Event Binding Bug (Root Cause of ISSUE-002)
- **Status:** [x] Fixed
- **Priority:** Critical
- **Fixed:** 2025-12-11
- **Component:** LDM FileExplorer.svelte

**Problem:** Files selected in FileUploader never actually uploaded. Backend API worked (tested via curl), but frontend failed silently.

**Root Cause:** Carbon FileUploader `on:add` event returns internal FileItem objects, NOT raw File objects. The `bind:files` binding gives actual `File` objects.

**Bad Code:**
```svelte
<FileUploader on:add={(e) => uploadFiles = [...uploadFiles, ...e.detail]} />
```

**Fix Applied:**
```svelte
<FileUploader bind:files={uploadFiles} />
```

**Verification:** Backend upload works via curl - confirmed 4 rows uploaded successfully

---

#### ISSUE-003: Tasks Button Missing Icon
- **Status:** [x] Fixed
- **Priority:** Medium
- **Fixed:** 2025-12-11
- **Component:** +layout.svelte

**Problem:** Tasks button had no icon unlike other nav buttons.

**Fix Applied:**
- Imported `TaskComplete` icon from carbon-icons-svelte
- Changed from `HeaderNavItem` to custom button with icon
- Added matching CSS styling

---

#### ISSUE-004: Tasks Button Hover Cursor
- **Status:** [x] Fixed
- **Priority:** Low
- **Fixed:** 2025-12-11
- **Component:** +layout.svelte

**Problem:** Cursor didn't change to pointer on hover.

**Fix Applied:**
- Added `.tasks-button` CSS class with `cursor: pointer`
- Proper hover states matching Carbon header styling

---

#### ISSUE-005: LDM Default App Routing
- **Status:** [x] Fixed
- **Priority:** Critical
- **Fixed:** 2025-12-11

**Problem:** LDM didn't show as default app on startup.

**Root Cause:** In Electron file:// mode, +error.svelte acts as main page.

**Fix Applied:**
- Added LDM import and default case to `src/routes/+error.svelte`
- Documented in `docs/troubleshooting/ELECTRON_TROUBLESHOOTING.md`

---

## Fixed Issues Table

| ID | Description | Fixed Date | Files Changed |
|----|-------------|------------|---------------|
| ISSUE-001 | Tooltip z-index | 2025-12-11 | app.css |
| ISSUE-002 | File upload progress UI | 2025-12-11 | FileExplorer.svelte |
| ISSUE-003 | Tasks button icon | 2025-12-11 | +layout.svelte |
| ISSUE-004 | Tasks button cursor | 2025-12-11 | +layout.svelte |
| ISSUE-005 | LDM default app | 2025-12-11 | +error.svelte, +page.svelte |
| ISSUE-006 | FileUploader bind:files | 2025-12-11 | FileExplorer.svelte |

---

## Issue History

### Session 2025-12-11
- **6 issues identified and fixed** in single session
- Root cause of ISSUE-002 discovered via backend API testing (curl verified upload works)
- Key lesson: Carbon FileUploader requires `bind:files` not `on:add` for raw File objects

---

## How to Add New Issues

1. Use next available ISSUE-XXX number
2. Include:
   - Status: [ ] Open or [x] Fixed
   - Priority: Critical/High/Medium/Low
   - Reported date
   - Component affected
   - Clear problem description
   - Expected behavior
   - Suggested fix location

---

## Categories

- **LDM UI** - LanguageData Manager interface issues
- **Navigation** - App routing, menu issues
- **General** - Cross-app issues
- **Performance** - Speed/memory issues
- **Backend** - Server/API issues

---

*All issues from 2025-12-11 session have been resolved.*
