# PLAN: InspectData + PageData Feature for NewItem Generator

> **Status:** IMPLEMENTED
> **Target file:** `generators/newitem.py`
> **Date:** 2026-03-05

---

## 1. PROBLEM STATEMENT

The current NewItem generator extracts only 3 text fields per item:
- `ItemName` (Korean name)
- `ItemDesc` (Korean description)
- KnowledgeInfo linked via `KnowledgeKey`/`RewardKnowledgeKey`

**MISSING:** All `<InspectData>` children are completely ignored. This means:
- Recipe items lose their InspectData `Desc` (crafting instructions, effects)
- Recipe items lose their InspectData `RewardKnowledgeKey` → KnowledgeInfo chain
- Book items lose ALL page content (entire stories, lore, dialogues)
- Book items lose page-level `RewardKnowledgeKey` → KnowledgeInfo links

---

## 2. XML STRUCTURE ANALYSIS

### Pattern A: Simple InspectData (Recipe Items)

```xml
<ItemInfo StrKey="Recipe_Item_Skill_AbyssGear_Immune_Bismuth"
          ItemName="기어 제작법 : 돌의 심장"
          ItemDesc="어비스 기어: 돌의 심장을 제작하기 위한 재료가 적혀 있다...">
  <Price .../>
  <InspectAction UseMacro="Macro_Paper_InspectAction"/>
  <UseItem .../>
  <InspectData SocketName="InspectSocket_0" ActionType="Read"
               Desc="기어 제작법: 돌의 심장<br/>..."
               RewardKnowledgeKey="Knowledge_Recipe_Item_Skill_AbyssGear_Immune_Bismuth"/>
  <PrefabData .../>
</ItemInfo>
```

**Structure:**
- `<InspectData>` is a DIRECT child of `<ItemInfo>`
- Has `Desc` attribute (the inspect text)
- Has `RewardKnowledgeKey` attribute (link to KnowledgeInfo)
- Usually just 1 InspectData per item

**Data to extract:**
1. InspectData.Desc → new row type `InspectData`
2. RewardKnowledgeKey → lookup KnowledgeInfo → Name + Desc → new row type `InspectKnowledgeData`

---

### Pattern B: Book/PageData InspectData (Book Items)

```xml
<ItemInfo StrKey="Ziane_Diary"
          ItemName="지안의 일지"
          ItemDesc="지안의 일지, 그가 생전에 겪었던 일들이 적혀 있다.">
  <InspectAction ActionName="MICROGIMMICK_LOOKAT_BOOK_START" .../>
  <UseItem .../>
  <PageData>
    <LeftPage TexturePath="...">
      <InspectData SocketName="InspectSocket_1" ActionType="Read"
                   Desc="데메니스 쪽에서 온 보고가 심상치 않다..."
                   SpeakerCharacterKey="NHM_Unique_Ziane_TwoHandSword_411"
                   DialogStrKey="textdialog_ziane_diary_00159"/>
    </LeftPage>
    <RightPage TexturePath="...">
      <InspectData SocketName="InspectSocket_0" UseLeftPageInspectData="True"/>
    </RightPage>
  </PageData>
  <PageData>
    <LeftPage ...>
      <InspectData ... Desc="검은곰..." DialogStrKey="textdialog_ziane_diary_00160"/>
    </LeftPage>
    <RightPage ...>
      <InspectData ... UseLeftPageInspectData="True"/>
    </RightPage>
  </PageData>
  <!-- ... more PageData ... -->
  <PageData>
    <LeftPage ...>
      <InspectData ... Desc="나에게 무슨 일이 생긴다면..."
                   RewardKnowledgeKey="Knowledge_PailuneLeader"
                   DialogStrKey="textdialog_ziane_diary_00148"/>
    </LeftPage>
    <RightPage ...>
      <InspectData ... UseLeftPageInspectData="True"/>
    </RightPage>
  </PageData>
</ItemInfo>
```

