# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-19 02:00 | **Build:** 300 ✅

---

## NEXT SESSION: Fix Critical Bugs + UI/UX Minimalism

### Priority 1: Critical Bugs (Must Fix First)

| Bug | Problem | Investigation |
|-----|---------|---------------|
| **BUG-028** | "No module named model2vec" on Sync | Check PyInstaller includes model2vec |
| **BUG-029** | Right-click "Upload as TM" broken | Check context menu handler + API |

### Priority 2: TM Viewer Minimalism (Batch)

Remove all this clutter:
- Items per page selector → **Replace with lazy load**
- "1 of 1" pagination → **Remove, use infinite scroll**
- "Confirm" button → **Review code, remove entirely**
- "Showing rows 1-5 of 5" → **Remove**

**Goal:** Window-sized lazy loading. No pagination. No unnecessary controls.

### Priority 3: File Viewer Cleanup (Batch)

Remove from 3-dot menu next to "Viewing":
- Download review option
- Download all option
- "i" info button

**Reason:** Users download via right-click on file list. These are redundant.

### Priority 4: Tooltip Smart Positioning

**Problem:** Tooltips get cut off at window edges (especially right side).
**Solution:** Svelte 5 has built-in solutions for smart tooltip positioning.

### Priority 5: Other Items

- **BUG-030:** WebSocket disconnected - investigate if normal
- **UI-031/032:** Font size + Bold settings not working
- **UI-033:** App Settings empty
- **Q-001:** Decide auto-sync vs manual sync for TM

---

## Full Issue Count

| Category | Count |
|----------|-------|
| Critical Bugs | 2 |
| Medium Bugs | 1 |
| UI/UX Issues | 11 |
| Questions | 1 |
| **Total** | **15** |

See [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) for full details.

---

## Current State

| Item | Status |
|------|--------|
| Build | **300** ✅ |
| Playground | **v25.1218.2204** |
| Model2Vec | **potion-multilingual-128M** (101 languages, Korean ✅) |
| Test Data | `tests/fixtures/sample_1000_rows.txt` ready |

---

## What Was Tested This Session (QA Report)

User performed manual QA testing on Playground Build 300. Findings:

**Working:**
- TM Viewer basic display ✅
- Server status shows DB connected ✅

**Broken:**
- Model2Vec import error on sync
- Upload as TM context menu not working
- WebSocket shows disconnected
- Font/Bold settings non-functional
- Tooltips cut off at edges

**Useless UI (to remove):**
- Items per page / pagination
- Confirm button
- Row count display
- Download options in 3-dot menu
- Info button

---

## Key Files to Modify

### For TM Viewer Minimalism (UI-025 to UI-028)
```
locaNext/src/lib/components/ldm/TMViewer.svelte
```

### For File Viewer Cleanup (UI-029, UI-030)
```
locaNext/src/lib/components/ldm/FileViewer.svelte
```

### For Tooltip Positioning (UI-034)
```
locaNext/src/lib/components/ui/Tooltip.svelte (or similar)
```

### For Model2Vec Bug (BUG-028)
```
server/pyinstaller.spec (or build config)
server/tools/shared/embedding_engine.py
```

### For Upload as TM Bug (BUG-029)
```
locaNext/src/lib/components/ldm/FileViewer.svelte (context menu)
server/routers/ldm.py (API endpoint)
```

---

## Questions to Ask User

1. **Auto-sync:** Should TM indexes auto-sync when TM changes? Or keep manual button?
   - User opinion: Auto for Model2Vec (fast/cheap)

---

## Commands for Next Session

```bash
# 1. Check servers
./scripts/check_servers.sh

# 2. Launch Playground if needed
./scripts/playground_install.sh --launch --auto-login

# 3. After fixing bugs, trigger build
echo "Build 301" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Fix: BUG-028, BUG-029, UI minimalism" && git push origin main && git push gitea main
```

---

## Work Plan Summary

```
Morning (Critical):
├── BUG-028: Fix model2vec import in PyInstaller
├── BUG-029: Fix right-click Upload as TM
└── Build 301 + Test

Afternoon (UI/UX):
├── UI-025 to UI-028: TM Viewer lazy load + cleanup
├── UI-029, UI-030: File Viewer cleanup
└── Build 302 + Test

If Time (Polish):
├── UI-034: Tooltip smart positioning
├── BUG-030: WebSocket investigation
└── UI-031 to UI-033: Settings fixes
```

---

## Playground Info

```
Version:  v25.1218.2204 (Build 300)
Path:     C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
Mode:     ONLINE (PostgreSQL)
Login:    neil/neil
CDP:      http://127.0.0.1:9222
```

---

*Session handoff document - Next: Critical bugs then UI minimalism*
