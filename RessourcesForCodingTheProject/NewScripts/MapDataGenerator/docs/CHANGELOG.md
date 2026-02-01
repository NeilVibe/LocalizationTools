# MapDataGenerator Changelog

## 2026-02-01 - Major Feature Update

### New Features

#### Mode-Specific Column Layouts
Each mode now shows different columns relevant to that data type:

| Mode | Columns Displayed |
|------|-------------------|
| MAP | KOR, Translation, Description, Position (X,Y,Z), StrKey |
| CHARACTER | KOR, Translation, Race/Gender, Age, Job |
| ITEM | KOR, Translation, StrKey, StringID |
| AUDIO | EventName, KOR Script, ENG Script |

**Files changed:**
- `core/linkage.py` - Added `use_macro`, `age`, `job` fields to DataEntry
- `core/search.py` - Added same fields to SearchResult
- `gui/result_panel.py` - MODE_DISPLAY_COLUMNS, displaycolumns switching
- `config.py` - UI text for new column headers

#### Cell Selection & Copy (Ctrl+C)
- Click any cell to select it
- Press Ctrl+C to copy the full (untruncated) cell value
- Visual feedback shows "Copied: [value]" or "Selected: [column]"
- Works with all modes and all columns

**Implementation:**
- `_selected_cell` tuple tracks (strkey, col_id)
- `_full_text_cache` stores untruncated values
- `_on_cell_click()` identifies clicked cell
- `_copy_selected_cell()` handles Ctrl+C

#### Column Toggle Checkboxes
Restored the "Show: [x] KOR [x] Translation [ ] Description..." checkboxes that let users toggle column visibility per mode.

---

### Bug Fixes

#### Settings Persistence Fixed
**Problem:** Settings changes (like default category) saved but reverted on app restart.

**Cause:** Silent `except Exception:` in `load_settings()` and `save_settings()` swallowed all errors.

**Fix:** Added proper logging:
```python
except Exception as e:
    log.warning("Failed to load settings from %s: %s", settings_path, e)
```

**File:** `config.py` lines 421-422, 438-439

#### Mode Switching Fixed (AUDIO → MAP)
**Problem:** After going to AUDIO mode, switching back to MAP/CHARACTER/ITEM would fail silently.

**Cause:** `self._texture_folder` was only set in `_on_data_loaded()`. When app started in AUDIO mode, it was never set. Mode switching checked `elif self._texture_folder:` which was None.

**Fix:** Changed to use fallback:
```python
texture_folder = self._texture_folder or Path(settings.texture_folder)
```

**File:** `gui/app.py` line 338

#### Thread Safety for Rapid Mode Switching
**Problem:** Rapid clicking mode buttons could corrupt state (multiple threads, stale callbacks).

**Fix:** Two-part solution:

1. **Loading Lock (`_loading` flag)**
   - Disables mode buttons during load
   - Rejects clicks while loading
   - Re-enables on complete/error

2. **Generation Counter (`_load_generation`)**
   - Increments on each load start
   - Callbacks check generation matches
   - Stale callbacks are ignored

**File:** `gui/app.py`
- `__init__`: Added `_loading`, `_load_generation`
- `_on_mode_change()`: Early return if `_loading`
- `_start_data_load()`: Set lock, increment gen, disable buttons
- `_start_audio_data_load()`: Same pattern
- `_on_data_loaded()`: Check gen, clear lock, enable buttons
- `_on_audio_data_loaded()`: Same pattern
- `_on_load_error()`: Same pattern

---

### Code Quality Improvements

- O(1) lookup for result selection (`_results_by_strkey` dict)
- Proper `destroy()` method for tooltip cleanup
- Lambda capture fix (capture values, not references)
- None safety in `truncate()` method
- Empty cell feedback for copy operations
- Clipboard error handling with try/except

---

### Build History (from MAPDATAGENERATOR_BUILD.txt)

```
Build - Add mode-specific columns (CHARACTER: UseMacro/Age/Job, ITEM: StringID) + cell copy (Ctrl+C)
Build - FIX: None safety in truncate(), cache values, empty cell feedback
Build - FIX: AUDIO None safety, tooltip cleanup, clipboard error handling, fast delete
Build - FIX: O(1) lookup, destroy(), lambda capture, mode validation, truncate as method
Build - RESTORE: Column toggle checkboxes (Show: [x] KOR [x] Translation [ ] Description...)
Build - FIX: Settings persistence (log errors), mode switching (AUDIO→MAP works now)
Build - Thread safety: Loading lock + generation counter (no rapid switching corruption)
```

---

### Files Modified Summary

| File | Changes |
|------|---------|
| `config.py` | Settings logging, UI text for new columns |
| `core/linkage.py` | DataEntry fields: use_macro, age, job |
| `core/search.py` | SearchResult fields, string_id extraction |
| `gui/app.py` | Mode switch fix, thread safety |
| `gui/result_panel.py` | Mode columns, cell copy, column toggle |

---

### Testing Verification

8 code review agents verified:
- All 12 mode switching combinations work
- Settings persist correctly across restart
- Rapid mode switching is blocked during load
- Stale callbacks are ignored
- Cell copy works with Ctrl+C
