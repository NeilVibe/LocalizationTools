# Mock Data Generator Script -- Approach B Research

**Researched:** 2026-03-21
**Domain:** Python generator script for MegaIndex mock data
**Confidence:** HIGH (all findings from direct source code analysis of mega_index.py, schemas, and existing fixtures)

---

## 1. Executive Summary

A single Python script CAN generate ALL mock data files needed to populate every one of MegaIndex's 35 dictionaries. The existing fixture directory (`tests/fixtures/mock_gamedata/`) already has good Phase 1-2 XML coverage (knowledge, character, item, faction, skill) but is **completely missing** the files needed for Phase 3 (localization), Phase 5 (devmemo), and Phase 7 (composed dicts), plus all binary assets (DDS, WEM).

The generator script must produce:
- **7 XML file types** in the correct folder hierarchy
- **Mock DDS files** (4-byte minimum with `.dds` extension -- MegaIndex only checks `rglob("*.dds")`, never reads content)
- **Mock WEM files** (same -- `rglob("*.wem")` filename scan only, content irrelevant)
- **Cross-references** validated at generation time

**Primary recommendation:** Write `tests/fixtures/mock_gamedata/generate_megaindex_data.py` that generates the complete folder tree, reusing the existing showcase theme (Elder Varon, Kira, Grimjaw, etc.) and extending it with the missing file types.

---

## 2. Gap Analysis: What Exists vs. What MegaIndex Needs

### 2A. Current Fixture Inventory

| File | Exists | Populates Dicts |
|------|--------|----------------|
| `StaticInfo/knowledgeinfo/knowledgeinfo_showcase.staticinfo.xml` | YES (30 entries) | D1, D15, R1, R4, C1 |
| `StaticInfo/characterinfo/characterinfo_showcase.staticinfo.xml` | YES (5 entries) | D2, R1, R2, R5 |
| `StaticInfo/iteminfo/iteminfo_showcase.staticinfo.xml` | YES (5 entries) | D3, D14, R1, R2, R7 |
| `StaticInfo/factioninfo/FactionInfo.staticinfo.xml` | YES (14 regions) | D4, D5, D6, D16, R1, R2, R5 |
| `StaticInfo/skillinfo/skillinfo_showcase.staticinfo.xml` | YES (3 entries) | D7, R2, R5 |
| `StaticInfo/gimmickinfo/gimmickinfo_*.xml` | **NO** | D8 |
| `loc/languagedata_KOR.xml` | **NO** | D12, R6, C4, C6, C7 |
| `loc/languagedata_ENG.xml` | **NO** | D13, C5 |
| `export__/**/*.xml` (event mappings) | **NO** | D11, D20, D21, R3, C3, C4, C5 |
| `export__/**/*.loc.xml` (export loc) | **NO** | D17, D18, C6, C7 |
| `texture/image/**/*.dds` | **NO** (only `.png`) | D9, C1 |
| `sound/windows/English(US)/**/*.wem` | **NO** | D10, C2, C3 |
| Any file with DevMemo/DevComment attr | **NO** (attr not in current XMLs) | D19 |

### 2B. Dict Coverage Summary

| Category | Dicts | Currently Populated | Missing |
|----------|-------|-------------------|---------|
| Phase 1: Foundation | D1, D9, D10, D15 | D1, D15 | **D9 (DDS), D10 (WEM)** |
| Phase 2: Entity Parse | D2-D8, D14, D16 | D2-D7, D14 (partial) | **D8 (gimmick), D16 (partial)** |
| Phase 3: Localization | D11-D13, D17-D18, D20-D21 | NONE | **ALL MISSING** |
| Phase 5: Broad Scan | D19 | NONE | **D19 (devmemo)** |
| Phase 6: Reverse | R1-R7 | R1-R2 (partial) | **R3-R7 depend on missing dicts** |
| Phase 7: Composed | C1-C7 | NONE | **ALL depend on missing dicts** |

**Bottom line:** 15 of 35 dicts get zero data from current fixtures. The composed dicts (C1-C7), which are the most valuable for the Codex UI, are entirely empty.

---

## 3. Folder Structure Required by MegaIndex

MegaIndex's `build()` method resolves paths via `PerforcePathService.get_all_resolved()`. For mock data, we need this tree:

```
tests/fixtures/mock_gamedata/
  StaticInfo/
    knowledgeinfo/         # knowledge_folder -> D1, D15
      knowledgeinfo_showcase.staticinfo.xml  (EXISTS)
    characterinfo/         # character_folder -> D2
      characterinfo_showcase.staticinfo.xml  (EXISTS)
    iteminfo/              # item_folder (= staticinfo/iteminfo) -> D3, D14
      iteminfo_showcase.staticinfo.xml  (EXISTS)
    factioninfo/           # faction_folder -> D4, D5, D6, D16
      FactionInfo.staticinfo.xml  (EXISTS)
    skillinfo/             # parsed via staticinfo.rglob("skillinfo_*") -> D7
      skillinfo_showcase.staticinfo.xml  (EXISTS)
    gimmickinfo/           # parsed via staticinfo.rglob("gimmickinfo_*") -> D8
      gimmickinfo_showcase.staticinfo.xml  (GENERATE)
  loc/                     # loc_folder -> D12, D13
    languagedata_KOR.xml   (GENERATE)
    languagedata_ENG.xml   (GENERATE)
  export__/                # export_folder -> D11, D17, D18, D20, D21
    Dialog/
      QuestDialog/
        questdialog_showcase.xml        (GENERATE - event+stringid pairs)
        questdialog_showcase.loc.xml    (GENERATE - LocStr with StrOrigin)
    Character/
      characterinfo_showcase.staticinfo.xml      (GENERATE)
      characterinfo_showcase.staticinfo.loc.xml  (GENERATE)
    Item/
      iteminfo_showcase.staticinfo.xml      (GENERATE)
      iteminfo_showcase.staticinfo.loc.xml  (GENERATE)
  texture/
    image/                 # texture_folder -> D9
      *.dds files          (GENERATE - empty stub files)
  sound/
    windows/
      English(US)/         # audio_folder -> D10
        *.wem files        (GENERATE - empty stub files)
```

---

## 4. Answers to Research Questions

### Q1: Can we write ONE Python script that generates ALL mock data files?

**YES.** One script, ~400-600 lines, organized as:

```python
# Phase 0: Define all entities in a central registry (the "truth")
CHARACTERS = [...]  # strkey, name_kr, name_eng, knowledge_key, ...
ITEMS = [...]
REGIONS = [...]
SKILLS = [...]
GIMMICKS = [...]
AUDIO_EVENTS = [...]  # event_name, stringid, strorigin_kr, str_eng

# Phase 1: Generate StaticInfo XMLs (knowledge, character, item, faction, skill, gimmick)
# Phase 2: Generate loc/ XMLs (languagedata_KOR, languagedata_ENG)
# Phase 3: Generate export__/ XMLs (event mappings + .loc.xml)
# Phase 4: Generate binary stubs (DDS, WEM)
# Phase 5: Validate by running MegaIndex.build()
```

### Q2: How to ensure cross-references are valid?

**Use a single source-of-truth registry.** All generators read from the same Python dicts. Cross-reference rules:

| Reference | Rule |
|-----------|------|
| Character.KnowledgeKey | Must exist in KNOWLEDGE registry |
| Item.KnowledgeKey | Must exist in KNOWLEDGE registry |
| Region.KnowledgeKey (FactionNode) | Must exist in KNOWLEDGE registry |
| Knowledge.UITextureName | Must have matching `.dds` file generated |
| export XML SoundEventName | Must have matching `.wem` file generated |
| export XML StringId | Must exist in languagedata_KOR.xml |
| export .loc.xml StringId | Must match export XML StringId |
| export .loc.xml StrOrigin | Must match languagedata_KOR.xml StrOrigin |
| C6/C7 bridge: entity.source_file -> export filename | Export .loc.xml filename must match entity source_file stem |

**Implementation:** Build the registry first, then generate all files from it. Validation is built-in because all generators share the same data.

### Q3: Minimal entity count per type?

