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

    # Level 3: STRINGID + Korean + Secondary (for same-Korean duplicates)
    # Example: Same character name, same STRINGID, but different COMMAND
    #   NHW_Citizen_... vs NHM_Citizen_...
    if stringid and korean and secondary:
        matches = find_rows_by_stringid_korean_secondary(new_tab, stringid, korean, secondary)
        if len(matches) == 1:
            inject_work(new_tab, matches[0], old_row_data)
            return (True, "STRINGID+Korean+Secondary", matches[0])

    # Level 4: Korean + Secondary key (no STRINGID)
    if korean and secondary:
        matches = find_rows_by_korean_and_secondary(new_tab, korean, secondary)
        if len(matches) == 1:
            inject_work(new_tab, matches[0], old_row_data)
            return (True, "Korean+Secondary", matches[0])

    # Level 5: Korean + Tab name context
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

## TEST RESULTS: Matching Simulation (2026-01-08)

### Test Setup

Used example file data to simulate old→new matching:

**OLD DATA (with QA work):**
```
Row 3: 환자                  | STRINGID: 12940736462896  | NO ISSUE
Row 4: 은색 비지오네 쓴 환자   | STRINGID: 4295864944164912 | ISSUE (comment A)
Row 5: 은색 비지오네 쓴 환자   | STRINGID: 4295864944164912 | ISSUE (comment B)
Row 6: 하녀                  | STRINGID: 12658599618792128560 | NO ISSUE
```

**NEW DATA (shuffled, 1 added, 1 deleted):**
```
Row 2: 하녀                  | STRINGID: 12658599618792128560
Row 3: 새로운 캐릭터          | STRINGID: 99999999999999 (NEW)
Row 4: 은색 비지오네 쓴 환자   | STRINGID: 4295864944164912
Row 5: 은색 비지오네 쓴 환자   | STRINGID: 4295864944164912
(환자 DELETED)
```

### Test Results

| Old Row | Result | Method | Notes |
|---------|--------|--------|-------|
| Row 3 (환자) | ❌ NOT FOUND | - | Row deleted in new version |
| Row 4 | ✅ → New Row 4 | STRINGID+Korean | Matched correctly |
| Row 5 | ⚠️ → New Row 4 | STRINGID+Korean | COLLISION with row 4! |
| Row 6 | ✅ → New Row 2 | STRINGID | Matched correctly |

### Key Finding: Duplicate STRINGID Problem

**Problem:** Rows 4 and 5 have:
- Same STRINGID: `4295864944164912`
- Same Korean: `은색 비지오네 쓴 환자`
- BUT different comments!

**Result:** Both old rows matched to same new row 4. One comment will overwrite the other.

### Solutions for Duplicates

**Option 1: Positional Matching (Recommended)**
```
If multiple old rows match same new rows:
  Sort both by row index
  Map 1st old → 1st new
  Map 2nd old → 2nd new
  ...
```

**Option 2: Merge Comments**
```
If old row 4 comment = "이름 잘림 (스크린샷 참조)"
And old row 5 comment = "이름 잘림 (414행과 동일)"
New comment = "이름 잘림 (스크린샷 참조)\n---\n이름 잘림 (414행과 동일)"
```

**Option 3: Use Additional Column**
```
Check COMMAND column or other differentiator
Row 4: /create character NHW_Citizen_Silver_Vis...
Row 5: /create character NHM_Citizen_Silver_Vis... (different!)
```

### Test Conclusion

✅ **STRINGID matching works** - handles row reordering correctly
✅ **Deleted rows detected** - logged for manual review
✅ **Duplicate handling available** - COMMAND column can differentiate if needed

---

## FINAL SIMPLIFIED APPROACH (2026-01-08)

After discussion, we simplified to a cleaner approach:

### Matching Strategy: Translation + STRINGID

```
Match criteria: Translation column + STRINGID column
  - If MATCH → Transfer STATUS, COMMENT, SCREENSHOT
  - If NO MATCH → Leave blank (tester must recheck anyway)
```

**Why this is better:**
1. Simple and reliable
2. If translation changed, tester needs to recheck anyway
3. No complex fallback cascade needed
4. STRINGID ensures uniqueness

### Translation Column Names (by language)

| Language | Column Header |
|----------|---------------|
| English | Translation (ENG) or English (ENG) |
| Chinese | Translation (ZHO-CN) |

### Columns to Sync

