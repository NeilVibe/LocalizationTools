# Mock Data Research: Approach A — Mirror Real Structure

**Researched:** 2026-03-21
**Domain:** MegaIndex mock data for testing all 35 dicts + 12 parse sources
**Confidence:** HIGH (all findings from direct source code analysis of mega_index.py, perforce_path_service.py, linkage.py, and existing fixtures)

---

## Executive Summary

MegaIndex.build() resolves paths via PerforcePathService, then parses 12 source types (P1-P12) into 35 dicts. The mock data must mirror the real Perforce folder structure exactly so the same parsers work unchanged. The existing `tests/fixtures/mock_gamedata/` already has 80% of the needed XML data (StaticInfo, textures) but is missing 5 critical directories that MegaIndex needs: `stringtable/loc/`, `stringtable/export__/`, `sound/windows/`, `gimmickinfo/`, and the proper `texture/image/` path (current PNGs are at `textures/` with wrong extension).

**Primary recommendation:** Restructure mock data into `tests/fixtures/perforce_mock/` that mirrors the real Perforce layout, reusing existing XML content and adding the 5 missing data types with minimal but complete entries.

---

## 1. Exact Folder Structure MegaIndex Expects

MegaIndex resolves paths via `PerforcePathService.PATH_TEMPLATES`. The real structure is:

```
F:\perforce\cd\{branch}\resource\GameData\
  StaticInfo\
    knowledgeinfo\          ← P1: *.xml (KnowledgeInfo, KnowledgeGroupInfo)
    characterinfo\          ← P2: characterinfo_*.staticinfo.xml (CharacterInfo)
    iteminfo\               ← P3: *.staticinfo.xml (ItemGroupInfo, ItemInfo, InspectData)
    factioninfo\            ← P4: *.xml (FactionGroup, Faction, FactionNode, RegionInfo)
      NodeWaypointInfo\     ← (waypoints, optional)
    skillinfo_*.xml         ← P5: (SkillInfo) — SIBLING files, not subfolder!
    gimmickinfo_*.xml       ← P6: (GimmickGroupInfo, GimmickInfo, SealData) — SIBLING files
    **/*.xml                ← P12: Broad scan for StrKey + DevMemo/DevComment
  stringtable\
    loc\                    ← P7: languagedata_{code}.xml (LocStr: StringId, StrOrigin, Str)
    export__\               ← P8: *.xml (SoundEventName/EventName + StringId)
                            ← P8: *.loc.xml (LocStr for ordered export index)

F:\perforce\common\{branch}\commonresource\ui\
  texture\image\            ← P10: **/*.dds (filename stem = texture name)

F:\perforce\cd\{branch}\resource\
  sound\windows\English(US)\← P9: **/*.wem (filename stem = event name)
  editordata\VoiceRecordingSheet__\ ← P11: *.xlsx (EventName column ordering)
```

### Mock Structure for Tests

The mock root maps to `tests/fixtures/perforce_mock/`:

```
tests/fixtures/perforce_mock/
  cd/mainline/resource/GameData/
    StaticInfo/
      knowledgeinfo/
        knowledgeinfo_showcase.staticinfo.xml     ← EXISTING (copy)
      characterinfo/
        characterinfo_showcase.staticinfo.xml     ← EXISTING (copy)
      iteminfo/
        iteminfo_showcase.staticinfo.xml          ← EXISTING (copy, needs ItemGroupInfo wrapper)
      factioninfo/
        FactionInfo.staticinfo.xml                ← EXISTING (copy)
        NodeWaypointInfo/
          NodeWaypointInfo.staticinfo.xml          ← EXISTING (copy)
      skillinfo_showcase.staticinfo.xml           ← **MOVE** from skillinfo/ subfolder
      gimmickinfo_showcase.staticinfo.xml         ← **NEW** (P6)
      questinfo_showcase.staticinfo.xml           ← EXISTING (copy, for DevMemo P12)
      regioninfo_showcase.staticinfo.xml          ← EXISTING (copy)
    stringtable/
      loc/
        languagedata_KOR.xml                      ← **NEW** (P7) — Korean StrOrigin
        languagedata_ENG.xml                      ← **NEW** (P7) — English translations
      export__/
        characterinfo_showcase.staticinfo.xml      ← **NEW** (P8) — EventName→StringId
        characterinfo_showcase.staticinfo.loc.xml  ← **NEW** (P8) — LocStr for export index
        iteminfo_showcase.staticinfo.xml           ← **NEW** (P8) — EventName→StringId
        iteminfo_showcase.staticinfo.loc.xml       ← **NEW** (P8)
        Dialog/
          QuestDialog/
            quest_dialogue.xml                     ← **NEW** (P8) — nested export path
  common/mainline/commonresource/ui/
    texture/image/
      *.dds                                        ← **NEW** (P10) — stub DDS files
  cd/mainline/resource/
    sound/windows/
      English(US)/
        *.wem                                      ← **NEW** (P9) — stub WEM files
      Korean/
        *.wem                                      ← **NEW** (P9) — optional
```