| Entity Type | Current Count | Recommended Min | Why |
|-------------|--------------|-----------------|-----|
| Knowledge (D1) | 30 | 30 (keep) | Covers all entity types' knowledge links |
| Characters (D2) | 5 | 5 (keep) | Enough for relationship graph, faction distribution |
| Items (D3) | 5 | 7 (add 2) | Need items across 2+ groups for D14/R7 hierarchy |
| Regions (D4) | 14 | 14 (keep) | 14 regions across 2 factions = rich map |
| Factions (D5) | 0 explicit | 2 (add) | Need FactionGroup > Faction > FactionNode hierarchy |
| Skills (D7) | 3 | 3 (keep) | Each linked to a character |
| Gimmicks (D8) | 0 | 3 (add) | Need GimmickGroupInfo > GimmickInfo > SealData nesting |
| Audio events (D10+D11) | 0 | 10 (add) | ~2 per character = voicelines, cover export path categories |
| StringIds (D12) | 0 | 40-50 (add) | All entity names + descs + audio lines |
| DDS textures (D9) | 0 (.dds) | 25 (add) | One per UITextureName in knowledge entries |
| WEM files (D10) | 0 | 10 (add) | Match audio event names |

### Q4: Can we generate mock WEM files?

**YES -- trivially.** MegaIndex only does `rglob("*.wem")` and reads `stem.lower()` as the key. It NEVER opens or reads WEM file content. An empty file with `.wem` extension works perfectly:

```python
wem_path = audio_folder / f"{event_name}.wem"
wem_path.write_bytes(b"")  # 0 bytes is fine
```

The MegaIndex WEM scanner (line 339-349 of mega_index.py):
```python
for wem_path in audio_folder.rglob("*.wem"):
    stem_lower = wem_path.stem.lower()
    self.wem_by_event[stem_lower] = wem_path
```

No header parsing, no content reading. Empty files work.

### Q5: Can we generate mock DDS files?

**YES -- same pattern.** MegaIndex DDS scanner (line 327-337):
```python
for dds_path in texture_folder.rglob("*.dds"):
    stem_lower = dds_path.stem.lower()
    self.dds_by_stem[stem_lower] = dds_path
```

Empty `.dds` files work. However, if the DDS-to-PNG conversion endpoint is ever tested, we might want a valid DDS header. For now, empty stubs are sufficient since MegaIndex only indexes paths.

```python
dds_path = texture_folder / f"{texture_name}.dds"
dds_path.write_bytes(b"")  # or b"DDS " + b"\x00" * 124 for a valid header
```

**Note:** The existing `.png` files in `textures/` will NOT be found by MegaIndex (it scans for `*.dds`). We must generate `.dds` files in the correct `texture/image/` subfolder.

### Q6: How to generate export XMLs with correct SoundEventName + StringId?

MegaIndex `_parse_export_events()` (line 797-834) iterates ALL elements and looks for `SoundEventName` or `EventName` + `StringId` attributes:

```xml
<!-- export__/Dialog/QuestDialog/questdialog_showcase.xml -->
<?xml version="1.0" encoding="utf-8"?>
<DialogList>
  <Dialog SoundEventName="play_varon_greeting_01" StringId="DLG_VARON_GREETING_01"
          Speaker="Character_ElderVaron" />
  <Dialog SoundEventName="play_kira_taunt_01" StringId="DLG_KIRA_TAUNT_01"
          Speaker="Character_ShadowKira" />
</DialogList>
```

And the matching `.loc.xml` for `_parse_export_loc()` (line 836-874):

```xml
<!-- export__/Dialog/QuestDialog/questdialog_showcase.loc.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringId="DLG_VARON_GREETING_01" StrOrigin="봉인된 도서관에 오신 것을 환영합니다." />
  <LocStr StringId="DLG_KIRA_TAUNT_01" StrOrigin="네 화살은 빗나갔어." />
</LanguageData>
```

**Key detail:** The export XML filename (normalized by `_get_export_key()`) must match the `.loc.xml` filename. The function strips `.xml` and `.loc` extensions and lowercases:
```python
def _get_export_key(filename: str) -> str:
    return filename.lower().replace(".xml", "").replace(".loc", "")
```

So `questdialog_showcase.xml` and `questdialog_showcase.loc.xml` both become `"questdialog_showcase"`.

**For C6/C7 bridge:** Export `.loc.xml` filenames should match entity `source_file` stems. Example: character entity has `source_file="characterinfo_showcase.staticinfo.xml"`, so we need `export__/Character/characterinfo_showcase.staticinfo.loc.xml` with the character name/desc StringIds.

### Q7: How to generate languagedata XMLs?

Standard LocStr format, must contain ALL StringIds used anywhere:

```xml
<!-- loc/languagedata_KOR.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <!-- Character names and descriptions -->
  <LocStr StringId="CHAR_VARON_NAME" StrOrigin="장로 바론" Str="장로 바론" />
  <LocStr StringId="CHAR_VARON_DESC" StrOrigin="봉인된 도서관의 수호자..." Str="봉인된 도서관의 수호자..." />
  <!-- Dialog lines -->
  <LocStr StringId="DLG_VARON_GREETING_01" StrOrigin="봉인된 도서관에 오신 것을 환영합니다." Str="봉인된 도서관에 오신 것을 환영합니다." />
  ...
</LanguageData>
```

```xml
<!-- loc/languagedata_ENG.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <LocStr StringId="CHAR_VARON_NAME" Str="Elder Varon" />
  <LocStr StringId="CHAR_VARON_DESC" Str="Guardian of the Sealed Library..." />
  <LocStr StringId="DLG_VARON_GREETING_01" Str="Welcome to the Sealed Library." />
  ...
</LanguageData>
```

**Critical:** KOR file uses `StrOrigin` attribute (parsed by `_parse_loc_strorigin` which reads `elem.get("StrOrigin")`). ENG file uses `Str` attribute (parsed by `_parse_loc_translations` which reads `elem.get("Str")`).

**For C6/C7 bridge to work:** The `StrOrigin` in the KOR languagedata must EXACTLY match (after normalization) the Korean name/desc in StaticInfo entities. This is how `_build_entity_strkey_to_stringids()` resolves the bridge.

### Q8: Should the generator be idempotent?

**YES.** The script should:
1. Delete and recreate output directories (not the root `mock_gamedata/`)
2. Overwrite all generated files
3. Leave existing StaticInfo XMLs untouched OR regenerate them from the same registry
4. Be safe to run repeatedly with identical output (deterministic)

**Recommendation:** Generate EVERYTHING from the central registry, including the StaticInfo XMLs that currently exist. This ensures consistency. Mark the existing hand-written XMLs as deprecated/replaceable.

### Q9: How to validate the generated data?

Run `MegaIndex.build()` against the generated data and assert all 35 dicts are non-empty:

```python
def validate(mock_root: Path):
    """Run MegaIndex.build() and verify all dicts populated."""
    from unittest.mock import patch
    from server.tools.ldm.services.mega_index import MegaIndex

    # Patch PerforcePathService to return mock_root paths
    mock_paths = {
        "knowledge_folder": mock_root / "StaticInfo" / "knowledgeinfo",
        "character_folder": mock_root / "StaticInfo" / "characterinfo",
        "faction_folder": mock_root / "StaticInfo" / "factioninfo",
        "texture_folder": mock_root / "texture" / "image",
        "audio_folder": mock_root / "sound" / "windows" / "English(US)",
        "export_folder": mock_root / "export__",
        "loc_folder": mock_root / "loc",
    }

    with patch("server.tools.ldm.services.mega_index.get_perforce_path_service") as mock_svc:
        mock_svc.return_value.get_all_resolved.return_value = mock_paths
        idx = MegaIndex()
        idx.build()

    # Assert all 35 dicts non-empty
    assert len(idx.knowledge_by_strkey) > 0, "D1 empty"
    assert len(idx.character_by_strkey) > 0, "D2 empty"
    # ... etc for all 35
    print(f"PASS: All 35 dicts populated. Build time: {idx._build_time:.2f}s")
```

---

## 5. Cross-Reference Chain Map

This is the critical part. Every arrow must be valid in the generated data:

```
KNOWLEDGE (D1)
  .strkey ──────────── Character.knowledge_key (D2)
  .strkey ──────────── Item.knowledge_key (D3)
  .strkey ──────────── Region.knowledge_key (D4, via FactionNode)
  .strkey ──────────── Skill.learn_knowledge_key (D7)
  .ui_texture_name ──→ DDS file stem (D9) ──→ C1 (strkey_to_image_path)
  .name (Korean) ────→ StrOrigin match ──→ StringId (R6, C6, C7)

EXPORT XML (D11)
  .SoundEventName ──→ WEM file stem (D10) ──→ C2, C3
  .StringId ────────→ languagedata_KOR StrOrigin (D12) ──→ C4
  .StringId ────────→ languagedata_ENG Str (D13) ──→ C5

EXPORT .LOC.XML (D17, D18)
  .filename stem ───→ entity.source_file stem (C6/C7 bridge)
  .StringId ────────→ matches D12 StringId
  .StrOrigin ───────→ matches D12 StrOrigin (for ordered_export_index)

FACTION hierarchy (D5, D6)
  FactionGroup.strkey → Faction.group_strkey
  Faction.strkey → FactionNode.parent (via XML nesting)
```

