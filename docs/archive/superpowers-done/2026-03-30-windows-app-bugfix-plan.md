# Windows App Bugfix Plan — 2026-03-30

From full Windows app log analysis + user testing on <PC_NAME> PC.

## Already Fixed (in working tree, not yet committed)

### FIX-1: Frontend Shows "Model2Vec UNAVAILABLE" / "FAISS UNAVAILABLE" Despite Backend Having Them
**File:** `locaNext/src/lib/stores/aiCapabilityStore.svelte.ts:41`
**Root cause:** Backend log PROVES Model2Vec is loaded (`Model2Vec loaded: dim=256`). But the frontend store fetches capabilities from `"/api/ldm/ai-capabilities"` (relative URL). In Electron, this resolves to `app://./api/ldm/ai-capabilities` — Electron's protocol handler tries to serve it as a FILE, never hits `localhost:8888`. Fetch fails → catch block sets everything to "unavailable".
**Fix:** Changed to `fetch(\`${getApiBase()}/api/ldm/ai-capabilities\`)` — same pattern all other stores use.
**Result after fix:** Frontend will correctly show Model2Vec = available, FAISS = available.

### FIX-2: Factory.py Deadlock (_ModuleLock) — CRITICAL CRASH
**File:** `server/repositories/factory.py`
**Root cause:** All 9 factory functions use lazy `from server.repositories.sqlite.X import Y` inside function body. When 2+ concurrent requests hit at startup (e.g., GET /api/ldm/projects + GET /api/ldm/platforms simultaneously), Python's module lock deadlocks on `_ModuleLock('server.repositories.sqlite.platform_repo')`.
**Log evidence:** `_frozen_importlib._DeadlockError: deadlock detected by _ModuleLock('server.repositories.sqlite.platform_repo')`
**Fix:** Moved all SQLite imports to top-level (eager). PostgreSQL imports stay lazy (only needed when PG available).

### FIX-3: Export Event Parser Case-Sensitivity (Audio chain broken) — CRITICAL
**File:** `server/tools/ldm/services/mega_index_data_parsers.py:259-266`
**Root cause:** MegaIndex used `elem.get("SoundEventName")` (exact CamelCase). MDG uses `{k.lower(): v for k, v in elem.attrib.items()}` (case-insensitive). If XML has `soundeventname` or `SOUNDEVENTNAME`, MegaIndex misses it → 0 events → R3 (stringid_to_event) empty → C2/C3 audio lookup = 0.
**MDG reference:** `core/linkage.py:997-1001` — AudioIndex.load_event_mappings()
**Fix:** Grafted MDG's case-insensitive attr extraction pattern.

### FIX-4: MegaIndex Debug Logging Improvements
**Files:** `mega_index.py`, `mega_index_entity_parsers.py`, `mega_index_data_parsers.py`
**What:** Added per-file extraction counts for faction/skill/gimmick parsers, export .loc.xml parse logging, singleton init logging, upgraded all `except Exception` blocks from `logger.warning` to `logger.exception` (includes tracebacks).

---

## Needs Fixing

### BUG-5: Multi-Language Audio Folders (MDG has 3, LocaNext has 1)
**Severity:** HIGH — audio panel shows nothing for non-English languages
**What MDG does (config.py:143-145, 192-201):**
- 3 audio folders on disk:
  - `English(US)` → `F:\perforce\cd\mainline\resource\sound\windows\English(US)`
  - `Korean` → `F:\perforce\cd\mainline\resource\sound\windows\Korean`
  - `Chinese(PRC)` → `F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)`
- Language-to-audio-folder routing:
  - **Latin** (eng, fre, ger, spa-es, spa-mx, por-br, ita, rus, tur, pol) → **English(US)** audio
  - **KOR, JPN, ZHO-TW** → **Korean** audio
  - **ZHO-CN** → **Chinese(PRC)** audio

**What LocaNext does now:**
- Only scans ONE audio folder (English(US)) hardcoded in path resolution
- No language→audio folder mapping
- Even after FIX-3, only English audio would be found