**CRITICAL: Path Template Mapping for Tests**

To make MegaIndex work with mock data, override PerforcePathService with a test double that returns:

| Template Key | Maps To |
|---|---|
| `knowledge_folder` | `{mock_root}/cd/mainline/resource/GameData/StaticInfo/knowledgeinfo` |
| `character_folder` | `{mock_root}/cd/mainline/resource/GameData/StaticInfo/characterinfo` |
| `faction_folder` | `{mock_root}/cd/mainline/resource/GameData/StaticInfo/factioninfo` |
| `texture_folder` | `{mock_root}/common/mainline/commonresource/ui/texture/image` |
| `audio_folder` | `{mock_root}/cd/mainline/resource/sound/windows/English(US)` |
| `export_folder` | `{mock_root}/cd/mainline/resource/GameData/stringtable/export__` |
| `loc_folder` | `{mock_root}/cd/mainline/resource/GameData/stringtable/loc` |

MegaIndex derives `staticinfo_folder = knowledge_folder.parent` and `item_folder = staticinfo_folder / "iteminfo"`, so the hierarchy MUST be exact.

---

## 2. Exact XML Element/Attribute Names Per Parser

### P1: KnowledgeInfo (knowledgeinfo/*.xml)

**Elements:**
- `<KnowledgeInfo>`: `StrKey`, `Name`, `Desc`, `UITextureName`, `KnowledgeGroupKey` (or `GroupKey`)
- `<KnowledgeGroupInfo>`: `StrKey`, `GroupName` (or `Name`), contains child `<KnowledgeInfo>` elements
- Optional child `<LevelData>`: `Level`, `Learnable`, `RequiredLevel`, `ManaCost`

**Parser:** `root.iter("KnowledgeInfo")` and `root.iter("KnowledgeGroupInfo")`

### P2: CharacterInfo (characterinfo/*.xml)

**Elements:**
- `<CharacterInfo>`: `StrKey`, `CharacterName`, `CharacterDesc`, `UseMacro`, `Age`, `Job`, `UIIconPath`, `KnowledgeKey` (or `RewardKnowledgeKey` on children)
- Optional child `<SkillRef>`: `SkillKey`, `SkillName`

**Parser:** `root.iter("CharacterInfo")`, uses `_find_knowledge_key()` which checks element and direct children for `KnowledgeKey` or `RewardKnowledgeKey`

### P3: ItemInfo (iteminfo/*.staticinfo.xml)

**Elements:**
- `<ItemGroupInfo>`: `StrKey`, `GroupName`, `ParentStrKey` — hierarchy container
- `<ItemInfo>` (nested inside `<ItemGroupInfo>`): `StrKey`, `ItemName`, `ItemDesc`, `KnowledgeKey`
- `<InspectData>` (child of ItemInfo): `Desc`, `RewardKnowledgeKey`, `UseLeftPageInspectData`
- `<PageData>` (child of InspectData): `Desc`, `RewardKnowledgeKey` — book pattern

**Parser:** `root.iter("ItemGroupInfo")` for hierarchy, `root.iter("ItemInfo")` for items. Group determined by `elem.getparent().tag == "ItemGroupInfo"`

### P4: FactionInfo (factioninfo/*.xml)

**Elements:**
- `<FactionGroup>`: `StrKey`, `GroupName` (or `Name`), `KnowledgeKey` — top level
- `<Faction>` (child of FactionGroup): `StrKey`, `Name`, `KnowledgeKey`
- `<FactionNode>` (child of Faction): `StrKey`, `KnowledgeKey`, `WorldPosition` (format: "x,y,z"), `Type`, `AliasName` (or `Name`)
- `<RegionInfo>`: `KnowledgeKey`, `DisplayName`
- `<Polygon>`: `Points` (only in existing mock, not parsed by MegaIndex)

**Parser:** `root.iter("FactionGroup")`, `root.iter("Faction")`, `root.iter("FactionNode")`, `root.iter("RegionInfo")`

**IMPORTANT:** Existing `FactionInfo.staticinfo.xml` uses FLAT `<FactionNode>` elements without `<FactionGroup>`/`<Faction>` wrappers. MegaIndex expects hierarchical nesting: `FactionGroup > Faction > FactionNode`. The mock needs restructuring.

### P5: SkillInfo (StaticInfo/skillinfo_*.xml)

**Elements:**
- `<SkillInfo>`: `StrKey`, `SkillName`, `Desc` (or `SkillDesc`), `LearnKnowledgeKey`

**Parser:** `staticinfo_folder.rglob("skillinfo_*.xml")` then `root.iter("SkillInfo")`

**CRITICAL:** MegaIndex scans for `skillinfo_*.xml` files in `StaticInfo/` directly using rglob. Current mock has `StaticInfo/skillinfo/skillinfo_showcase.staticinfo.xml` which WILL be found by rglob since it matches the pattern. No move needed.

