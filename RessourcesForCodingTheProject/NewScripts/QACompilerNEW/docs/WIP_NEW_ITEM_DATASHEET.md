# WIP: NEW Item Datasheet + ItemKnowledgeCluster

> Two outputs: (1) Updated NewItem LQA datasheet, (2) NEW ItemKnowledgeCluster mega-datasheet.

---

## CRITICAL BUG FIX: KnowledgeKey Is in CHILDREN

**Found during testing (2026-02-24):** KnowledgeKey is NOT a direct attribute on ItemInfo. It's in **child elements** of the ItemInfo node.

```xml
<!-- WRONG assumption (current code) -->
<ItemInfo StrKey="item_001" ItemName="검" ItemDesc="설명" KnowledgeKey="Knowledge_001">

<!-- ACTUAL structure — KnowledgeKey is in a CHILD element -->
<ItemInfo StrKey="item_001" ItemName="검" ItemDesc="설명">
    <SomeChild KnowledgeKey="Knowledge_001" />
    <!-- could be any child element, need to search ALL children -->
</ItemInfo>
```

**Current code (line 304):** `knowledge_key = item.get("KnowledgeKey") or ""` — only checks ItemInfo attributes.
**Fix needed:** Search ALL child elements of ItemInfo for a `KnowledgeKey` attribute.

---

## Deliverable 1: Updated NewItem Datasheet (existing)

### What changes

The existing NewItem datasheet gets two updates:

#### A. Fix KnowledgeKey child-node scanning

Search all children of ItemInfo for `KnowledgeKey` attribute instead of just the ItemInfo element itself.

#### B. Add Pass 2: Identical Name Match (rows 5-6)

After the existing 4-step pass, add a new pass:

| Step | Row Type | Source | What We Extract |
|------|----------|--------|----------------|
| **1** | ItemData | `ItemInfo.ItemName` | Item name (Korean) |
| **2** | ItemData | `ItemInfo.ItemDesc` | Item description (Korean) |
| **3** | KnowledgeData | `KnowledgeInfo.Name` (via KnowledgeKey from children) | Knowledge name (Korean) |
| **4** | KnowledgeData | `KnowledgeInfo.Desc` (via KnowledgeKey from children) | Knowledge desc (Korean) |
| **5** | KnowledgeData2 | `KnowledgeInfo.Name` (identical name match) | Matching knowledge name (Korean) |
| **6** | KnowledgeData2 | `KnowledgeInfo.Desc` (identical name match) | Matching knowledge desc (Korean) |

**Pass 2 logic:**
- Take `ItemInfo.ItemName` (Korean)
- Search ALL KnowledgeInfo entries for one whose `Name` attribute is **identical** to the ItemName
- If found AND it's NOT the same entry already used in Pass 1 (KnowledgeKey), output as KnowledgeData2
- Output Name (row 5) and Desc (row 6), skip empty as usual

### Updated Row Blocks Per Item

- **Block of 2**: No knowledge at all → steps 1-2 only
- **Block of 3-4**: KnowledgeKey found → steps 1-2 + knowledge rows 3/4
- **Block of 5-6**: Identical name match found → + KnowledgeData2 rows 5/6
- **Block of 4-6**: Could have only Pass 2 match (no KnowledgeKey but identical name exists)

### Updated Data Structure

```python
@dataclass
class NewItemEntry:
    item_strkey: str
    item_name_kor: str
    item_desc_kor: str
    knowledge_key: str              # From children scan
    knowledge_name_kor: str         # Pass 1: via KnowledgeKey
    knowledge_desc_kor: str         # Pass 1: via KnowledgeKey
    knowledge2_name_kor: str        # Pass 2: identical name match
    knowledge2_desc_kor: str        # Pass 2: identical name match
    group_key: str
    source_file: str
    knowledge_source_file: str      # Pass 1 knowledge source
    knowledge2_source_file: str     # Pass 2 knowledge source
```

---

## Deliverable 2: ItemKnowledgeCluster (NEW mega-datasheet)

### Goal

Cluster ALL item-related data from the entire StaticInfo folder into a single mega-sheet. Maximum data extraction — every possible connection between items and knowledge.

### Simplified Columns (no Filename)

