# NON-ISSUE Feature Plan

**Created:** 2026-01-05 | **Status:** ✅ IMPLEMENTED

---

## Problem Statement

Currently we have no way to track **false positives** - when a tester reports an ISSUE but the manager determines it's actually NOT a real issue.

**Why this matters:**
- Measures tester accuracy
- Identifies testers who over-report (many false positives)
- Quality metric for LQA process

---

## Current Flow

```
USER FILE:
┌─────────┬─────────┬──────────────────┐
│ STATUS  │ COMMENT │ (other cols)     │
├─────────┼─────────┼──────────────────┤
│ ISSUE   │ "typo"  │ ...              │  ← Compiled (but shouldn't have context)
│ NO ISSUE│ "ok"    │ ...              │  ← Also compiled (wrong!)
│ BLOCKED │ "stuck" │ ...              │  ← Also compiled (wrong!)
│ ISSUE   │ "wrong" │ ...              │  ← Compiled
└─────────┴─────────┴──────────────────┘

MASTER FILE (current):
┌──────────────┬───────────────┐
│ COMMENT_User │ STATUS_User   │
├──────────────┼───────────────┤
│ "typo"       │ FIXED         │  ← Manager says: real issue, fixed
│ "ok"         │ (empty)       │  ← Shouldn't be here!
│ "stuck"      │ (empty)       │  ← Shouldn't be here!
│ "wrong"      │ REPORTED      │  ← Manager says: real issue, reported
└──────────────┴───────────────┘

Manager Status Options: FIXED | REPORTED | CHECKING
```

---

## New Flow

```
USER FILE:
┌─────────┬─────────┬──────────────────┐
│ STATUS  │ COMMENT │ (other cols)     │
├─────────┼─────────┼──────────────────┤
│ ISSUE   │ "typo"  │ ...              │  ← ONLY this gets compiled
│ NO ISSUE│ "ok"    │ ...              │  ← SKIP (no issue = no comment needed)
│ BLOCKED │ "stuck" │ ...              │  ← SKIP (blocked = different workflow)
│ ISSUE   │ "wrong" │ ...              │  ← ONLY this gets compiled
└─────────┴─────────┴──────────────────┘

MASTER FILE (new):
┌──────────────┬───────────────┐
│ COMMENT_User │ STATUS_User   │
├──────────────┼───────────────┤
│ "typo"       │ FIXED         │  ← Real issue, fixed
│ (empty)      │ (empty)       │  ← Row skipped (NO ISSUE in user file)
│ (empty)      │ (empty)       │  ← Row skipped (BLOCKED in user file)
│ "wrong"      │ NON-ISSUE     │  ← FALSE POSITIVE! Not a real issue
└──────────────┴───────────────┘

Manager Status Options: FIXED | REPORTED | CHECKING | NON-ISSUE (NEW!)
```

---

## Key Metric: False Positive Rate

**Formula:**
```
False Positive % = (NON-ISSUE count / Total ISSUE count) * 100
```

**Example:**
- Alice reported 10 issues
- Manager marked 2 as NON-ISSUE
- False Positive % = 2/10 = 20%

**Interpretation:**
- 0% = Perfect accuracy (all reported issues are real)
- 20% = 1 in 5 reported issues are false positives
- 50%+ = Tester is over-reporting, needs training

---

## Implementation Steps

### Step 1: Add NON-ISSUE to Manager Status Dropdown
**File:** `compile_qa.py`
**Location:** Where we create STATUS_{User} dropdown

```python
# Current
MANAGER_STATUS_VALUES = ["FIXED", "REPORTED", "CHECKING"]

# New
MANAGER_STATUS_VALUES = ["FIXED", "REPORTED", "CHECKING", "NON-ISSUE"]
```

### Step 2: Only Compile ISSUE Comments
**File:** `compile_qa.py`
**Location:** `process_qa_sheet()` function