### P6: GimmickInfo (StaticInfo/gimmickinfo_*.xml)

**Elements:**
- `<GimmickGroupInfo>`: `StrKey`, `GimmickName`
- `<GimmickInfo>` (child of GimmickGroupInfo): `StrKey`, `Desc`, `GimmickName`
- `<SealData>` (child of GimmickInfo): `Desc`

**Parser:** `staticinfo_folder.rglob("gimmickinfo_*.xml")` then `root.iter("GimmickGroupInfo")`, `group_elem.iter("GimmickInfo")`

### P7: LanguageData (loc/languagedata_{code}.xml)

**Elements:**
- `<LocStr>`: `StringId` (or `StringID`), `StrOrigin`, `Str`

**Parser for KOR (D12):** `loc_folder.glob("**/languagedata_[Kk][Oo][Rr]*.xml")` — extracts StringId -> StrOrigin
**Parser for translations (D13):** `loc_folder.rglob("*.xml")` where stem starts with `languagedata_` — extracts StringId -> {lang: Str}

**Root element:** `<LanguageData>` (confirmed from existing showcase_items.loc.xml)

### P8: Export XMLs (export__/*.xml and export__/*.loc.xml)

**Event mapping (D11):** Elements with `SoundEventName` (or `EventName`) + `StringId` attributes. Case-insensitive.
**Export loc (D17/D18):** `*.loc.xml` files containing `<LocStr>` with `StringId` + `StrOrigin`

**Parser:** `export_folder.rglob("*.xml")` excluding `.loc.xml` for events; `export_folder.rglob("*.loc.xml")` for loc index

### P9: WEM Audio Files (sound/windows/{lang}/**/*.wem)

**Scanner:** `audio_folder.rglob("*.wem")` — key = `stem.lower()`, value = Path

### P10: DDS Texture Files (texture/image/**/*.dds)

**Scanner:** `texture_folder.rglob("*.dds")` — key = `stem.lower()`, value = Path

### P11: VRS Excel (VoiceRecordingSheet__/*.xlsx)

**Scanner:** Most recent `.xlsx` file. Reads "EventName" column header. Optional for mock.

### P12: Broad DevMemo Scan (StaticInfo/**/*.xml)

**Scanner:** `staticinfo_folder.rglob("*.xml")` — every element with `StrKey` attribute, extracts `DevMemo` or `DevComment`

---

## 3. Minimum Entries Per Type

### Target: Exercise ALL MegaIndex Features

| Feature | Min Required | Why |
|---------|-------------|-----|
| **Cards** (entity display) | 1+ per type | Cards render entity name, desc, image |
| **Search** (FAISS/text) | 3+ entities with varied names | Need multiple results for relevance ranking |
| **Categories** | 2+ groups per hierarchy type | ItemGroupInfo parent/child, KnowledgeGroupInfo |
| **Detail panels** | 1+ entity with ALL fields populated | Full CharacterEntry with knowledge_key, skills, etc. |
| **Cross-references** | 3+ entities linked via KnowledgeKey | Character -> Knowledge -> Region chain |
| **Audio chain** | 2+ events with StringId -> WEM | event_to_stringid + WEM file exists |
| **Image chain** | 3+ UITextureName -> DDS exists | knowledge -> dds_by_stem lookup |
| **StrKey<->StringId bridge** | 3+ Korean text matches | Korean name in StaticInfo = StrOrigin in loc |
| **Export scoping** | 2+ export files with overlapping Korean | Disambiguation via source_file |
| **Reverse lookups** | 2+ entities sharing same KnowledgeKey | R2 knowledge_key_to_entities |
| **Hierarchy** | 2 ItemGroups (parent + child) | ItemGroupNode.parent_strkey + child_strkeys |

### Existing Mock Data Counts (Already Sufficient)

| Entity Type | Count | Status |
|---|---|---|
| KnowledgeInfo | 29 entries (5 character, 3 skill, 14 region, 2 faction, 5 item) | SUFFICIENT |
| CharacterInfo | 5 entries | SUFFICIENT |
| ItemInfo | 5 entries | SUFFICIENT (needs ItemGroupInfo wrapper) |
| FactionNode (regions) | 14 entries | SUFFICIENT (needs hierarchy wrapper) |
| SkillInfo | 3 entries | SUFFICIENT |
| QuestInfo | 3 entries | BONUS (not parsed by MegaIndex directly) |
| RegionInfo | 5 entries | SUFFICIENT |
| Textures (PNG) | 36 files | Need DDS stub conversion |

### NEW Data Needed (Minimal)

