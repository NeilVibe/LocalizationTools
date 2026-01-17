# QA Excel Compiler - Code Review Report

**Date:** 2026-01-08
**Reviewer:** Claude
**Scope:** Full code review of `compile_qa.py` with focus on DAILY tab calculations and charts

---

## Executive Summary

The QA Excel Compiler is a well-structured tool with robust error handling and comprehensive features. However, this review identified **2 bugs** and **2 potential issues** that should be addressed.

| Severity | Count | Description |
|----------|-------|-------------|
| **BUG** | 2 | Issues causing incorrect behavior |
| **POTENTIAL** | 2 | Edge cases that may cause problems |
| **NOT AN ISSUE** | 1 | Initially flagged but found to be handled correctly |
| **INFO** | 2 | Minor observations |

---

## BUG #1: DAILY Chart Uses String "--" Values (MEDIUM)

**Location:** `compile_qa.py:1889-1894`

**Problem:** When a user has no work for a day, the code displays "--" instead of a numeric value. However, this string is then referenced by the chart.

```python
# Line 1889-1890
done_display = done_val if done_val > 0 else "--"
issues_display = issues_val if issues_val > 0 else "--"

# Line 1893-1894 - these values go into cells that the chart references
for i, val in enumerate([done_display, issues_display]):
    cell = ws.cell(data_row, col + i, val)
```

The chart (lines 1994-2001) references these cells:
```python
data_ref = Reference(
    ws,
    min_col=done_col,
    ...
)
chart.add_data(data_ref, titles_from_data=False)
```

**Impact:** Excel may interpret "--" as:
- A zero value (best case)
- An error (causes chart rendering issues)
- A text category (corrupts the chart type)

**Recommended Fix:** Store numeric 0 in cells, use conditional formatting or a separate display layer to show "--" visually, OR use two separate cell sets (one for display, one for chart data).

---

## BUG #2: DAILY Delta Calculation Cross-Category Contamination (HIGH)

**Location:** `compile_qa.py:1676-1735`

**Problem:** The DAILY sheet aggregates by `(date, user)` across ALL categories before calculating deltas. This causes incorrect calculations when a user's different categories have data on different dates.

**Scenario:**
1. Alice's Quest file modified 2026-01-04: 50 done
2. Alice's Item file modified 2026-01-05: 30 done
3. Quest file NOT modified on 2026-01-05

**What `_DAILY_DATA` contains:**
```
(2026-01-04, Alice, Quest) = {done: 50}
(2026-01-05, Alice, Item)  = {done: 30}
```

**What `build_daily_sheet` aggregates:**
```python
# Line 1693-1700: Sums ALL categories for (date, user)
daily_data["2026-01-04"]["Alice"] = {done: 50}  # Only Quest
daily_data["2026-01-05"]["Alice"] = {done: 30}  # Only Item
```

**Delta calculation (lines 1717-1735):**
```
2026-01-04: delta = 50 - 0 = 50  (correct)
2026-01-05: delta = 30 - 50 = -20 → clamped to 0  (WRONG!)
```

**Reality:** Alice did 30 items of work on 01/05, but the delta shows 0 because her Quest cumulative (50) from 01/04 is subtracted from her Item cumulative (30) on 01/05.

**Impact:** DAILY tab shows incorrect daily work when categories have different modification dates.

**Root Cause:** The data model stores cumulative values per (date, user, category), but the DAILY aggregation sums across categories before computing deltas. This makes cross-date comparisons invalid.

**Note:** The TOTAL tab correctly handles this by using only the LATEST date for each (user, category) - see lines 2040-2070. The DAILY tab needs similar logic.

**Recommended Fix Options:**

1. **Per-Category Delta First:** Calculate deltas per (user, category), then sum the deltas for daily totals
2. **Carry Forward Missing Categories:** If a category exists on date N but not date N+1, carry forward date N's values to date N+1 before aggregation
3. **Store Daily Work, Not Cumulative:** Change the data model to store daily increments instead of cumulative totals

---

## POTENTIAL ISSUE #1: Chart X-Axis Labels - Confirmed Working

**Location:** `compile_qa.py:1981-1987, 2013`

**Analysis:** The user asked if the X-axis shows "1, 2, 3, 4, 5" instead of actual dates.

**Findings:** The code DOES correctly reference the date column:

```python
# Line 1981-1987
cats_ref = Reference(
    ws,
    min_col=1,          # Column 1 = Date column
    min_row=data_start_row,
    max_row=data_end_row
)
chart.set_categories(cats_ref)

# Line 2013
chart.x_axis.title = "Date"
```