---

## 6. Generator Script Design

### 6A. Central Registry (Single Source of Truth)

```python
# All entities defined once with all cross-reference keys
KNOWLEDGE_ENTRIES = [
    KnowledgeDef(
        strkey="Knowledge_ElderVaron",
        name_kr="장로 바론",
        desc_kr="고대 봉인의 수호자이자...",
        ui_texture="character_varon",
        group_key="KnowledgeGroup_Character",
    ),
    # ... 30 total (reuse existing showcase data)
]

CHARACTERS = [
    CharacterDef(
        strkey="Character_ElderVaron",
        name_kr="장로 바론",
        name_eng="Elder Varon",
        desc_kr="봉인된 도서관의 수호자인...",
        desc_eng="Guardian of the Sealed Library...",
        knowledge_key="Knowledge_ElderVaron",  # -> KNOWLEDGE_ENTRIES
        source_file="characterinfo_showcase.staticinfo.xml",
    ),
    # ... 5 total
]

AUDIO_EVENTS = [
    AudioDef(
        event_name="play_varon_greeting_01",
        stringid="DLG_VARON_GREETING_01",
        strorigin_kr="봉인된 도서관에 오신 것을 환영합니다.",
        str_eng="Welcome to the Sealed Library.",
        export_subdir="Dialog/QuestDialog",
        export_file="questdialog_showcase",
    ),
    # ... 10 total
]
```

### 6B. Generator Functions

```python
def generate_staticinfo_xmls(root: Path, registry: Registry) -> None:
    """Generate all StaticInfo XMLs from registry."""
    # knowledge, character, item, faction, skill, gimmick

def generate_loc_xmls(root: Path, registry: Registry) -> None:
    """Generate languagedata_KOR.xml and languagedata_ENG.xml."""
    # Collects ALL StringIds across all entity types + audio events

def generate_export_xmls(root: Path, registry: Registry) -> None:
    """Generate export event XMLs + .loc.xml files."""
    # Groups by export_subdir, creates matching .xml + .loc.xml pairs

def generate_dds_stubs(root: Path, registry: Registry) -> None:
    """Generate empty .dds files for all UITextureName values."""

def generate_wem_stubs(root: Path, registry: Registry) -> None:
    """Generate empty .wem files for all audio event names."""

def generate_devmemo_xml(root: Path, registry: Registry) -> None:
    """Add DevMemo attributes to StaticInfo XMLs or generate separate file."""

def validate(root: Path) -> None:
    """Run MegaIndex.build() and assert all 35 dicts non-empty."""
```

### 6C. StringId Convention

To make the C6/C7 bridge work (entity StrKey -> StringId), we need StringIds for every entity's Korean name and description. Convention:

| Entity Type | Name StringId | Desc StringId |
|-------------|--------------|---------------|
| Character | `CHAR_{KEY}_NAME` | `CHAR_{KEY}_DESC` |
| Item | `ITEM_{KEY}_NAME` | `ITEM_{KEY}_DESC` |
| Region | `REGION_{KEY}_NAME` | `REGION_{KEY}_DESC` |
| Skill | `SKILL_{KEY}_NAME` | `SKILL_{KEY}_DESC` |
| Gimmick | `GIMMICK_{KEY}_NAME` | `GIMMICK_{KEY}_DESC` |
| Knowledge | `KNOW_{KEY}_NAME` | `KNOW_{KEY}_DESC` |
| Dialog | `DLG_{CHAR}_{NUM}` | (no desc) |

### 6D. Export File Naming for C6/C7 Bridge

The bridge works via `_get_export_key(entity.source_file)` matching `_get_export_key(loc_xml.name)`:

| Entity source_file | Export key | Needed .loc.xml |
|-------------------|------------|-----------------|
| `characterinfo_showcase.staticinfo.xml` | `characterinfo_showcase.staticinfo` | `export__/Character/characterinfo_showcase.staticinfo.loc.xml` |
| `iteminfo_showcase.staticinfo.xml` | `iteminfo_showcase.staticinfo` | `export__/Item/iteminfo_showcase.staticinfo.loc.xml` |
| `skillinfo_showcase.staticinfo.xml` | `skillinfo_showcase.staticinfo` | `export__/Skill/skillinfo_showcase.staticinfo.loc.xml` |
| `gimmickinfo_showcase.staticinfo.xml` | `gimmickinfo_showcase.staticinfo` | `export__/Gimmick/gimmickinfo_showcase.staticinfo.loc.xml` |

Each `.loc.xml` must contain `<LocStr StringId="..." StrOrigin="..." />` for the Korean name+desc of entities in that source file.

---

## 7. Gimmick XML Format

MegaIndex expects this nesting (from `_parse_gimmick_info`, line 692-731):

```xml
<?xml version="1.0" encoding="utf-8"?>
<GimmickInfoList>
  <GimmickGroupInfo StrKey="GimmickGroup_Seal01" GimmickName="봉인 장치 1">
    <GimmickInfo StrKey="Gimmick_Seal01_Active" Desc="활성화된 봉인 장치">
      <SealData Desc="이 봉인은 현자의 불꽃으로만 해제할 수 있습니다." />
    </GimmickInfo>
  </GimmickGroupInfo>
  <GimmickGroupInfo StrKey="GimmickGroup_Trap01" GimmickName="함정 장치 1">
    <GimmickInfo StrKey="Gimmick_Trap01_Poison" GimmickName="독 함정" Desc="독을 뿌리는 함정" />
  </GimmickGroupInfo>
  <!-- Group without inner GimmickInfo (stored as group itself) -->
  <GimmickGroupInfo StrKey="GimmickGroup_Door01" GimmickName="봉인된 문" />
</GimmickInfoList>
```

This covers all three code paths in `_parse_gimmick_info()`:
1. GimmickGroupInfo > GimmickInfo > SealData (full nesting)
2. GimmickGroupInfo > GimmickInfo (no SealData)
3. GimmickGroupInfo alone (no inner GimmickInfo)

---

## 8. FactionGroup/Faction Hierarchy

The current `FactionInfo.staticinfo.xml` only has flat `<FactionNode>` elements (no `<FactionGroup>` or `<Faction>` wrappers). For D5 and D6, we need proper nesting:

```xml
<?xml version="1.0" encoding="utf-8"?>
<FactionInfoList>
  <FactionGroup StrKey="FactionGroup_World" GroupName="세계" KnowledgeKey="">
    <Faction StrKey="Faction_SageOrder" Name="현자의 결사" KnowledgeKey="Knowledge_SageOrder">
      <FactionNode StrKey="Region_SealedLibrary" KnowledgeKey="Knowledge_SealedLibrary"
                   Type="Main" WorldPosition="350,0,150" />
      <FactionNode StrKey="Region_SageTower" KnowledgeKey="Knowledge_SageTower"
                   Type="Main" WorldPosition="400,0,450" />
      <!-- ... more nodes ... -->
    </Faction>
    <Faction StrKey="Faction_DarkCult" Name="어둠의 교단" KnowledgeKey="Knowledge_DarkCult">
      <FactionNode StrKey="Region_DarkCultHQ" KnowledgeKey="Knowledge_DarkCultHQ"
                   Type="Fortress" WorldPosition="650,0,200" />
      <!-- ... more nodes ... -->
    </Faction>
  </FactionGroup>
</FactionInfoList>
```

This populates: D5 (2 factions), D6 (1 faction group), and D4 (all regions with parent faction context).

**Important:** `RegionInfo` elements with `DisplayName` are also needed for D16:
```xml
<RegionInfo KnowledgeKey="Knowledge_SealedLibrary" DisplayName="봉인된 도서관 (1층)" />
```

---

## 9. DevMemo for D19

The broad scan in `_scan_devmemo()` looks for ANY element with `StrKey` + `DevMemo` or `DevComment` attributes across ALL StaticInfo XMLs. Easiest approach: add `DevMemo` attributes to existing entities:

```xml
<CharacterInfo StrKey="Character_ElderVaron" CharacterName="장로 바론"
               DevMemo="[NPC] 메인 퀘스트 NPC, 봉인 도서관 수호자" ... />
```

Or create a separate file with generic `StrKey` + `DevMemo` elements.

