# WIP - Work In Progress

**Updated:** 2025-12-18 11:00 KST | **Build:** 297 (pending) | **Open Issues:** 0

---

## ✅ ALL ISSUES COMPLETE

**BUG-020 + FEAT-001 done. memoQ-style metadata and TM Viewer enhancements complete!**

| Feature | Status | Details |
|---------|--------|---------|
| memoQ Metadata (BUG-020) | ✅ COMPLETE | is_confirmed, confirmed_by, confirmed_at, updated_at, updated_by |
| TM Metadata (FEAT-001) | ✅ COMPLETE | 7 metadata options in dropdown |
| Toast Notifications (BUG-016) | ✅ COMPLETE | Global toasts via WebSocket events |
| TM Viewer (FEAT-003) | ✅ COMPLETE | Paginated grid, sort, search, inline edit, confirm button |
| TM Export (FEAT-002) | ✅ COMPLETE | TEXT/Excel/TMX with column selection |
| E2E Tests (TASK-002) | ✅ COMPLETE | 20 tests for all 3 engines |
| Task Manager | ✅ COMPLETE | 22 operations tracked across 4 tools |

---

## Current Status

### Completed This Session (2025-12-18)
- ✅ **BUG-020** - memoQ-style metadata (5 new columns, confirm workflow, TM Viewer button)
- ✅ **FEAT-001** - TM Metadata enhancement (7 dropdown options)
- ✅ **BUG-016** - Global Toast Notifications (toastStore.js + GlobalToast.svelte)
- ✅ **FEAT-003** - TM Viewer (TMViewer.svelte + API endpoints)
- ✅ **FEAT-002** - TM Export (TEXT/Excel/TMX)
- ✅ **Task Manager Review** - All 22 long operations tracked

### Previously Completed (2025-12-17)
- ✅ **TASK-002** - Full E2E tests for all 3 engines (20 tests)
- ✅ **TASK-001** - All operations now use TrackedOperation
- ✅ **6 Critical Bugs Fixed** - All 3 pretranslation pipelines working
- ✅ **BUG-022** - Now using incremental TMSyncManager.sync()

### Pipeline Status

| Engine | Status | Notes |
|--------|--------|-------|
| **Standard TM** | ✅ WORKS | Staleness check, StringID support |
| **XLS Transfer** | ✅ WORKS | EmbeddingsManager created |
| **KR Similar** | ✅ WORKS | load_tm + find_similar |
| **Auto-Update** | ✅ FAST | Incremental sync |
| **Task Manager** | ✅ WORKS | 22 operations tracked |
| **Toast Notifications** | ✅ WORKS | Global toasts on any page |
| **memoQ Metadata** | ✅ WORKS | Confirm entries, track who/when |

---

## Priority Order

```
ALL ISSUES COMPLETE! ✅ (0 open)

ONGOING (LOW):
═══════════════════════════════════════
├── P25: LDM UX Overhaul (85% done)
└── BUG-021: Seamless UI during auto-update (optional)

RECENTLY FIXED:
═══════════════════════════════════════
├── BUG-020: ✅ memoQ-style metadata (5 columns, confirm workflow)
├── FEAT-001: ✅ TM Metadata enhancement (7 dropdown options)
├── BUG-016: ✅ Global Toast Notifications
├── FEAT-003: ✅ TM Viewer (paginated, sort, search, inline edit, confirm)
├── FEAT-002: ✅ TM Export (TEXT/Excel/TMX)
├── TASK-002: ✅ Full E2E tests (20 tests)
├── TASK-001: ✅ TrackedOperation for ALL long processes
└── BUG-022: ✅ Incremental updates
```

---

## Quick Navigation

| Need | File |
|------|------|
| **Session state?** | [SESSION_CONTEXT.md](SESSION_CONTEXT.md) |
| **Bug list?** | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) |
| **Roadmap?** | [Roadmap.md](../../Roadmap.md) |

---

## Task Details

### TASK-001: Task Manager Integration [FIXED ✅]

All long-running operations now use `TrackedOperation`.

**Current State:**
| Operation | Tracked? | File |
|-----------|----------|------|
| `build_tm_indexes` | ✅ YES | api.py:1268 |
| `pretranslate_file` | ✅ YES | api.py:1414 |
| `upload_file` | ✅ YES | api.py:538 |
| `upload_tm` | ✅ YES | api.py:1024 |
| Auto-sync (Standard) | ✅ YES | pretranslate.py:157 |
| Auto-sync (XLS Transfer) | ✅ YES | pretranslate.py:255 |
| Auto-sync (KR Similar) | ✅ YES | pretranslate.py:352 |

---

### TASK-002: Full E2E Tests [FIXED ✅]

**All 3 engines now have comprehensive TRUE E2E tests:**

