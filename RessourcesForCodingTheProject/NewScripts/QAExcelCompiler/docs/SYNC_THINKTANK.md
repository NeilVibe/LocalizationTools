# QA Data Synchronization - Thinktank Plan

**Created:** 2026-01-08 | **Status:** PLANNING | **Author:** Claude + Neil

---

## The Problem

When base datasheets are updated:
- Row indices change (new rows added, rows removed, reordered)
- Column structure may change
- **But we need to preserve ALL work done by:**
  1. **QA Testers** - STATUS, COMMENT, SCREENSHOT in their QA files
  2. **Managers** - STATUS_{User} (FIXED/REPORTED/CHECKING) in Master files

---

## Sheet Structures (Reference)

From `LQA FILE EXAMPLES TO THINK ABOUT SYNCHRONISATION.xlsx`:

### CHARACTER Sheet
```
Col A: Original (KR)
Col B: English (ENG)
Col C: COMMAND
Col D: STATUS          ← QA work
Col E: COMMENT         ← QA work
Col F: STRINGID        ← UNIQUE KEY
Col G: SCREENSHOT      ← QA work
```

### KNOWLEDGE Sheet
```
Col A: Original (KR)
Col B: English (ENG)
Col C: Translation (ZHO-CN)
Col D: STATUS          ← QA work
Col E: COMMENT         ← QA work
Col F: STRINGID        ← UNIQUE KEY
Col G: SCREENSHOT      ← QA work
```

### ITEM Sheet
```
Col A: Filename
Col B: SubGroup
Col C: ItemName(KOR)
Col D: ItemDesc(KOR)
Col E: ItemName(ENG)
Col F: ItemDesc(ENG)
Col G: ItemKey         ← UNIQUE KEY (alternative)
Col H: STATUS          ← QA work
Col I: COMMENT         ← QA work
Col J: STRINGID        ← UNIQUE KEY
Col K: SCREENSHOT      ← QA work
```

---

## Core Insight: STRINGID is the Universal Key

**STRINGID** appears in ALL sheet types and is:
- Unique per row (e.g., `12940736462896`, `4295864944164912`)
- Stable across updates (tied to the string, not the row position)
- Present even when other columns change

**This is the anchor for row matching.**

---

## Data That Needs Synchronization

### From QA Tester Files (Individual)
| Column | Description | Example |
|--------|-------------|---------|
| STATUS | QA status | ISSUE, NO ISSUE, BLOCKED |
| COMMENT | QA feedback | "이름 잘림 (스크린샷 참조)" |
| STRINGID | Already filled by tester | `4295864944164912` |
| SCREENSHOT | Image filename | "화면 캡처 2026-01-07.png" |

### From Master Files (Compiled)
| Column | Description | Example |
|--------|-------------|---------|
| COMMENT_{User} | Per-user comments | "Translation issue\n---\n(updated: ...)" |
| SCREENSHOT_{User} | Per-user screenshots | "John_Quest_bug.png" |
| STATUS_{User} | Manager status | FIXED, REPORTED, CHECKING |

---

## Sync Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SYNC WORKFLOW                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1: EXPORT (Before Update)                                        │
│  ─────────────────────────────────                                      │
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────────────────────┐          │
│  │ QA Tester Files  │ ──→ │ work_snapshot_testers.json       │          │
│  │ (old structure)  │     │ {STRINGID: {status, comment, img}}│          │
│  └──────────────────┘     └──────────────────────────────────┘          │
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────────────────────┐          │
│  │ Master Files     │ ──→ │ work_snapshot_masters.json       │          │
│  │ (old structure)  │     │ {STRINGID: {comments, statuses}} │          │
│  └──────────────────┘     └──────────────────────────────────┘          │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 2: UPDATE (You do this manually)                                 │
│  ───────────────────────────────────────                                │
│                                                                          │
│  - Update base datasheets (new rows, structure changes)                 │
│  - Distribute new blank QA files to testers                             │
│  - New files have STRINGID column already populated                     │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 3: IMPORT (After Update)                                         │
│  ──────────────────────────────────                                     │
│                                                                          │
│  ┌──────────────────────────────────┐     ┌──────────────────┐          │
│  │ work_snapshot_testers.json       │ ──→ │ QA Tester Files  │          │
│  │                                  │     │ (new structure)  │          │
│  └──────────────────────────────────┘     └──────────────────┘          │
│                                           Match by STRINGID,            │
│                                           inject STATUS/COMMENT/IMG     │
│                                                                          │
│  ┌──────────────────────────────────┐     ┌──────────────────┐          │
│  │ work_snapshot_masters.json       │ ──→ │ Master Files     │          │
│  │                                  │     │ (new structure)  │          │
│  └──────────────────────────────────┘     └──────────────────┘          │
│                                           Match by STRINGID,            │
│                                           inject COMMENT_{User}, etc    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Snapshot Data Structure

