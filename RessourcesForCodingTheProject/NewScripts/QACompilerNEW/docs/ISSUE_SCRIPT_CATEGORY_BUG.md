# ISSUE: Script Category (Sequencer/Dialog) Stats Bug

**Status:** FIX APPLIED - AWAITING VERIFICATION
**Priority:** CRITICAL
**Date:** 2026-01-23 to 2026-01-24
**Affects:** Dialog category (Sequencer works)

---

## Problem Summary

Dialog tester comments are NOT being written to Master file, causing Dialog users to be missing from manager_stats.

| Category | Tester Stats | Comments Written | In manager_stats |
|----------|--------------|------------------|------------------|
| Sequencer | ✅ Works | ✅ 55 comments | ✅ Yes |
| Dialog | ✅ Works | ❌ 0 comments | ❌ No (NO_USER) |

---

## Root Cause

**Dialog QA files don't have a MEMO column.**

The code looks for "MEMO" column to find tester comments. Dialog QA files don't have this column, so:
1. `qa_comment_col = None`
2. Comments not written to Master
3. Master Work Transform sheet has empty COMMENT_ columns
4. `collect_manager_stats` finds PENDING=0 for Dialog users
5. Dialog users not added to `manager_stats['Script']`
6. Lookup fails with NO_USER

---

## Evidence from Logs

### QA MEMO Column
```
Sequencer/유지윤: QA MEMO column: 8    → comments written: 30
Sequencer/조서영: QA MEMO column: 8    → comments written: 25
Dialog/김정원:    QA MEMO column: None → comments written: 0
Dialog/김찬용:    QA MEMO column: None → comments written: 0
Dialog/황하연:    QA MEMO column: None → comments written: 0
```

### Master File Sheet Summaries
```
English Script (Sequencer):
  유지윤: PENDING=30 ✅
  조서영: PENDING=25 ✅

Work Transform (Dialog):
  김정원: PENDING=0 ❌
  김찬용: PENDING=0 ❌
  황하연: PENDING=0 ❌
```

### manager_stats['Script']
```
Users: ['유지윤', '조서영']  ← Dialog users MISSING
```

### Lookup Results
```
유지윤/Sequencer: User found ✅
조서영/Sequencer: User found ✅
김정원/Dialog:    NO_USER ❌
김찬용/Dialog:    NO_USER ❌
황하연/Dialog:    NO_USER ❌
```

---

## Tester Stats (Work Correctly)

| User | Category | ISSUE | NON-ISSUE | Done |
|------|----------|-------|-----------|------|
| 유지윤 | Sequencer | 30 | 765 | 795 |
| 조서영 | Sequencer | 25 | 857 | 882 |
| 김정원 | Dialog | 85 | 3095 | 3180 |
| 김찬용 | Dialog | 63 | 1060 | 1123 |
| 황하연 | Dialog | 21 | 3480 | 3501 |

**Tester issue counts are correct for ALL users.** The problem is only with comment transfer and manager stats.

---

## Fix Applied

**File:** `core/processing.py`

**Change:** Added fallback to check COMMENT column if MEMO not found:

```python
# Before (broken for Dialog):
qa_comment_col = find_column_by_header(qa_ws, "MEMO")

# After (with fallback):
qa_comment_col = find_column_by_header(qa_ws, "MEMO")
if not qa_comment_col:
    qa_comment_col = find_column_by_header(qa_ws, "COMMENT")
```

**Also added:** Debug logging to show all QA file headers for Script category.

---

## Verification Needed

1. **What column do Dialog QA files use for comments?**
   - MEMO? (Sequencer uses this)
   - COMMENT?
   - Something else?

2. **Run compilation with updated code**
   - New debug logging will show: `QA file headers: [Col1:..., Col2:..., ...]`

3. **Check SCRIPT_DEBUG.log after run**
   - Look for Dialog file headers
   - Verify if COMMENT column exists

---

## Master File Structure

### English Script (Sequencer) - Col 7 = MEMO
```
Col 1: DialogType
Col 2: Group
Col 3: SequenceName
Col 4: DialogVoice
Col 5: RECORDING
Col 6: Text
Col 7: MEMO           ← Sequencer has MEMO
Col 8: EventName
```

### Work Transform (Dialog) - Col 7 = SubTimelineName
```
Col 1: DialogType
Col 2: Group
Col 3: SequenceName
Col 4: DialogVoice
Col 5: RECORDING
Col 6: Text
Col 7: SubTimelineName  ← Dialog has SubTimelineName instead
Col 8: EventName
```

---

## Related Documentation

- [SESSION_0124_COMPLETE_ANALYSIS.md](SESSION_0124_COMPLETE_ANALYSIS.md) - Full log analysis
- [ISSUE_TRACKER_INVESTIGATION_SESSION.md](ISSUE_TRACKER_INVESTIGATION_SESSION.md) - Investigation history
- [TECHNICAL_MATCHING_SYSTEM.md](TECHNICAL_MATCHING_SYSTEM.md) - Matching logic details

---

## Log Files Analyzed

- `FULL DEBUG LOG FOR CLAUDE 0123 2300.txt` (721KB)
- `SCRIPT DEBUGLOG FOR CLAUDE 0123 2300.txt`

---

## Timeline

| Date | Action |
|------|--------|
| 2026-01-23 | Issue reported - Script category shows 0 stats |
| 2026-01-23 | Initial investigation - case sensitivity hypothesis (WRONG) |
| 2026-01-23 | Debug logging added |
| 2026-01-23 22:53 | User uploaded debug logs |
| 2026-01-24 | Full log analysis - found Dialog MEMO issue |
| 2026-01-24 | Fix applied - COMMENT fallback + debug logging |
| 2026-01-24 | Awaiting verification |

---

*Last updated: 2026-01-24*
