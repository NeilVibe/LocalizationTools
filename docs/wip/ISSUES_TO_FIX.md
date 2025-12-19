# Issues To Fix

**Last Updated:** 2025-12-19 18:45 | **Build:** 303 | **Next:** 304

---

## Quick Summary

| Status | Count | Items |
|--------|-------|-------|
| **Fixed (verified)** | 3 | BUG-028, BUG-029, BUG-030 |
| **Fixed (Build 304)** | 3 | UI-031, UI-032, FONT-001 |
| **Closed** | 1 | UI-033 |
| **Open UI Issues** | 1 | UI-034 |
| **Decisions Needed** | 2 | UI-027, Q-001 |

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

### UI-031: Font Size Setting - FIXED (Build 304)

**Component:** Display Settings → VirtualGrid
**Problem:** Changing font size didn't affect the grid.
**Root Cause:** `VirtualGrid.svelte` had hardcoded `font-size: 0.8125rem` in CSS, ignored preferences.

**Fix Applied:**
1. Added `$derived` values for font styles from preferences store
2. Applied CSS custom properties `--grid-font-size` and `--grid-font-weight`
3. Updated `.cell` CSS to use these variables

**Files Changed:**
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte`

**Status:** ✅ Fixed - awaiting Build 304 verification

---

### UI-032: Bold Setting - FIXED (Build 304)

**Component:** Display Settings → VirtualGrid
**Problem:** Toggling bold didn't affect the grid.
**Root Cause:** Same as UI-031 - preferences not connected to grid CSS.

**Fix Applied:** Same fix as UI-031 (both use `--grid-font-weight` CSS variable)

**Status:** ✅ Fixed - awaiting Build 304 verification

---

### FONT-001: Multilingual Font Stack - FIXED (Build 304)

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

**Status:** ✅ Fixed - awaiting Build 304 verification

---

### UI-034: Tooltips Cut Off at Window Edge

**Component:** Global (all tooltips)
**Problem:** White tooltip bubbles get cut off when near window edge (especially right side).
**Example:** Settings button tooltip on far right is cut off.
**Solution:** Implement smart tooltip positioning - auto-adjust placement so tooltip is always fully visible.

---

## Decisions Needed

### UI-027: Confirm Button - Keep or Remove?

**Component:** TM Viewer
**Current Status:** KEEP - memoQ-style workflow for confirming TM entries.
**Question:** Is this useful for your workflow, or just clutter?

Options:
1. Keep as-is
2. Remove entirely
3. Make optional via settings

---

### Q-001: TM Sync - Automatic or Manual?

**Question:** Should TM indexes auto-sync when TM changes?
**Current:** Manual "Sync Indexes" button.
**User Opinion:** Should be automatic for Model2Vec (fast, cheap).

Options:
1. Auto-sync on any TM change
2. Keep manual button
3. Auto-sync with debounce (wait for user to stop editing)

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

*Updated 2025-12-19 18:50 | 0 critical, 0 bugs open, 3 UI open, 2 decisions*