```
From QA files, sync these columns:
  - Translation (language-specific header)
  - STATUS
  - COMMENT
  - STRINGID (must be clean format)
  - SCREENSHOT
```

### STRINGID Format Requirement

STRINGID must be stored as TEXT, not number:
- ✅ Good: `"12940736462896"` (string)
- ❌ Bad: `12940736462896` (number, loses precision)
- ❌ Bad: `1.29E+13` (scientific notation)

---

## MASTER SHEET SYNC PROCESS

### Current compile_qa.py Behavior

**Important to understand:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Does Master_Quest.xlsx EXIST?                                   │
├──────────────────┬──────────────────────────────────────────────┤
│       YES        │                    NO                        │
├──────────────────┼──────────────────────────────────────────────┤
│ LOAD existing    │ CREATE from first QA file as template        │
│ (keeps OLD       │ (deletes STATUS/COMMENT/SCREENSHOT cols,     │
│  structure!)     │  starts clean)                               │
└──────────────────┴──────────────────────────────────────────────┘
```

**Current manager STATUS handling:**
- `preprocess_manager_status()` reads old master BEFORE processing
- Saves STATUS_{User} values **BY ROW INDEX** (not by COMMENT)
- After processing, restores STATUS by row index
- **Problem:** If row order changes, wrong STATUS applied to wrong row!

### The New Approach

**Goal:** Extract COMMENT + STATUS pairs, rebuild fresh, apply STATUS by COMMENT match.

```
STEP 1: EXTRACT from old master
────────────────────────────────────────────────────────
  Load Master_Quest.xlsx (old structure)
           ↓
  Build map: {COMMENT_text: STATUS_value}

  Example:
    {"이름 잘림 (스크린샷 참조)": "FIXED"}
    {"번역 오류입니다": "REPORTED"}

STEP 2: DELETE old master
────────────────────────────────────────────────────────
  Remove Master_Quest.xlsx
  (forces fresh creation with new structure)

STEP 3: BUILD fresh master from synced QA files
────────────────────────────────────────────────────────
  Synced QA files (new structure)
           ↓
  compile_qa.py creates Master_Quest.xlsx
           ↓
  New master has:
    - New structure (from QA files)
    - COMMENT_{User} columns populated
    - STATUS_{User} columns EMPTY

STEP 4: APPLY STATUS by COMMENT match
────────────────────────────────────────────────────────
  For each row in new master:
    comment = COMMENT_{User}
    if comment in extracted_map:
      STATUS_{User} = extracted_map[comment]
           ↓
  Complete master with STATUS restored!
```

### Why Match by COMMENT (not STRINGID)?

| Match by | Pros | Cons |
|----------|------|------|
| **COMMENT** | Direct link (STATUS is response to COMMENT) | If comment text edited, no match |
| **STRINGID** | More stable identifier | STATUS might apply to different comment |

**COMMENT is better because:**
- Manager STATUS is a response to a specific COMMENT
- Same comment = same issue = same manager response
- If comment was edited/changed, manager should re-review anyway

### Changes Needed to compile_qa.py

```python
# CURRENT (row index based):
def preprocess_manager_status():
    for row in old_master:
        manager_status[row_index] = status_value  # ❌ By row

# NEW (comment based):
def preprocess_manager_status():
    for row in old_master:
        comment = get_comment(row)
        manager_status[comment] = status_value    # ✅ By comment
```

```python
# CURRENT restore:
if row_index in manager_status:
    apply_status(manager_status[row_index])       # ❌ By row

# NEW restore:
comment = get_comment(row)
if comment in manager_status:
    apply_status(manager_status[comment])         # ✅ By comment
