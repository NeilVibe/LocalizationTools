# Phase 43: Mockdata Quality Audit + WOW Amplification - Research

**Researched:** 2026-03-18
**Domain:** Mock data quality, XML entity cross-references, localization showcase data
**Confidence:** HIGH

## Summary

Phase 43 is a data-only phase -- no new features, no UI changes, no backend logic changes. The work is entirely about creating, fixing, and enriching mock/showcase XML files, localization strings, TM entries, and region textures so that every page of the LocaNext demo tells a compelling, interconnected story.

The current mock data has a strong foundation: 5 characters with rich Korean descriptions, 10 map regions with polygons and routes, 10 knowledge entries, 30 localization strings across 3 formats, and 35 TM entries. However, there are critical gaps: no SkillInfo/RegionInfo/QuestInfo XML files exist (skills/regions/quests are referenced but never defined), 3 characters have incomplete cross-references, KnowledgeKey format is inconsistent between FactionNode (lowercase) and KnowledgeInfo (PascalCase), and knowledge entries only cover 10 of the ~25 needed entities.

**Primary recommendation:** Split work into 4 parallel workstreams: (1) XML entity creation + cross-ref fixes, (2) knowledge expansion + TM enrichment, (3) localization string additions, (4) region texture generation. All are independent data files with no shared-file conflicts.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fix RegionKey format mismatch: standardize to `Region_` prefix format
- Fix KnowledgeKey format mismatch: standardize ALL to PascalCase `Knowledge_` prefix
- Fix Knowledge CharacterKey: change from raw `Key` (CHAR_001) to StrKey format (Character_ElderVaron)
- Fill missing cross-refs: Grimjaw needs RegionKey+SkillKey, Lune needs ItemKey+SkillKey, Drakmar needs ItemKey+RegionKey
- All 5 characters must have COMPLETE cross-ref sets: ItemKey, RegionKey, SkillKey, FactionKey, KnowledgeKey
- Create `skillinfo_showcase.staticinfo.xml` with 3 skills: Skill_SacredFlame, Skill_ShadowStrike, Skill_HolyShield
- Create `regioninfo_showcase.staticinfo.xml` with 5 key regions
- Create `questinfo_showcase.staticinfo.xml` with 2-3 quests
- Each new entity needs: Key, StrKey, Korean name, Korean description with `<br/>`, UITextureName, cross-reference keys
- Add KnowledgeInfo entries for ALL 10 map regions (currently only SealedLibrary has one)
- Add KnowledgeInfo entries for remaining 4 items (SageStaff, ShadowDagger, PlagueCure, SealScroll)
- Generate 10 PNG textures for all map regions using nano-banana (Gemini image gen)
- Add waypoints to 5-6 routes (2-3 intermediate coordinates each) for curved paths
- Add 5+ TM entries with `<br/>` multi-line content
- Add 5+ dialogue-related TM entries, 2-3 near-duplicate fuzzy pairs (95%+ match)
- Expand TM from 35 to ~50 entries with "Quest" and "Dialogue" context tags
- Add 5-10 quest strings to showcase_items.loc.xml
- Add 2-3 strings with placeholder variables (`{0}`, `{CharacterName}`)
- Add 2-3 rows with empty/missing Korean translations in Excel to demo untranslated highlighting
- Standardize Grimjaw Korean name to "그림죠" across ALL files
- Target: at least 20 typed links across 5 relationship types in graph

### Claude's Discretion
- Exact number of new map nodes (3-5 range)
- Skill stat values (damage, cooldown, etc.)
- Quest reward details
- Region description prose style
- Whether to add SkillTreeInfo (nice-to-have, not required)
- Whether to add GimmickInfo/SealDataInfo (low priority, skip unless easy)

