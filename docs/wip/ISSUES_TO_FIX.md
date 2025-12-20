# Issues To Fix

**Last Updated:** 2025-12-20 16:30 | **Build:** 307 (v25.1220.1551) | **Next:** 308

---

## Quick Summary

| Status | Count | Items |
|--------|-------|-------|
| **Fixed (verified)** | 10 | BUG-028, BUG-029, BUG-030, BUG-031, UI-031, UI-032, FONT-001, UI-034, UI-027, Q-001 |
| **Closed** | 1 | UI-033 |
| **Open** | 0 | None |

---

## Fixed - Build 303

### BUG-030: WebSocket Shows Disconnected - VERIFIED FIXED

**Component:** Server Status Panel
**Problem:** Always showed "WebSocket: disconnected" even when connected.

**Root Cause:** Nested try/except import structure in `get_websocket_stats()` failed silently.

**Fix Applied (Build 303):**
```python
# Before (broken):
from server.utils.websocket import sio
# ...
try:
    from server.utils.websocket import connected_clients
except: pass

# After (working):
from server.utils.websocket import sio, connected_clients
```

**Status:** ✅ Verified fixed in Build 303 (v25.1219.1829)

---

## Open UI Issues

### UI-031: Font Size Setting - ✅ VERIFIED (Build 304)

**Component:** Display Settings → VirtualGrid
**Problem:** Changing font size didn't affect the grid.
**Root Cause:** `VirtualGrid.svelte` had hardcoded `font-size: 0.8125rem` in CSS, ignored preferences.

**Fix Applied:**
1. Added `$derived` values for font styles from preferences store
2. Applied CSS custom properties `--grid-font-size` and `--grid-font-weight`
3. Updated `.cell` CSS to use these variables

**Verified:** 2025-12-20 via CDP test
- Small: 12px → Large: 16px ✅

---

### UI-032: Bold Setting - ✅ VERIFIED (Build 304)

**Component:** Display Settings → VirtualGrid
**Problem:** Toggling bold didn't affect the grid.
**Root Cause:** Same as UI-031 - preferences not connected to grid CSS.

**Fix Applied:** Same fix as UI-031 (both use `--grid-font-weight` CSS variable)

**Verified:** 2025-12-20 via CDP test
- Normal: 400 → Bold: 600 ✅

---

### FONT-001: Multilingual Font Stack - ✅ VERIFIED (Build 304)

**Component:** Global (app.css)
**Problem:** IBM Plex Sans doesn't support CJK/Cyrillic/Indic glyphs natively.
**Impact:** Non-Latin text might render with inconsistent fallback fonts.

**Fix Applied:** Complete multilingual font stack in `app.css`:

**Script Coverage:**

| Script | Languages | Windows Font | Noto Fallback |
|--------|-----------|--------------|---------------|
| **Latin** | English, French, German, Spanish, Portuguese, Italian, Polish, Dutch, Indonesian, Vietnamese, etc. | Segoe UI | Noto Sans |
| **Cyrillic** | Russian, Ukrainian, Bulgarian, Serbian, Macedonian, Belarusian | Segoe UI | Noto Sans |
| **Greek** | Greek | Segoe UI | Noto Sans |
| **CJK** | Korean | Malgun Gothic | Noto Sans CJK KR |
| | Chinese (Simplified) | Microsoft YaHei | Noto Sans CJK SC |
| | Chinese (Traditional) | Microsoft JhengHei | Noto Sans CJK TC |
| | Japanese | Meiryo, Yu Gothic | Noto Sans CJK JP |
| **Thai** | Thai | Leelawadee UI | Noto Sans Thai |
| **Arabic** | Arabic, Persian, Urdu | Segoe UI | Noto Sans Arabic |
| **Hebrew** | Hebrew | Segoe UI | Noto Sans Hebrew |
| **Indic** | Hindi, Marathi, Sanskrit | Nirmala UI | Noto Sans Devanagari |
| | Bengali | Nirmala UI | Noto Sans Bengali |
| | Tamil | Nirmala UI | Noto Sans Tamil |
| | Telugu | Nirmala UI | Noto Sans Telugu |
| **Caucasian** | Georgian | Segoe UI | Noto Sans Georgian |
| | Armenian | Segoe UI | Noto Sans Armenian |
| **Emoji** | All | Segoe UI Emoji | Noto Color Emoji |