```

### Full Sync Workflow (Updated)

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: SYNC QA FILES                                          │
│                                                                  │
│   Old QA files ──→ sync_qa.py ──→ New QA files                  │
│   (Translation + STRINGID matching)                             │
│                                                                  │
│   ✓ Match → Transfer STATUS, COMMENT, SCREENSHOT                │
│   ✗ No match → Leave blank (tester rechecks)                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: REBUILD MASTER FILES                                   │
│                                                                  │
│   1. Load old master → Extract {COMMENT: STATUS} map            │
│   2. Delete old master files                                    │
│   3. Run compile_qa.py (creates fresh from synced QA)           │
│   4. Apply STATUS by COMMENT matching                           │
│                                                                  │
│   Result: New structure + preserved manager work                │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Works

1. **compile_qa.py is index-based** - Works fine because QA files are synced first
2. **Manager STATUS linked to COMMENT** - Same comment = same issue = same status
3. **No match = new issue** - If comment didn't exist before, no status to transfer

### Manager STATUS Transfer Logic

```python
def transfer_manager_status(old_master_ws, new_master_ws, user):
    """
    Transfer STATUS_{User} from old master to new master.
    Match by COMMENT_{User} content.
    """
    comment_col = f"COMMENT_{user}"
    status_col = f"STATUS_{user}"

    # Build map: comment_text → status_value from old master
    old_status_map = {}
    for row in range(2, old_master_ws.max_row + 1):
        comment = get_cell_value(old_master_ws, row, comment_col)
        status = get_cell_value(old_master_ws, row, status_col)
        if comment and status:
            # Use comment text (or first 100 chars) as key
            key = str(comment).strip()[:100]
            old_status_map[key] = status

    # Apply to new master
    matched = 0
    for row in range(2, new_master_ws.max_row + 1):
        comment = get_cell_value(new_master_ws, row, comment_col)
        if comment:
            key = str(comment).strip()[:100]
            if key in old_status_map:
                set_cell_value(new_master_ws, row, status_col, old_status_map[key])
                matched += 1

    return matched
```

### Alternative: Use STRINGID for Manager STATUS

If COMMENT matching is unreliable (comments might be edited):

```python
# Build map: STRINGID → STATUS_{User}
old_status_by_stringid = {}
for row in old_master:
    stringid = get_stringid(row)
    status = get_status(row, user)
    if stringid and status:
        old_status_by_stringid[stringid] = status

# Apply to new master by STRINGID
for row in new_master:
    stringid = get_stringid(row)
    if stringid in old_status_by_stringid:
        set_status(row, user, old_status_by_stringid[stringid])
```

---

## Critical Workflow Timing

### The Danger Zone

```
⚠️  CRITICAL: Export MUST happen BEFORE update!

Timeline:
──────────────────────────────────────────────────────────────
       SAFE ZONE              DANGER ZONE        SAFE ZONE
      (can export)            (data loss!)      (can import)
──────────────────────────────────────────────────────────────
   QA files have work    →  Datasheets updated  →  New structure
   Master has STATUS     →  Old files replaced  →  Work restored
──────────────────────────────────────────────────────────────

If you update datasheets BEFORE exporting:
  - OLD structure gone
  - QA work in OLD files cannot be read
  - Manager STATUS in OLD master lost forever!
```

### Export Checklist (BEFORE Update)

```
Before running ANY datasheet script (fullcharacter1.py, etc.):

□ Collect ALL tester QA files
    - Every {User}_{Category}/ folder
    - Both EN and CN if applicable

□ Collect ALL Master files
    - Master_Quest.xlsx
    - Master_Character.xlsx
    - etc.

□ Run export commands
    python3 sync_qa.py export-testers --source QAfolder
    python3 sync_qa.py export-masters --source Masterfolder

□ Verify snapshots created
    - tester_work.json exists
    - master_work.json exists
    - Check row counts match expectations

□ BACKUP the export files
    - Copy to separate location
    - These are your safety net!

ONLY THEN: Run datasheet update scripts
```

---

## Error Recovery Procedures

### Scenario A: Export Failed Midway

```
Symptom: sync_qa.py crashed during export
Problem: Incomplete snapshot