| Data Type | Entries Needed | Justification |
|---|---|---|
| GimmickGroupInfo/GimmickInfo | 2 groups x 2 gimmicks each | Light up D8 |
| languagedata_KOR.xml | ~30 LocStr (reuse existing showcase_items.loc.xml data + add entity names) | Light up D12, R6 |
| languagedata_ENG.xml | ~30 LocStr matching KOR | Light up D13 |
| Export event XML | 5-10 event entries | Light up D11, D20, D21 |
| Export .loc.xml | 2 files x ~15 LocStr | Light up D17, D18 |
| WEM stubs | 5 files | Light up D10, C3 |
| DDS stubs | 36 files (convert existing PNGs) | Light up D9, C1 |
| ItemGroupInfo wrapper | 2 groups wrapping existing items | Light up D14, R7 |
| FactionGroup/Faction wrapper | 1 group + 2 factions wrapping existing nodes | Light up D5, D6 |

---

## 4. Mock WEM Files

### Can We Use WAV Renamed?

**NO for vgmstream conversion.** WEM files have a specific Wwise RIFF header that vgmstream validates. A renamed WAV will fail vgmstream decoding.

**YES for MegaIndex.** MegaIndex only scans filenames (`rglob("*.wem")`, key = `stem.lower()`). It never opens or decodes WEM files. The DDS-to-image and WEM-to-audio conversion happens in separate services (MapDataService thumbnail endpoint, audio player).

### Recommendation: 0-byte .wem Stubs

Create empty files with `.wem` extension. MegaIndex only indexes the filename. For tests that need actual audio playback, mock at the service layer.

```python
# Create stub WEM files
for name in ["play_varon_greeting", "play_kira_taunt", "play_grimjaw_forge", "play_lune_whisper", "play_drakmar_chant"]:
    (audio_folder / f"{name}.wem").touch()
```

### Real WEM for Audio Tests (If Needed Later)

Use `ffmpeg` to create minimal Ogg/WAV, then `wwise_cli` to encode. But this is NOT needed for MegaIndex testing.

---

## 5. Mock DDS Files

### Can We Keep PNGs and Add a DEV Fallback?

**NO for MegaIndex.** MegaIndex scans for `*.dds` only: `texture_folder.rglob("*.dds")`. PNG files will NOT be found.

**YES with a fallback scanner.** MapDataService already has DDS-to-PNG conversion. Adding a test-mode fallback to scan PNGs as well would work, but it changes production code for tests.

### Recommendation: 0-byte .dds Stubs (Same as WEM)

MegaIndex only indexes the filename. It never opens DDS files. DDS-to-PNG conversion is a separate service. For MegaIndex testing, 0-byte stubs with `.dds` extension are perfect.

```python
# Create stub DDS files from existing PNG names
for png in texture_folder.rglob("*.png"):
    dds_path = dds_folder / f"{png.stem}.dds"
    dds_path.touch()
```

### For Image Display Tests (If Needed Later)

A minimal DDS file needs the 128-byte DDS header. This is the DDS_HEADER struct:

```python
import struct

def create_minimal_dds(path, width=4, height=4):
    """Create a 4x4 RGBA DDS file (128 header + 64 pixel bytes)."""
    DDS_MAGIC = b'DDS '
    header = struct.pack('<4sI II II III 44x IIII 20x',
        DDS_MAGIC,
        124,           # dwSize
        0x1007,        # dwFlags (CAPS|HEIGHT|WIDTH|PIXELFORMAT)
        height, width,
        0, 0, 0,       # pitch, depth, mipmaps
        32,            # ddspf.dwSize
        0x41,          # ddspf.dwFlags (ALPHAPIXELS|RGB)
        0,             # ddspf.dwFourCC
        32,            # ddspf.dwRGBBitCount
    )
    pixel_data = b'\xFF\x00\xFF\xFF' * (width * height)  # Magenta RGBA
    with open(path, 'wb') as f:
        f.write(header)
        f.write(pixel_data)
```

But for MegaIndex tests, `touch()` is sufficient.

---

## 6. Export XML Structure (EventName → StringId Mapping)

### Event Mapping XML (P8 — non-.loc.xml files)

MegaIndex looks for ANY element with `SoundEventName` (or `EventName`) + `StringId` attributes:

```xml
<?xml version="1.0" encoding="utf-8"?>
<SoundExportData>
  <!-- Character voice lines -->
  <SoundEvent SoundEventName="play_varon_greeting" StringId="CHAR_VARON_GREETING"
              Category="Dialog" SubCategory="NPC" />
  <SoundEvent SoundEventName="play_kira_taunt" StringId="CHAR_KIRA_TAUNT"
              Category="Dialog" SubCategory="Boss" />
  <SoundEvent SoundEventName="play_grimjaw_forge" StringId="CHAR_GRIMJAW_FORGE"
              Category="Dialog" SubCategory="NPC" />
  <SoundEvent SoundEventName="play_lune_whisper" StringId="CHAR_LUNE_WHISPER"
              Category="Dialog" SubCategory="NPC" />
  <SoundEvent SoundEventName="play_drakmar_chant" StringId="CHAR_DRAKMAR_CHANT"
              Category="Dialog" SubCategory="NPC" />
</SoundExportData>
```

