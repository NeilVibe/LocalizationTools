# Phase 15: Mock Gamedata Universe - Research

**Researched:** 2026-03-15
**Domain:** XML mock data generation, cross-reference integrity, binary asset stubs
**Confidence:** HIGH

## Summary

Phase 15 is a pure data generation phase -- no new code features, services, or UI. The goal is to produce a comprehensive `MockGameData/` folder tree with realistic XML files that match the exact patterns consumed by the existing XMLParsingEngine, TranslatorMergeService, GameDevMergeService, and ExportService. Every subsequent v3.0 phase (16-21) depends on this data existing.

The project already has a small proof-of-concept mock dataset at `tests/fixtures/mock_gamedata/` (5 characters, 5 items, 10 knowledge entries, 8 LocStr entries, 10 DDS files, 5 WEM files) with passing integration tests in `tests/integration/test_mock_gamedata_pipeline.py`. Phase 15 scales this up to 100+ items, 30+ characters, 10+ regions, 50+ skills, 20+ gimmicks while adding missing entity types (SkillInfo, SkillTreeInfo, GimmickGroupInfo, FactionNode hierarchy, EXPORT .loc.xml indexes, NodeWaypointInfo) and ensuring round-trip validation.

**Primary recommendation:** Write a Python generator script (`tests/fixtures/mock_gamedata/generate_mock_universe.py`) that programmatically creates all XML, DDS, and WEM files with deterministic seeds, ensuring cross-reference integrity by construction. Do NOT hand-write 100+ XML entries.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MOCK-01 | Realistic mock folder structure matching real staticinfo XML patterns | Folder structure documented from QACompiler generators -- exact paths, filename conventions, and nesting verified |
| MOCK-02 | Cross-reference chains between entities | All 6 cross-reference chains documented with exact attribute names from generator source code |
| MOCK-03 | DDS image and WEM audio file references per entity | Existing 1152-byte DDS stubs and ~22KB WEM stubs provide templates; UITextureName linkage pattern documented |
| MOCK-04 | Language data files with LocStr entries matching mock Korean source text | LocStr format verified from existing fixtures; Korean text patterns from knowledgeinfo_sample.xml provide templates |
| MOCK-05 | EXPORT index files (.loc.xml) with StringID mappings | EXPORT index parsing pattern documented from generators/base.py build_export_indexes() |
| MOCK-06 | Region WorldPosition coordinates and NodeWaypointInfo route data | FactionNode.WorldPosition attribute and NodeWaypointInfo structure documented from region generator |
| MOCK-07 | Sufficient volume (100+ items, 30+ characters, 10+ regions, 50+ skills, 20+ gimmicks) | Programmatic generator with deterministic seeds; volume targets validated against grid performance needs |
| MOCK-08 | Round-trip validation (parse -> merge -> export -> re-parse) | Existing XMLParsingEngine, TranslatorMerge, GameDevMerge, ExportService provide the pipeline to validate against |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | existing | XML generation and validation | Already used by XMLParsingEngine, all generators |
| Python 3.x | existing | Generator script | Server runtime |
| pytest | existing | Round-trip validation tests | Already used in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| struct | stdlib | DDS/WEM binary header generation | Creating minimal valid binary stubs |
| random (seeded) | stdlib | Deterministic data generation | Reproducible mock data |
| pathlib | stdlib | File/folder creation | Directory tree generation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python generator script | Hand-written XML files | Generator ensures cross-ref integrity by construction; hand-written XML at 100+ items scale is error-prone |
| Minimal DDS stubs (1152 bytes) | Real DDS images | Stubs already pass header validation; real images waste space and add nothing for data pipeline testing |

**Installation:**
No new dependencies required. All tools already in the project.

## Architecture Patterns

