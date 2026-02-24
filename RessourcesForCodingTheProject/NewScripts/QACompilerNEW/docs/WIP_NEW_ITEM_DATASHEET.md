# WIP: NEW Item Datasheet

> Rebuild of the current Item datasheet with a row-per-text structure and 4-step pass.

---

## Overview

The NEW Item Datasheet replaces the current item datasheet's approach where ItemName and ItemDesc share the same row. Instead, each text entry gets its **own row**, and we extract data from **two sources** per item:

1. **ItemData** (from ItemInfo node directly)
2. **KnowledgeData** (from KnowledgeInfo node linked via KnowledgeKey attribute)

---

## The 4-Step Pass

For each ItemInfo element found in the resource folder:

| Step | Row Type | Source | What We Extract |
|------|----------|--------|----------------|
| **1** | ItemData | `ItemInfo.ItemName` | The item's display name (Korean) |
| **2** | ItemData | `ItemInfo.ItemDesc` | The item's description text (Korean) |
| **3** | KnowledgeData | `KnowledgeInfo.Name` (via KnowledgeKey) | The knowledge entry's name (Korean) |
| **4** | KnowledgeData | `KnowledgeInfo.Desc` (via KnowledgeKey) | The knowledge entry's description (Korean) |

### Row Blocks Per Item

Each item produces a **variable-size block** depending on available data:

- **Block of 2**: No KnowledgeKey, or knowledge Name+Desc both empty → steps 1-2 only
- **Block of 3**: KnowledgeKey exists but only one of Name/Desc is non-empty → steps 1-2 + one knowledge row
- **Block of 4**: KnowledgeKey exists with both Name and Desc non-empty → all 4 steps

**Rule: Skip empty rows.** If a knowledge text (Name or Desc) is empty, that row is not output.

---

## How KnowledgeKey Linking Works

```
ItemInfo XML element:
  ├── StrKey="item_sword_001"
  ├── ItemName="용사의 검"              ← Step 1 source
  ├── ItemDesc="전설의 용사가 사용한 검"  ← Step 2 source
  └── KnowledgeKey="Knowledge_Sword_001" ← Link attribute

KnowledgeInfo XML element (in knowledge folder):
  ├── StrKey="Knowledge_Sword_001"       ← Matches KnowledgeKey above
  ├── Name="용사의 검 정보"              ← Step 3 source
  └── Desc="이 검은 고대 전설의..."       ← Step 4 source
```

**Current code** (`item.py:390-415`) only loads `StrKey → Desc` mapping.
**New code** needs `StrKey → (Name, Desc, source_file)` mapping to support all 4 steps.

---

## Output Structure

**Exactly 2 folders:**

```
NewItemData_Map_All/
├── ExecuteFiles/                ← text files with /create item commands
│   ├── FolderName1/
│   │   ├── SubgroupName1.txt
│   │   └── SubgroupName2.txt
│   ├── FolderName2/
│   │   └── SubgroupName.txt
│   └── Others/
│       └── Others_1.txt
├── NewItem_LQA_ENG.xlsx         ← one Excel per language
├── NewItem_LQA_ZHO-CN.xlsx
├── NewItem_LQA_FRE.xlsx
└── ...
```

---

## Excel Structure (Minimal/Light)

**One Excel file per language.** No Full/Sorted split — just ONE file.

### Columns (left to right):

| Col | Header | Description |
|-----|--------|-------------|
| A | **DataType** | `"ItemData"` or `"KnowledgeData"` — differentiates the source |
| B | **Filename** | The text file name (from ExecuteFiles) for in-game LQA |
| C | **SourceText (KR)** | Korean source text (ItemName, ItemDesc, KnowledgeName, or KnowledgeDesc) |
| D | **Translation** | Target language translation |
| E | **STATUS** | Dropdown: ISSUE / NO ISSUE / BLOCKED / KOREAN |
| F | **COMMENT** | Tester notes |
| G | **SCREENSHOT** | Screenshot reference |
| H | **STRINGID** | StringID resolved via EXPORT index (same technique as other datasheets) |

### Row Layout Example (for one item WITH KnowledgeKey):

| DataType | Filename | SourceText (KR) | Translation | STATUS | COMMENT | SCREENSHOT | STRINGID |
|----------|----------|-----------------|-------------|--------|---------|------------|----------|
| ItemData | Weapon/Sword.txt | 용사의 검 | Hero's Sword | | | | 10001 |
| ItemData | Weapon/Sword.txt | 전설의 용사가 사용한 검 | A sword used by... | | | | 10002 |
| KnowledgeData | Weapon/Sword.txt | 용사의 검 정보 | Hero's Sword Info | | | | 20001 |
| KnowledgeData | Weapon/Sword.txt | 이 검은 고대 전설의... | This sword is from... | | | | 20002 |

### Row Layout Example (for one item WITHOUT KnowledgeKey):

| DataType | Filename | SourceText (KR) | Translation | STATUS | COMMENT | SCREENSHOT | STRINGID |
|----------|----------|-----------------|-------------|--------|---------|------------|----------|
| ItemData | Consumable/Potion.txt | 회복 물약 | Recovery Potion | | | | 10050 |
| ItemData | Consumable/Potion.txt | HP를 50 회복 | Restores 50 HP | | | | 10051 |

---

## StringID Resolution

Same battle-tested technique as all other generators (via `base.py`):

1. Track `source_file` (the XML filename containing the ItemInfo)
2. Normalize to EXPORT key: `source_file.lower().replace(".xml", "").replace(".loc", "")`
3. Look up StringIDs in EXPORT index for that file
4. Match Korean text in language table → find candidate whose StringID is in the EXPORT set
5. Return correct (translation, stringid) pair