**Audio lookup chain (how it SHOULD work, matching MDG):**
```
User opens file (e.g., languagedata_FRE.loc.xml)
  → File language = FRE (French)
  → Audio folder = English(US) [Latin language → English audio]

User clicks row (StringID = "12345678901234567")
  → R3: stringid_to_event["12345678901234567"] = "vo_quest_001_greeting"
  → D10: wem_by_event_en["vo_quest_001_greeting"] = Path("F:\...\English(US)\vo_quest_001_greeting.wem")
  → Context panel plays that WEM file

For Korean file (languagedata_KOR.loc.xml):
  → Audio folder = Korean
  → wem_by_event_kr["vo_quest_001_greeting"] = Path("F:\...\Korean\vo_quest_001_greeting.wem")
```

**Fix needed:**
1. Add 3 audio folder paths to MegaIndex path config
2. Scan all 3 folders into separate dicts: `wem_by_event_en`, `wem_by_event_kr`, `wem_by_event_zh`
3. Add `LANG_TO_AUDIO` mapping (same as MDG)
4. `get_audio_path_by_stringid(string_id, file_language)` picks the right dict
5. Frontend passes current file's language when requesting audio

**Files to modify:**
- `server/tools/ldm/services/mega_index.py` — path resolution (add kr/zh audio folders)
- `server/tools/ldm/services/mega_index_data_parsers.py` — scan 3 audio folders
- `server/tools/ldm/services/mega_index_builders.py` — build per-language audio lookups
- `server/tools/ldm/services/mega_index_api.py` — `get_audio_path_by_stringid(sid, lang)` routes to correct dict
- `server/tools/ldm/services/context_service.py` — pass language when resolving audio
- `server/tools/ldm/routes/mega_index.py` — audio endpoint accepts language param

### BUG-6: Image Fallback — Korean Text Matching When StringID Has No Image
**Severity:** MEDIUM — missed image opportunities
**Current behavior:** StringID → C7 (stringid_to_entity) → entity strkey → C1 (strkey_to_image_path). If no entity for that StringID, no image shown.
**Proposed enhancement (user request):**
1. **Primary:** StringID → entity → image (current, label: "Matched via StringID")
2. **Fallback:** Korean text (StrOrigin/source) → R1 (name_kr_to_strkeys) → first entity → image (label: "Matched via Korean text")
3. Context panel shows a small badge indicating which method matched

**Implementation:**
- `context_service.py` `resolve_chain()` — add fallback step after StringID lookup fails
- Use R1 (`name_kr_to_strkeys`) to find entities by Korean name
- Return `match_method: "stringid" | "korean_text"` in chain result
- Frontend shows "Matched via StringID" or "Matched via Korean" badge

### BUG-7: "LocaNext Status" Menu Needed — AI Status NOT in Preferences
**Severity:** MEDIUM — UX overhaul
**User request:** Move all system status OUT of Preferences into a dedicated "LocaNext Status" view:
- Server connection status (online/offline/sqlite)
- AI Engine status (Model2Vec available/unavailable, FAISS, Qwen3)
- MegaIndex status (built/not built, entry counts per type)
- Database status (PG/SQLite, tables, row counts)
- Version info

**Current state:** AI badges are in Display Settings / Preferences modal. StatusPage component was created in session 2026-03-29c but may not be wired into navigation.

**Fix:**
1. Verify StatusPage component exists and has AI status
2. Wire it into the navigation sidebar/menu
3. Move AI capability badges FROM Preferences TO StatusPage
4. Remove AI section from Preferences

### BUG-8: Merge Direction Wrong — Right-Click = SOURCE Not TARGET
**Severity:** HIGH — core workflow confusion
**Current:** Right-click file → Merge → file treated as TARGET (destination to merge into).
**User's mental model:** Right-click file = SOURCE (the file with corrections). Then pick TARGET via file dialog.
**Fix:** Reverse the merge flow:
- Right-clicked file = `source_file` (has corrections)
- File picker dialog = `target_file` (file to merge into)
- Update FileMergeModal props and API call accordingly

