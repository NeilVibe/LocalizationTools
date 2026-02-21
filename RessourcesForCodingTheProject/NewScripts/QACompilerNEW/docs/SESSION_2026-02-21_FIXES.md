# QACompiler Session - 2026-02-21

## Summary

GUI layout fix + critical tracker bug fix + robustness improvements.

## Changes Made

### 1. GUI: Window Height 1000 → 1100 + Centering
**File:** `gui/app.py`
- `WINDOW_HEIGHT` changed from 1000 to 1100
- Added window centering logic (`winfo_screenwidth/height` calculation)
- Removed static "Ready" text from status bar (was taking up space for no reason)
- Status bar still functions during operations (30+ references use it)
- Section 6 (Update Tracker Only) now fully visible without compression

### 2. CRITICAL FIX: Word Count Dead Code Bug
**File:** `core/tracker_update.py` (lines ~235-263)
- **Problem:** Word counting block was accidentally nested inside a debug-only `else` branch that only executed for Script categories when NO status rows existed. It was dead code for ALL practical scenarios.
- **Impact:** `word_count` was always 0 for ALL categories in tracker-update mode. Words/Chars columns in tracker were empty.
- **Fix:** Moved word counting block inside the main `for row` loop, inside the `if status_value:` block, so it runs for ALL categories and ALL rows with valid status.

### 3. Robustness: try/finally for Workbook Close
**File:** `core/tracker_update.py` (function `count_qa_folder_stats`)
- **Problem:** If `count_sheet_stats()` raised an exception, the workbook opened via `safe_load_workbook()` was never closed, leaking file handles.
- **Fix:** Wrapped the sheet processing loop in `try/finally` to ensure `wb.close()` is always called.

### 4. Fix Bare `except:` Clauses
**Files:** `core/tracker_update.py` (line 82), `tracker/data.py` (line 235)
- **Problem:** Bare `except:` catches everything including `KeyboardInterrupt` and `SystemExit`.
- **Fix:** Changed to `except Exception:` in both locations.

## Files Modified
- `gui/app.py` — GUI height, centering, status bar
- `core/tracker_update.py` — Word count fix, try/finally, bare except
- `tracker/data.py` — Bare except fix

## Review Notes
- All 5 review agents independently confirmed the word count bug
- No functional logic was changed in how statuses are counted (ISSUE/NO ISSUE/etc.)
- The GUI status bar is preserved for operation progress (only "Ready" initial text removed)
- Window centering uses standard tkinter approach