**Structure:**
- `<ItemInfo>` → `<PageData>` (multiple) → `<LeftPage>`/`<RightPage>` → `<InspectData>`
- Each PageData is a "spread" (left + right page)
- `UseLeftPageInspectData="True"` = SKIP (duplicate reference, no unique text)
- `RewardKnowledgeKey` is OPTIONAL per page (most pages don't have it)
- Additional attributes: `SpeakerCharacterKey`, `SpeakerDesc`, `DialogStrKey`
- Pages must be output in SEQUENTIAL ORDER (top to bottom in XML = page 1, 2, 3...)

**Data to extract per page:**
1. InspectData.Desc → row type `InspectData`
2. If RewardKnowledgeKey exists → lookup KnowledgeInfo → Name + Desc → `InspectKnowledgeData`

**SKIP rules:**
- Skip `<InspectData>` with `UseLeftPageInspectData="True"` (no unique content)
- Skip `<InspectData>` with empty or missing `Desc`

---

## 3. UNIFIED PARSING STRATEGY

Both patterns can be handled with ONE recursive scan:

```
For each <ItemInfo>:
  1. Collect direct <InspectData> children (Pattern A)
  2. Collect <PageData> → <LeftPage>/<RightPage> → <InspectData> (Pattern B)
  3. For each collected InspectData:
     - Skip if UseLeftPageInspectData="True"
     - Skip if Desc is empty
     - Store: (desc, reward_knowledge_key, page_index)
     - If reward_knowledge_key → lookup in knowledge_map → store linked knowledge
```

The order is guaranteed by XML document order (lxml preserves element order).

---

## 4. DATA STRUCTURE CHANGES

### Current `NewItemEntry` dataclass:
```python
@dataclass
class NewItemEntry:
    item_strkey: str
    item_name_kor: str
    item_desc_kor: str
    knowledge_key: str
    knowledge_name_kor: str
    knowledge_desc_kor: str
    group_key: str
    source_file: str
    knowledge_source_file: str
    knowledge2_name_kor: str = ""
    knowledge2_desc_kor: str = ""
    knowledge2_source_file: str = ""
    child_knowledge_entries: List[Tuple[str, str, str]] = field(default_factory=list)
```

### New field to add:
```python
    # InspectData entries: list of (desc, knowledge_name, knowledge_desc, knowledge_source_file)
    inspect_entries: List[Tuple[str, str, str, str]] = field(default_factory=list)
```

Each tuple represents one InspectData element:
- `desc` — the InspectData.Desc text (Korean)
- `knowledge_name` — KnowledgeInfo.Name if RewardKnowledgeKey found, else ""
- `knowledge_desc` — KnowledgeInfo.Desc if RewardKnowledgeKey found, else ""
- `knowledge_source_file` — source file of the KnowledgeInfo, else ""

This handles BOTH patterns uniformly:
- Pattern A (recipe): 1 entry in the list
- Pattern B (book): N entries in the list (one per page with actual content)

---

## 5. NEW ROW TYPES IN EXCEL OUTPUT

### Current row sequence per item:
```
Row 1:  ItemData              — item_name_kor
Row 2:  ItemData              — item_desc_kor
Row 3+: ChildKnowledgeData    — inline <Knowledge> children (Pass 0)
Row N:  KnowledgeData         — knowledge_name_kor (Pass 1)
Row N+1: KnowledgeData        — knowledge_desc_kor (Pass 1)
Row N+2: KnowledgeData2       — knowledge2_name_kor (Pass 2)
Row N+3: KnowledgeData2       — knowledge2_desc_kor (Pass 2)
```

### NEW row sequence per item:
```
Row 1:   ItemData              — item_name_kor
Row 2:   ItemData              — item_desc_kor
--- InspectData block (NEW) ---
Row 3:   InspectData           — inspect_entries[0].desc
Row 4:   InspectKnowledgeData  — inspect_entries[0].knowledge_name  (if exists)
Row 5:   InspectKnowledgeData  — inspect_entries[0].knowledge_desc  (if exists)
Row 6:   InspectData           — inspect_entries[1].desc            (page 2, if book)
Row 7:   InspectData           — inspect_entries[2].desc            (page 3, if book)
...      (continues for all pages)
Row N:   InspectData           — inspect_entries[last].desc
Row N+1: InspectKnowledgeData  — inspect_entries[last].knowledge_name (if exists)
Row N+2: InspectKnowledgeData  — inspect_entries[last].knowledge_desc (if exists)
--- Existing knowledge block (unchanged) ---
Row M:   ChildKnowledgeData    — inline children (Pass 0)
Row M+1: KnowledgeData         — knowledge_name_kor (Pass 1)
Row M+2: KnowledgeData         — knowledge_desc_kor (Pass 1)
Row M+3: KnowledgeData2        — knowledge2_name_kor (Pass 2)
Row M+4: KnowledgeData2        — knowledge2_desc_kor (Pass 2)
```

**Key design decisions:**
- InspectData comes AFTER ItemData but BEFORE existing knowledge blocks
- Each InspectData entry outputs its Desc first, then its linked knowledge (if any)
- For books: pages are sequential, each page's knowledge (if any) follows immediately
- Empty knowledge = skip those rows (adaptive, robust)

---

## 6. STRINGID RESOLUTION

InspectData Desc and InspectKnowledgeData Name/Desc need translations too.

**How it works:**
- The current system uses `eng_tbl` (English) and `lang_tbl` (target language) lookup tables
- These are keyed by Korean text → returns (translation, stringid)
- InspectData Desc text is Korean → look up in same tables
- KnowledgeInfo Name/Desc is Korean → already handled by existing knowledge resolution pattern

**Pre-resolution pass:** The existing pre-resolution loop (lines 698-723) iterates items in document order to consume StringIDs correctly. We must add InspectData entries to this loop in the correct position (after ItemData, before existing knowledge).

---

## 7. IMPLEMENTATION STEPS

### Step 1: Update `NewItemEntry` dataclass
- Add `inspect_entries: List[Tuple[str, str, str, str]]` field

### Step 2: Create `_collect_inspect_data()` helper function
```python
def _collect_inspect_data(item_element, knowledge_map: dict) -> List[Tuple[str, str, str, str]]:
    """
    Collect all InspectData from an ItemInfo element.
    Handles both Pattern A (direct children) and Pattern B (PageData→Page→InspectData).
    Returns list of (desc, knowledge_name, knowledge_desc, knowledge_source_file).
    """
```

Logic:
1. Find direct `<InspectData>` children of `<ItemInfo>`
2. Find `<PageData>` → iterate `<LeftPage>`, `<RightPage>` → find `<InspectData>`
3. For each InspectData:
   - Skip if `UseLeftPageInspectData="True"`
   - Skip if `Desc` is empty/missing
   - Get `RewardKnowledgeKey` → lookup in `knowledge_map`
   - Append tuple to results
4. Return list in document order

### Step 3: Update `scan_items_with_knowledge()` (lines 296-407)
- After extracting ItemName/ItemDesc, call `_collect_inspect_data(item, knowledge_map)`
- Store result in `NewItemEntry.inspect_entries`

### Step 4: Update Korean string collection
- Add InspectData Desc strings to the Korean coverage tracking set
- Add linked KnowledgeInfo Name/Desc strings

### Step 5: Update pre-resolution pass in `write_newitem_excel()`
- After pre-resolving ItemName and ItemDesc
- Iterate `entry.inspect_entries`:
  - Pre-resolve desc via `eng_tbl` and `lang_tbl`
  - Pre-resolve knowledge_name and knowledge_desc if non-empty

### Step 6: Update Excel write loop in `write_newitem_excel()`
- After writing ItemData rows (name + desc)
- Before writing ChildKnowledgeData rows
- For each inspect entry:
  - Write `InspectData` row with desc
  - If knowledge_name non-empty: write `InspectKnowledgeData` row with name
  - If knowledge_desc non-empty: write `InspectKnowledgeData` row with desc

### Step 7: Update `write_text_files()` if needed
- Text command files use `/create item {StrKey}` — these don't need changes
- The InspectData is part of the item, not a separate entity

---

## 8. EDGE CASES & ROBUSTNESS

| Case | Handling |
|------|----------|
| No InspectData on item | `inspect_entries` = empty list → no rows output |
| InspectData with no Desc | Skip (don't add to list) |
| InspectData with `UseLeftPageInspectData="True"` | Skip (duplicate reference) |
| InspectData with Desc but no RewardKnowledgeKey | Output Desc row only, no knowledge rows |
| InspectData with RewardKnowledgeKey but key not in knowledge_map | Output Desc row only, skip knowledge |
| Book with 11 pages, only last has RewardKnowledgeKey | 10 pages output Desc only, last page outputs Desc + knowledge |
| Item has BOTH direct InspectData AND PageData InspectData | Collect both, direct first then pages (document order) |
| Translation not found for InspectData Desc | Empty translation cell (same as existing behavior) |
| InspectData Desc contains `<br/>` tags | Preserved as-is (existing `<br/>` handling in QACompiler) |

---

## 9. WHAT THIS DOES NOT CHANGE

- ItemGroupInfo hierarchy parsing — unchanged
- Clustering logic — unchanged
- Monster extraction — unchanged
- Text command file generation — unchanged (InspectData is part of item)
- Existing Pass 0/1/2 knowledge resolution — unchanged, runs AFTER InspectData block
- Column count — unchanged (still 8 columns)
- Color alternation logic — unchanged (per item_strkey)

---

## 10. EXAMPLE OUTPUT: Recipe Item

```
DataType              | Filename    | SourceText (KR)                              | Translation | ...
ItemData              | ETC_1.txt   | 기어 제작법 : 돌의 심장                        | ...         |
ItemData              | ETC_1.txt   | 어비스 기어: 돌의 심장을 제작하기 위한...         | ...         |
InspectData           | ETC_1.txt   | 기어 제작법: 돌의 심장<br/><br/>필요 재료: ...   | ...         |
InspectKnowledgeData  | know_1.txt  | 돌의 심장                                      | ...         |
InspectKnowledgeData  | know_1.txt  | [제작 방법]<br/>제작 장소: 각 지역의 마녀를...    | ...         |
KnowledgeData         | know_1.txt  | (Pass 1 if different key)                     | ...         |
```

## 11. EXAMPLE OUTPUT: Book Item (Ziane's Diary)

```
DataType              | Filename    | SourceText (KR)                                    | Translation | ...
ItemData              | Quest_1.txt | 지안의 일지                                          | ...         |
ItemData              | Quest_1.txt | 지안의 일지, 그가 생전에 겪었던 일들이 적혀 있다.       | ...         |
InspectData           | Quest_1.txt | 데메니스 쪽에서 온 보고가 심상치 않다...               | ...         |
InspectData           | Quest_1.txt | 검은곰.<br/><br/>페일룬을 하나로 결속시키려면...       | ...         |
InspectData           | Quest_1.txt | 불확실한 시간 속에서도, 파울루스와 함께라면...          | ...         |
InspectData           | Quest_1.txt | 파울루스의 강력한 추천에, 톨스테인을...                | ...         |
InspectData           | Quest_1.txt | 칼페이드.<br/><br/>타협 없는 방패라는 별명처럼...      | ...         |
InspectData           | Quest_1.txt | 칼페이드만이 아닌, 에르난드 전체를...                  | ...         |
InspectData           | Quest_1.txt | 회색갈기.<br/><br/>나와 같은 이상을 지지하는...        | ...         |
InspectData           | Quest_1.txt | 페일룬과 멀리 떨어진 델레시아는...                     | ...         |
InspectData           | Quest_1.txt | 승냥이들이 많이 자랐다...                             | ...         |
InspectData           | Quest_1.txt | 나에게 무슨 일이 생긴다면...                          | ...         |
InspectKnowledgeData  | know_2.txt  | (Knowledge_PailuneLeader Name)                      | ...         |
InspectKnowledgeData  | know_2.txt  | (Knowledge_PailuneLeader Desc)                      | ...         |
InspectData           | Quest_1.txt | 페일룬.<br/><br/>춥고 척박한 땅...                    | ...         |
```

Note: Page 10 has `RewardKnowledgeKey="Knowledge_PailuneLeader"` so its InspectKnowledgeData rows appear right after that page's InspectData row. All other pages only have InspectData rows.

---

## 12. RISK ASSESSMENT

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking existing knowledge resolution | HIGH | InspectData block is SEPARATE, inserted BEFORE existing passes |
| StringID consumption order disruption | HIGH | Pre-resolution loop must match exact write order |
| Performance with book items (many pages) | LOW | Still just string lookups, no heavy computation |
| Items with no InspectData | NONE | Empty list = no extra rows, zero impact |

---

## 13. FILES TO MODIFY

| File | Changes |
|------|---------|
| `generators/newitem.py` | Dataclass, parser, pre-resolution, Excel writer |

That's it. ONE file. The change is self-contained within the NewItem generator.

---

*Plan document for PRXR protocol. Ready for executive order.*
