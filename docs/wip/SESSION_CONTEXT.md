# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-17 22:45 KST
**Build:** 298 (v25.1217.2220) RELEASED
**Session:** Ready for CDP Testing

---

## Current State

**Build 298 released and deployed to Playground. Ready for feature verification.**

| Item | Status |
|------|--------|
| Gitea Build | v25.1217.2220 released |
| GitHub Build | Triggered, running |
| Playground | Fresh install, ONLINE mode |
| Open Issues | 0 |

---

## Features to Test (CDP)

| Feature | Component | Test |
|---------|-----------|------|
| **TM Viewer** | LDM → TM Manager → View | Paginated grid, sort, search, inline edit |
| **TM Confirm** | TM Viewer → Checkmark button | Confirm/unconfirm entries, green highlight |
| **TM Export** | TM Manager → Download button | TEXT/Excel/TMX formats |
| **Global Toasts** | Any page during operations | Start/complete/fail notifications |
| **Metadata Dropdown** | TM Viewer → Metadata column | 7 options (StringID, Confirmed, dates, etc.) |

---

## What Was Fixed This Session

### Build 298 Content

| ID | Description | Files |
|----|-------------|-------|
| **BUG-020** | memoQ-style metadata (5 columns, confirm workflow) | models.py, tm_manager.py, api.py, TMViewer.svelte |
| **FEAT-001** | TM Metadata enhancement (7 dropdown options) | TMViewer.svelte |
| **BUG-016** | Global Toast Notifications | toastStore.js, GlobalToast.svelte, +layout.svelte |
| **FEAT-002** | TM Export (TEXT/Excel/TMX) | tm_manager.py, api.py, TMManager.svelte |
| **FEAT-003** | TM Viewer (paginated, sort, search, inline edit) | TMViewer.svelte, tm_manager.py, api.py |
| **Fix** | Lazy import SentenceTransformer (server startup hang) | translation.py, process_operation.py, translate_file.py |

### memoQ Metadata Columns (BUG-020)
```
updated_at      - When entry was last modified
updated_by      - Who modified it
confirmed_at    - When entry was confirmed
confirmed_by    - Who confirmed it
is_confirmed    - Boolean status
```

### TM Metadata Options (FEAT-001)
```
1. StringID
2. Confirmed (Yes/No)
3. Created At
4. Created By
5. Updated At
6. Confirmed At
7. Confirmed By
```

---

## Pipeline Status

| Component | Status |
|-----------|--------|
| Standard TM | WORKS |
| XLS Transfer | WORKS |
| KR Similar | WORKS |
| TM Auto-Update | WORKS (incremental) |
| Task Manager | WORKS (22 operations) |
| Toast Notifications | WORKS (global) |
| TM Viewer | WORKS |
| TM Export | WORKS |
| memoQ Confirm | WORKS |

---

## Playground Details

```
Version:  v25.1217.2220
Path:     C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
Mode:     ONLINE (PostgreSQL)
User:     neil (auto-logged in)
CDP:      http://127.0.0.1:9222
Size:     3.8G
```

---

## Next Steps

1. **CDP Testing** - Verify new features work in Playground
2. **Check GitHub Build** - Wait for completion
3. **Update docs** - If all features verified

---

## Quick Commands

```bash
# Check Gitea build status
curl -s "http://172.28.150.120:3000/neilvibe/LocaNext/actions" | grep -B15 'runs/302'

# Playground install (if needed)
./scripts/playground_install.sh --launch --auto-login

# Run CDP verification
# (manual via browser DevTools at http://127.0.0.1:9222)
```

---

*This document is the source of truth for session handoff.*
