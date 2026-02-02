# Korean Miss Extractor

## Overview

Extracts Korean strings from a **Target** file that do NOT exist in a **Source** file.
Used to identify untranslated or missing localization entries.

## How to Use

1. **Open QuickTranslate**

2. **Set SOURCE file** (top Browse button)
   - Your CORRECTIONS/REFERENCE file
   - Contains StringID + StrOrigin of strings you HAVE worked on
   - Example: `corrections_batch1.xlsx` or `languagedata_kor_corrected.xml`

3. **Set TARGET file** (second Browse button)
   - The LOC file you want to CHECK
   - Contains Korean strings (Str attribute has Korean)
   - Example: `F:\...\loc\languagedata_kor.xml`

4. **Click "Extract Korean Misses"** (orange button)

5. **Choose output file location** (save dialog)

6. **Watch TERMINAL** for detailed results

## Matching Logic

```
For each Korean string in TARGET:

  KEY = (StringID, normalized_StrOrigin)

  if KEY exists in SOURCE lookup:
      HIT  (string exists in your corrections)
  else:
      MISS (string NOT in your corrections - needs work!)
```

### Normalization

StrOrigin is normalized before comparison:
- Strip leading/trailing whitespace
- Collapse multiple spaces to single space
- Convert to lowercase

This ensures minor whitespace differences don't cause false misses.

## Process Flow

```
Step 1: Build EXPORT Index
        Scan export__ folder for .loc.xml files
        Create mapping: StringID -> file path (e.g., "System/Gimmick/item.loc.xml")

Step 2: Parse SOURCE File
        Build Set[(StringID, normalized_StrOrigin)] lookup

Step 3: Parse TARGET File
        Collect all LocStr elements with Korean in Str attribute

Step 4: Compare
        For each Korean string, check if (StringID, StrOrigin) exists in SOURCE
        Found = HIT, Not Found = MISS

Step 5: Filter by Excluded Paths
        Remove MISSES in System/Gimmick/* and System/MultiChange/*
        Uses EXPORT index for path lookup (LOC files don't have File attribute!)

Step 6: Write Output
        Save remaining MISSES to output XML file

Step 7: Print Results
        Detailed statistics shown in TERMINAL
```

## Why EXPORT Index?

LOC files (`languagedata_kor.xml`) do NOT have a `File` attribute.
The `File` attribute only exists in EXPORT files (`.loc.xml`).

To know which StringID is in which folder (e.g., System/Gimmick), we must:
1. Scan the EXPORT folder
2. Build StringID -> file path mapping
3. Use this mapping for path filtering

## Excluded Paths

By default, these paths are filtered out (non-priority strings):
- `System/Gimmick/*`
- `System/MultiChange/*`

## Terminal Output

The function prints detailed results to terminal including:
- Progress for each step
- Source lookup count
- Korean strings found
- HITS and MISSES counts
- Filtered out count
- Sample strings (first 5-10 of each category)

## Code Location

- **Core function**: `core/korean_miss_extractor.py`
- **GUI handler**: `gui/app.py` (`_extract_korean_misses` method)
- **Config paths**: `config.py` (`EXPORT_FOLDER`, `LOC_FOLDER`)

## Key Functions

| Function | Purpose |
|----------|---------|
| `build_export_index()` | Scan EXPORT folder, map StringID -> file path |
| `_build_source_lookup()` | Build (StringID, StrOrigin) set from source |
| `_collect_korean_locstr()` | Find all Korean LocStr in target |
| `_filter_by_excluded_paths()` | Filter using EXPORT index |
| `extract_korean_misses()` | Main orchestration function |
| `contains_korean()` | Check if text has Korean characters |

## Example Output

```
================================================================================
KOREAN MISS EXTRACTOR - Terminal Output
================================================================================
Source (reference): F:\corrections\batch1.xlsx
Target (to check):  F:\loc\languagedata_kor.xml
Output:             F:\output\korean_misses.xml
Export folder:      F:\export__
Excluded paths:     System/MultiChange, System/Gimmick
--------------------------------------------------------------------------------

[STEP 1] Building EXPORT index...
[EXPORT INDEX] Scanning 1523 .loc.xml files in: F:\export__
[EXPORT INDEX] Indexed 45678 StringIDs

[STEP 2] Parsing SOURCE file...
  Built source lookup with 1234 (StringID, StrOrigin) pairs

[STEP 3] Parsing TARGET file and collecting Korean strings...
  Found 5000 LocStr elements with Korean text

[STEP 4] Matching against source lookup...
  HITS (found in source):  1200
  MISSES (not in source):  3800

[STEP 5] Filtering by excluded paths...
  Filtered out (excluded paths): 500
  Final misses to write:         3300

================================================================================
RESULTS SUMMARY
================================================================================
Total Korean in Target:    5000
HITS (in source):          1200
MISSES (not in source):    3800
Filtered out:              500
FINAL MISSES:              3300
================================================================================
```

## Verified

- Code reviewed: No bugs found
- Matching logic: Correct (exact StringID + StrOrigin tuple match)
- Path filtering: Uses EXPORT index correctly
- All tests: PASSED

---
*Last updated: 2026-02-03*