| Engine | Test File | Tests | Key Features |
|--------|-----------|-------|--------------|
| Standard TM | `true_e2e_standard.py` | 6 | StringID variations, fuzzy match, fallback |
| XLS Transfer | `true_e2e_xls_transfer.py` | 7 | Code preservation, split/whole mode |
| KR Similar | `true_e2e_kr_similar.py` | 7 | Triangle markers, structure adapt, load_tm |

**Total: 20 E2E tests** - Run: `pytest tests/fixtures/stringid/true_e2e_*.py -v`

---

### TM Auto-Update (BUG-022 - FIXED ✅)

**NOW FIXED - Incremental Sync:**
```
pretranslate(file_id, engine, tm_id)
    │
    ├── Load TM from PostgreSQL
    │
    ├── Check: indexed_at < updated_at?
    │   ├── YES (STALE):
    │   │   ├── TMSyncManager.sync()  ← INCREMENTAL! Only new/changed
    │   │   └── Update indexed_at timestamp
    │   └── NO (FRESH): Skip
    │
    └── Route to engine
```

**What's Done:**
- ✅ Staleness check in all 3 engines
- ✅ Incremental sync when stale (BUG-022 FIXED)
- ✅ indexed_at updated after sync
- ✅ TMSyncManager.sync() used in all engines
- ✅ TrackedOperation for sync (TASK-001 FIXED)

**What's Still Missing:**
- Nothing! All features complete.

---

## P36 Phase Status

```
Phase 1:  ✅ COMPLETE - E2E testing (2,133 tests)
Phase 2A: ✅ COMPLETE - Excel File Editing
Phase 2B: ✅ COMPLETE - TM StringID Support
Phase 2C: ✅ COMPLETE - Pretranslation API
Phase 2C+:✅ COMPLETE - PKL StringID Metadata
Phase 2D: ✅ COMPLETE - TRUE E2E Testing
Phase 2E: ✅ COMPLETE - Pipeline Bug Fixes (6 bugs)
Phase 2F: ✅ COMPLETE - Task Manager (TASK-001) + Full E2E (TASK-002 pending)
Phase 3:  ⏳ Frontend Modals
```

---

## Active WIP Files

| Priority | File | Status | Description |
|----------|------|--------|-------------|
| - | `SESSION_CONTEXT.md` | Always | Claude handoff state |
| - | `ISSUES_TO_FIX.md` | 2 open | Bug/task tracker |
| **1** | `P36_PRETRANSLATION_STACK.md` | ✅ Complete | Implementation checklist |
| **1** | `P36_TECHNICAL_DESIGN.md` | ✅ Complete | DB + StringID + Excel design |
| **1** | `P36_STRINGID_TESTING_PLAN.md` | ✅ Complete | Test fixtures + E2E plan |
| **4** | `P25_LDM_UX_OVERHAUL.md` | 85% | TM matching, QA checks |

---

## Test Files Location

```
tests/fixtures/stringid/
├── true_e2e_standard.py         # ✅ 6 tests - StringID, fuzzy, fallback
├── true_e2e_xls_transfer.py     # ✅ 7 tests - Code preservation
├── true_e2e_kr_similar.py       # ✅ 7 tests - NEW! Triangle, structure
├── test_e2e_1_tm_upload.py      # Basic TM upload (10)
├── test_e2e_2_pkl_index.py      # PKL variations (8)
├── test_e2e_3_tm_search.py      # TMSearcher (9)
├── test_e2e_4_pretranslate.py   # Pretranslation (10)
└── stringid_test_data.py        # Test data module
```

---

## Key Files Modified This Session

| File | Changes |
|------|---------|
| `locaNext/src/lib/stores/toastStore.js` | BUG-016: NEW! Global toast store |
| `locaNext/src/lib/components/GlobalToast.svelte` | BUG-016: NEW! Toast container component |
| `locaNext/src/routes/+layout.svelte` | BUG-016: Added GlobalToast component |
| `locaNext/src/lib/components/ldm/TMViewer.svelte` | FEAT-003: NEW! TM entry viewer |
| `locaNext/src/lib/components/ldm/TMManager.svelte` | FEAT-002/003: Export + View buttons |
| `server/tools/ldm/tm_manager.py` | FEAT-002/003: Export + Viewer methods |
| `server/tools/ldm/api.py` | FEAT-002/003: Export + Viewer endpoints |

---

## Quick Commands

```bash
# Check build
http://172.28.150.120:3000/neilvibe/LocaNext/actions

# Trigger build
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Check servers
./scripts/check_servers.sh

# Run tests
python3 -m pytest tests/fixtures/stringid/ -v
```

---

*Updated 2025-12-18 10:00 KST. BUG-016 COMPLETE - Global toast notifications.*
