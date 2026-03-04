# MasterSubmitDatasheet — Non-Script ISSUE Row Collection

## Context

The existing `MasterSubmitScript` system (`core/submit_script.py`) collects ISSUE rows from **Script categories** (Sequencer + Dialog) and compiles them into a ready-to-submit Excel. It relies on EventName → EXPORT mapping for StringID + StrOrigin resolution.

**Non-script datasheets** (Item, Character, Region, Skill, Knowledge, Quest, Help, Gimmick, ItemKnowledgeCluster) already have SourceText and STRINGID columns directly in their QA files — no EXPORT mapping needed. We need a **simpler, parallel system** to collect ISSUE rows from these categories.

## Problem

When testers mark rows as `STATUS=ISSUE` with a correction in COMMENT/MEMO, there's no automated way to compile those corrections from non-script QA files into a single submission-ready file.

## Solution: MasterSubmitDatasheet

Scan all non-script QA files, collect rows where `STATUS=ISSUE` + correction exists, and compile them into:
- `MasterSubmitDatasheet_EN.xlsx` — all ISSUE rows from EN QA files
- `MasterSubmitDatasheet_CN.xlsx` — all ISSUE rows from CN QA files
- `MasterSubmitDatasheet_Conflicts_EN.xlsx` — conflicting corrections (if any)
- `MasterSubmitDatasheet_Conflicts_CN.xlsx` — conflicting corrections (if any)

## Key Differences from MasterSubmitScript

| Aspect | MasterSubmitScript (Script) | MasterSubmitDatasheet (Non-Script) |
|--------|----------------------------|-------------------------------------|
| **Categories** | Sequencer, Dialog only | All non-script: Item, Character, Region, Skill, Knowledge, Quest, Help, Gimmick, ItemKnowledgeCluster |
| **SourceText** | From EXPORT (StrOrigin) | Directly from QA file column (SourceText/KR column) |
| **StringID** | From EXPORT (EventName lookup) | Directly from QA file STRINGID column |
| **EventName** | Key identifier + output column | Not applicable |
| **EXPORT mapping** | Required | Not needed |
| **Dedup key** | EventName (lowercase) | StringID (lowercase) — same text can appear with different StringIDs |
| **Output columns** | StrOrigin \| Correction \| StringID \| EventName | SourceText \| Correction \| StringID \| Category |

## Column Detection (per QA file)

Non-script QA files have varying column layouts depending on category and format:

### Required columns (must find ALL or skip file):
1. **STATUS** — always named `STATUS`
2. **STRINGID** — always named `STRINGID`
3. **SourceText** — varies by category:
   - Row-per-text (Item, Character, Skill): `SourceText (KR)` (col 3)
   - Standard (Quest, Knowledge, Help, Gimmick, Region): `Korean` or `Original` (col 1-2)
   - ItemKnowledgeCluster: `SourceText (KR)` (col 2)

### Correction column (try in order):
1. `MEMO` → 2. `COMMENT` → 3. `COMMENT_{username}` columns

### Detection strategy:
Use `build_column_map()` (existing in `excel_ops.py`) to find columns by header name. This is robust regardless of column position.

## Data Structure

```python
@dataclass
class DatasheetIssueRow:
    """One ISSUE row from a non-script QA file."""
    source_text: str         # Korean source text from SourceText column
    correction: str          # Tester's fix from MEMO/COMMENT
    stringid: str            # STRINGID from QA file
    category: str            # Category name (Item, Character, etc.)
    username: str = ""       # Tester who made the correction
```

## Algorithm

```
For each non-script QA folder (grouped by language):
    For each Excel file in folder:
        For each sheet (skip "STATUS" sheet):
            Build column map from header row
            Find: STATUS col, STRINGID col, SourceText col, MEMO/COMMENT col
            If any required column missing → skip sheet

            For each row where STATUS="ISSUE":
                Get stringid, source_text, correction
                Skip if no correction (ISSUE without fix)
                Skip if no stringid (can't submit without ID)

                dedup_key = stringid.lower()
                Track: corrections_by_key[dedup_key].append((username, correction, source_text, category))

Dedup + conflict detection:
    For each dedup_key:
        Collect unique corrections
        If >1 unique correction → add to conflicts
        Take last correction (last wins)

    Output: issue_rows + conflict_rows
```