### Recommended Folder Structure (MockGameData)
```
tests/fixtures/mock_gamedata/
├── generate_mock_universe.py          # Generator script (deterministic, re-runnable)
├── StaticInfo/
│   ├── iteminfo/
│   │   ├── iteminfo_weapon.staticinfo.xml
│   │   ├── iteminfo_armor.staticinfo.xml
│   │   ├── iteminfo_consumable.staticinfo.xml
│   │   └── iteminfo_accessory.staticinfo.xml
│   ├── characterinfo/
│   │   ├── characterinfo_npc.staticinfo.xml
│   │   ├── characterinfo_npc_shop.staticinfo.xml
│   │   └── characterinfo_monster.staticinfo.xml
│   ├── skillinfo/
│   │   ├── skillinfo_pc.staticinfo.xml
│   │   └── SkillTreeInfo.staticinfo.xml
│   ├── knowledgeinfo/
│   │   ├── knowledgeinfo_character.staticinfo.xml
│   │   ├── knowledgeinfo_item.staticinfo.xml
│   │   ├── knowledgeinfo_region.staticinfo.xml
│   │   └── knowledgeinfo_contents.staticinfo.xml
│   ├── factioninfo/
│   │   ├── FactionInfo.staticinfo.xml
│   │   └── NodeWaypointInfo/
│   │       └── NodeWaypointInfo.staticinfo.xml
│   └── gimmickinfo/
│       ├── Background/
│       │   └── GimmickInfo_Background_Door.staticinfo.xml
│       ├── Item/
│       │   └── GimmickInfo_Item_Chest.staticinfo.xml
│       └── Puzzle/
│           └── GimmickInfo_Puzzle_Seal.staticinfo.xml
├── stringtable/
│   ├── export__/
│   │   └── System/
│   │       ├── iteminfo_weapon.loc.xml
│   │       ├── characterinfo_npc.loc.xml
│   │       ├── skillinfo_pc.loc.xml
│   │       └── ... (one per staticinfo file)
│   └── loc/
│       ├── languagedata_kor.xml
│       ├── languagedata_eng.xml
│       └── languagedata_fre.xml
├── textures/
│   └── *.dds                          # Minimal valid DDS stubs
├── audio/
│   └── *.wem                          # Minimal valid WEM/RIFF stubs
└── export/
    └── event_mapping.xml              # SoundEventName -> StringId
```

### Pattern 1: Cross-Reference Integrity by Construction
**What:** The generator script builds all entities in dependency order, maintaining lookup tables as it goes. Each entity's cross-reference keys are assigned from the same pool, guaranteeing every `KnowledgeKey`, `LearnKnowledgeKey`, and `StrKey` reference resolves.
**When to use:** Always -- this is the core correctness guarantee.
**Example:**
```python
# Build order: Knowledge first, then entities that reference it
knowledge_entries = generate_knowledge(count=80)  # characters + items + regions + skills
knowledge_map = {k.strkey: k for k in knowledge_entries}

# Characters reference knowledge via KnowledgeKey
characters = generate_characters(count=30, knowledge_map=knowledge_map)

# Skills reference knowledge via LearnKnowledgeKey (NOT KnowledgeKey!)
skills = generate_skills(count=50, knowledge_map=knowledge_map)

# SkillTree references skills via StrKey (NOT numeric Key!)
skill_trees = generate_skill_trees(skills=skills)
```