### Deferred Ideas (OUT OF SCOPE)
- SkillTreeInfo with parent-child hierarchy (nested tree demo) -- future phase
- GimmickInfo/SealDataInfo entity types -- low priority, skip
- SceneObjectData for map enrichment -- future phase
- Route type visual differentiation (road/river/mountain) in MapCanvas -- future phase
- Animated markers for special locations on map -- future phase
- Real multilingual stringtable (6 languages) -- future phase, current showcase is KR+ENG only
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MOCK-AUDIT-01 | Codex: All 5 characters have rich Korean descriptions with br formatting, unique AI portraits, and at least 3 cross-references each (item, skill, region, faction) | Cross-ref fix patterns documented below; character XML pattern established |
| MOCK-AUDIT-02 | Map: All 10 regions have Korean names, distinct terrain types, and route connections forming coherent geography | FactionInfo.xml already has 10 regions with Korean names; waypoints need curved coordinates |
| MOCK-AUDIT-03 | GameData Tree: XML files parse cleanly, all cross-refs resolve, hover preview works | ENTITY_TAG_MAP supports SkillInfo/RegionInfo/QuestInfo tags; codex_service cross-ref lookup uses StrKey |
| MOCK-AUDIT-04 | LanguageData Grid: All 3 files have 25+ strings, TM shows exact/fuzzy/semantic matches | Current counts: XLSX=27, TXT=28, XML=30 strings; TM=35 entries; expansion targets documented |
</phase_requirements>

## Standard Stack

This phase involves no new libraries. All work is data file creation/editing.

### Core Tools
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| lxml (existing) | XML parsing/validation | Already used by codex_service and gamedata services |
| xlsxwriter (existing) | Excel file generation | Already used by generate_showcase_data.py |
| nano-banana skill | Region texture generation via Gemini | Locked decision from CONTEXT.md |

### No Installation Needed
This phase creates/modifies data files only. No `npm install` or `pip install` required.

## Architecture Patterns

### Current Mock Data File Structure
```
tests/fixtures/mock_gamedata/
├── StaticInfo/
│   ├── characterinfo/
│   │   └── characterinfo_showcase.staticinfo.xml     # 5 characters (EXISTS)
│   ├── factioninfo/
│   │   ├── FactionInfo.staticinfo.xml                # 10 map regions (EXISTS)
│   │   └── NodeWaypointInfo/
│   │       └── NodeWaypointInfo.staticinfo.xml       # 13 routes (EXISTS)
│   ├── knowledgeinfo/
│   │   └── knowledgeinfo_showcase.staticinfo.xml     # 10 entries (EXISTS, expand to ~25)
│   ├── skillinfo/                                     # MISSING - CREATE
│   │   └── skillinfo_showcase.staticinfo.xml
│   ├── regioninfo/                                    # MISSING - CREATE
│   │   └── regioninfo_showcase.staticinfo.xml
│   └── questinfo/                                     # MISSING - CREATE
│       └── questinfo_showcase.staticinfo.xml
├── localization/
│   ├── showcase_items.loc.xml                         # 30 LocStr entries (expand)
│   ├── showcase_dialogue.txt                          # 28 dialogue lines (expand)
│   ├── showcase_ui_strings.xlsx                       # 27 rows (expand)
│   └── generate_showcase_data.py                      # Generator script (extend)
├── textures/
│   ├── character_*.png                                # 5 character portraits (EXISTS)
│   ├── item_*.png                                     # Multiple item textures (EXISTS)
│   ├── region_*.png                                   # Only 3 exist, need 10 more
│   └── skill_*.png                                    # 3 skill textures (EXISTS)
└── audio/
    └── *.wem                                          # Voice files (EXISTS)
```

### Pattern 1: XML Entity File Structure
**What:** All StaticInfo XML files follow a consistent pattern with root list element, entity elements with Key/StrKey/Korean attrs, and cross-ref attributes.
**When to use:** Creating new SkillInfo, RegionInfo, QuestInfo files.
**Example (from characterinfo_showcase):**
```xml
<?xml version='1.0' encoding='UTF-8'?>
<SkillInfoList>
  <SkillInfo Key="SKILL_001" StrKey="Skill_SacredFlame"
      SkillName="성스러운 불꽃"
      SkillDesc="현자의 결사에서 전승되는 신성한 화염 마법.&lt;br/&gt;어둠의 존재를 정화하는 힘을 지닌다."
      CooldownSec="8" Damage="450" ManaCost="30" RequireLevel="10"
      CharacterKey="Character_ElderVaron"
      UITextureName="skill_0001" />
</SkillInfoList>
```

