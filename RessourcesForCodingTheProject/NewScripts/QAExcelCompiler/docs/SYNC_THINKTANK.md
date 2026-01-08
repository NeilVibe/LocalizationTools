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

## Next Steps

1. [ ] Confirm STRINGID is present and unique in ALL sheet types
2. [ ] Build `sync_qa.py` with export command
3. [ ] Test export on real QA files
4. [ ] Build import command
5. [ ] Test full export→update→import cycle
6. [ ] Add master file sync support
7. [ ] Add image handling

---

*Document created for QA Compiler sync planning*