### Pattern 2: XML Attribute Format (from real generators)
**What:** XML elements use specific attribute naming conventions that MUST be matched exactly.
**When to use:** Every XML file generated.
**Example:**
```xml
<!-- ItemInfo: Key (numeric), StrKey (string ID), ItemName, ItemDesc, KnowledgeKey -->
<ItemInfo Key="10001" StrKey="STR_ITEM_IRON_SWORD" ItemName="Iron Sword"
          ItemDesc="A sturdy iron sword." KnowledgeKey="KNOW_ITEM_IRON_SWORD" />

<!-- CharacterInfo: StrKey, CharacterName, KnowledgeKey, Gender, Age, Job, Race -->
<CharacterInfo StrKey="STR_CHAR_VARON" CharacterName="Varon"
               KnowledgeKey="KNOW_CHAR_VARON" Gender="Male" Age="45" Job="Elder" Race="Human" />

<!-- SkillInfo: Key (numeric), StrKey, SkillName, SkillDesc, LearnKnowledgeKey (NOT KnowledgeKey!) -->
<SkillInfo Key="15001" StrKey="Skill_Wrestle_AirBodySlam" SkillName="Air Body Slam"
           SkillDesc="Leap into the air..." LearnKnowledgeKey="KNOW_SKILL_AIR_SLAM" />

<!-- SkillTreeInfo: SkillNode uses SkillKey = SkillInfo.StrKey (NOT numeric Key!) -->
<SkillTreeInfo Key="1" StrKey="TREE_WARRIOR" CharacterKey="CHAR_WARRIOR" UIPageName="전사 스킬">
  <SkillNode NodeId="1" SkillKey="Skill_Wrestle_AirBodySlam" ParentNodeId="0"
             UIPositionXY="0,0" />
</SkillTreeInfo>

<!-- FactionNode: StrKey, KnowledgeKey, WorldPosition, nested children -->
<FactionGroup GroupName="서부 지역" StrKey="FGRP_WEST">
  <Faction Name="검은별 세력" StrKey="FAC_BLACKSTAR" KnowledgeKey="KNOW_FAC_BLACKSTAR">
    <FactionNode StrKey="FNODE_VILLAGE" KnowledgeKey="KNOW_REGION_BLACKSTAR"
                 WorldPosition="1250.5,0,3400.2" Type="Main">
      <FactionNode StrKey="FNODE_MARKET" KnowledgeKey="KNOW_REGION_MARKET"
                   WorldPosition="1280.0,0,3420.0" Type="Sub" />
    </FactionNode>
  </Faction>
</FactionGroup>

<!-- GimmickGroupInfo > GimmickInfo: StrKey, GimmickName, SealData child -->
<GimmickGroupInfo StrKey="GGRP_DOOR_001" GimmickName="Ancient Door">
  <GimmickInfo StrKey="GIMM_DOOR_001" GimmickName="봉인된 문">
    <SealData Desc="고대 봉인이 걸려 있다.&lt;br/&gt;열쇠가 필요하다." />
  </GimmickInfo>
</GimmickGroupInfo>

<!-- KnowledgeInfo: StrKey, Name, Desc, UITextureName, nested KnowledgeList -->
<KnowledgeInfo StrKey="KNOW_CHAR_VARON" Name="장로 바론"
               Desc="검은별 마을의 장로.&lt;br/&gt;역병에 맞서 싸우며 마을의 마지막 희망이 되었다."
               UITextureName="character_varon" />

<!-- NodeWaypointInfo: FromNodeKey, ToNodeKey, WorldPosition children -->
<NodeWaypointInfo FromNodeKey="FNODE_VILLAGE" ToNodeKey="FNODE_MARKET">
  <WorldPosition X="1260.0" Y="0" Z="3410.0" />
  <WorldPosition X="1275.0" Y="0" Z="3415.0" />
</NodeWaypointInfo>

<!-- LocStr: StringId, StrOrigin (Korean), Str (translation), DescOrigin, Desc -->
<LocStr StringId="SID_VARON_001" StrOrigin="검은별 마을의 장로."
        Str="The elder of Blackstar Village." DescOrigin="" Desc="" />

<!-- EXPORT .loc.xml: Same LocStr format, one file per staticinfo source -->
<!-- File: export__/System/characterinfo_npc.loc.xml -->
<LocStrList>
  <LocStr StringId="SID_CHAR_VARON_NAME" StrOrigin="바론" Str="" />
</LocStrList>
```

### Pattern 3: Korean Text with br-tags
**What:** Korean descriptions MUST use `&lt;br/&gt;` (escaped) in XML attributes for multiline content. This is the ONLY correct format.
**When to use:** All Description/Desc attributes that span multiple lines.
**Example:**
```xml
<!-- In XML source (attribute value): -->
Desc="첫 번째 줄&lt;br/&gt;두 번째 줄"
<!-- After lxml parse, attribute value contains literal: -->
<!-- 첫 번째 줄<br/>두 번째 줄 -->
```

### Pattern 4: Minimal Valid Binary Stubs
**What:** DDS and WEM files need valid magic bytes but minimal data.
**When to use:** All texture and audio mock files.
**Example:**
```python
# DDS: 128-byte header + 1024 bytes pixel data = 1152 bytes total
# Magic: b"DDS " + 124 bytes DDS_HEADER (dwSize=124, flags, width=64, height=64, etc.)
# Existing stubs in project are 1152 bytes -- copy this exact pattern

# WEM: RIFF/WAVE header + minimal audio data = ~22KB
# Magic: b"RIFF" + size + b"WAVE" + fmt chunk + data chunk
# Existing stubs in project are ~22094 bytes -- copy this exact pattern
```