### work_snapshot_testers.json
```json
{
  "export_date": "2026-01-08T10:30:00",
  "source_files": ["John_Quest", "Alice_Quest", "Bob_Knowledge"],
  "data": {
    "4295864944164912": {
      "category": "Character",
      "sheet": "Sheet1",
      "user": "John",
      "status": "ISSUE",
      "comment": "이름 잘림 (스크린샷 참조)",
      "screenshot": "화면 캡처 2026-01-07 172345.png",
      "original_row": 4
    },
    "12940736462896": {
      "category": "Character",
      "sheet": "Sheet1",
      "user": "John",
      "status": "NO ISSUE",
      "comment": "",
      "screenshot": "",
      "original_row": 3
    }
  }
}
```

### work_snapshot_masters.json
```json
{
  "export_date": "2026-01-08T10:30:00",
  "source_files": ["Master_Quest.xlsx", "Master_Knowledge.xlsx"],
  "data": {
    "4295864944164912": {
      "category": "Character",
      "sheet": "Sheet1",
      "users": {
        "John": {
          "comment": "이름 잘림...\n---\nstringid:\n4295864944164912\n(updated: 260107 1723)",
          "screenshot": "John_Character_화면캡처.png",
          "manager_status": "REPORTED"
        },
        "Alice": {
          "comment": "",
          "screenshot": "",
          "manager_status": ""
        }
      },
      "original_row": 4
    }
  }
}
```

---

## Row Matching Algorithm

### Primary: STRINGID Match (99% of cases)
```python
def find_row_by_stringid(new_ws, stringid, stringid_col):
    """Find row in new worksheet by STRINGID."""
    for row_idx in range(2, new_ws.max_row + 1):
        cell_value = new_ws.cell(row=row_idx, column=stringid_col).value
        if str(cell_value) == str(stringid):
            return row_idx
    return None  # STRINGID not found (row deleted in new version)
```

### Fallback: Composite Key (if STRINGID missing)
```python
def find_row_by_composite(new_ws, old_row_data, key_columns):
    """
    Match by 2+ column values when STRINGID is missing.

    key_columns = ['Original (KR)', 'English (ENG)']
    """
    for row_idx in range(2, new_ws.max_row + 1):
        matches = 0
        for col_name in key_columns:
            old_val = old_row_data.get(col_name)
            new_val = get_cell_by_header(new_ws, row_idx, col_name)
            if old_val and new_val and str(old_val).strip() == str(new_val).strip():
                matches += 1
        if matches >= 2:
            return row_idx
    return None
```

---

## Edge Cases & Handling

| Scenario | What Happens | Handling |
|----------|--------------|----------|
| **Row exists in both** | Normal case | Copy data to matching row |
| **Row deleted in new** | STRINGID not found | Log warning, data preserved in snapshot |
| **Row added in new** | No old data | Leave blank (new row, no QA work yet) |
| **STRINGID changed** | Rare, problematic | Fallback to composite key matching |
| **Duplicate STRINGIDs** | Data integrity issue | Log error, use first match |
| **Column moved** | Different column index | Find column by header name |
| **Column renamed** | e.g., "ENG" → "English" | Column mapping config |
| **Column deleted** | Column doesn't exist | Skip that data field |
| **New column added** | Doesn't affect sync | Ignore, only sync known fields |

---

## Sync Reports

After import, generate a report:

```
=== SYNC REPORT ===
Date: 2026-01-08 14:30:00

TESTERS SYNC:
  Rows matched:     1,234
  Rows not found:   12 (see below)
  New rows (blank): 45

MASTER SYNC:
  Rows matched:     1,234
  Rows not found:   12
  Users synced:     John, Alice, Bob, Mary

MISSING ROWS (work may be lost):
  STRINGID: 4295864944164912 (was row 45 in Character sheet)
    - John: ISSUE, "이름 잘림..."
  STRINGID: 8138866672623682705 (was row 13 in Knowledge sheet)
    - Alice: BLOCKED, "따옴표 뒷부분..."

ACTION REQUIRED:
  - Review 12 missing rows
  - Manually re-add if strings were moved/renamed
```

