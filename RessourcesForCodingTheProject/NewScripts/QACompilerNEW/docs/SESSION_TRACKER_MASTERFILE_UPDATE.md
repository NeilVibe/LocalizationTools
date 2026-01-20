# SESSION: Progress Tracker & Master File Updates

**Date:** 2026-01-17
**Status:** IMPLEMENTED (pending testing)

---

## Overview

Two major updates requested:
1. **Progress Tracker** - Add Workload Analysis columns to TOTAL tab
2. **Master Files** - Add Manager Comment + hide empty Screenshot column

---

## PART 1: Progress Tracker Updates

### Current TOTAL Tab Structure (EN/CN TESTER STATS tables)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EN TESTER STATS                                   │
├──────────┬─────────────────────────────┬────────────────────────────────────┤
│  Tester  │  BLUE: Tester Stats         │  GREEN: Manager Stats              │
│  Name    │  Done│Issue│NoIssue│Block│KR│  Fixed│Reported│Checking│NonIssue │
├──────────┼─────────────────────────────┼────────────────────────────────────┤
│ 김민영   │  150 │  45 │   80  │  15 │10│    30 │    10  │    5   │    0    │
│ 황하연   │  200 │  60 │  100  │  25 │15│    40 │    15  │    5   │    0    │
└──────────┴─────────────────────────────┴────────────────────────────────────┘
```

### NEW Structure (with Workload Analysis)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          EN TESTER STATS                                                 │
├──────────┬─────────────────────────────┬────────────────────────────────────┬─────────────────────────────────────────────────────────────┐
│  Tester  │  BLUE: Tester Stats         │  GREEN: Manager Stats              │  LIGHT ORANGE: Workload Analysis          │ Assessment    │
│  Name    │  Done│Issue│NoIssue│Block│KR│  Fixed│Reported│Checking│NonIssue │  ActualDone│DailyAvg│Type│DaysWorked │ (manual)      │
├──────────┼─────────────────────────────┼────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 김민영   │  150 │  45 │   80  │  15 │10│    30 │    10  │    5   │    0    │    125     │  12.5  │Text│    10     │ Good quality  │
│ 황하연   │  200 │  60 │  100  │  25 │15│    40 │    15  │    5   │    0    │    160     │  16.0  │Game│    10     │ Excellent     │
└──────────┴─────────────────────────────┴────────────────────────────────────┴─────────────────────────────────────────────────────────────┘
```

### New Columns (Light Orange Section)

| Column | Formula/Source | Description |
|--------|----------------|-------------|
| **Actual Done** | `Total Done - Total Blocked - Total Korean` | Real completed work |
| **Daily Average of Actual Done** | `Actual Done / Days Worked` | Productivity metric |
| **Type of Tester** | From `TesterType.txt` | "Text" or "Gameplay" |
| **Days Worked** | Manual entry | Filled by manager |
| **Tester Assessment** | Manual entry | Overall quality comment |

### TesterType.txt File Format

```
Text
김민영
황하연
박지훈

Gameplay
김춘애
최문석
이승현
```

**Location:** `QACompilerNEW/TesterType.txt`
**Format:** Same as `languageTOtester_list.txt` (section headers, names below)

### Implementation Steps (Progress Tracker)

1. **config.py**
   - Add `TESTER_TYPE_FILE = SCRIPT_DIR / "TesterType.txt"`
   - Add `load_tester_type_mapping()` function

2. **tracker/total.py** (or wherever TOTAL tab is built)
   - Add new columns after Manager Stats section
   - Calculate Actual Done = Done - Blocked - Korean
   - Calculate Daily Average = Actual Done / Days Worked (handle div by 0)
   - Load tester type from mapping
   - Leave Days Worked and Assessment as blank (manual fill)
   - Apply light orange fill color

3. **Create TesterType.example.txt**
   - Example file for distribution

---

## PART 2: Master File Updates

### Current Master File Column Structure

```
│ Korean │ Translation │ ... │ STATUS │ COMMENT │ STRINGID │ SCREENSHOT │ MANAGER_STATUS │
│   A    │     B       │ ... │   X    │    Y    │    Z     │     AA     │      AB        │
```

### NEW Structure (with Manager Comment)

```
│ Korean │ Translation │ ... │ STATUS │ COMMENT │ STRINGID │ SCREENSHOT │ MANAGER_STATUS │ MANAGER_COMMENT │
│   A    │     B       │ ... │   X    │    Y    │    Z     │     AA     │      AB        │       AC        │
```

### Pairing Logic (CRITICAL)

The pairing must be ROBUST:

```
TESTER PAIR                    MANAGER PAIR
┌─────────┬─────────┐         ┌─────────────────┬─────────────────┐
│ STATUS  │ COMMENT │    ←→   │ MANAGER_STATUS  │ MANAGER_COMMENT │
└─────────┴─────────┘         └─────────────────┴─────────────────┘
     ↓         ↓                      ↓                  ↓
  Row 5     Row 5                  Row 5              Row 5
```

Both pairs must:
- Be on the SAME ROW (matched by STRINGID + Translation)
- Transfer together during merge operations
- Be preserved during sheet processing

### Screenshot Column Hiding

**Rule:** If SCREENSHOT column has NO content (all cells empty), hide it completely.

**Implementation:**
1. After autofit completes
2. Check if any cell in SCREENSHOT column has value
3. If all empty → hide column
4. Same logic as other hidden columns

