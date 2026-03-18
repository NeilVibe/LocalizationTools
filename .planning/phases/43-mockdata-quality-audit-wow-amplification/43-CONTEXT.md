# Phase 43: Mockdata Quality Audit + WOW Amplification - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** 5-scout Hive research audit + auto-discuss decisions

<domain>
## Phase Boundary

Audit and elevate ALL mock/showcase data across all 5 pages (Codex, Map, GameData Tree, LanguageData Grid, Right Panel) to create maximum WOW effect. Fix broken cross-references, add missing entity types, generate missing textures, and ensure every page has rich interconnected data that tells a compelling story. NO new features or UI changes — data quality and completeness only.

</domain>

<decisions>
## Implementation Decisions

### Cross-Reference Integrity (CRITICAL)
- Fix RegionKey format mismatch: characters use `Region_SealedLibrary` but map nodes use `sealed_library` — standardize to `Region_` prefix format in map XML OR add matching entries in knowledgeinfo
- Fix KnowledgeKey format mismatch: FactionNode uses `knowledge_mist_forest` (lowercase) but KnowledgeInfo uses `Knowledge_SealedLibrary` (PascalCase) — standardize ALL to PascalCase `Knowledge_` prefix
- Fix Knowledge CharacterKey: knowledge entries reference raw `Key` (CHAR_001) instead of `StrKey` (Character_ElderVaron) — change to StrKey format
- Fill missing cross-refs on 3 characters: Grimjaw needs RegionKey+SkillKey, Lune needs ItemKey+SkillKey, Drakmar needs ItemKey+RegionKey
- All 5 characters should have COMPLETE cross-ref sets: ItemKey, RegionKey, SkillKey, FactionKey, KnowledgeKey

### Missing Entity Types (HIGH PRIORITY)
- Create `StaticInfo/skillinfo/skillinfo_showcase.staticinfo.xml` with 3 skills: Skill_SacredFlame, Skill_ShadowStrike, Skill_HolyShield — all referenced by existing characters
- Create `StaticInfo/regioninfo/regioninfo_showcase.staticinfo.xml` with RegionInfo entries for at least 5 key regions (SealedLibrary, BlackstarVillage, DragonTomb, SageTower, DarkCultHQ)
- Create `StaticInfo/questinfo/questinfo_showcase.staticinfo.xml` with 2-3 quests connecting the storyline (main quest for Sealed Library + side quests)
- Each new entity needs: Key, StrKey, Korean name, Korean description with `<br/>`, UITextureName, cross-reference keys back to characters/items/regions
- Skills need: SkillName, SkillDesc, CooldownSec, Damage, ManaCost, RequireLevel, CharacterKey
- Quests need: QuestName, QuestDesc, RequireLevel, RewardKey, RegionKey, NPC giver reference

### Knowledge Info Expansion
- Add KnowledgeInfo entries for ALL 10 map regions (currently only SealedLibrary has one)
- Add KnowledgeInfo entries for remaining 4 items (SageStaff, ShadowDagger, PlagueCure, SealScroll)
- Each knowledge entry needs: Key, StrKey, Korean name, Korean description (multi-line), UITextureName, cross-ref keys
- Total knowledge entries: expand from 10 to ~25

### Region Textures (Map WOW)
- Generate 10 PNG textures for all map regions using nano-banana (Gemini image gen)
- Each texture should match the region's biome/type: misty forest, ancient library, peaceful village, dragon cavern, sage tower, dark fortress, wind canyon, forgotten fortress, moonlight lake, volcanic terrain
- Name format: `region_{strkey}.png` (e.g., `region_mist_forest.png`)
- Place in `tests/fixtures/mock_gamedata/textures/`
- Update KnowledgeInfo UITextureName to reference these new textures

### Map Data Enhancement
- Add waypoints to at least 5-6 routes (2-3 intermediate coordinates each) for curved paths instead of straight lines
- Consider adding 3-5 more map nodes for spatial density (trading post, mining camp, harbor, ancient temple, watchtower)
- Map polygon shapes: OK as-is for now (hexagons work for demo)

### TM Coverage Expansion
- Add 5+ TM entries with `<br/>` multi-line content to demo multi-line TM matching
- Add 5+ dialogue-related TM entries so TXT file strings get TM hits
- Add 2-3 near-duplicate fuzzy pairs (95%+ match) for fine-grained scoring demo
- Add "Quest" and "Dialogue" context tags
- Total TM entries: expand from 35 to ~50

### Localization String Enrichment
- Add 5-10 quest strings to showcase_items.loc.xml (quest names, objectives, completion)
- Add 2-3 strings with placeholder variables (`{0}`, `{CharacterName}`)
- Add 2-3 rows with empty/missing Korean translations in Excel to demo untranslated highlighting
- Add 1-2 multi-line strings to dialogue TXT with `<br/>`
- Standardize Grimjaw Korean name to "그림죠" across ALL files (already fixed in characterinfo, verify others)

### Relationship Graph Quality
- With fixed cross-refs + added SkillInfo/RegionInfo, the graph should show meaningful typed links (owns, knows, member_of, located_in) instead of 130 generic "related" links
- Target: at least 20 typed links across 5 relationship types
- Suppress or reduce same-file "related" links when typed links exist (code change in codex_service if needed)