## Conflict Detection

Same logic as MasterSubmitScript: if multiple testers corrected the **same StringID** with **different corrections**, flag it as a conflict.

```python
@dataclass
class DatasheetConflictRow:
    """Conflict: same StringID corrected differently by multiple testers."""
    stringid: str
    source_text: str
    category: str
    corrections: List[Tuple[str, str]]  # (username, correction) pairs
```

## Output Format

### MasterSubmitDatasheet_EN/CN.xlsx

**Sheet:** `SubmitDatasheet`

| Column | Width | Content |
|--------|-------|---------|
| SourceText | 50 | Korean source text |
| Correction | 50 | Tester's fix |
| StringID | 45 | STRINGID from QA file |
| Category | 20 | Category name (Item, Quest, etc.) |

- All cells: text wrap, borders, left-aligned
- StringID column: text format (`@`) to prevent scientific notation
- No orange highlighting needed (StringID comes directly from QA file, no EXPORT lookup)
- Header: bold, light blue background (same as MasterSubmitScript)

### MasterSubmitDatasheet_Conflicts_EN/CN.xlsx

**Sheet:** `Conflicts`

| Column | Width | Content |
|--------|-------|---------|
| STRINGID | 45 | The conflicting StringID |
| SourceText | 50 | Korean source text |
| Category | 20 | Category name |
| USER | 15 | Tester username |
| CORRECTION | 50 | That tester's correction |

- Header: bold, light red background (same as MasterSubmitScript conflicts)

## Integration Point (compiler.py)

Runs alongside MasterSubmitScript in **STEP 1** (early output, before heavy Master file processing):

```python
# STEP 1a: MasterSubmitScript (Script categories — existing)
# ... existing Sequencer + Dialog logic ...

# STEP 1b: MasterSubmitDatasheet (Non-Script categories — NEW)
from core.submit_datasheet import collect_datasheet_issue_rows, generate_master_submit_datasheet, generate_datasheet_conflict_file

# Non-script categories to scan
NON_SCRIPT_CATEGORIES = ["Item", "Character", "Region", "Skill",
                         "Knowledge", "Quest", "Help", "Gimmick",
                         "ItemKnowledgeCluster"]

# EN
en_datasheet_folders = []
for cat in NON_SCRIPT_CATEGORIES:
    if cat in by_category_en:
        en_datasheet_folders.extend(by_category_en[cat])

if en_datasheet_folders:
    en_ds_issues, en_ds_conflicts = collect_datasheet_issue_rows(en_datasheet_folders)
    generate_master_submit_datasheet(en_ds_issues, MASTER_FOLDER_EN / "MasterSubmitDatasheet_EN.xlsx", "EN")
    generate_datasheet_conflict_file(en_ds_conflicts, MASTER_FOLDER_EN / "MasterSubmitDatasheet_Conflicts_EN.xlsx", "EN")

# CN: same pattern
```

## File Structure

```
core/
├── submit_script.py          # EXISTING — Script categories (Sequencer + Dialog)
├── submit_datasheet.py       # NEW — Non-Script categories (Item, Character, etc.)
├── export_index.py           # EXISTING — only used by submit_script.py
└── compiler.py               # MODIFIED — add STEP 1b call
```

## Non-Script Categories and Their Column Names

| Category | SourceText column name | STRINGID column name | Notes |
|----------|----------------------|---------------------|-------|
| Item | `SourceText (KR)` | `STRINGID` | Row-per-text format |
| Character | `SourceText (KR)` | `STRINGID` | Row-per-text format |
| Skill | `SourceText (KR)` | `STRINGID` | Row-per-text format |
| Region | `Original` | `STRINGID` | Standard format |
| Quest | `Korean` | `STRINGID` | Standard format |
| Knowledge | `Korean` | `STRINGID` | Standard format |
| Help | `Korean` | `STRINGID` | Standard format |
| Gimmick | `Korean` | `STRINGID` | Standard format |
| ItemKnowledgeCluster | `SourceText (KR)` | `STRINGID` | Mega-sheet format |

**Detection approach:** Search header row for any of: `SourceText (KR)`, `Korean`, `Original` — use the first match found.

---

*Created: 2026-03-05*