**Key points:**
- Case-insensitive attribute extraction: `attrs.get("soundeventname")` or `attrs.get("eventname")`
- Event name stored lowercase in dict
- D20 (`event_to_export_path`) = relative dir from export root (e.g., `"Dialog/QuestDialog"`)
- D21 (`event_to_xml_order`) = global element counter across all files

### Export Loc XML (P8 — .loc.xml files)

```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringId="CHAR_VARON_NAME" StrOrigin="장로 바론" />
  <LocStr StringId="CHAR_VARON_DESC" StrOrigin="봉인된 도서관의 수호자인 장로 바론은..." />
  <LocStr StringId="ITEM_SAGE_STAFF_NAME" StrOrigin="현자의 지팡이" />
  <LocStr StringId="ITEM_SAGE_STAFF_DESC" StrOrigin="장로 바론이 수백 년간 사용해온 고대의 지팡이." />
</LanguageData>
```

**Key points:**
- Filename stem (normalized) becomes export key: `"characterinfo_showcase.staticinfo"` → used for D17 (`export_file_stringids`)
- D18 (`ordered_export_index`): normalized StrOrigin -> list of StringIds in document order
- `_get_export_key()` strips `.xml` and `.loc` from filename

---

## 7. LanguageData Structure (StringId → StrOrigin → Str)

### languagedata_KOR.xml (P7 — D12: StringId → StrOrigin)

```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <!-- Character names (bridge KnowledgeInfo.Name to StringId) -->
  <LocStr StringId="CHAR_VARON_NAME" StrOrigin="장로 바론" Str="장로 바론" />
  <LocStr StringId="CHAR_KIRA_NAME" StrOrigin="그림자 암살자 키라" Str="그림자 암살자 키라" />
  <LocStr StringId="CHAR_GRIMJAW_NAME" StrOrigin="대장장이 그림죠" Str="대장장이 그림죠" />

  <!-- Item names -->
  <LocStr StringId="ITEM_SAGE_STAFF_NAME" StrOrigin="현자의 지팡이" Str="현자의 지팡이" />
  <LocStr StringId="ITEM_BLACKSTAR_SWORD_NAME" StrOrigin="검은별 대검" Str="검은별 대검" />

  <!-- Region names -->
  <LocStr StringId="REGION_MIST_FOREST_NAME" StrOrigin="안개의 숲" Str="안개의 숲" />
  <LocStr StringId="REGION_SEALED_LIBRARY_NAME" StrOrigin="봉인된 도서관" Str="봉인된 도서관" />

  <!-- Dialogue (for audio chain) -->
  <LocStr StringId="CHAR_VARON_GREETING" StrOrigin="별들이 다가오는 거대한 어둠에 대해 이야기합니다." Str="별들이 다가오는 거대한 어둠에 대해 이야기합니다." />
</LanguageData>
```

**Key points for KOR:**
- KOR file is used ONLY for D12 (StringId → StrOrigin)
- `Str` for KOR is typically same as StrOrigin
- MegaIndex skips `lang == "kor"` in `_parse_loc_translations()` — KOR is not treated as a "translation"

### languagedata_ENG.xml (P7 — D13: StringId → translations)

```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringId="CHAR_VARON_NAME" StrOrigin="장로 바론" Str="Elder Varon" />
  <LocStr StringId="CHAR_KIRA_NAME" StrOrigin="그림자 암살자 키라" Str="Shadow Assassin Kira" />
  <LocStr StringId="ITEM_SAGE_STAFF_NAME" StrOrigin="현자의 지팡이" Str="Sage's Staff" />
  <LocStr StringId="ITEM_BLACKSTAR_SWORD_NAME" StrOrigin="검은별 대검" Str="Blackstar Greatsword" />
  <LocStr StringId="REGION_MIST_FOREST_NAME" StrOrigin="안개의 숲" Str="Mist Forest" />
  <LocStr StringId="CHAR_VARON_GREETING" StrOrigin="별들이 다가오는..." Str="The stars speak of a great darkness approaching." />
</LanguageData>
```

**Key points for non-KOR:**
- Parser extracts lang code from filename: `languagedata_ENG.xml` → `lang = "eng"`
- Only preloaded languages are parsed (default: `["eng", "kor"]`)
- Builds D13: `stringid_to_translations[sid]["eng"] = Str`

---

## 8. ItemGroupInfo Hierarchy (Parent → Child → Items)

### XML Structure

