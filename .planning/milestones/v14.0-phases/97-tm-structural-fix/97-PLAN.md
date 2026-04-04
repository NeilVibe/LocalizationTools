# Phase 97: TM Structural Fix + Full Verification

**Date:** 2026-03-28
**Status:** PLANNED
**Priority:** CRITICAL — blocks production build

---

## Goal

TM system works like Windows folders. Upload in folder = appears in folder = auto-activates for files in that folder. No orphan TMs. Full verification of all v14.0 fixes before build.

## DB State

NUKED CLEAN. 0 TMs, 0 entries, 0 assignments. Fresh start.

---

## Plan

### Task 1: Verify getCurrentScope() wiring
**What:** The header Upload TM button should pass the current folder scope
**Files:** TMExplorerGrid.svelte (getCurrentScope export), TMPage.svelte (header button onclick)
**Test:**
1. Navigate to TM > PC > SampleProject > Korean
2. Click header Upload TM button
3. Check browser DevTools: does the upload modal receive targetScope?
**Pass criteria:** Modal heading shows "Upload TM to Korean"

### Task 2: Verify upload + folder assignment
**What:** Upload a TMX file while inside Korean folder → TM should be assigned to that folder
**Files:** TMUploadModal.svelte (auto-assign code lines 126-149), backend /api/ldm/tm/{id}/assign
**Test:**
1. Upload test TMX inside Korean folder
2. Check API logs for PATCH /tm/{id}/assign?folder_id=97
3. Check TM tree API: TM should appear under Korean folder, NOT unassigned
**Pass criteria:** `curl /api/ldm/tm-tree` shows TM inside Korean folder

### Task 3: Verify TM auto-activation for files
**What:** TM in Korean folder should auto-activate when opening files in that folder
**Files:** server/tools/ldm/routes/files.py (get active TMs), StatusColors.svelte (TM suggestions)
**Test:**
1. Open showcase_items.loc.xml (in Korean folder)
2. Check right panel TM tab: should show "TM ACTIVE: [uploaded TM name]"
3. Select a row → TM suggestions should appear
**Pass criteria:** TM tab shows active TM and provides suggestions

### Task 4: Verify FileUploader spinner fix
**What:** File selection shows checkmark, not infinite spinner
**Files:** TMUploadModal.svelte (status="complete" on both FileUploader instances)
**Test:** Open upload modal, select a file → should show filename with checkmark icon
**Pass criteria:** No spinning circle next to filename

### Task 5: Verify upload progress (no 90% stuck)
**What:** Upload returns instantly, indexing runs in background
**Files:** server/tools/ldm/routes/tm_crud.py (_background_index_tm, upload_response)
**Test:** Upload a file, watch progress → should reach 100% and close within 2 seconds
**Pass criteria:** Modal closes with success, toast shows entry count

### Task 6: Verify Projects endpoint (no 500)
**What:** /api/ldm/projects returns 200 (owner_id made Optional)
**Files:** server/tools/ldm/schemas/project.py
**Test:** `curl /api/ldm/projects` → 200
**Pass criteria:** HTTP 200, valid JSON array

### Task 7: Verify Offline Storage breadcrumb
**What:** TM page: Offline Storage > folder (not Offline Storage > Offline Storage > folder)
**Files:** TMExplorerGrid.svelte (P9 skip project in breadcrumb)
**Test:** Navigate TM > Offline Storage > any folder → check breadcrumb
**Pass criteria:** Breadcrumb shows "Home > Offline Storage > folder_name"

### Task 8: Verify Image chain
**What:** StringID → image thumbnail in right panel
**Test:** `curl /api/ldm/mapdata/image/ITEM_BLACKSTAR_SWORD_NAME` → has_image=true
**Pass criteria:** API returns thumbnail_url

### Task 9: Verify Audio chain
**What:** StringID → audio event → WEM stream
**Test:**
1. `curl /api/ldm/mapdata/audio/DLG_VARON_01` → event_name found
2. `curl /api/ldm/codex/audio/stream/play_varon_greeting_01` → 200, WAV bytes
**Pass criteria:** Both return valid data

### Task 10: Verify Merge modal
**What:** Merge accessible from Apps dropdown, has ignore_spaces/ignore_punctuation toggles
**Test:** Click Apps > Merge to LOCDEV → modal opens with normalization section
**Pass criteria:** Modal shows Normalization toggles

---

## Execution Order

1. Tasks 6, 8, 9 first (API-only, fast curl verification)
2. Task 1, 4 (frontend visual checks)
3. Task 2, 3, 5 (TM upload E2E flow — the critical path)
4. Task 7, 10 (navigation/UI checks)

## Dependencies

- Backend must be running with latest code (restarted earlier with background indexing fix)
- Frontend HMR should have latest Svelte changes
- DB is clean (0 TMs)

## After All Pass

- Commit all changes
- Trigger Gitea build (test)
- If Gitea passes → trigger GitHub `Build Light` (production)