| Col | Header | Description |
|-----|--------|-------------|
| A | **DataType** | Identifies the match type and source |
| B | **SourceText (KR)** | Korean source text |
| C | **Translation ({CODE})** | Target language translation |
| D | **STATUS** | Dropdown |
| E | **COMMENT** | Tester notes |
| F | **SCREENSHOT** | Screenshot ref |
| G | **STRINGID** | EXPORT-resolved StringID |

### Multi-Pass Data Collection

#### Pass 1: Direct KnowledgeKey (from children)
- Same as NewItem: scan ItemInfo children for KnowledgeKey → resolve in KnowledgeInfo
- DataType: `"ItemData"` for item name/desc, `"KnowledgeData"` for knowledge name/desc

#### Pass 2: Exact Name Match
- For each ItemInfo.ItemName, find KnowledgeInfo entries with identical `Name`
- Also search entire StaticInfo (not just knowledgeinfo folder)
- DataType: `"KnowledgeMatch-Exact"`

#### Pass 3: Fuzzy Match (difflib, threshold >= 80%)
- For each ItemInfo.ItemName, run `difflib.SequenceMatcher` against all names in StaticInfo
- Both iteminfo AND knowledgeinfo matches
- Threshold: 80% similarity (configurable)
- DataType: `"KnowledgeMatch-Fuzzy"` or `"ItemMatch-Fuzzy"` (depending on source)

### Single Mega-Sheet Output

**NO per-folder sheets.** Everything goes into ONE sheet per language.

### Clustering & Ordering Strategy

Each item is a "cluster anchor" (starting point). Around each anchor, stack:
1. The item's own data (ItemData)
2. KnowledgeKey matches (KnowledgeData)
3. Exact name matches (KnowledgeMatch-Exact)
4. Fuzzy matches (sorted by similarity score, highest first)

**Inter-cluster ordering:** Order clusters by similarity to each other:
- Compare anchor ItemNames pairwise using difflib
- Sort so similar items are adjacent (gradient from most-similar-groups down)
- This creates a natural flow where related items appear near each other

### Output Structure

```
GeneratedDatasheets/
├── NewItemData_Map_All/          ← Deliverable 1 (existing, updated)
│   ├── ExecuteFiles/
│   └── NewItem_LQA_*.xlsx
└── ItemKnowledgeCluster/         ← Deliverable 2 (NEW)
    ├── ItemKnowledgeCluster_LQA_ENG.xlsx
    ├── ItemKnowledgeCluster_LQA_ZHO-CN.xlsx
    └── ...
```

---

## Decisions Log

| # | Decision | Answer | Date |
|---|----------|--------|------|
| 1 | Skip empty knowledge rows? | YES | 2026-02-24 |
| 2 | Row ordering per item block? | Strict: Name → Desc → Knowledge → Knowledge2 → Fuzzy | 2026-02-24 |
| 3 | Output folder? | Separate folders for each deliverable | 2026-02-24 |
| 4 | KnowledgeKey location? | CHILDREN of ItemInfo, not direct attribute | 2026-02-24 |
| 5 | Identical name match scope? | knowledgeinfo folder (Deliverable 1), full StaticInfo (Deliverable 2) | 2026-02-24 |
| 6 | Fuzzy match threshold? | 80% (difflib.SequenceMatcher) | 2026-02-24 |
| 7 | Fuzzy match scope? | Both iteminfo AND knowledgeinfo in StaticInfo | 2026-02-24 |
| 8 | ItemKnowledgeCluster sheet structure? | Single mega-sheet (no folder splitting) | 2026-02-24 |
| 9 | Inter-cluster ordering? | Similarity-based (pairwise difflib on anchor names) | 2026-02-24 |

---

## Status

- [x] Codebase exploration
- [x] Initial implementation (4-step pass)
- [x] Pipeline integration (populate, coverage, CLI)
- [x] First real-world test → found KnowledgeKey children bug
- [x] **Fix KnowledgeKey child-node scanning** (`_find_knowledge_key()` helper)
- [x] **Add Pass 2 identical name match (KnowledgeData2)** (name index in `load_knowledge_data()`)
- [x] **Create ItemKnowledgeCluster generator** (`generators/itemknowledgecluster.py`)
- [x] **Register in pipeline** (config, dispatch, CLI, populate, coverage)
- [ ] Testing
- [ ] Build & deploy

---

*Last updated: 2026-02-24*