**Total:** 100+ languages via system fonts + Noto fallbacks

**Files Changed:**
- `locaNext/src/app.css`

**Status:** ✅ VERIFIED - Build 304 installed, fonts render correctly

---

### UI-034: Tooltips Cut Off at Window Edge - ✅ FIXED (Build 305)

**Component:** Global (all tooltips)
**Problem:** White tooltip bubbles get cut off when near window edge (especially right side).
**Example:** Settings button tooltip on far right is cut off.

**Fix Applied:**
1. Added `tooltipAlignment="end"` to all right-side buttons:
   - LDM toolbar buttons (TM, Grid Columns, Reference Settings, Server Status, Display Settings)
   - GlobalStatusBar action buttons
   - TMManager, TMViewer, TMDataGrid action buttons
2. Added CSS rules to constrain tooltips to viewport

**Files Changed:**
- `locaNext/src/lib/components/apps/LDM.svelte`
- `locaNext/src/lib/components/GlobalStatusBar.svelte`
- `locaNext/src/lib/components/ldm/TMManager.svelte`
- `locaNext/src/lib/components/ldm/TMViewer.svelte`
- `locaNext/src/lib/components/ldm/TMDataGrid.svelte`
- `locaNext/src/app.css`

**Status:** ✅ VERIFIED - Build 305 (v25.1220.1414)
**Verified:** 2025-12-20 via CDP test - all right-side buttons have `tooltipAlignment="end"`

---

## Verified (Build 306)

### UI-027: Confirm Button - ✅ VERIFIED REMOVED

**Decision:** Remove entirely
**Reason:** Simplifies UI - auto-save without confirmation step
**Implementation:** Removed Confirm/Unconfirm button from TMViewer.svelte
**Verified:** 2025-12-20 via source grep - no toggleConfirm function, no Confirm button

---

### Q-001: TM Sync - ✅ VERIFIED AUTO-SYNC (LIVE-TESTED)

**Decision:** Auto-sync on any TM change
**Reason:** Model2Vec is fast (~29k sentences/sec) - sync automatically
**Implementation:** Added background task auto-sync to:
- `add_tm_entry` endpoint
- `update_tm_entry` endpoint
- `delete_tm_entry` endpoint
**Verified:** 2025-12-20 via source grep - _auto_sync_tm_indexes in all three endpoints
**Live-Tested:** 2025-12-20 - Backend logs show: `Auto-sync TM 131: INSERT=6, UPDATE=0, time=13.05s`

---

### BUG-031: TM Upload Response Error - ✅ FIXED (Build 307)

**Problem:** `AttributeError: 'dict' object has no attribute 'entry_count'`
**Root Cause:** In `api.py` line 1069, `result.entry_count` was used but `result` is a dict.
**Fix:** Changed to `result['entry_count']`
**Verified:** 2025-12-20 - TM upload works, auto-sync triggers correctly

---

## Completed (Build 301)

| ID | Description | Verified |
|----|-------------|----------|
| BUG-028 | Model2Vec pip install in build.yml | ✅ CDP tested |
| BUG-029 | Upload as TM context menu fix | ✅ CDP tested |
| UI-025 | Removed "Items per page" selector | ✅ |
| UI-026 | Removed pagination, added infinite scroll | ✅ |
| UI-028 | Removed "Showing rows X-Y" | ✅ |
| UI-029 | Removed download menu from VirtualGrid | ✅ |
| UI-030 | Info button removal (was already removed) | ✅ |
| UI-033 | App Settings NOT empty (has Preferences) | ✅ Closed |

---

## Completed (Earlier Builds)

| ID | Description | Build |
|----|-------------|-------|
| BUG-023 | MODEL_NAME NameError fix | 300 |
| FEAT-005 | Model2Vec default engine | 300 |
| PERF-001 | Incremental HNSW | 300 |
| PERF-002 | FAISS factorization | 300 |
| UI-024 | Dynamic engine name in build modal | 300 |
| Lazy Import | CI timeout fix (kr_similar) | 300 |

---

## Model2Vec Info

**Model:** `minishlab/potion-multilingual-128M`
- 101 languages (Korean ✅)
- 29,269 sentences/sec
- 256 dimensions
- MIT license

This is the most powerful multilingual Model2Vec model available.

---

*Updated 2025-12-20 16:30 | 0 critical, 0 bugs open, 0 UI open, all verified*