### Pattern 2: Cross-Reference Key Format
**What:** All cross-ref keys use `{EntityType}_{EntityName}` PascalCase format.
**Critical:** The codex_service looks up cross-refs by matching the attribute value against registered entity StrKeys. If `CharacterInfo.SkillKey="Skill_SacredFlame"` but no entity has `StrKey="Skill_SacredFlame"`, the link resolves to nothing.

**Current format issues found:**
| File | Attribute | Current Value | Should Be |
|------|-----------|---------------|-----------|
| FactionInfo.xml | KnowledgeKey on all nodes | `knowledge_mist_forest` (lowercase) | `Knowledge_MistForest` (PascalCase) |
| KnowledgeInfo | CharacterKey on entries | `CHAR_001` (raw Key) | `Character_ElderVaron` (StrKey) |

### Pattern 3: Entity Registration in Codex
**What:** `ENTITY_TAG_MAP` defines which XML tags get registered as entities.
**Already supports:** CharacterInfo, ItemInfo, SkillInfo, GimmickGroupInfo, KnowledgeInfo, FactionNode
**Does NOT register:** QuestInfo, RegionInfo, SkillTreeInfo, SceneObjectData

**Implication:** New `QuestInfo` and `RegionInfo` XML elements will NOT appear in the Codex entity registry or relationship graph unless `ENTITY_TAG_MAP` is extended. However, they WILL appear in the GameData Tree (which shows raw XML structure). For Codex graph typed links, the character/knowledge cross-refs are what matter -- the SkillInfo file is the critical addition since `SkillKey` values on characters need to resolve.

### Pattern 4: FactionNode as Region Entity
**What:** `FactionNode` is the tag that registers as `"region"` entity type in Codex. The StrKey on FactionNode becomes the entity's StrKey in the registry.
**Current:** FactionNode StrKeys are lowercase (`mist_forest`, `sealed_library`). Character RegionKey values use `Region_SealedLibrary`. These don't match.
**Fix:** Either change FactionNode StrKeys to `Region_SealedLibrary` format, OR change character RegionKey to `sealed_library`. Since the CONTEXT.md says "standardize to Region_ prefix format in map XML", FactionNode StrKeys should change.

### Anti-Patterns to Avoid
- **Mixing Key and StrKey in cross-refs:** Cross-refs MUST use StrKey values, not raw Key values. The codex_service `entity_index` is keyed by StrKey.
- **Inconsistent Korean names:** Grimjaw was "그림조" in some files and "그림죠" in others. Must be "그림죠" everywhere.
- **Forgetting `&lt;br/&gt;` escaping:** On disk, `<br/>` in XML attribute values must be escaped as `&lt;br/&gt;`. Never use `&#10;` or literal newlines.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Region textures | Manual image creation | nano-banana skill (Gemini image gen) | Generates consistent fantasy RPG concept art |
| Waypoint coordinates | Guess random points | Calculate intermediate points from WorldPosition | Routes should curve naturally between source/destination |
| Korean translations | English-first then translate | Write Korean first with cultural context | Showcase is for Korean game localization; Korean must feel native |
| TM fuzzy pairs | Randomly modify strings | Carefully craft 95%+ match pairs | Fuzzy matching demo needs precise similarity scoring |

## Common Pitfalls