### Anti-Patterns to Avoid
- **Hand-writing XML at scale:** With 100+ items, hand-written XML will have cross-reference bugs. Use a generator.
- **Random non-deterministic data:** Mock data should be reproducible. Always seed the random generator.
- **Inventing new attribute names:** Copy EXACTLY from real QACompiler generators. `LearnKnowledgeKey` not `KnowledgeKey` for skills. `SkillKey = StrKey` not numeric `Key` in SkillTree nodes.
- **Flat folder structure:** Real gamedata has nested folders (`gimmickinfo/Background/`, `gimmickinfo/Item/`). Mock must match.
- **Forgetting EXPORT index files:** The EXPORT .loc.xml files are separate from languagedata and map StringIDs to source files. Phase 16 (Category Clustering) needs these.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML serialization | String concatenation | lxml.etree.tostring() with xml_declaration=True | Handles encoding, escaping, attribute order correctly |
| DDS file creation | Pixel-by-pixel image generation | Copy existing 1152-byte stub template | Only header validation matters, not visual content |
| WEM file creation | Audio synthesis | Copy existing ~22KB RIFF/WAVE stub template | Only header validation matters, not audio content |
| Korean text generation | Manual writing of 200+ strings | Pre-built corpus of Korean game text patterns | Realistic variety without needing native speaker for each string |
| Cross-reference validation | Manual inspection | Programmatic assertion in generator script | 100% coverage, zero human error |

**Key insight:** This phase is about DATA INTEGRITY, not creativity. The generator script must guarantee that every cross-reference resolves, every StringID maps to a LocStr entry, and every UITextureName has a matching DDS file.

## Common Pitfalls

### Pitfall 1: SkillTree uses StrKey, not numeric Key
**What goes wrong:** SkillNode.SkillKey references SkillInfo.StrKey (e.g., "Skill_Wrestle_AirBodySlam"), NOT the numeric Key (e.g., "15004"). Using numeric keys breaks the entire skill tree resolution.
**Why it happens:** Both Key and StrKey exist on SkillInfo; naive assumption is Key is the join field.
**How to avoid:** The generator must set SkillNode.SkillKey = corresponding SkillInfo.StrKey.
**Warning signs:** Skill tree nodes show "no skill found" when loaded in the Game Dev grid.

### Pitfall 2: LearnKnowledgeKey vs KnowledgeKey
**What goes wrong:** Skills use `LearnKnowledgeKey` (not `KnowledgeKey`) to reference knowledge entries. Characters use `KnowledgeKey`. Mixing them up breaks cross-reference chains.
**Why it happens:** Inconsistent naming across entity types in the game's XML schema.
**How to avoid:** Follow the exact attribute names from each QACompiler generator.
**Warning signs:** Knowledge data appears for characters but not skills.

### Pitfall 3: br-tag encoding in XML attributes
**What goes wrong:** Using literal `<br/>` in XML attribute values causes parse errors. Using `&#10;` (newline entity) breaks the downstream pipeline.
**Why it happens:** XML attribute values cannot contain raw `<` characters.
**How to avoid:** Always use `&lt;br/&gt;` in XML attribute values. When lxml parses this, it becomes literal `<br/>` in the string -- which is the correct in-memory representation.
**Warning signs:** XMLSyntaxError on parse, or `&#10;` appearing in the UI instead of line breaks.

### Pitfall 4: Case sensitivity in StrKey lookups
**What goes wrong:** Cross-reference lookups fail because one side uses "KNOW_char_varon" and the other uses "KNOW_CHAR_VARON".
**Why it happens:** QACompiler generators use `.lower()` for all key lookups but the XML stores mixed case.
**How to avoid:** Generate all StrKeys in UPPER_SNAKE_CASE consistently. The lookup code already handles case-insensitive matching via `.lower()`.
**Warning signs:** Cross-reference resolution returns empty for entries that clearly exist.