```xml
<ItemInfoList>
  <!-- Root group (no parent) -->
  <ItemGroupInfo StrKey="ItemGroup_Equipment" GroupName="장비">

    <!-- Child group (parent = root) -->
    <ItemGroupInfo StrKey="ItemGroup_Weapons" GroupName="무기" ParentStrKey="ItemGroup_Equipment">

      <!-- Items in this group -->
      <ItemInfo Key="Item_BlackstarSword" StrKey="Item_BlackstarSword"
          ItemName="검은별 대검" Grade="6" RequireLevel="90" AttackPower="620"
          KnowledgeKey="Knowledge_BlackstarSword"
          UITextureName="item_blackstar_sword_v2"
          ItemDesc="대장장이 그림죠의 필생의 역작." />

      <ItemInfo Key="Item_SageStaff" StrKey="Item_SageStaff"
          ItemName="현자의 지팡이" Grade="5" RequireLevel="80" AttackPower="450"
          KnowledgeKey="Knowledge_SacredFlame"
          UITextureName="item_sage_staff"
          ItemDesc="장로 바론이 수백 년간 사용해온 고대의 지팡이." />

      <ItemInfo Key="Item_ShadowDagger" StrKey="Item_ShadowDagger"
          ItemName="어둠의 단검" Grade="5" RequireLevel="85" AttackPower="380"
          KnowledgeKey="Knowledge_ShadowStrike"
          UITextureName="item_dark_dagger"
          ItemDesc="그림자 암살자 키라의 상징적인 무기." />
    </ItemGroupInfo>

    <!-- Another child group -->
    <ItemGroupInfo StrKey="ItemGroup_Consumables" GroupName="소모품" ParentStrKey="ItemGroup_Equipment">

      <ItemInfo Key="Item_PlagueCure" StrKey="Item_PlagueCure"
          ItemName="역병 치료제" Grade="3" RequireLevel="30" ItemType="Consumable"
          UITextureName="item_plague_cure_v2"
          ItemDesc="봉인된 도서관 주변에 퍼진 역병을 치료하는 약." />
    </ItemGroupInfo>
  </ItemGroupInfo>

  <!-- Quest items (separate root) -->
  <ItemGroupInfo StrKey="ItemGroup_Quest" GroupName="퀘스트 아이템">

    <ItemInfo Key="Item_SealScroll" StrKey="Item_SealScroll"
        ItemName="봉인의 두루마리" Grade="4" ItemType="Quest"
        KnowledgeKey="Knowledge_SealedLibrary"
        FactionKey="Faction_SageOrder"
        UITextureName="item_seal_scroll"
        ItemDesc="봉인된 도서관의 봉인을 유지하기 위한 고대 두루마리.">

      <!-- InspectData with book pattern (PageData) -->
      <InspectData>
        <PageData Desc="봉인의 첫 번째 열쇠는 성스러운 불꽃이다."
                  RewardKnowledgeKey="Knowledge_SacredFlame" />
        <PageData Desc="두 번째 열쇠는 검은별 금속이다."
                  RewardKnowledgeKey="Knowledge_BlackstarSword" />
      </InspectData>
    </ItemInfo>
  </ItemGroupInfo>
</ItemInfoList>
```

### How MegaIndex Parses This

1. **D14 (item_group_hierarchy):** Iterates `<ItemGroupInfo>` elements:
   - Extracts `StrKey`, `GroupName`, `ParentStrKey`
   - Collects child `<ItemInfo>` StrKeys within each group
   - Builds `ItemGroupNode(strkey, group_name, parent_strkey, child_strkeys, item_strkeys)`

2. **D3 (item_by_strkey):** Iterates `<ItemInfo>` elements:
   - Extracts `StrKey`, `ItemName`, `ItemDesc`, `KnowledgeKey`
   - Determines `group_key` from `elem.getparent().tag == "ItemGroupInfo"`
   - Extracts `InspectData` → `PageData` chain with `RewardKnowledgeKey` resolution

3. **R7 (group_key_to_items):** Built from D3 by accumulating items per group_key

### Key Wiring Requirements

- `ParentStrKey` on child `<ItemGroupInfo>` MUST reference the parent's `StrKey`
- `<ItemInfo>` MUST be a direct child of `<ItemGroupInfo>` for group detection
- `InspectData` → `PageData` → `RewardKnowledgeKey` must reference existing knowledge entries (from D1)

---

## 9. FactionInfo Hierarchy (Restructured for MegaIndex)