### Pitfall 1: Cross-Ref Resolution Fails Silently
**What goes wrong:** You add `SkillKey="Skill_SacredFlame"` to a character but the SkillInfo file has `StrKey="SacredFlame"` (without prefix). The graph shows no typed link.
**Why it happens:** `codex_service.py` line 476-478 does an exact match: `target_strkey = str(attr_value)` then `if target_strkey not in entity_index: continue`.
**How to avoid:** Every cross-ref value MUST exactly match the StrKey of the target entity. Verify each cross-ref after creation.
**Warning signs:** Relationship graph shows "related" links instead of typed links (owns, knows, etc.).

### Pitfall 2: FactionNode StrKey Change Breaks Routes
**What goes wrong:** If you change FactionNode StrKeys from `mist_forest` to `Region_MistForest`, all NodeWaypointInfo FromNodeKey/ToNodeKey values must also change.
**Why it happens:** Routes reference FactionNode StrKeys.
**How to avoid:** Update FactionInfo.xml and NodeWaypointInfo.xml atomically in the same change.

### Pitfall 3: KnowledgeInfo Not Found for New Entities
**What goes wrong:** New SkillInfo entities have `StrKey="Skill_SacredFlame"` but KnowledgeInfo uses `LearnApplySkillKey="Skill_SacredFlame"`. The codex checks `KnowledgeKey` attribute on the entity, not reverse lookups.
**Why it happens:** Knowledge linking is one-directional -- the character/skill must have `KnowledgeKey="Knowledge_SacredFlame"` to link.
**How to avoid:** Every new entity should have a `KnowledgeKey` attribute pointing to its knowledge entry.

### Pitfall 4: Excel Rows Without Korean Break Untranslated Highlighting
**What goes wrong:** Adding rows with empty Translation column to XLSX may break the file parser if it expects non-null values.
**How to avoid:** Use empty string `""` not null/None. The generate_showcase_data.py uses xlsxwriter which handles empty strings correctly.

### Pitfall 5: Texture Filenames Must Match UITextureName
**What goes wrong:** KnowledgeInfo has `UITextureName="region_mist_forest"` but the texture file is `region_MistForest.png`. Image loading fails.
**Why it happens:** The mapdata route serves thumbnails by matching UITextureName to filenames.
**How to avoid:** Use consistent naming: `region_mist_forest.png` and `UITextureName="region_mist_forest"` (lowercase with underscores).

## Code Examples

### Creating SkillInfo XML (verified pattern from characterinfo_showcase)
```xml
<?xml version='1.0' encoding='UTF-8'?>
<SkillInfoList>
  <SkillInfo Key="SKILL_001" StrKey="Skill_SacredFlame"
      SkillName="성스러운 불꽃"
      SkillDesc="현자의 결사에서 전승되는 신성한 화염 마법.&lt;br/&gt;어둠의 존재를 정화하는 힘을 지닌다.&lt;br/&gt;사용 시 주변의 그림자를 소멸시킨다."
      CooldownSec="8" Damage="450" ManaCost="30" RequireLevel="10"
      CharacterKey="Character_ElderVaron"
      KnowledgeKey="Knowledge_SacredFlame"
      UITextureName="skill_0001" />
</SkillInfoList>
```

### Fixing FactionNode KnowledgeKey Format
```xml
<!-- BEFORE (broken) -->
<FactionNode StrKey="mist_forest" KnowledgeKey="knowledge_mist_forest" ... />

<!-- AFTER (fixed) -->
<FactionNode StrKey="Region_MistForest" KnowledgeKey="Knowledge_MistForest" ... />
```

### Fixing KnowledgeInfo CharacterKey Format
```xml
<!-- BEFORE (broken) -->
<KnowledgeInfo StrKey="Knowledge_ElderVaron" CharacterKey="CHAR_001" ... />

<!-- AFTER (fixed) -->
<KnowledgeInfo StrKey="Knowledge_ElderVaron" CharacterKey="Character_ElderVaron" ... />
```