### BUG-9: CATEGORY Column Too Narrow + No Resize Handle
**Severity:** LOW — UX annoyance
**Two issues:**
1. Default width too narrow — "Character" shows as "Characte" (cut off)
2. Column resize drag handle not working — can't manually widen like Excel

**Fix:**
1. Increase default CATEGORY column width (find in VirtualGrid column config)
2. Verify `resizable: true` in column definition
3. Check if resize handle CSS is missing or broken for that column

### BUG-10: "Project Settings" Menu Item is DEAD
**Severity:** LOW — dead UI
**Current:** Clicking "Project Settings" in settings menu leads to nothing.
**Fix:** Either wire it properly or remove the dead menu item.

### BUG-11: About LocaNext Version is Hardcoded/Outdated
**Severity:** MEDIUM — confusing for users
**Fix:** Auto-detect version from `window.electronAPI.getVersion()` or build-time injection. Must always match the actual build version (e.g., "26.329.0300").

### BUG-12: About LocaNext Cleanup
**Severity:** LOW — polish
**Remove:**
- "XLS Transfer + QuickSearch + KRSimilar" tool listing (internal, not user-facing)
- "Localization Team" section at bottom
- "Release: Production" label
**Add:**
- "Created by Neil Schmitt"
**Keep:**
- LocaNext name/logo, auto version, brief description

---

## Priority Order for Implementation

| Priority | Issue | Type | Effort |
|----------|-------|------|--------|
| 1 | FIX-2: Deadlock | DONE in working tree | - |
| 2 | FIX-3: Case-sensitive events | DONE in working tree | - |
| 3 | FIX-1: AI caps fetch URL | DONE in working tree | - |
| 4 | FIX-4: Logging improvements | DONE in working tree | - |
| 5 | BUG-5: Multi-language audio | NEW — implement | HIGH |
| 6 | BUG-6: Image Korean fallback | NEW — implement | MEDIUM |
| 7 | BUG-7: Remove dead AI Status from Preferences (StatusPage exists!) | NEW — cleanup | LOW |
| 8 | BUG-8: Merge direction | NEW — implement | HIGH |
| 9 | BUG-9: Category column | NEW — implement | LOW |
| 10 | BUG-10: Dead "Project Settings" menu item | NEW — cleanup | LOW |
| 11 | BUG-11: About version auto-detect | NEW — implement | MEDIUM |
| 12 | BUG-12: About cleanup + "Created by Neil Schmitt" | NEW — cleanup | LOW |

---

## NEW Issues from <PC_NAME> PC Testing Round 2 (2026-03-30 session 2)

### Phase 100 Completed (bugs 1-12 + case-insensitive)
All committed and built. Post-build review found + fixed: frontend language wiring, image C7 chain, health.py counts, test mocks, inline editor Space/Enter.

### BUG-13: Merge matches IDENTICAL strings — 169,650 unnecessary updates (CRITICAL)
**Severity:** CRITICAL — core workflow broken, 42s wasted on no-ops
**Evidence:** `matched: 169650, skipped: 233, total: 203965, rows_updated: 169650`
**Root cause:** LocaNext merge does NOT skip identical rows. QuickTranslate's `core/transfer.py` ONLY transfers corrections where target DIFFERS. LocaNext overwrites all matching rows even if target is already correct.
**Fix:** Deep graft of QT `core/transfer.py` logic into `server/services/merge/translator_merge.py`:
- Skip identical (source match + target identical = no-op)
- Only transfer differences (source match + target DIFFERS = correction)
- Per-row logging with old→new values
- Match type tracking per row
- Dry run mode (preview before commit)
- Progress callback for streaming feedback

### BUG-14: Merge modal shows NO progress — just infinite loading (HIGH)
**Severity:** HIGH — 42 seconds of blank spinner, user has zero feedback
**Fix:**
- Backend: streaming SSE or WebSocket progress during merge (row count, %, match types)
- Frontend: FileMergeModal shows live progress bar with counts
- At minimum: periodic log updates visible to user