The dates are formatted as MM/DD (line 1855):
```python
display_date = date[5:7] + "/" + date[8:10]  # YYYY-MM-DD -> MM/DD
```

**Verdict:** X-axis SHOULD display actual dates (e.g., "01/04", "01/05"). If user sees "1, 2, 3, 4, 5", it may be due to:
- Excel caching issues (try regenerating the file)
- Chart type confusion (categories vs series)

**Status:** NO CODE FIX NEEDED - verify in actual output

---

## POTENTIAL ISSUE #2: Empty User in _DAILY_DATA (LOW)

**Location:** `compile_qa.py:1682-1701`

**Problem:** The code checks `if date and user:` but doesn't validate that values are non-empty strings.

```python
for row in range(2, data_ws.max_row + 1):
    date = data_ws.cell(row, 1).value
    user = data_ws.cell(row, 2).value
    ...
    if date and user:  # Truthy check, but "" would fail
        daily_data[date][user]["total_rows"] += total_rows
```

**Impact:** If a row has empty string "" for user, it would be skipped (correct behavior). However, whitespace-only strings like "  " would pass the check.

**Recommended Fix:** Add `.strip()` validation:
```python
if date and user and str(user).strip():
```

---

## ~~POTENTIAL ISSUE #3: Schema Version Mismatch~~ ✅ NOT AN ISSUE

**Location:** `compile_qa.py:1614-1617, 1667-1669`

**Original Concern:** Schema versioning seemed fragile.

**Analysis:** Upon closer inspection, the code handles this correctly:

1. **DAILY/TOTAL sheets:** Fully deleted and recreated each run (line 1667-1669)
2. **_DAILY_DATA sheet:** Checks BOTH header name AND column count:
   ```python
   if ws.cell(1, 1).value != "Date" or ws.max_column < 12:
       headers = ["Date", "User", "Category", ...]  # Rewrites all headers
   ```
3. **Explicit column writes:** Data is written with hardcoded column indices (lines 1646-1657), not relying on existing structure

**Verdict:** Schema migration is handled properly. Old files with fewer columns trigger header rewrite via `max_column < 12` check.

---

## INFO #1: Robust Excel Filter Repair

**Location:** `compile_qa.py:113-150`

**Observation:** The `repair_excel_filters()` function is an excellent addition that handles corrupted Excel files by stripping autoFilter XML. This addresses the error shown in `errorLOGSforClaude/log01081731.txt`.

**Status:** Working as designed

---

## INFO #2: TOTAL Tab Double-Count Fix Verified

**Location:** `compile_qa.py:2040-2070`

**Observation:** The TOTAL tab correctly uses only the LATEST date for each (user, category) combination:

```python
# First pass: find the latest date for each (user, category)
latest_data = {}
for row in range(...):
    key = (user, category)
    if key not in latest_data or str(date) > str(latest_data[key]["date"]):
        latest_data[key] = {...}  # Keep latest only
```

This correctly avoids the double-counting bug mentioned in the README update notes.

**Status:** Working correctly

---

## Code Quality Observations

### Strengths

1. **Comprehensive error handling** - `safe_load_workbook()` with repair fallback
2. **Clear documentation** - Function docstrings explain behavior well
3. **Modular design** - Separate functions for each concern
4. **Data validation** - Clamping, null checks, and edge case handling
5. **User experience** - Progress messages, warnings, and hidden data sheets

### Areas for Improvement

1. **Magic numbers** - Column indices (4, 5, 6...) could be named constants
2. **Long functions** - `build_daily_sheet()` and `build_total_sheet()` are 300+ lines each
3. **Code duplication** - Chart creation logic is similar between DAILY and TOTAL tabs

---

## Recommended Priority

| Priority | Issue | Effort |
|----------|-------|--------|
| **P1** | BUG #2: Delta calculation | Medium - requires data model change |
| **P2** | BUG #1: String "--" in charts | Low - simple fix |
| **P3** | POTENTIAL #2: Empty user validation | Trivial |
| ~~P4~~ | ~~POTENTIAL #3: Schema versioning~~ | ✅ NOT AN ISSUE |

---

## Summary

The DAILY chart X-axis is correctly coded to show dates. However, there are two bugs:

1. **"--" strings in chart data** - May cause chart rendering issues
2. **Cross-category delta contamination** - Shows 0 or wrong values when categories have different modification dates

The TOTAL tab logic is correct and well-implemented. The DAILY tab needs similar "latest date per category" logic before aggregation to fix the delta calculation bug.

---

*Report generated: 2026-01-08*