---

## Tool Commands (Proposed)

```bash
# PHASE 1: Export before update
python3 sync_qa.py export --source QAfolder --output work_snapshot.json

# PHASE 1b: Export master data too
python3 sync_qa.py export-master --source Masterfolder_EN --output master_snapshot.json

# PHASE 3: Import after update
python3 sync_qa.py import --snapshot work_snapshot.json --target QAfolder_NEW

# PHASE 3b: Import master data
python3 sync_qa.py import-master --snapshot master_snapshot.json --target Masterfolder_EN_NEW

# Generate sync report
python3 sync_qa.py report --snapshot work_snapshot.json --target QAfolder_NEW
```

---

## Image Handling

Images need special care:

### Export Phase
1. Copy all images from `QAfolder/{User}_{Category}/` to `sync_backup/images/`
2. Record image→STRINGID mapping in snapshot

### Import Phase
1. For each matched row with screenshot:
   - Find image in `sync_backup/images/`
   - Copy to new `QAfolder/{User}_{Category}/`
   - Update hyperlink if needed

---

## CRITICAL Questions for Neil

### Must Answer Before Implementation:

| # | Question | Why It Matters |
|---|----------|----------------|
| 1 | **Is STRINGID pre-filled in base sheets?** | If testers fill it manually, it might be missing or wrong |
| 2 | **Is STRINGID unique per row?** | Duplicates would break matching |
| 3 | **Does STRINGID survive updates?** | If same string gets new ID, matching fails |
| 4 | **What generates STRINGID?** | Need to understand the source system |
| 5 | **Can STRINGID be empty?** | Need fallback strategy if yes |

### Workflow Questions:

| # | Question | Options |
|---|----------|---------|
| 6 | **Who runs the sync tool?** | You (manager) vs each tester |
| 7 | **When do testers get new files?** | Before sync (they run import) vs after sync (you run import, send them result) |
| 8 | **Multiple testers same category?** | Need to merge their work or keep separate? |

### Findings from Current Files:

```
Test QA files: STRINGID in column 8
  - John_Quest: 10001, 10002, 10003...
  - Alice_Quest: 10001, 10002, 10003... (SAME as John!)
  - Bob_Knowledge: 20001, 20002, 20003...

Your example file: Much longer IDs
  - Character: 12940736462896, 4295864944164912
  - Knowledge: 18040527660286738689
  - Item: 4302191430991984
```

**Observation:** Test data uses simple sequential IDs. Real data uses large unique hashes. This confirms STRINGID is the right key.

---

## Implementation Priority

| Priority | Task | Complexity |
|----------|------|------------|
| P1 | Export tester work to JSON | Medium |
| P1 | Import tester work from JSON | Medium |
| P2 | Export master work to JSON | High (more complex structure) |
| P2 | Import master work from JSON | High |
| P3 | Sync report generation | Low |
| P3 | Image backup/restore | Medium |

---

## Alternative Approaches Considered

### Option A: Row-by-Row (Current compile_qa.py)
- **How**: Match by row index
- **Problem**: Breaks when rows are added/removed/reordered
- **Verdict**: NOT SUITABLE for datasheet updates

### Option B: STRINGID-Based (This Plan)
- **How**: Use STRINGID as primary key
- **Problem**: Requires STRINGID in all sheets
- **Verdict**: BEST APPROACH if STRINGID is reliable

### Option C: Fuzzy Text Matching
- **How**: Match by similar text content
- **Problem**: Slow, error-prone, false positives
- **Verdict**: Only as last-resort fallback

---

## CRITICAL: Testing Before Implementation

### Why Testing First?

We CANNOT afford to lose QA work. Before building the full tool:

1. **Validate STRINGID reliability** on real data
2. **Test matching algorithm** manually
3. **Verify data integrity** after transfer
4. **Identify edge cases** in production data

### Proposed Test Plan

```
PHASE 1: STRINGID Analysis (No code, just investigation)
────────────────────────────────────────────────────────
1. Take ONE real tester file (e.g., 김동헌_Character.xlsx)
2. Open in Excel, examine STRINGID column:
   - Are values present for all rows?
   - Are they unique?
   - Are they numeric or text?
   - Any scientific notation (1.29E+13)?

3. Generate NEW Character datasheet (run fullcharacter1.py)
4. Compare STRINGIDs between old and new:
   - Same values?
   - Same order?
   - Any missing?

Expected outcome: Understand STRINGID reliability
```