### BUG-15: Merge logging has FORMAT STRING BUG (MEDIUM)
**Severity:** MEDIUM — `%d` and `%s` placeholders not interpolated
**Evidence:** `[MERGE] Merge request: target_file=%d, source_file=%d, mode=%s, threshold=%.2f`
**Fix:** Change `%d` to f-string or .format() in merge route logging

### BUG-16: Merge options silently dropped by backend (HIGH)
**Severity:** HIGH — UI shows transfer_scope, all_categories, non_script_only, ignore_spaces, etc. but MergeRequest Pydantic model doesn't have those fields
**Fix:** Either extend MergeRequest + TranslatorMergeService or remove UI options that don't work

### BUG-17: Inline editor Space blocked (FIXED — commit 75fd23a9)
Row onkeydown intercepted Space during editing. Fixed with !inlineEditingRowId guard.

### BUG-18: Inline editor Enter saves instead of linebreak (FIXED — commit 75fd23a9 + session fix)
Enter now inserts visual linebreak. **Session fix:** `document.execCommand('insertText', '<br/>')` was inserting LITERAL TEXT. Changed to `insertHTML '<br>'` for actual HTML line break.

### BUG-19: TM suggest spam loop during editing (FIXED — session 2026-03-30 evening)
**Root cause:** Every save-and-move-next called `onRowSelect({row})` → triggered TM+context API calls.
**Fix:** Added `isEditing: true` flag to onRowSelect from InlineEditor. GridPage skips TM fetch when flag is set.

### BUG-19b: Save freeze during editing (FIXED — session 2026-03-30 evening)
**Root cause:** `saveRowToAPI` awaited HTTP PUT before updating local state. 200-500ms freeze per save. Then `rebuildCumulativeHeights` fired synchronously on 100k+ rows.
**Fix:** Optimistic UI — local state updates instantly, API fires async, revert on failure. Height rebuild deferred to `requestAnimationFrame`.

### BUG-19c: Blur+keyboard double-save race (FIXED — session 2026-03-30 evening)
**Root cause:** Tab/Enter fires keyboard save AND contenteditable blur fires another save simultaneously.
**Fix:** Added `isSaving` boolean mutex guard to `saveInlineEdit` and `confirmInlineEdit`.

### BUG-20: Cell distortion / addRange() warning during editing (LOW)
**Severity:** LOW — `addRange(): The given range isn't in document` renderer warning
**May be fixed** by BUG-17/18 fixes (Space/Enter no longer fight between handlers)

### BUG-21: Merge COMPLETELY BROKEN — target file NOT modified after merge (CRITICAL)
**Severity:** CRITICAL — merge completes with "success" but file is unchanged
**Evidence:** User completed merge, got success toast with 169,650 matched, but target file had ZERO modifications. Nothing changed at all.
**Possible causes:**
1. BUG-8 merge direction reversal broke data flow (source/target IDs swapped incorrectly)
2. bulk_update wrote to source file rows instead of target file rows
3. Rows updated in DB but file not re-exported/refreshed on disk
4. The "updated" rows had identical content (BUG-13) so no visible change
**MUST INVESTIGATE:** Read the full merge flow: FileMergeModal → route → translator_merge.py → row_repo.bulk_update

### BUG-22: QuickTranslate "make file writable" technique NOT grafted (HIGH)
**Severity:** HIGH — QT has battle-tested file handling that LocaNext doesn't use
**What QT does:**
- `make_file_writable()` before ANY write operation
- Checks file permissions, removes read-only flag
- Handles Windows file locking gracefully
- Creates backup before modification
**What LocaNext does:** Unknown — needs research
**Fix:** Graft QT's file writable pattern into LocaNext merge/export flows

