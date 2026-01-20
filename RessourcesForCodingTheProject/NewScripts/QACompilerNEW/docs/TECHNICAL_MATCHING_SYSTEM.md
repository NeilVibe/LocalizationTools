# Technical: Two-Stage Matching System

**Date:** 2026-01-20
**Status:** ✅ STABLE - WORKING

---

## Overview

QACompiler uses a two-stage matching system during Master file rebuilds to preserve:
1. Tester work (STATUS, COMMENT, SCREENSHOT)
2. Manager work (STATUS_{User}, MANAGER_COMMENT_{User})

This document explains how both systems work together.

---

## The Problem (Before Fix)

Manager STATUS and MANAGER_COMMENT were being LOST during rebuild because:
- The lookup key used STRINGID from the **QA file** (often EMPTY!)
- Key mismatch occurred: QA stringid "" != Master stringid "12345"
- Manager work was not found, so it was lost

---

## The Solution (Two-Stage Matching)

### Stage 1: QA Tester Work -> Master Row (TRANSLATION Matching)

**Purpose:** Find which Master row corresponds to a QA row

**Match Key:** STRINGID + Translation content (with fallback to Translation only)

**Location:** `core/matching.py`

**Flow:**
```
QA Row (STRINGID="", Translation="Hello world")
    |
    v
build_master_index(master_ws) -> {("12345", "Hello world"): row_5, ...}
    |
    v
find_matching_row_in_master()
    1. Try: ("", "Hello world") -> Not found
    2. Fallback: Translation-only lookup -> Found row_5
    |
    v
Matched to Master Row 5 (which HAS stringid="12345")
```

**Key Functions:**
- `build_master_index(ws)` - Creates O(1) lookup dictionary from Master worksheet
- `find_matching_row_in_master(qa_row, master_index)` - Two-step cascade matching
- `extract_qa_row_data(row, category, is_item)` - Extracts matching keys from QA row

### Stage 2: Manager Status Lookup (COMMENT Matching)

**Purpose:** Restore manager STATUS and MANAGER_COMMENT for matched rows

**Match Key:** STRINGID (from MASTER row) + Tester Comment

**Critical Insight:** Uses the MASTER row's STRINGID (reliable) NOT the QA file's STRINGID (often empty)

**Location:**
- Collection: `core/compiler.py` - `collect_manager_status()`
- Restoration: `core/processing.py` - `process_sheet()`

**Flow:**
```
OLD Master Row 5:
    STRINGID="12345", COMMENT_John="Typo here", STATUS_John="FIXED"
    |
    v
collect_manager_status() -> {("12345", "Typo here"): {"John": {"status": "FIXED", ...}}}

NEW QA Row (matched to NEW Master Row 5 via Stage 1):
    COMMENT="Typo here", now linked to Master row with STRINGID="12345"
    |
    v
Lookup key: (master_stringid="12345", qa_comment="Typo here")
    |
    v
Found! Restore STATUS_John="FIXED" to new Master row
```

---

## Dict Structure

```python
manager_status = {
    "Quest": {                           # Category
        "Main Quest": {                  # Sheet name
            ("12345", "Typo here"): {    # (MASTER stringid, TESTER comment)
                "John": {
                    "status": "FIXED",
                    "manager_comment": "Fixed in build 5"
                },
                "Mary": {
                    "status": "REPORTED",
                    "manager_comment": "Sent to dev"
                }
            },
            ("", "Another issue"): {...}  # Fallback key (empty stringid)
        }
    }
}
```

---

## Category-Specific Matching

### Standard Categories (Quest, Knowledge, Region, Character, Skill, Help, Gimmick)

**Stage 1 Keys:**
- Primary: `(STRINGID, Translation)`
- Fallback: `(Translation,)` only

### Item Category

**Stage 1 Keys:**
- Primary: `(ItemName, ItemDesc, STRINGID)`
- Fallback: `(ItemName, ItemDesc)` only

### Contents Category

**Stage 1 Keys:**
- Primary: `INSTRUCTIONS` column value (col 2)
- No fallback

---

## Key Functions

### core/matching.py

```python
def build_master_index(ws: Worksheet) -> Dict[Tuple, int]:
    """Build O(1) lookup index for master worksheet.
    Returns: {(stringid, translation): row_number, ...}
    """

def find_matching_row_in_master(qa_row, master_index, category, is_item) -> Optional[int]:
    """Find matching master row using 2-step cascade.
    1. Try exact match (stringid + content)
    2. Fallback to content-only match
    """

def extract_qa_row_data(row, category, is_item) -> Tuple:
    """Extract matching keys from QA row based on category type."""
```

### core/compiler.py

```python
def collect_manager_status(master_path: Path) -> Dict:
    """PRELOAD old Master file, create lookup dict.
    Key: (stringid, tester_comment) from MASTER rows
    Value: {username: {status, manager_comment}}
    """
```

### core/processing.py

```python
def extract_comment_text(formatted_comment: str) -> str:
    """Extract raw comment text from formatted comment.
    Input: "Typo here\n---\nstringid:\n12345\n(updated: 2026-01-20)"
    Output: "Typo here"
    """

def process_sheet(...):
    """Process QA sheet, restore manager status.
    Uses MASTER row's stringid (not QA's) for lookup.
    """
```

---

## Why This Design Works

1. **QA files often have empty STRINGIDs** - Testers work with files that may not have stringids populated
2. **Master files have reliable STRINGIDs** - Built from authoritative source data
3. **Translation content is the bridge** - Matches QA work to correct Master row
4. **Manager lookup uses MASTER context** - After matching QA to Master, we have the reliable stringid

---

## Debugging Tips

If manager status is being lost:

1. **Check Stage 1 matching** - Is QA row matching to correct Master row?
   ```python
   logger.warning(f"GDP: QA trans='{translation}' matched to Master row {row_num}")
   ```

2. **Check stringid source** - Is it using MASTER stringid or QA stringid?
   ```python
   logger.warning(f"GDP: Looking up ({master_stringid}, {comment})")
   ```

3. **Check manager_status dict** - Was the status collected?
   ```python
   logger.warning(f"GDP: Collected manager_status keys: {list(sheet_status.keys())[:5]}")
   ```

---

## Files Modified for This Fix

| File | Function | Change |
|------|----------|--------|
| `core/compiler.py` | `collect_manager_status()` | Key by (stringid, comment) from Master rows |
| `core/processing.py` | `process_sheet()` | Use Master row stringid for lookup |
| `core/processing.py` | `extract_comment_text()` | Extract raw comment before "---" delimiter |
| `core/matching.py` | All functions | Content-based matching with fallback |

---

*Technical Reference Document | v1.0 | 2026-01-20*