```
PHASE 2: Manual Sync Test (Spreadsheet-only, no code)
────────────────────────────────────────────────────────
1. Pick 5-10 rows with QA work from old file
2. Note: Korean text, STRINGID, STATUS, COMMENT
3. In new file, manually find matching rows by STRINGID
4. Check: Did we find correct rows?
5. If not: Try fallback (Korean + tab name)

Expected outcome: Prove the matching strategy works
```

```
PHASE 3: Prototype Script Test
────────────────────────────────────────────────────────
1. Build minimal export-only script
2. Run on ONE tester folder
3. Review JSON output - is data captured correctly?
4. Build minimal import script
5. Test on COPY of new datasheet (not original!)
6. Verify data injected correctly

Expected outcome: Confidence before batch processing
```

---

## Workflow Options to Consider

### Option A: One-by-One Processing

```
For each tester:
  1. Collect their old QA file
  2. Run export (creates JSON + image backup)
  3. Give them new blank datasheet
  4. Run import on their new file
  5. Verify manually
  6. Send back updated file
```

**Pros:** Safe, catch errors early, easy rollback
**Cons:** Slow (20+ testers × 6 categories = 120 operations)

### Option B: Batch by Category

```
For each category (Character, Quest, etc.):
  1. Collect ALL tester files for that category
  2. Run batch export
  3. Distribute new blank datasheets
  4. Run batch import
  5. Spot-check a few files
  6. Send back all files
```

**Pros:** Faster, organized by category
**Cons:** More risk if something goes wrong

### Option C: Full Batch with Safety Net

```
1. Export ALL work from ALL folders (creates huge snapshot)
2. Update ALL datasheets
3. Import ALL work to new folders
4. Generate detailed report
5. Manual review of problem rows
```

**Pros:** Fastest
**Cons:** Highest risk, complex debugging

### Recommendation: Option B (Batch by Category)

- Manageable chunks
- Category-specific issues easier to debug
- Can pause between categories if problems arise

---

## Sync Tool Input/Output Structure

### Three-Folder System

```
QAExcelCompiler/
├── sync_input_old/              # INPUT 1: Old QA files with work
│   ├── 김동헌_Character/
│   │   ├── LQA.xlsx             # Has STATUS, COMMENT, SCREENSHOT filled
│   │   └── bug.png
│   ├── 황하연_Character/
│   │   └── LQA.xlsx
│   ├── 김동헌_Quest/
│   │   └── LQA.xlsx
│   └── ...
│
├── sync_input_templates/        # INPUT 2: New blank datasheets (one per category)
│   ├── Character_LQA.xlsx       # Fresh from fullcharacter1.py
│   ├── Quest_LQA.xlsx           # Fresh from fullquest15.py
│   ├── Knowledge_LQA.xlsx
│   ├── Item_LQA.xlsx
│   ├── Region_LQA.xlsx
│   └── Gimmick_LQA.xlsx
│
└── sync_output/                 # OUTPUT: Synchronized files
    ├── 김동헌_Character/
    │   ├── LQA.xlsx             # Work transferred to new structure!
    │   └── bug.png              # Images copied
    ├── 황하연_Character/
    │   └── LQA.xlsx
    └── ...
```

### Auto-Recognition (Same as compile_qa.py)

**Folder name format:** `{Username}_{Category}/`

```python
# Parse folder name - same logic as existing compiler
folder_name = "김동헌_Character"
parts = folder_name.split('_')
username = parts[0]              # "김동헌"
category = '_'.join(parts[1:])   # "Character"

# Match to template
template_file = f"{category}_LQA.xlsx"  # "Character_LQA.xlsx"
```

### Category Detection from Template

Templates named by category: `{Category}_LQA.xlsx`

The sync tool:
1. Scans `sync_input_old/` for `{User}_{Category}/` folders
2. Finds matching template in `sync_input_templates/{Category}_LQA.xlsx`
3. Creates output in `sync_output/{User}_{Category}/`

---

## Per-Category Column Mapping

Each category has different column structure. Need explicit mapping.

### From Example File Analysis:

**CHARACTER Structure:**
```
Col A: Original (KR)     ← Korean source (matching key)
Col B: English (ENG)
Col C: COMMAND           ← Secondary key (has strkey)
Col D: STATUS            ← QA work to sync
Col E: COMMENT           ← QA work to sync
Col F: STRINGID          ← Primary matching key
Col G: SCREENSHOT        ← QA work to sync
```

**KNOWLEDGE Structure:**
```
Col A: Original (KR)     ← Korean source
Col B: English (ENG)     ← Secondary key
Col C: Translation (ZHO-CN)
Col D: STATUS            ← QA work
Col E: COMMENT           ← QA work
Col F: STRINGID          ← Primary key
Col G: SCREENSHOT        ← QA work
```

**ITEM Structure:**
```
Col A: Filename
Col B: SubGroup
Col C: ItemName(KOR)     ← Korean source
Col D: ItemDesc(KOR)
Col E: ItemName(ENG)
Col F: ItemDesc(ENG)
Col G: ItemKey           ← Secondary key (game ID)
Col H: STATUS            ← QA work
Col I: COMMENT           ← QA work
Col J: STRINGID          ← Primary key
Col K: SCREENSHOT        ← QA work
```

### Category Mapping Config

```python
CATEGORY_MAPPING = {
    "Character": {
        "korean_col": "Original (KR)",
        "stringid_col": "STRINGID",
        "secondary_col": "COMMAND",
        "work_cols": ["STATUS", "COMMENT", "SCREENSHOT"],
    },
    "Knowledge": {
        "korean_col": "Original (KR)",
        "stringid_col": "STRINGID",
        "secondary_col": "English (ENG)",
        "work_cols": ["STATUS", "COMMENT", "SCREENSHOT"],
    },
    "Item": {
        "korean_col": "ItemName(KOR)",
        "stringid_col": "STRINGID",
        "secondary_col": "ItemKey",
        "work_cols": ["STATUS", "COMMENT", "SCREENSHOT"],
    },
    "Quest": {
        "korean_col": "Original (KR)",
        "stringid_col": "STRINGID",
        "secondary_col": "StringKey",
        "work_cols": ["STATUS", "COMMENT", "SCREENSHOT"],
    },
    "Region": {
        "korean_col": "Original (KR)",
        "stringid_col": "STRINGID",
        "secondary_col": "English (ENG)",
        "work_cols": ["STATUS", "COMMENT", "SCREENSHOT"],
    },
    "Gimmick": {
        "korean_col": "Original (KR)",
        "stringid_col": "STRINGID",
        "secondary_col": "COMMAND",
        "work_cols": ["STATUS", "COMMENT", "SCREENSHOT"],
    },
}
```

### Adding New Categories

When you provide more category examples:
1. Identify the Korean source column name
2. Identify the STRINGID column name
3. Identify best secondary key column
4. Add to CATEGORY_MAPPING dict

---

## Multi-Tab Sheet Handling

Some categories have multiple tabs (sheets) within one Excel file.

### Example: Character File

```
Character_LQA.xlsx
├── NPC          # Tab 1 - NPC characters
├── MONSTER      # Tab 2 - Monsters
├── BOSS         # Tab 3 - Boss enemies
└── MERCHANT     # Tab 4 - Merchants
```

### Sync Strategy for Multi-Tab

**Tab matching by name:**
1. Old file has tabs: NPC, MONSTER, BOSS
2. New template has tabs: NPC, MONSTER, BOSS, MERCHANT (new tab added)
3. Sync process:
   - NPC → NPC (match by tab name)
   - MONSTER → MONSTER
   - BOSS → BOSS
   - MERCHANT → no old data (new tab, leave blank)

**What if tab names change?**
- Old: "NPC_Characters" → New: "NPC"
- Need tab name mapping or fuzzy matching
- Or: Match by content (find tab with matching STRINGIDs)

### Tab Matching Algorithm