**Current logic:**
```python
# Copy comment regardless of status
if comment:
    master_ws.cell(row, comment_col, formatted_comment)
```

**New logic:**
```python
# Only copy comment if STATUS = "ISSUE"
user_status = qa_ws.cell(row, status_col).value
if user_status and "ISSUE" in str(user_status).upper() and "NO" not in str(user_status).upper():
    if comment:
        master_ws.cell(row, comment_col, formatted_comment)
```

### Step 3: Track NON-ISSUE Count in Daily Data
**File:** `compile_qa.py`
**Location:** `update_daily_data_sheet()` and `collect_manager_stats_for_tracker()`

**Add new column to _DAILY_DATA:**
```
Schema: Date, User, Category, TotalRows, Done, Issues, NoIssue, Blocked, Fixed, Reported, Checking, NonIssue
```

### Step 4: Calculate and Display False Positive %
**File:** `compile_qa.py`
**Location:** `build_daily_sheet()` and `build_total_sheet()`

**Add columns:**
- "Non-Issue" (count)
- "FP %" (False Positive percentage)

**Calculation:**
```python
fp_pct = round(non_issue / issues * 100, 1) if issues > 0 else 0
```

### Step 5: Update Charts
**File:** `compile_qa.py`
**Location:** Chart creation in build_daily_sheet() and build_total_sheet()

- Consider adding FP% to charts or keeping it simple

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER FILE                                  │
│  STATUS = ISSUE  ────────────────────────────────────────────────┐  │
│  STATUS = NO ISSUE (skip)                                        │  │
│  STATUS = BLOCKED (skip)                                         │  │
└──────────────────────────────────────────────────────────────────│──┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MASTER FILE                                  │
│  COMMENT_{User} = only ISSUE comments                               │
│  STATUS_{User} = FIXED | REPORTED | CHECKING | NON-ISSUE           │
└─────────────────────────────────────────────────────────────────────┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PROGRESS TRACKER                                │
│  DAILY: ... | Non-Issue | FP % |                                    │
│  TOTAL: ... | Non-Issue | FP % |                                    │
│                                                                      │
│  Calculation: FP % = Non-Issue / Issues * 100                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Column Changes Summary

### Master Files (Master_Quest.xlsx, etc.)

**STATUS_{User} dropdown values:**
| Before | After |
|--------|-------|
| FIXED | FIXED |
| REPORTED | REPORTED |
| CHECKING | CHECKING |
| - | **NON-ISSUE** (NEW) |

### Progress Tracker (_DAILY_DATA)

**Schema change:**
```
Before: Date, User, Category, TotalRows, Done, Issues, NoIssue, Blocked, Fixed, Reported, Checking
After:  Date, User, Category, TotalRows, Done, Issues, NoIssue, Blocked, Fixed, Reported, Checking, NonIssue
```

### Progress Tracker (DAILY tab)

**New columns in Manager Stats section:**
| Fixed | Reported | Checking | Pending | **Non-Issue** | **FP %** |

### Progress Tracker (TOTAL tab)

**New columns:**
| ... | Fixed | Reported | Checking | Pending | **Non-Issue** | **FP %** |

---

## Edge Cases

| Case | Handling |
|------|----------|
| User has 0 issues | FP % = 0 (can't have false positives if no issues) |
| All issues are NON-ISSUE | FP % = 100% (worst case) |
| STATUS_{User} is empty | Don't count as NON-ISSUE |
| User comment exists but STATUS != ISSUE | Skip compilation (new behavior) |

---

## Acceptance Criteria

- [x] NON-ISSUE option appears in STATUS_{User} dropdown
- [x] Only ISSUE comments are compiled to COMMENT_{User}
- [x] NON-ISSUE count tracked in _DAILY_DATA
- [x] Actual Issues % calculated and displayed in DAILY tab
- [x] Actual Issues % calculated and displayed in TOTAL tab
- [x] Existing FIXED/REPORTED/CHECKING data preserved

---

*Plan created: 2026-01-05*
