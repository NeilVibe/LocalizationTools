# MemoQ Unconfirmed Eraser Script

**Purpose:** Remove unconfirmed translations from LanguageData by cross-referencing with MemoQ export
**Status:** WIP | **Created:** 2025-12-12

---

## Problem Statement

Some strings that should NOT be in LanguageData got submitted incorrectly. We identified these by checking MemoQ - the lines that exist in LanguageData are actually "unconfirmed" in MemoQ.

**Goal:** Erase these unconfirmed translations from LanguageData by replacing `Str` with `StrOrigin` (Korean source).

---

## Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Prepare Source Files (Manual - in MemoQ)               │
├─────────────────────────────────────────────────────────────────┤
│  1. In MemoQ, EMPTY all unconfirmed strings (Str="")            │
│  2. Export those files as XML                                   │
│  3. Place exported files in a SOURCE FOLDER                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Run Script                                             │
├─────────────────────────────────────────────────────────────────┤
│  User selects:                                                  │
│  - SOURCE FOLDER (contains MemoQ exported XMLs)                 │
│  - TARGET FILE (LanguageData XML to modify)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Extract Empty Nodes from Source                        │
├─────────────────────────────────────────────────────────────────┤
│  For each XML file in SOURCE FOLDER:                            │
│  - Parse XML                                                    │
│  - Find all <String> nodes where Str="" (empty)                 │
│  - Extract: Stringid + StrOrigin (for matching)                 │
│  - Store in memory as "nodes to erase"                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Process Target LanguageData                            │
├─────────────────────────────────────────────────────────────────┤
│  - Unlock read-only file if needed                              │
│  - Parse TARGET XML                                             │
│  - For each "node to erase":                                    │
│    - Find matching node in TARGET (Stringid + StrOrigin match)  │
│    - If MATCH: Replace Str value with StrOrigin value           │
│  - Save modified XML (overwrite TARGET)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Report                                                 │
├─────────────────────────────────────────────────────────────────┤
│  - Show total nodes processed                                   │
│  - Show matches found and erased                                │
│  - Show any nodes not found in target                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## XML Structure

### Source XML (MemoQ Export with Empty Str)
```xml
<String Stringid="UI_MENU_001" StrOrigin="메뉴" Str="">
  <!-- Str is EMPTY = unconfirmed in MemoQ -->
</String>
```

### Target LanguageData (Before)
```xml
<String Stringid="UI_MENU_001" StrOrigin="메뉴" Str="Menu">
  <!-- Has translation that shouldn't be here -->
</String>
```

### Target LanguageData (After)
```xml
<String Stringid="UI_MENU_001" StrOrigin="메뉴" Str="메뉴">
  <!-- Str replaced with StrOrigin = translation erased -->
</String>
```

---

## Matching Logic

A node matches when **BOTH** conditions are true:
1. `Stringid` attribute values are identical
2. `StrOrigin` attribute values are identical

**Why both?** Same Stringid might have different source text versions.

---

## Technical Requirements

| Requirement | Implementation |
|-------------|----------------|
| Folder walking | `os.walk()` for recursive XML discovery |
| XML parsing | `xml.etree.ElementTree` (preserve formatting) |
| Read-only unlock | `os.chmod()` or `stat` module |
| Progress display | Console print with counts |
| Encoding | UTF-8 with BOM handling |

---

## Script Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  MemoQ Unconfirmed Eraser                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Select Source Folder]  (contains MemoQ exported XMLs)         │
│                                                                 │
│  [Select Target File]    (LanguageData XML to modify)           │
│                                                                 │
│  [Run Process]                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Console Output Example

```
=== MemoQ Unconfirmed Eraser ===

Source Folder: D:\MemoQ_Export\
Target File: D:\LanguageData\EN_LanguageData.xml

Scanning source folder...
  - Found 3 XML files
  - File 1: export_001.xml - 150 empty nodes
  - File 2: export_002.xml - 89 empty nodes
  - File 3: export_003.xml - 45 empty nodes
  - Total empty nodes to process: 284

Processing target LanguageData...
  - Total nodes in target: 52,340
  - Unlocking read-only file...
  - Searching for matches...
  [============================] 284/284

Results:
  - Matches found and erased: 271
  - Not found in target: 13
  - Target file updated successfully!

Done!
```

---

## Error Handling

| Error | Handling |
|-------|----------|
| Source folder empty | Show warning, abort |
| No XML files found | Show warning, abort |
| Target file not found | Show error, abort |
| XML parse error | Log error, skip file, continue |
| Permission denied | Try unlock, if fail show error |

---

## File Location

Script: `RessourcesForCodingTheProject/NewScripts/MemoQUnconfirmedEraser/memoq_unconfirmed_eraser.py`

---

*Created: 2025-12-12*