```python
def find_matching_tab(old_ws, new_wb, old_tab_name):
    """
    Find matching tab in new workbook.

    Strategy:
    1. Exact name match
    2. Case-insensitive match
    3. Partial match (NPC in NPC_Characters)
    4. Content-based match (same STRINGIDs)
    """
    # 1. Exact match
    if old_tab_name in new_wb.sheetnames:
        return new_wb[old_tab_name]

    # 2. Case-insensitive
    for new_name in new_wb.sheetnames:
        if new_name.upper() == old_tab_name.upper():
            return new_wb[new_name]

    # 3. Partial match
    for new_name in new_wb.sheetnames:
        if old_tab_name.upper() in new_name.upper():
            return new_wb[new_name]
        if new_name.upper() in old_tab_name.upper():
            return new_wb[new_name]

    # 4. Content-based (extract STRINGIDs from old, find in new)
    old_stringids = extract_stringids(old_ws)
    for new_name in new_wb.sheetnames:
        new_stringids = extract_stringids(new_wb[new_name])
        overlap = len(old_stringids & new_stringids)
        if overlap > len(old_stringids) * 0.5:  # >50% match
            return new_wb[new_name]

    return None  # No match found
```

---

## Complete Sync Algorithm Flow

### High-Level Process

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SYNC ALGORITHM FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STEP 1: SCAN INPUT FOLDERS                                              │
│  ─────────────────────────────                                          │
│  • Scan sync_input_old/ for {User}_{Category}/ folders                  │
│  • Scan sync_input_templates/ for {Category}_LQA.xlsx files             │
│  • Build mapping: which users work on which categories                  │
│                                                                          │
│  Result: List of (user, category, old_file, template_file) tuples       │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STEP 2: FOR EACH (USER, CATEGORY) PAIR                                 │
│  ───────────────────────────────────────                                │
│                                                                          │
│  2a. Load files                                                          │
│      • old_wb = load(old_file)                                          │
│      • template_wb = load(template_file)                                │
│      • Get category mapping config                                       │
│                                                                          │
│  2b. For each TAB in old workbook:                                      │
│      • Find matching tab in template (by name or content)               │
│      • If no match → log warning, skip tab                              │
│                                                                          │
│  2c. For each ROW in old tab with work:                                 │
│      • Extract: STRINGID, Korean, secondary_key, STATUS, COMMENT, IMG   │
│      • Find matching row in new tab (cascading fallback)                │
│      • If found → inject work data                                      │
│      • If not found → log as missing                                    │
│                                                                          │
│  2d. Save output                                                         │
│      • Create sync_output/{User}_{Category}/                            │
│      • Save modified template as LQA.xlsx                               │
│      • Copy images from old folder                                      │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STEP 3: GENERATE REPORT                                                │
│  ───────────────────────                                                │
│  • Total rows processed                                                 │
│  • Rows successfully matched                                            │
│  • Rows not found (with details for manual review)                      │
│  • Tabs not matched                                                      │
│  • Images copied                                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Row Matching Detail (Step 2c)

```python
def sync_row(old_row_data, new_tab, category_config):
    """
    Try to find and update matching row in new tab.

    Returns: (success: bool, match_level: str, new_row_idx: int or None)
    """
    stringid = normalize_stringid(old_row_data['stringid'])
    korean = old_row_data['korean']
    secondary = old_row_data['secondary']
    tab_name = old_row_data['tab']

    # Level 1: STRINGID alone
    if stringid:
        matches = find_rows_by_stringid(new_tab, stringid)
        if len(matches) == 1:
            inject_work(new_tab, matches[0], old_row_data)
            return (True, "STRINGID", matches[0])

    # Level 2: STRINGID + Korean (for duplicates)
    if stringid and korean:
        matches = find_rows_by_stringid_and_korean(new_tab, stringid, korean)
        if len(matches) == 1:
            inject_work(new_tab, matches[0], old_row_data)
            return (True, "STRINGID+Korean", matches[0])

    # Level 3: Korean + Secondary key
    if korean and secondary:
        matches = find_rows_by_korean_and_secondary(new_tab, korean, secondary)
        if len(matches) == 1:
            inject_work(new_tab, matches[0], old_row_data)
            return (True, "Korean+Secondary", matches[0])

    # Level 4: Korean + Tab name context
    if korean:
        matches = find_rows_by_korean(new_tab, korean)
        if len(matches) == 1:
            inject_work(new_tab, matches[0], old_row_data)
            return (True, "Korean", matches[0])

    # No match found
    return (False, "NOT_FOUND", None)


def inject_work(new_tab, row_idx, old_row_data):
    """Inject STATUS, COMMENT, SCREENSHOT into new row."""
    col_map = get_column_map(new_tab)

    if old_row_data.get('status') and 'STATUS' in col_map:
        new_tab.cell(row_idx, col_map['STATUS']).value = old_row_data['status']

    if old_row_data.get('comment') and 'COMMENT' in col_map:
        new_tab.cell(row_idx, col_map['COMMENT']).value = old_row_data['comment']

    if old_row_data.get('screenshot') and 'SCREENSHOT' in col_map:
        new_tab.cell(row_idx, col_map['SCREENSHOT']).value = old_row_data['screenshot']
```