### Adding Waypoints to Routes
```xml
<!-- BEFORE (straight lines) -->
<NodeWaypointInfo FromNodeKey="Region_MistForest" ToNodeKey="Region_SealedLibrary" ... />

<!-- AFTER (curved path with waypoints) -->
<NodeWaypointInfo FromNodeKey="Region_MistForest" ToNodeKey="Region_SealedLibrary" ...>
  <Waypoint X="200" Y="0" Z="180" />
  <Waypoint X="280" Y="0" Z="160" />
</NodeWaypointInfo>
```
**Note:** Waypoint coordinates should be intermediate values between FromNode and ToNode WorldPosition values, offset to create a natural curve.

### TM Entry with Multi-line Content
```python
{"source": "A blade forged in the heart of a dying star.<br/>Its edge cuts through both flesh and shadow.",
 "target": "죽어가는 별의 심장에서 단조된 검.<br/>그 날은 살과 그림자를 모두 베어냅니다.",
 "context": "Item"}
```

### Quest String in LocStr Format
```xml
<LocStr StringID="QUEST_SEALED_LIBRARY_NAME" StrOrigin="The Sealed Library" Str="봉인된 도서관"/>
<LocStr StringID="QUEST_SEALED_LIBRARY_OBJ" StrOrigin="Find Elder Varon in the Sealed Library and retrieve the ancient scroll." Str="봉인된 도서관에서 장로 바론을 찾아 고대 두루마리를 되찾으세요."/>
<LocStr StringID="QUEST_SEALED_LIBRARY_DONE" StrOrigin="Thank you, {CharacterName}. The scroll is safe once more." Str="{CharacterName}, 감사합니다. 두루마리가 다시 안전해졌습니다."/>
```

## Current Data Inventory & Gap Analysis

### Characters (5 total -- characterinfo_showcase.staticinfo.xml)
| Character | ItemKey | RegionKey | SkillKey | FactionKey | KnowledgeKey | Status |
|-----------|---------|-----------|----------|------------|--------------|--------|
| ElderVaron | Item_SageStaff | Region_SealedLibrary | Skill_SacredFlame | Faction_SageOrder | Knowledge_ElderVaron | COMPLETE |
| ShadowKira | Item_ShadowDagger | Region_SealedLibrary | Skill_ShadowStrike | Faction_DarkCult | Knowledge_ShadowKira | COMPLETE |
| Grimjaw | Item_BlackstarSword | **MISSING** | **MISSING** | Faction_SageOrder | Knowledge_Grimjaw | NEEDS RegionKey+SkillKey |
| Lune | **MISSING** | Region_SealedLibrary | **MISSING** | Faction_SageOrder | Knowledge_Lune | NEEDS ItemKey+SkillKey |
| Drakmar | **MISSING** | **MISSING** | Skill_HolyShield | Faction_SageOrder | Knowledge_Drakmar | NEEDS ItemKey+RegionKey |

### Knowledge Entries (10 existing, need ~25)
| Existing | Missing |
|----------|---------|
| ElderVaron, ShadowKira, Grimjaw | Lune, Drakmar (characters) |
| SacredFlame, ShadowStrike, HolyShield | (skills covered) |
| SealedLibrary | MistForest, BlackstarVillage, DragonTomb, SageTower, DarkCultHQ, WindCanyon, ForgottenFortress, MoonlightLake, VolcanicZone (9 regions) |
| SageOrder, DarkCult | (factions covered) |
| BlackstarSword | SageStaff, ShadowDagger, PlagueCure, SealScroll (4 items) |

### Map Regions (10 total -- all exist in FactionInfo.xml)
All have Korean names and polygons. KnowledgeKey format needs PascalCase fix. Waypoints are empty arrays on all 13 routes.

### Textures
| Type | Existing | Needed |
|------|----------|--------|
| Characters | 5 PNG | None |
| Items | 6+ PNG | None |
| Skills | 3 PNG | None |
| Regions | 3 PNG (0001, 0002, fortress) | 10 region-specific PNGs for all map nodes |

### Localization Strings
| File | Current Count | Target |
|------|---------------|--------|
| XLSX | 27 rows | 30+ (add 3 untranslated + quest strings) |
| TXT | 28 lines | 30+ (add multi-line dialogue) |
| XML | 30 entries | 40+ (add quest strings, placeholder vars) |