**For ItemData rows:** source_file = the item XML file (e.g. `iteminfo_weapon.staticinfo.xml`)
**For KnowledgeData rows:** source_file = the knowledge XML file (e.g. `knowledgeinfo_combat.staticinfo.xml`)

Different source files → different EXPORT keys → correct StringID for each row type.

---

## Text Files (Debug Commands)

Same approach as current item.py:
- Output to `NewItemData_Map_All/ExecuteFiles/`
- `/create item {ItemKey}` commands per text file
- Grouped by folder/subgroup
- Max 300 commands per file (split into multiple files if needed)
- Prefixed with `/reset inventory` and `/expandinventory 2 300`

---

## Modular Architecture (CRITICAL — No Reinventing)

### Reuse from `generators/base.py` (battle-tested, zero changes):

| Function | Purpose |
|----------|---------|
| `parse_xml_file()` | XML parsing with sanitization, entity fixing, recovery |
| `iter_xml_files()` | Recursive XML file iteration |
| `load_language_tables()` | All language table loading with duplicate resolution |
| `resolve_translation()` | EXPORT-aware StringID resolution |
| `get_export_index()` | EXPORT index building (cached) |
| `get_first_translation()` | Fallback translation lookup |
| `normalize_placeholders()` | Placeholder stripping |
| `is_good_translation()` | Translation quality check |
| `autofit_worksheet()` | Column auto-sizing |
| `THIN_BORDER` | Border styling constant |

### Reuse patterns from `generators/item.py` (logic, not the file):

| Pattern | Purpose |
|---------|---------|
| `parse_master_groups()` | ItemGroupInfo hierarchy for text file organization |
| Depth-based clustering | Folder organization for ExecuteFiles |
| Monster item extraction | Separate folder for monster items |
| Text file generation | `/create item` command files |
| Korean collection | Coverage tracking |

### New code (only what's actually different):

| Function | Purpose |
|----------|---------|
| `load_knowledge_data(folder)` | Extended: `StrKey → (Name, Desc, source_file)` |
| `scan_items_with_knowledge(folder, knowledge_map)` | Captures all 4 text sources per item |
| `write_newitem_excel(items, ...)` | New minimal 8-column row-per-text writer |
| `generate_newitem_datasheets()` | Main entry point |

---

## Implementation Plan

### Step 1: Create `generators/newitem.py`

**Data structure:**
```python
@dataclass
class NewItemEntry:
    item_strkey: str           # ItemInfo StrKey
    item_name_kor: str         # ItemInfo.ItemName (Korean)
    item_desc_kor: str         # ItemInfo.ItemDesc (Korean)
    knowledge_key: str         # ItemInfo.KnowledgeKey (may be empty)
    knowledge_name_kor: str    # KnowledgeInfo.Name (Korean, empty if no key)
    knowledge_desc_kor: str    # KnowledgeInfo.Desc (Korean, empty if no key)
    group_key: str             # Parent ItemGroupInfo StrKey
    source_file: str           # Item XML filename (for EXPORT matching)
    knowledge_source_file: str # Knowledge XML filename (for EXPORT matching)
```

**Functions:**
1. `load_knowledge_data(folder)` → `Dict[str, Tuple[str, str, str]]` mapping `StrKey → (Name, Desc, source_file)`
2. `scan_items_with_knowledge(folder, knowledge_map)` → `List[NewItemEntry]`
3. `build_text_files(items, output_folder)` → text file map for Filename column
4. `write_newitem_excel(items, lang_tables, lang_code, text_file_map, output_path)` → Excel
5. `generate_newitem_datasheets()` → main entry point

### Step 2: Register in `generators/__init__.py`

Add lazy import for `newitem` module, map `"NewItem"` → `generate_newitem_datasheets`.

### Step 3: Add to `config.py`

Add `"NewItem"` to `CATEGORIES` list. No `CATEGORY_TO_MASTER` entry (no master file integration yet).

### Step 4: GUI auto-detects

GUI reads `CATEGORIES` dynamically → new checkbox appears automatically.

### Step 5: Test

- Verify 2/3/4 row blocks based on available data
- Verify StringID resolution for both ItemData and KnowledgeData rows
- Verify text files generated correctly
- Verify per-language Excel output
- Verify GUI checkbox works

---

## Decisions Log

| # | Decision | Answer | Date |
|---|----------|--------|------|
| 1 | Skip empty knowledge rows? | YES — skip if Name/Desc is empty | 2026-02-24 |
| 2 | Row ordering per item block? | Strict: ItemName → ItemDesc → KnowledgeName → KnowledgeDesc | 2026-02-24 |
| 3 | Output folder? | Separate: `NewItemData_Map_All/` (not shared with old) | 2026-02-24 |
| 4 | Text file approach? | Same as current item.py, in own ExecuteFiles subfolder | 2026-02-24 |
| 5 | Coverage tracking? | Together — KnowledgeData + ItemData in same Korean set | 2026-02-24 |
| 6 | Empty ItemDesc row? | YES — still output (tester sees it's empty) | 2026-02-24 |
| 7 | File structure? | New file `generators/newitem.py`, old `item.py` untouched | 2026-02-24 |

---

## Status

- [x] Codebase exploration (6 agents)
- [x] Plan written
- [x] All decisions finalized
- [ ] Plan approved → enter Plan Mode
- [ ] Implementation
- [ ] Testing
- [ ] GUI integration verified
- [ ] Production validation

---

*Last updated: 2026-02-24*