### Output Report Format

```
═══════════════════════════════════════════════════════════════════
                      QA SYNC REPORT - 2026-01-08
═══════════════════════════════════════════════════════════════════

SUMMARY
───────
  Folders processed:    25
  Total rows with work: 1,847
  Rows matched:         1,823 (98.7%)
  Rows NOT found:       24 (1.3%)
  Images copied:        156

MATCH LEVEL BREAKDOWN
─────────────────────
  STRINGID alone:       1,650 (90.5%)
  STRINGID + Korean:    120 (6.6%)
  Korean + Secondary:   45 (2.5%)
  Korean alone:         8 (0.4%)

BY CATEGORY
───────────
  Character:  450 matched, 3 missing
  Quest:      380 matched, 5 missing
  Knowledge:  520 matched, 8 missing
  Item:       300 matched, 6 missing
  Region:     173 matched, 2 missing

NOT FOUND ROWS (Manual Review Required)
───────────────────────────────────────
  [김동헌_Character] Row 145
    Korean: "은색 비지오네 쓴 환자"
    STRINGID: 4295864944164912
    STATUS: ISSUE
    COMMENT: "이름 잘림 (스크린샷 참조)"
    → Possible reason: Row deleted in new version

  [황하연_Quest] Row 892
    Korean: "신비로운 숲의 비밀"
    STRINGID: (empty)
    STATUS: NO ISSUE
    → Possible reason: No STRINGID, Korean text changed

  ... (22 more)

═══════════════════════════════════════════════════════════════════
```

---

## Folder Naming Convention

Current format: `{Username}_{Category}/`

Examples:
- `김동헌_Character/`
- `황하연_Quest/`
- `Alice_Knowledge/`

### Recognition Strategy

```python
# Parse folder name
parts = folder.name.split('_')
username = parts[0]          # "김동헌"
category = '_'.join(parts[1:])  # "Character" or "EN_Item"
```

### Special Cases

- `김동헌_EN_Item/` → username="김동헌", category="EN_Item"
- `Test_User_Quest/` → username="Test", category="User_Quest" (WRONG!)

**Risk:** Usernames with underscores will break parsing.

**Solution:** Use mapping file or strict naming convention (no underscores in usernames).

---

## Data Integrity Concerns

### What Could Go Wrong?

| Issue | Impact | Mitigation |
|-------|--------|------------|
| STRINGID missing | Can't match row | Fallback to Korean |
| STRINGID duplicate | Wrong row matched | Korean + STRINGID combo |
| Korean text changed | No match found | Log as missing, manual fix |
| New row in new sheet | No old data | Leave blank (expected) |
| Row deleted in new | Old data lost | Log warning, preserve in JSON |
| Screenshot not found | Broken hyperlink | Image backup system |
| Excel corrupts data | Silent data loss | Read with data_only=False |

### STRINGID Format Issues

```
Possible formats:
- Integer: 12940736462896
- Float: 12940736462896.0
- Scientific: 1.29407364629E+13
- String: "12940736462896"
- Truncated: 12940736462000 (precision lost!)
```

**Critical:** Must normalize ALL formats to same string.

---

## Questions Still Open

1. **Do we have real tester files to test with?**
   - Need at least 1 complete file with STATUS/COMMENT filled

2. **When will new datasheets be generated?**
   - Need to coordinate export BEFORE update

3. **How many testers × categories?**
   - Helps estimate scope of work

4. **Any testers with non-standard folder names?**
   - Need to know exceptions

5. **Where are Master files currently?**
   - Need to sync manager work too

---

## Next Steps (Revised)

### Immediate (Before coding):
1. [ ] Get ONE real tester file with work
2. [ ] Analyze STRINGID format and reliability
3. [ ] Manual matching test (5-10 rows)
4. [ ] Confirm workflow choice (Option A/B/C)

### After validation:
5. [ ] Build export command (tester files)
6. [ ] Test on real data
7. [ ] Build import command
8. [ ] Build master sync commands
9. [ ] Full integration test

---

*Document created for QA Compiler sync planning*
*Updated: 2026-01-08 - Added testing strategy and workflow options*