### Claude's Discretion
- Exact number of new map nodes (3-5 range)
- Skill stat values (damage, cooldown, etc.)
- Quest reward details
- Region description prose style
- Whether to add SkillTreeInfo (nice-to-have, not required)
- Whether to add GimmickInfo/SealDataInfo (low priority, skip unless easy)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Mock Data Structure
- `tests/fixtures/mock_gamedata/StaticInfo/characterinfo/characterinfo_showcase.staticinfo.xml` — 5 characters, cross-ref pattern to follow
- `tests/fixtures/mock_gamedata/StaticInfo/knowledgeinfo/knowledgeinfo_showcase.staticinfo.xml` — 10 knowledge entries, expansion target
- `tests/fixtures/mock_gamedata/StaticInfo/factioninfo/FactionInfo.staticinfo.xml` — 10 map nodes, KnowledgeKey format to fix
- `tests/fixtures/mock_gamedata/StaticInfo/factioninfo/NodeWaypointInfo/NodeWaypointInfo.staticinfo.xml` — 13 routes, waypoints to add
- `tests/fixtures/mock_gamedata/localization/showcase_items.loc.xml` — 30 LocStr entries, expansion target
- `tests/fixtures/mock_gamedata/localization/showcase_dialogue.txt` — 28 dialogue lines
- `tests/fixtures/mock_gamedata/localization/generate_showcase_data.py` — Generator pipeline

### TM & Localization
- `server/tools/ldm/services/mock_tm_loader.py` — TM entry loader, expansion target
- `CLAUDE.md` — `<br/>` = newlines in XML (CRITICAL rule)

### Backend Services (cross-ref resolution)
- `server/tools/ldm/services/codex_service.py` — Entity registry, relationship graph builder, cross-ref key lookup
- `server/tools/ldm/services/gamedata_context_service.py` — Forward/backward cross-ref resolution
- `server/tools/ldm/services/gamedata_browse_service.py` — XML file parsing, entity counting
- `server/tools/ldm/routes/mapdata.py` — Thumbnail serving, audio streaming

### Frontend Components (what data they consume)
- `locaNext/src/lib/components/ldm/CodexRelationshipGraph.svelte` — D3 graph, needs typed links
- `locaNext/src/lib/components/ldm/MapCanvas.svelte` — Map renderer, supports waypoints/polygons
- `locaNext/src/lib/components/ldm/GameDataTree.svelte` — Tree viewer, EDITABLE_ATTRS for 12 entity types
- `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` — Entity detail, shows related entities

### Project Rules
- `CLAUDE.md` — loguru, Svelte 5 runes, `<br/>` tags, optimistic UI

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `characterinfo_showcase.staticinfo.xml`: Pattern for all new XML entities (Key, StrKey, Korean attrs, cross-ref keys, `&lt;br/&gt;` descriptions)
- `mock_tm_loader.py`: TM entry loader — extend with new entries, already handles idempotency
- `generate_showcase_data.py`: Generation pipeline for XLSX/TXT/XML — extend for quest strings
- `nano-banana skill`: Gemini image generation for region textures

### Established Patterns
- XML attribute naming: PascalCase (CharacterName, SkillDesc, RegionKey)
- Cross-reference keys: `{EntityType}_{EntityName}` format (e.g., `Skill_SacredFlame`)
- Korean descriptions: Multi-line with `&lt;br/&gt;` escaped as `&lt;br/&gt;` on disk
- Textures: PNG files in `tests/fixtures/mock_gamedata/textures/` named after UITextureName value

### Integration Points
- `codex_service.py` line 477: Cross-ref key lookup — must match StrKey format exactly
- `gamedata_context_service.py` VOICE_ATTRS tuple: Cross-ref attribute detection
- `GameDataTree.svelte` EDITABLE_ATTRS: Entity type → editable attribute mapping (12 types defined)
- MapCanvas: Reads `waypoints[]` from route data — currently empty arrays, needs coordinates

</code_context>

<specifics>
## Specific Ideas

- The 5-character Sealed Library storyline (Sage Order vs Dark Cult) is STRONG — all new data should reinforce this narrative
- Every entity should be reachable from at least 2 other entities (no dead-end nodes)
- The relationship graph should visually tell the story: Sage Order cluster vs Dark Cult cluster, with the Sealed Library as the contested center
- Region textures should look like fantasy RPG concept art — atmospheric, distinctive per biome
- TM matches should demonstrate the full cascade: exact (100%), high fuzzy (90%+), medium fuzzy (75%+), semantic (60%+)
- Quest strings should follow the RPG pattern: quest name, objective text, completion dialogue

</specifics>

<deferred>
## Deferred Ideas

- SkillTreeInfo with parent-child hierarchy (nested tree demo) — future phase
- GimmickInfo/SealDataInfo entity types — low priority, skip
- SceneObjectData for map enrichment — future phase
- Route type visual differentiation (road/river/mountain) in MapCanvas — future phase
- Animated markers for special locations on map — future phase
- Real multilingual stringtable (6 languages) — future phase, current showcase is KR+ENG only

</deferred>

---

*Phase: 43-mockdata-quality-audit-wow-amplification*
*Context gathered: 2026-03-18*