### Pitfall 5: Missing EXPORT index files
**What goes wrong:** Category clustering (Phase 16) cannot classify content because it depends on EXPORT .loc.xml files to map StringIDs back to source files.
**Why it happens:** EXPORT files are easy to forget -- they're separate from the main languagedata files.
**How to avoid:** Generate one .loc.xml file per staticinfo source file in `stringtable/export__/System/`.
**Warning signs:** Category column shows "Unknown" for all entries.

### Pitfall 6: Insufficient WorldPosition variety
**What goes wrong:** Map visualization (Phase 20) shows all nodes stacked on top of each other because positions are too similar.
**Why it happens:** Generating positions without spatial planning.
**How to avoid:** Spread WorldPosition coordinates across a meaningful 2D space (e.g., X: 500-5000, Z: 500-5000) with at least 100-unit separation between nodes.
**Warning signs:** Map shows a single cluster instead of a distributed world.

## Code Examples

### Generator Script Structure
```python
#!/usr/bin/env python3
"""Generate the Mock Gamedata Universe for LocaNext v3.0 testing."""
from __future__ import annotations
import random
from pathlib import Path
from lxml import etree

SEED = 42
OUTPUT_DIR = Path(__file__).parent

# Korean name/desc corpus (pre-built, realistic game text)
KOREAN_NAMES = {
    "characters": ["장로 바론", "전사 키라", "마법사 드라크마르", ...],
    "items": ["검은별의 검", "달빛 부적", "잿빛 역병 치료제", ...],
    "regions": ["검은별 마을", "광명의 형제회 전초기지", ...],
    "skills": ["공중 바디슬램", "번개 베기", ...],
}

def generate_knowledge(entities: dict) -> list[dict]:
    """Generate KnowledgeInfo entries for all entity types."""
    entries = []
    for entity in entities:
        entries.append({
            "strkey": f"KNOW_{entity['type']}_{entity['id']}",
            "name": entity["kr_name"],
            "desc": entity["kr_desc"],
            "ui_texture": entity["texture_name"],
        })
    return entries

def write_xml(root_tag: str, elements: list, path: Path):
    """Write XML file with proper declaration and encoding."""
    root = etree.Element(root_tag)
    for el_data in elements:
        tag = el_data.pop("_tag")
        el = etree.SubElement(root, tag)
        for k, v in el_data.items():
            if not k.startswith("_"):
                el.set(k, str(v))
        # Handle child elements
        for child in el_data.get("_children", []):
            child_tag = child.pop("_tag")
            child_el = etree.SubElement(el, child_tag)
            for ck, cv in child.items():
                if not ck.startswith("_"):
                    child_el.set(ck, str(cv))

    path.parent.mkdir(parents=True, exist_ok=True)
    tree = etree.ElementTree(root)
    tree.write(str(path), encoding="utf-8", xml_declaration=True, pretty_print=True)
```

### DDS Stub Generation
```python
import struct

def create_dds_stub(path: Path) -> None:
    """Create minimal valid DDS file (1152 bytes)."""
    # Copy from existing template
    template = Path(__file__).parent / "textures" / "character_varon.dds"
    if template.exists():
        shutil.copy2(template, path)
    else:
        # Fallback: generate from scratch
        header = b"DDS "  # Magic
        header += struct.pack("<I", 124)  # dwSize
        header += struct.pack("<I", 0x1007)  # dwFlags (CAPS|HEIGHT|WIDTH|PIXELFORMAT)
        header += struct.pack("<I", 64)  # dwHeight
        header += struct.pack("<I", 64)  # dwWidth
        header += struct.pack("<I", 256)  # dwPitchOrLinearSize
        header += b"\x00" * (124 - len(header) + 4)  # Pad to 128 bytes
        pixel_data = b"\x00" * 1024  # Minimal pixel data
        path.write_bytes(header + pixel_data)
```