### BUG-23: QuickTranslate merge logic NOT fully grafted (CRITICAL)
**Severity:** CRITICAL — the CORE merge algorithm doesn't match QT
**QT battle-tested behaviors that must be grafted:**
1. `parse_corrections()` — builds correction dict from source file
2. `apply_corrections()` — iterates target, ONLY modifies rows where target DIFFERS
3. Skip identical — source match + target identical = no-op, not a "match"
4. Normalization — whitespace, br-tags, placeholders normalized before comparison
5. Transfer scope filtering (all / only untranslated / only different)
6. Category filtering (script / non-script / all)
7. Statistics — transferred count, skipped count, identical count, error count
8. Per-row detailed log — which rows changed, old→new values
9. Dry run — preview mode before committing
10. Make file writable before write
**Research needed:** 8 parallel Explore agents on QT core/transfer.py, core/matching.py, core/normalization.py

### Priority Order for Remaining Work (Phase 101)

| Priority | Issue | Status | Phase |
|----------|-------|--------|-------|
| 1 | BUG-21: Merge target unchanged | **ROOT CAUSE FOUND** — no identical-skip | 101-01 |
| 2 | BUG-13: Merge matches identical strings | **SAME ROOT CAUSE** as BUG-21 | 101-01 |
| 3 | BUG-23: QT merge logic not grafted | **PLAN WRITTEN** — identical-skip graft | 101-01 |
| 4 | BUG-16: Merge options silently dropped | **PLAN WRITTEN** — extend MergeRequest | 101-02 |
| 5 | BUG-14: Merge no progress feedback | **PLAN WRITTEN** — detailed results | 101-02 |
| 6 | BUG-15: Merge format string bug | **FALSE ALARM** — Python % format is correct | N/A |
| 7 | BUG-22: Make file writable not grafted | **N/A** — LocaNext writes to DB, not disk | N/A |
| 8 | BUG-19: TM suggest spam during editing | **FIXED** (session 2026-03-30 evening) | done |
| 9 | BUG-19b: Save freeze during editing | **FIXED** (optimistic UI) | done |
| 10 | BUG-19c: Blur+keyboard double-save | **FIXED** (isSaving guard) | done |
| 11 | BUG-20: Cell distortion | MAYBE FIXED | verify |

### Research Findings (2026-03-30 evening)

**BUG-21 + BUG-13 ROOT CAUSE:** `translator_merge.py` has NO identical-skip check. When `matched_text == existing target`, it still adds to `updated_rows` and bulk_updates DB. All 169,650 rows got "updated" with the same value. Nothing visibly changed. QT has `if new_str != old_str: update else: UNCHANGED` (xml_transfer.py L574).

**BUG-15 FALSE ALARM:** The `%d/%s` logging in merge.py uses Python % formatting which loguru handles correctly. Not a bug.

**BUG-22 N/A:** QT's `make_file_writable()` is for on-disk XML writes. LocaNext merge writes to PostgreSQL via `RowRepository.bulk_update()`. No file permission issue.

**GSD Plans:** `.planning/phases/101-merge-deep-graft/101-01-PLAN.md` (core fix) + `101-02-PLAN.md` (options + progress)

---

## What IS Working Perfectly (confirmed by log)

- Model2Vec detection + loading: dim=256 ✓
- MegaIndex 7-phase build in 15.06s ✓
- Knowledge: 5,288 + 513 groups ✓
- Characters: 7,998 ✓
- Items: 6,158 ✓
- Regions: 1,158 ✓
- Factions: 135 (7 groups) ✓
- Skills: 1,722 ✓
- Gimmicks: 13,540 ✓
- DDS textures: 21,142 ✓
- WEM files: 57,535 (scanned) ✓
- StrOrigins: 173,675 ✓
- Export .loc.xml: 1,811 files ✓
- Images (C1): 3,005 resolved ✓
- Entity↔StringID (C6/C7): 26,251 / 55,552 ✓
- SQLite offline mode ✓
- Backend startup: 12s ✓
- GameData browse: working ✓
- WebSocket: connected after MegaIndex build ✓
- Per-file logging for faction/skill/gimmick: showing in log ✓
- Singleton MegaIndex init logging: showing in log ✓