The existing `FactionInfo.staticinfo.xml` has FLAT `<FactionNode>` elements. MegaIndex expects hierarchical nesting. Here is the proper structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<FactionInfoList>
  <FactionGroup StrKey="FactionGroup_World" GroupName="세계" KnowledgeKey="Knowledge_SageOrder">

    <Faction StrKey="Faction_SageOrder" Name="현자의 결사" KnowledgeKey="Knowledge_SageOrder">
      <FactionNode StrKey="Region_SealedLibrary" KnowledgeKey="Knowledge_SealedLibrary"
                   Type="Dungeon" WorldPosition="350,0,150" />
      <FactionNode StrKey="Region_SageTower" KnowledgeKey="Knowledge_SageTower"
                   Type="Main" WorldPosition="400,0,450" />
      <FactionNode StrKey="Region_BlackstarVillage" KnowledgeKey="Knowledge_BlackstarVillage"
                   Type="Town" WorldPosition="500,0,300" />
    </Faction>

    <Faction StrKey="Faction_DarkCult" Name="어둠의 교단" KnowledgeKey="Knowledge_DarkCult">
      <FactionNode StrKey="Region_DarkCultHQ" KnowledgeKey="Knowledge_DarkCultHQ"
                   Type="Fortress" WorldPosition="650,0,200" />
      <FactionNode StrKey="Region_ForgottenFortress" KnowledgeKey="Knowledge_ForgottenFortress"
                   Type="Fortress" WorldPosition="600,0,550" />
    </Faction>

  </FactionGroup>

  <!-- Region display names -->
  <RegionInfo KnowledgeKey="Knowledge_SealedLibrary" DisplayName="봉인된 도서관 (메인)" />
  <RegionInfo KnowledgeKey="Knowledge_BlackstarVillage" DisplayName="흑성 마을 (거점)" />
</FactionInfoList>
```

---

## 10. GimmickInfo Structure (NEW — P6)

```xml
<?xml version="1.0" encoding="utf-8"?>
<GimmickInfoList>
  <GimmickGroupInfo StrKey="GimmickGroup_Seals" GimmickName="봉인 장치">
    <GimmickInfo StrKey="Gimmick_LibrarySeal01" GimmickName="도서관 제1봉인" Desc="고대 현자의 첫 번째 봉인 장치">
      <SealData Desc="성스러운 불꽃을 바쳐야 봉인이 풀린다." />
    </GimmickInfo>
    <GimmickInfo StrKey="Gimmick_LibrarySeal02" GimmickName="도서관 제2봉인" Desc="고대 현자의 두 번째 봉인 장치">
      <SealData Desc="검은별 금속의 열쇠가 필요하다." />
    </GimmickInfo>
  </GimmickGroupInfo>

  <GimmickGroupInfo StrKey="GimmickGroup_Traps" GimmickName="함정">
    <GimmickInfo StrKey="Gimmick_ShadowTrap01" GimmickName="그림자 함정" Desc="어둠의 교단이 설치한 마법 함정">
      <SealData Desc="그림자 속에 숨겨진 위험한 마법 장치." />
    </GimmickInfo>
  </GimmickGroupInfo>
</GimmickInfoList>
```

---

## 11. Cross-Reference Wiring Map

This table shows how entities cross-reference each other, critical for reverse dicts (R1-R7) and composed dicts (C1-C7):

### Entity → KnowledgeKey → Image Chain

```
Character_ElderVaron
  ├── KnowledgeKey = "Knowledge_ElderVaron"
  │   ├── UITextureName = "character_varon"      → dds_by_stem["character_varon"] → C1
  │   └── Name = "장로 바론"                       → R1 name_kr_to_strkeys
  ├── VoicePath = "audio/characters/elder_varon_greeting.wem"
  └── source_file = "characterinfo_showcase.staticinfo.xml"
      └── export_file_stringids["characterinfo_showcase.staticinfo"] → C6
```

### Audio Chain (EventName → StringId → StrOrigin)

```
WEM file: play_varon_greeting.wem
  → wem_by_event["play_varon_greeting"]                    (D10)
  → event_to_stringid["play_varon_greeting"] = "CHAR_VARON_GREETING"  (D11)
  → stringid_to_strorigin["CHAR_VARON_GREETING"] = "별들이..."        (D12)
  → stringid_to_translations["CHAR_VARON_GREETING"]["eng"] = "The stars..."  (D13)
  → event_to_script_kr["play_varon_greeting"] = "별들이..."            (C4)
  → event_to_script_eng["play_varon_greeting"] = "The stars..."        (C5)