### Order of Operations (CRITICAL)

```
1. Build master file structure
2. Add all data (tester status, comment, manager status, manager comment)
3. Apply autofit to all columns
4. THEN hide empty columns:
   - Hide Translation if ENG file
   - Hide SCREENSHOT if empty
   - Hide rows based on status rules
```

### Implementation Steps (Master Files)

1. **core/processing.py**
   - Add MANAGER_COMMENT column header
   - Update column finding logic
   - Update transfer logic to include MANAGER_COMMENT
   - Ensure MANAGER_STATUS and MANAGER_COMMENT are paired

2. **core/excel_ops.py** (or relevant file)
   - Add `hide_empty_screenshot_column()` function
   - Call AFTER autofit

3. **core/compiler.py**
   - Ensure build order: data → autofit → hide

---

## Files to Modify

| File | Changes |
|------|---------|
| `config.py` | Add TESTER_TYPE_FILE, load_tester_type_mapping() |
| `tracker/total.py` | Add Workload Analysis columns |
| `core/processing.py` | Add MANAGER_COMMENT, Screenshot hiding |
| `core/excel_ops.py` | Hide empty screenshot column function |
| `TesterType.txt` | New file (create) |
| `TesterType.example.txt` | New file (create) |
| `USER_GUIDE.md` | Document new features |
| `README.md` | Update column descriptions |

---

## Color Scheme

| Section | Color | Hex Code |
|---------|-------|----------|
| Tester Stats | Blue | `4472C4` (existing) |
| Manager Stats | Green | `70AD47` (existing) |
| Workload Analysis | Light Orange | `FCE4D6` |
| Assessment | Light Orange | `FCE4D6` |

---

## Testing Checklist

- [ ] TesterType.txt loads correctly
- [ ] Actual Done calculates correctly (Done - Blocked - Korean)
- [ ] Daily Average handles division by zero (Days Worked = 0)
- [ ] Type of Tester shows correctly from mapping
- [ ] Days Worked column is editable (not formula)
- [ ] Assessment column is editable (not formula)
- [ ] MANAGER_COMMENT transfers correctly during merge
- [ ] MANAGER_STATUS + MANAGER_COMMENT stay paired
- [ ] Screenshot column hides when empty
- [ ] Hiding happens AFTER autofit
- [ ] Existing functionality still works

---

## Questions to Clarify (if needed)

1. Should Days Worked be per-category or overall?
2. Should Tester Assessment be per-category or overall?
3. What happens if tester not in TesterType.txt? Default to "Unknown"?

---

## Detailed Implementation Notes

### Manager Comment Pairing (CRITICAL)

Current column structure per user:
```
COMMENT_{User} | TESTER_STATUS_{User} | STATUS_{User} | SCREENSHOT_{User}
```

NEW column structure per user:
```
COMMENT_{User} | TESTER_STATUS_{User} | STATUS_{User} | MANAGER_COMMENT_{User} | SCREENSHOT_{User}
```

**Two-Stage Matching System (UPDATED 2026-01-20):**

See `docs/TECHNICAL_MATCHING_SYSTEM.md` for full details.

**Stage 1: QA -> Master Row (TRANSLATION matching)**
- Match by: STRINGID + Translation content
- Fallback: Translation only
- Located in: `core/matching.py`

**Stage 2: Manager Status Lookup (COMMENT matching)**
- Match by: (MASTER stringid, TESTER comment)
- CRITICAL: Uses STRINGID from MASTER row (reliable), NOT QA file (often empty!)
- Located in: `core/compiler.py` (collect) and `core/processing.py` (restore)

**Dict Structure:**
```python
manager_status = {
    "Quest": {
        "Main Quest": {
            ("12345", "Typo here"): {  # (MASTER stringid, TESTER comment)
                "John": {"status": "FIXED", "manager_comment": "Fixed build 5"}
            }
        }
    }
}
```

**Key Functions:**
1. `core/compiler.py` - `collect_manager_status()` - PRELOAD old Master, create lookup dict
2. `core/processing.py` - `process_sheet()` - RESTORE manager status during build
3. `core/processing.py` - `extract_comment_text()` - Extract raw comment (before "---" delimiter)
4. `core/matching.py` - Content-based matching with fallback

### Screenshot Hiding Logic

**Where to add:** `core/processing.py` in `hide_unused_columns()` function (around line 670+)

**Logic:**
```python
# After processing all sheets, check SCREENSHOT_{User} columns
for each SCREENSHOT_{User} column:
    has_content = any(cell.value for cell in column[2:])  # Skip header
    if not has_content:
        hide column
```

**Order:**
1. Build data
2. autofit_rows_with_wordwrap()
3. THEN hide_unused_columns() (including screenshot check)

---

## Next Steps

1. ✅ Create this planning document
2. ✅ Create TesterType.example.txt
3. ✅ Update config.py with new loader (load_tester_type_mapping)
4. ✅ Update tracker/total.py with Workload Analysis columns
5. ✅ Update core/compiler.py - collect_manager_status with MANAGER_COMMENT
6. ✅ Update core/processing.py - add MANAGER_COMMENT column creation/restoration
7. ✅ Update core/processing.py - add screenshot hiding in hide_unused_columns
8. ✅ Ensure hide happens AFTER autofit (verified: order correct in compiler.py)
9. ⬜ Test all changes
10. ✅ Update USER_GUIDE.md and README.md
11. ⬜ Update ZIP and push