Recovery:
1. Check partial snapshot - may still have some data
2. Re-run export with --continue flag (if implemented)
3. Or: Re-run full export (safe - doesn't modify source files)

Prevention:
- Export is READ-ONLY operation
- Can always re-run from same source
```

### Scenario B: Forgot to Export Before Update

```
Symptom: Datasheets updated, then realized export wasn't done
Problem: Old files still exist but structure changed

Recovery:
1. DO NOT PANIC
2. Old tester files likely still on testers' machines
3. Collect old files from testers ASAP
4. Run export on collected old files
5. Proceed with import

If old files truly gone:
- Check for backups
- Check email attachments
- Check cloud sync history
- Last resort: Manual re-work
```

### Scenario C: Import Matched Wrong Rows

```
Symptom: STATUS/COMMENT appears on wrong rows
Problem: Matching algorithm failure

Recovery:
1. Import to NEW copies, not originals
2. Keep original synced files untouched
3. Review sync report - which rows were "forced matches"?
4. Manual correction for problematic rows

Prevention:
- Run import on TEST copies first
- Spot-check results before distribution
```

### Scenario D: Some Rows Not Found

```
Symptom: Sync report shows "NOT FOUND" rows
Problem: Row deleted OR matching failed

Analysis:
1. Open old file at original row
2. Check: Is STRINGID present?
3. Check: Does STRINGID exist in new file?
4. If STRINGID exists: Why didn't it match? (format issue?)
5. If STRINGID missing: Manually locate by Korean text

Decision:
- If row DELETED: Note in report, tester doesn't need it
- If row EXISTS but not matched: Manual transfer or fix matching
```

---

## When Tester vs When Manager Runs Tool

### Option A: Manager Runs Everything (Recommended)

```
Manager workflow:
1. Collect all QA files from testers
2. Run export on collected files
3. Update datasheets (run fullXXX.py scripts)
4. Create new blank QA files
5. Run import (transfers work to new files)
6. Distribute synced files back to testers
7. Rebuild master from synced files
8. Apply manager STATUS from old master

Pros:
- Centralized control
- Consistent processing
- Manager can review sync report
- Easy to troubleshoot

Cons:
- Manager does all the work
- Testers wait for files
```

### Option B: Testers Run Import Themselves

```
Manager workflow:
1. Collect all QA files from testers
2. Run export (creates portable snapshot)
3. Update datasheets
4. Create new blank QA files
5. Distribute: snapshot + new blank files to testers

Tester workflow:
1. Receive: their_snapshot.json + new blank file
2. Run: sync_qa.py import --snapshot their_snapshot.json --target new_file
3. Verify their work transferred
4. Continue QA

Pros:
- Testers can verify their own data
- Parallel processing

Cons:
- Need to train testers
- Testers need Python installed
- More support requests
```

### Recommendation: Option A

Manager runs everything. Simpler, fewer failure points, better control.

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

## What-If Scenarios

### What if STRINGID is missing from some rows?

```
Scenario: Old file has rows with empty STRINGID column

Impact: Cannot use primary matching key

Fallback strategy:
  1. Try: Translation text + Korean text
  2. Try: Korean text alone (if unique in sheet)
  3. Log as "unmatched" - requires manual review

Prevention for future:
  - Ensure fullXXX.py scripts ALWAYS populate STRINGID
  - Validate: Check for empty STRINGIDs before distribution
```

### What if translation text changed?

```
Scenario: English translation was updated in new datasheet

Example:
  Old: "Silver Patient" → STATUS: ISSUE
  New: "Silver-Wearing Patient" → no match?

Analysis:
  - If STRINGID same → Should still match!
  - Matching uses Translation + STRINGID
  - Changed translation but same STRINGID = still matches

Edge case:
  - STRINGID changed AND translation changed = no match
  - This means it's essentially a NEW string
  - Old QA work may not apply anymore
  - Log for review
```

### What if same STRINGID appears multiple times?

```
Scenario: Duplicate STRINGID in same sheet

Example (from test):
  Row 4: "은색 비지오네 쓴 환자" | 4295864944164912 | ISSUE (comment A)
  Row 5: "은색 비지오네 쓴 환자" | 4295864944164912 | ISSUE (comment B)

Problem: Which old row maps to which new row?

Strategy:
  1. Group by STRINGID
  2. If same count old and new: Match by position
     - Old row 4 → New row with same STRINGID (position 1)
     - Old row 5 → New row with same STRINGID (position 2)
  3. If different count: Log for manual review

Alternative:
  - Use additional column (COMMAND) to differentiate
  - Row 4: NHW_Citizen_... (female)
  - Row 5: NHM_Citizen_... (male)
```

### What if image file is missing?

```
Scenario: SCREENSHOT column references "bug.png" but file doesn't exist

Impact: Hyperlink will be broken in new file

Handling:
  1. During export: Check if referenced images exist
  2. Log: "Image not found: bug.png (row 45)"
  3. During import: Still transfer the filename reference
  4. Warn: Tester may need to re-take screenshot

Prevention:
  - Validate images exist before sync
  - Provide list of missing images to testers
```

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

## Implementation Considerations

### Dependencies

```python
# Required packages (same as compile_qa.py)
openpyxl     # Excel read/write
json         # Snapshot files
os, shutil   # File operations
datetime     # Timestamps
argparse     # CLI interface
```

### File Structure

```
QAExcelCompiler/
├── compile_qa.py           # Existing compiler (modify for COMMENT-based matching)
├── sync_qa.py              # NEW - Main sync tool
├── sync_utils.py           # NEW - Shared utilities (normalization, matching)
├── docs/
│   └── SYNC_THINKTANK.md   # This planning document
└── tests/
    └── test_sync.py        # NEW - Unit tests for sync logic
```

### Core Functions to Implement

```python
# sync_qa.py - Main commands
def export_testers(source_folder, output_file):
    """Export all tester work to JSON snapshot."""

def export_masters(source_folder, output_file):
    """Export all master work (including manager STATUS) to JSON snapshot."""

def import_testers(snapshot_file, template_folder, output_folder):
    """Import tester work from snapshot into new templates."""

def import_masters(snapshot_file, master_folder):
    """Import manager STATUS from snapshot by COMMENT matching."""

def generate_report(snapshot_file, target_folder):
    """Generate detailed sync report."""

# sync_utils.py - Utilities
def normalize_stringid(value):
    """Convert any STRINGID format to clean string."""

def find_row_by_stringid(ws, stringid, stringid_col):
    """Find row in worksheet by STRINGID."""

def find_row_by_stringid_and_translation(ws, stringid, translation, stringid_col, translation_col):
    """Find row by STRINGID + Translation combo."""

def get_column_index_by_header(ws, header_name):
    """Find column index by header text."""

def inject_work_data(ws, row_idx, status, comment, screenshot, col_map):
    """Write STATUS, COMMENT, SCREENSHOT to row."""
```

### CLI Interface Design

```bash
# Tester file operations
python3 sync_qa.py export-testers \
    --source /path/to/QAfolder \
    --output tester_work.json

python3 sync_qa.py import-testers \
    --snapshot tester_work.json \
    --templates /path/to/new_templates \
    --output /path/to/synced_output

# Master file operations
python3 sync_qa.py export-masters \
    --source /path/to/Masterfolder_EN \
    --output master_work.json

python3 sync_qa.py import-masters \
    --snapshot master_work.json \
    --target /path/to/new_Masterfolder_EN

# Report
python3 sync_qa.py report \
    --snapshot tester_work.json \
    --target /path/to/synced_output \
    --format text|json|excel
```

### Testing Strategy

```
Phase 1: Unit tests (no real files)
────────────────────────────────────────
- test_normalize_stringid()
  - Handles: int, float, scientific, string
- test_find_row_by_stringid()
  - Found, not found, duplicate cases
- test_inject_work_data()
  - Writes to correct columns

Phase 2: Integration tests (mock Excel files)
────────────────────────────────────────
- test_export_single_file()
- test_import_single_file()
- test_round_trip() - export then import, verify data intact

Phase 3: Real data test (before production)
────────────────────────────────────────
- One real tester file
- Manual verification of matched rows
```

### Performance Considerations

```
Scale estimates:
- Testers: ~20-30
- Categories: 6 (Character, Quest, Knowledge, Item, Region, Gimmick)
- Rows per file: ~5,000-50,000
- Total rows: ~600,000 - 6,000,000

Processing time:
- Export: ~1-5 min (read all files, build JSON)
- Import: ~5-15 min (read templates, match rows, write output)

Memory:
- JSON snapshot: ~10-100 MB
- Keep only one workbook open at a time
- Process file by file, not all in memory
```

---

## Summary: The Simple Version

For anyone who skipped to the end:

```
┌─────────────────────────────────────────────────────────────────┐
│                    QA SYNC IN 30 SECONDS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PROBLEM:                                                       │
│    Datasheets will be updated → row indices change              │
│    QA work (STATUS, COMMENT, SCREENSHOT) tied to old rows       │
│    Must transfer work to new structure                          │
│                                                                  │
│  SOLUTION:                                                       │
│    Match rows by: Translation + STRINGID                        │
│    Export work BEFORE update                                    │
│    Import work AFTER update                                     │
│                                                                  │
│  COMMANDS:                                                       │
│    1. sync_qa.py export-testers  (before update)                │
│    2. Update datasheets          (fullXXX.py scripts)           │
│    3. sync_qa.py import-testers  (after update)                 │
│    4. sync_qa.py import-masters  (restore manager STATUS)       │
│                                                                  │
│  KEY RULE:                                                       │
│    EXPORT FIRST! If you update before export, work is LOST.     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Document created for QA Compiler sync planning*
*Updated: 2026-01-08 - Added error recovery, what-if scenarios, implementation details*