### Round-Trip Validation Test
```python
def test_round_trip_parse_merge_export_reparse():
    """MOCK-08: Parse -> merge -> export -> re-parse produces consistent results."""
    from server.tools.ldm.services.xml_parsing import XMLParsingEngine

    engine = XMLParsingEngine()
    mock_dir = Path("tests/fixtures/mock_gamedata")

    # Step 1: Parse all XML files
    parsed = {}
    for xml_path in mock_dir.rglob("*.xml"):
        root = engine.parse_file(xml_path)
        assert root is not None, f"Failed to parse: {xml_path}"
        parsed[xml_path.name] = root

    # Step 2: Serialize back to string
    for name, root in parsed.items():
        xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True)
        # Step 3: Re-parse
        reparsed = etree.fromstring(xml_bytes)
        # Step 4: Compare element counts
        orig_count = len(list(root.iter()))
        new_count = len(list(reparsed.iter()))
        assert orig_count == new_count, f"Element count mismatch in {name}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Small hand-written fixtures (5-10 entries) | Programmatic generator with volume targets | Phase 15 (now) | Enables grid performance testing, realistic Codex browsing |
| Missing entity types (no skills, gimmicks, factions) | Full coverage of all 6 entity types | Phase 15 (now) | Every Game Dev feature has data to work with |
| No EXPORT index files | Full EXPORT .loc.xml generation | Phase 15 (now) | Enables Category Clustering (Phase 16) |

**Existing artifacts to preserve:**
- `tests/fixtures/mock_gamedata/` -- existing small fixtures should NOT be deleted; they are referenced by `tests/integration/test_mock_gamedata_pipeline.py`
- The new MockGameData universe is an EXPANSION, not a replacement. The generator should create new files alongside existing ones.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | tests/conftest.py |
| Quick run command | `cd /home/neil1988/LocalizationTools && python -m pytest tests/integration/test_mock_gamedata_pipeline.py -x -v` |
| Full suite command | `cd /home/neil1988/LocalizationTools && python -m pytest tests/ -x -v --timeout=60` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOCK-01 | Folder structure matches real staticinfo patterns | unit | `pytest tests/unit/test_mock_universe_structure.py -x` | No -- Wave 0 |
| MOCK-02 | Cross-reference chains resolve | integration | `pytest tests/integration/test_mock_crossref.py -x` | No -- Wave 0 |
| MOCK-03 | DDS/WEM files exist per entity with valid headers | unit | `pytest tests/unit/test_mock_media_stubs.py -x` | No -- Wave 0 |
| MOCK-04 | Language data files load with Korean LocStr entries | integration | `pytest tests/integration/test_mock_language_data.py -x` | No -- Wave 0 |
| MOCK-05 | EXPORT .loc.xml files have correct StringID mappings | integration | `pytest tests/integration/test_mock_export_index.py -x` | No -- Wave 0 |
| MOCK-06 | WorldPosition coordinates and NodeWaypointInfo routes | unit | `pytest tests/unit/test_mock_map_data.py -x` | No -- Wave 0 |
| MOCK-07 | Volume targets met (100+ items, 30+ chars, etc.) | unit | `pytest tests/unit/test_mock_volume.py -x` | No -- Wave 0 |
| MOCK-08 | Round-trip validation passes | integration | `pytest tests/integration/test_mock_roundtrip.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/test_mock_universe_structure.py tests/unit/test_mock_volume.py -x -v`
- **Per wave merge:** `python -m pytest tests/integration/test_mock_gamedata_pipeline.py tests/integration/test_mock_crossref.py tests/integration/test_mock_roundtrip.py -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_mock_universe_structure.py` -- covers MOCK-01
- [ ] `tests/integration/test_mock_crossref.py` -- covers MOCK-02
- [ ] `tests/unit/test_mock_media_stubs.py` -- covers MOCK-03
- [ ] `tests/integration/test_mock_language_data.py` -- covers MOCK-04
- [ ] `tests/integration/test_mock_export_index.py` -- covers MOCK-05
- [ ] `tests/unit/test_mock_map_data.py` -- covers MOCK-06
- [ ] `tests/unit/test_mock_volume.py` -- covers MOCK-07
- [ ] `tests/integration/test_mock_roundtrip.py` -- covers MOCK-08

## Cross-Reference Chain Reference

These are the 6 cross-reference chains that MUST be valid in the mock data:

| Chain | Source Attribute | Target Attribute | Notes |
|-------|-----------------|------------------|-------|
| Item -> Knowledge | ItemInfo.KnowledgeKey | KnowledgeInfo.StrKey | Standard pattern |
| Character -> Knowledge | CharacterInfo.KnowledgeKey | KnowledgeInfo.StrKey | Standard pattern |
| Skill -> Knowledge | SkillInfo.LearnKnowledgeKey | KnowledgeInfo.StrKey | NOT KnowledgeKey! |
| SkillTree -> Skill | SkillNode.SkillKey | SkillInfo.StrKey | NOT numeric Key! |
| FactionNode -> Knowledge | FactionNode.KnowledgeKey | KnowledgeInfo.StrKey | For display name + desc |
| Entity -> Texture | KnowledgeInfo.UITextureName | DDS filename (stem) | Case-insensitive match |

## Volume Targets

| Entity Type | Count | Files | Notes |
|-------------|-------|-------|-------|
| Items | 120+ | 4 files (weapon/armor/consumable/accessory) | With ItemGroupInfo hierarchy |
| Characters | 35+ | 3 files (npc/npc_shop/monster) | With inline Knowledge children |
| Skills | 55+ | 1 file (skillinfo_pc) | With SkillDesc and LearnKnowledgeKey |
| SkillTrees | 5+ | 1 file (SkillTreeInfo) | With SkillNode children (UIPositionXY) |
| Knowledge | 80+ | 4 files (by entity type) | Names in Korean, descriptions with br-tags |
| Regions/Factions | 12+ | 1 FactionInfo + 1 NodeWaypointInfo | With WorldPosition coordinates |
| Gimmicks | 25+ | 3+ files across folders | With SealData.Desc |
| LocStr (Korean) | 300+ | 1 languagedata_kor.xml | All mock Korean text |
| LocStr (English) | 300+ | 1 languagedata_eng.xml | Translated equivalents |
| LocStr (French) | 300+ | 1 languagedata_fre.xml | Third language for testing |
| EXPORT indexes | N/A | 7+ .loc.xml files | One per staticinfo source file |
| DDS textures | 50+ | Per UITextureName | 1152-byte stubs |
| WEM audio | 15+ | Per voice-acted entity | ~22KB RIFF/WAVE stubs |

## Open Questions

1. **Should the generator preserve existing small fixtures?**
   - What we know: `tests/integration/test_mock_gamedata_pipeline.py` references the current small fixtures by exact path and count
   - What's unclear: Should new data live alongside or replace?
   - Recommendation: Generate into the SAME directory but ADD new files; update existing test counts. Keeps backward compat while expanding.

2. **Korean text corpus size**
   - What we know: Need 300+ unique Korean strings for LocStr entries
   - What's unclear: How much variety is needed vs. templated generation
   - Recommendation: Use a mix of ~30 hand-written Korean game text templates with parametric substitution (character/item/region names inserted). The existing fixture already has high-quality Korean text to use as templates.

## Sources

### Primary (HIGH confidence)
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/item.py` -- ItemInfo XML structure, InspectData patterns
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/character.py` -- CharacterInfo structure, Knowledge children
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/skill.py` -- SkillInfo/SkillTreeInfo structure, StrKey join
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/region.py` -- FactionNode/WorldPosition structure
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/gimmick.py` -- GimmickGroupInfo/GimmickInfo/SealData
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/knowledge.py` -- KnowledgeInfo nesting
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/base.py` -- EXPORT index parsing, StringIdConsumer
- `server/tools/ldm/services/xml_parsing.py` -- XMLParsingEngine, LocStr patterns
- `tests/integration/test_mock_gamedata_pipeline.py` -- Existing mock fixture tests
- `tests/fixtures/mock_gamedata/` -- Existing DDS/WEM stub templates

### Secondary (MEDIUM confidence)
- Existing mock fixture XML files (verified against generator patterns)

### Tertiary (LOW confidence)
- None -- all findings verified from source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, all patterns proven in codebase
- Architecture: HIGH -- folder structure and XML patterns directly from QACompiler generators
- Pitfalls: HIGH -- all documented from actual bugs found in QACompiler development (Viking memory)
- Cross-references: HIGH -- verified attribute names from each generator's scan function

**Research date:** 2026-03-15
**Valid until:** Indefinite (patterns are stable, based on game engine XML schema)