---

## 10. Implementation Plan

### Step 1: Define registry (~100 lines)
- Reuse all 5 characters, 5 items, 14 regions, 3 skills from existing XMLs
- Add 3 gimmicks, 2 factions, 1 faction group
- Define 10 audio events (2 per character)
- Compute all StringIds (name+desc per entity = ~80 StringIds + 10 audio = ~90 total)

### Step 2: Generate StaticInfo XMLs (~100 lines)
- Regenerate all from registry (replaces hand-written files)
- Add FactionGroup/Faction wrappers to factioninfo
- Add gimmickinfo
- Add DevMemo attributes for D19

### Step 3: Generate localization XMLs (~60 lines)
- `languagedata_KOR.xml` with all StringIds + StrOrigin
- `languagedata_ENG.xml` with all StringIds + Str (English translations)

### Step 4: Generate export XMLs (~80 lines)
- Event mapping XMLs (SoundEventName + StringId)
- Export .loc.xml files (matching entity source_file stems)
- Organize by export subdirectories

### Step 5: Generate binary stubs (~20 lines)
- `.dds` files in `texture/image/` (one per UITextureName)
- `.wem` files in `sound/windows/English(US)/` (one per audio event)

### Step 6: Validation function (~40 lines)
- Run MegaIndex.build()
- Assert each of the 35 dicts has entries
- Print summary with counts

**Total estimated size:** 400-500 lines of Python.

---

## 11. Pitfalls to Avoid

### P1: StrOrigin normalization mismatch
**What goes wrong:** C6/C7 bridge fails because entity Korean text != languagedata StrOrigin after normalization.
**Prevention:** Use EXACTLY the same Korean text in both StaticInfo Name/Desc and languagedata StrOrigin. Copy from registry, never hand-type twice.

### P2: Export filename key mismatch
**What goes wrong:** D17/D18 don't match entity source_file because `_get_export_key()` strips `.xml` and `.loc` differently.
**Prevention:** Test with `_get_export_key(entity.source_file)` == `_get_export_key(loc_xml.name)`. The function is: `filename.lower().replace(".xml", "").replace(".loc", "")`.

### P3: Case sensitivity in event names
**What goes wrong:** WEM filename stem is lowercased, but export XML SoundEventName might be mixed case.
**Prevention:** MegaIndex lowercases event names everywhere (`event_lower = event_name.lower()`). Generate WEM files with lowercase stems, export XMLs can use any case.

### P4: Missing KnowledgeGroupInfo for D15
**What goes wrong:** D15 (knowledge_group_hierarchy) stays empty.
**Prevention:** Add `<KnowledgeGroupInfo>` wrapper elements in knowledgeinfo XML with `StrKey` and `GroupName` attributes, containing child `<KnowledgeInfo>` elements.

### P5: FactionNode without Faction parent
**What goes wrong:** D5 stays empty, D4 regions have no `parent_strkey` for faction context.
**Prevention:** Wrap FactionNodes inside `<Faction>` elements inside `<FactionGroup>` elements.

### P6: Empty .wem files on Windows
**What goes wrong:** On some systems, `Path.write_bytes(b"")` may not create the file.
**Prevention:** Use `wem_path.touch()` as fallback, or write a single null byte.

---

## 12. Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Folder structure | HIGH | Directly traced from mega_index.py build() method |
| XML attribute names | HIGH | Directly traced from each parser method |
| Cross-reference chains | HIGH | Traced from C6/C7 builder code |
| Binary stub approach | HIGH | Confirmed DDS/WEM scanners only read filenames |
| StringId convention | MEDIUM | Convention is our choice, but bridge logic verified |
| Entity counts | MEDIUM | Subjective "feels populated" assessment |

---

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/services/mega_index.py` -- all 35 dict definitions, 7-phase build pipeline, all parser methods
- `server/tools/ldm/services/mega_index_schemas.py` -- all 10 entity dataclass definitions
- `.planning/research/MEGAINDEX_DESIGN.md` -- dict inventory, cross-reference chain, StringId<->StrKey bridge
- `tests/fixtures/mock_gamedata/` -- existing fixture inventory and XML formats
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/core/linkage.py` -- AudioIndex WEM scan pattern

### Secondary (MEDIUM confidence)
- `server/tools/ldm/services/perforce_path_service.py` -- folder path templates
