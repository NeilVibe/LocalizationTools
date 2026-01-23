# BUG: Dialog QA Files Missing MEMO Column

**Status:** CONFIRMED BUG
**Priority:** HIGH
**Date Found:** 2026-01-24
**Evidence:** Logs `SCRIPT DEBUGLOG FOR CLAUDE 0123 2300.txt`

---

## Problem

Dialog category tester comments are NOT being written to Master file because Dialog QA files don't have a MEMO column.

---

## Evidence from Logs

### Sequencer (WORKS)
```
[PROCESS_SHEET] Sequencer/EN SCRIPT SEQUENCER.xlsx/유지윤
  QA MEMO column: 8        ✅ HAS MEMO
  comments written: 30     ✅ COMMENTS WRITTEN
```

### Dialog (BROKEN)
```
[PROCESS_SHEET] Dialog/김정원_Dialog.xlsx/김정원
  QA MEMO column: None     ❌ NO MEMO COLUMN
  comments written: 0      ❌ NO COMMENTS WRITTEN
```

---

## Root Cause

The Master_Script.xlsx has TWO different sheet structures:

### English Script (Sequencer data)
```
Col 1: DialogType
Col 2: Group
Col 3: SequenceName
Col 4: DialogVoice
Col 5: RECORDING
Col 6: Text
Col 7: MEMO           ← HAS MEMO
Col 8: EventName
Col 9: COMMENT_유지윤
...
```

### Work Transform (Dialog data)
```
Col 1: DialogType
Col 2: Group
Col 3: SequenceName
Col 4: DialogVoice
Col 5: RECORDING
Col 6: Text
Col 7: SubTimelineName  ← NO MEMO, HAS SUBTIMELINENAME INSTEAD
Col 8: EventName
Col 9: COMMENT_김정원
...
```

The Dialog QA files follow the Work Transform structure and DON'T have a MEMO column for testers to write comments.

---

## Impact

1. **Dialog tester comments NOT transferred to Master file**
   - Testers mark rows as ISSUE but comments aren't saved
   - `comments written: 0` for all Dialog files

2. **Manager stats incomplete for Dialog**
   - `collect_manager_status()` can't find tester comments
   - Manager_stats['Script'] doesn't include Dialog users
   - Tracker lookup returns NO_USER for Dialog testers

3. **Dialog users show 0 manager stats even after managers process**
   - Without tester comments in Master, manager can't respond
   - The whole Dialog workflow is broken

---

## Affected Stats

From LOOKUP PHASE:
```
[LOOKUP] 김찬용/Dialog
  '김찬용' in category_stats? False     ← NO_USER
  user_manager_stats: {'fixed': 0, 'reported': 0, 'checking': 0, 'nonissue': 0}
```

---

## FIX APPLIED

### Fix 1: Fallback to COMMENT column (DONE)

Modified `core/processing.py` to check for COMMENT column if MEMO not found:

```python
qa_comment_col = find_column_by_header(qa_ws, "MEMO")
if not qa_comment_col:
    # Fallback: Dialog files may use COMMENT instead of MEMO
    qa_comment_col = find_column_by_header(qa_ws, "COMMENT")
```

### Fix 2: Added debug logging (DONE)

Now logs ALL QA file headers for Script category:
```
QA file headers: [Col1:EventName, Col2:Text, Col3:Translation, ...]
```

This will show what columns Dialog files actually have.

---

## Code Location

```python
# core/processing.py lines 400-420 (MODIFIED)
```

---

## Next Steps

1. **Run full compilation** with updated code
2. **Check SCRIPT_DEBUG.log** for Dialog QA file headers
3. If Dialog has neither MEMO nor COMMENT:
   - Need to identify which column has tester comments
   - Or update Dialog QA template to add MEMO column

---

## Questions for User

1. Where do Dialog testers write their comments currently?
2. Is there a COMMENT column in Dialog QA files?
3. Should we add MEMO column to Dialog QA template?
4. Do we need to update existing Dialog files?

---

## Related

- [SESSION_0123_FINAL_ANALYSIS.md](SESSION_0123_FINAL_ANALYSIS.md)
- [ISSUE_MANAGER_STATS_ZERO.md](ISSUE_MANAGER_STATS_ZERO.md)

---

*Bug discovered during log analysis session 2026-01-24*
