# Session Context

**Updated:** 2025-12-28 22:30 | **Build:** 415 (STABLE) | **Status:** Planning MemoQ-Style Update

---

## Current State

**All previous bugs fixed.** Now planning major UX upgrade.

### Completed This Session

| Task | Status | Details |
|------|--------|---------|
| QA Panel Stability | DONE | Fixed freeze, timeout, error UI |
| QA Click Navigation | DONE | O(1 lookup, proper row highlight |
| Stale Task Cleanup | DONE | Backend endpoint + UI button |
| LanguageTool Config | DONE | Moved to config.py (env vars) |
| Hardcoded URLs | DONE | All frontend + backend fixed |
| Code Review Docs | DONE | 8 lessons documented |
| Enterprise Docs | DONE | Updated for env var config |

---

## Next: MemoQ-Style Non-Modal Editing (MAJOR)

### Vision
Transform LDM from modal-based to **inline editing** like memoQ.

### Key Features
1. **Inline Cell Editing** - Click target cell, edit directly
2. **Fixed TM/QA Column** - Right side panel (~300px)
3. **TM Metadata** - Show origin, creator, date for each match
4. **QA Integration** - LanguageTool + built-in checks in panel
5. **Keyboard Nav** - Tab, Enter, Arrow keys

### Layout
```
┌──────────────────────────────────────────────────────────────────┐
│ # │ Source              │ Target (editable)    │ TM/QA Panel    │
├───┼─────────────────────┼──────────────────────┼────────────────┤
│ 1 │ Hello world         │ Bonjour le monde     │ TM MATCHES     │
│ 2 │ Click here          │ [editing cursor]     │ 100% Bonjour...|
│ 3 │ Save changes        │ Enregistrer          │ QA ISSUES      │
└───┴─────────────────────┴──────────────────────┴────────────────┘
```

### TM Metadata to Display
- Match percentage (100%, fuzzy)
- Source project/file
- Creation type (Manual, Review, Auto-TM, Import)
- Created by (username)
- Created date

### Full Spec: [MEMOQ_STYLE_EDITING.md](MEMOQ_STYLE_EDITING.md)

---

## Grammar Checker Research

| Option | Languages | RAM | Status |
|--------|-----------|-----|--------|
| **LanguageTool** | 31 | ~900MB | Current, best multilingual |
| **Harper** | English only | ~18MB | Fast, Rust, offline |
| **HuggingFace T5** | 4-7 | ~500MB-2GB | Research phase |

**Verdict:** Stick with LanguageTool for 30+ language support.

---

## Priority Summary

| Priority | Feature | Status |
|----------|---------|--------|
| **P1** | MemoQ-Style Non-Modal | PLANNING |
| **P2** | TM Metadata Display | PLANNING |
| **P2** | QA in Side Panel | PLANNING |
| **P3** | Font Settings | DEFERRED |
| **P3** | Offline/Online Toggle | DEFERRED |

---

## Open Questions

1. **Drop Edit Modal?** User ready to go full non-modal
2. **Settings Toggle?** Or just switch entirely?
3. **TM Panel Width?** Fixed 300px or resizable?
4. **When Load TM?** On select or prefetch?

---

## Quick Reference

### Check Build Status
```bash
python3 -c "
import sqlite3, time
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, started FROM action_run ORDER BY id DESC LIMIT 1')
r = c.fetchone()
elapsed = int(time.time()) - r[2] if r[2] else 0
status_map = {1: 'SUCCESS', 2: 'FAILURE', 6: 'RUNNING'}
print(f'Run {r[0]}: {status_map.get(r[1], r[1])} | {elapsed//60}m')"
```

### Check Servers
```bash
./scripts/check_servers.sh
```

---

*Session focus: Planning MemoQ-style UX overhaul*