```

### StringId ↔ StrKey Bridge

```
StaticInfo: KnowledgeInfo.Name = "장로 바론" (StrKey = "Knowledge_ElderVaron")
LocData:    LocStr.StrOrigin = "장로 바론"  (StringId = "CHAR_VARON_NAME")
Bridge:     normalize("장로 바론") matches → C7 maps StringId to entity
```

### Required Consistency Rules

1. Every `UITextureName` in KnowledgeInfo MUST have a matching `.dds` file
2. Every `SoundEventName` in export XML MUST have a matching `.wem` file
3. Every `KnowledgeKey` on entities MUST exist in `knowledge_by_strkey`
4. Korean entity names MUST appear as `StrOrigin` in languagedata_KOR.xml for the bridge to work
5. Export `.loc.xml` filenames MUST match StaticInfo filenames for export scoping (D17)

---

## 12. Complete File Manifest

### Files to CREATE (New)

| File | Parse Source | Dict(s) Populated |
|---|---|---|
| `stringtable/loc/languagedata_KOR.xml` | P7 | D12, R6 |
| `stringtable/loc/languagedata_ENG.xml` | P7 | D13 |
| `stringtable/export__/characterinfo_showcase.staticinfo.xml` | P8 | D11, D20, D21 |
| `stringtable/export__/characterinfo_showcase.staticinfo.loc.xml` | P8 | D17, D18 |
| `stringtable/export__/iteminfo_showcase.staticinfo.xml` | P8 | D11, D20, D21 |
| `stringtable/export__/iteminfo_showcase.staticinfo.loc.xml` | P8 | D17, D18 |
| `stringtable/export__/Dialog/QuestDialog/quest_dialogue.xml` | P8 | D11, D20 (nested path) |
| `StaticInfo/gimmickinfo_showcase.staticinfo.xml` | P6 | D8 |
| 36x `.dds` stub files in `texture/image/` | P10 | D9, C1 |
| 5x `.wem` stub files in `sound/windows/English(US)/` | P9 | D10, C2, C3 |

### Files to MODIFY (Restructure)

| File | Change | Reason |
|---|---|---|
| `iteminfo_showcase.staticinfo.xml` | Wrap items in `<ItemGroupInfo>` hierarchy | D14 needs parent/child groups |
| `FactionInfo.staticinfo.xml` | Add `<FactionGroup>` and `<Faction>` wrappers + `<RegionInfo>` elements | D5, D6, D16 need hierarchy |

### Files to KEEP AS-IS (Copy)

| File | Parse Source |
|---|---|
| `knowledgeinfo_showcase.staticinfo.xml` | P1 |
| `characterinfo_showcase.staticinfo.xml` | P2 |
| `skillinfo_showcase.staticinfo.xml` | P5 (found by rglob) |
| `questinfo_showcase.staticinfo.xml` | P12 (DevMemo scan) |
| `regioninfo_showcase.staticinfo.xml` | P12 (DevMemo scan) |
| `NodeWaypointInfo.staticinfo.xml` | Not parsed by MegaIndex |

---

## 13. Test Infrastructure: PerforcePathService Override

### Option A: Monkey-Patch in conftest.py (Recommended)

```python
@pytest.fixture
def mock_perforce_root(tmp_path):
    """Create mock Perforce structure and override path service."""
    # Copy/create all mock files into tmp_path with correct structure
    mock_root = tmp_path / "perforce_mock"
    # ... setup ...

    # Override the path service singleton
    from server.tools.ldm.services.perforce_path_service import get_perforce_path_service
    svc = get_perforce_path_service()

    # Monkey-patch _resolved_paths directly
    svc._resolved_paths = {
        "knowledge_folder": mock_root / "cd/mainline/resource/GameData/StaticInfo/knowledgeinfo",
        "character_folder": mock_root / "cd/mainline/resource/GameData/StaticInfo/characterinfo",
        "faction_folder": mock_root / "cd/mainline/resource/GameData/StaticInfo/factioninfo",
        "texture_folder": mock_root / "common/mainline/commonresource/ui/texture/image",
        "audio_folder": mock_root / "cd/mainline/resource/sound/windows/English(US)",
        "export_folder": mock_root / "cd/mainline/resource/GameData/stringtable/export__",
        "loc_folder": mock_root / "cd/mainline/resource/GameData/stringtable/loc",
    }
    return mock_root
```

### Option B: Static Fixture Directory (Simpler)

Keep all mock data in `tests/fixtures/perforce_mock/` with the full directory tree. Tests reference it via `Path(__file__).parent.parent / "fixtures" / "perforce_mock"`. Override path service to point there.

**Recommendation:** Option B for the fixture data (committed to repo), Option A for test wiring.

---

## 14. DevMemo/DevComment for P12

Add `DevMemo` attributes to existing entities so the broad scan (D19) finds them:

```xml
<!-- In questinfo_showcase.staticinfo.xml -->
<QuestInfo StrKey="Quest_SealedLibraryMain" DevMemo="메인 퀘스트 - 봉인된 도서관" ... />

<!-- In knowledgeinfo_showcase.staticinfo.xml (add to a few entries) -->
<KnowledgeInfo StrKey="Knowledge_ElderVaron" DevComment="핵심 NPC - 봉인 수호자" ... />
```

---

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/services/mega_index.py` — all parse methods, build pipeline
- `server/tools/ldm/services/mega_index_schemas.py` — all 10 entity schemas
- `server/tools/ldm/services/perforce_path_service.py` — PATH_TEMPLATES, path resolution
- `.planning/research/MEGAINDEX_DESIGN.md` — all 12 parse sources, 35 dict definitions

### Secondary (HIGH confidence)
- `tests/fixtures/mock_gamedata/` — all existing fixture files (XML, PNG, loc)
- `RFC/NewScripts/MapDataGenerator/core/linkage.py` — AudioIndex, DDSIndex patterns
- `RFC/NewScripts/QACompilerNEW/generators/item.py` — ItemGroupInfo hierarchy