### TM Entries
| Current | 35 entries (10 exact, 10 fuzzy, 10 semantic, 5 bonus) |
|---------|-------------------------------------------------------|
| Target | ~50 entries (add multi-line, dialogue, near-dupes, Quest/Dialogue contexts) |

## Workstream Independence Analysis

| Workstream | Files Modified | Depends On |
|------------|----------------|------------|
| W1: XML entity creation + cross-ref fixes | characterinfo_showcase, FactionInfo, NodeWaypointInfo, NEW skillinfo/regioninfo/questinfo | Independent |
| W2: Knowledge expansion | knowledgeinfo_showcase | Needs final StrKey format from W1 |
| W3: Localization + TM enrichment | showcase_items.loc.xml, generate_showcase_data.py, mock_tm_loader.py, showcase_dialogue.txt | Independent |
| W4: Region texture generation | tests/fixtures/mock_gamedata/textures/ | Needs final region StrKeys from W1 |

**Dependency:** W2 and W4 depend on W1 completing the StrKey format standardization first (so KnowledgeKey/UITextureName values are correct). W3 is fully independent.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + API curl tests |
| Config file | testing_toolkit/api_test_protocol.sh |
| Quick run command | `curl -s http://localhost:8888/api/ldm/codex/entities \| python3 -m json.tool \| head -20` |
| Full suite command | `bash testing_toolkit/api_test_protocol.sh` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOCK-AUDIT-01 | 5 chars with 3+ cross-refs each | smoke | `curl -s localhost:8888/api/ldm/codex/entities \| python3 -c "import sys,json;d=json.load(sys.stdin);[print(e['name'],len(e.get('attributes',{}))) for e in d.get('entities',[])]"` | N/A (API check) |
| MOCK-AUDIT-02 | 10 regions with Korean names | smoke | `curl -s localhost:8888/api/ldm/mapdata/nodes \| python3 -m json.tool \| grep -c NameKR` | N/A (API check) |
| MOCK-AUDIT-03 | XML parses clean, cross-refs resolve | smoke | `curl -s localhost:8888/api/ldm/codex/relationship-graph \| python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Links: {len(d.get(\"links\",[]))}')"` | N/A (API check) |
| MOCK-AUDIT-04 | 3 files with 25+ strings, TM matches | manual | Load mock data, select row, verify TM tab | manual-only |

### Sampling Rate
- **Per task commit:** Visual inspection of XML structure + API smoke test
- **Per wave merge:** Full API test suite
- **Phase gate:** All 4 success criteria verified via API responses

### Wave 0 Gaps
- [ ] No dedicated test file needed -- this is data quality, verified via API smoke tests
- [ ] XML well-formedness can be checked with `python3 -c "from lxml import etree; etree.parse('file.xml')"`

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/services/codex_service.py` lines 33-40 -- ENTITY_TAG_MAP (which XML tags register as entities)
- `server/tools/ldm/services/codex_service.py` lines 450-461 -- REL_TYPE_MAP (cross-ref attribute to relationship type mapping)
- `server/tools/ldm/services/gamedata_context_service.py` lines 28-33 -- CROSS_REF_ATTRS set
- `locaNext/src/lib/components/ldm/GameDataTree.svelte` lines 68-82 -- EDITABLE_ATTRS (12 entity types supported)
- All mock data files in `tests/fixtures/mock_gamedata/` -- direct inspection

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions from 5-scout Hive research audit -- comprehensive but based on code inspection, not runtime testing

## Metadata

**Confidence breakdown:**
- Data structure patterns: HIGH -- directly verified from source files
- Cross-ref resolution: HIGH -- traced through codex_service.py code
- Workstream independence: HIGH -- files are distinct with clear dependencies
- Texture generation: MEDIUM -- nano-banana skill capability assumed from CONTEXT.md

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable -- data schema unlikely to change)
