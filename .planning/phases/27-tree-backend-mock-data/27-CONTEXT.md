# Phase 27: Tree Backend + Mock Data - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend lxml tree parser API that accepts XML gamedata file paths and returns hierarchical JSON with nested parent/child nodes (not flat rows). Expanded mock fixtures demonstrating real nesting patterns for SkillTree, Knowledge, and Gimmick entity types.

Requirements: TREE-05, TREE-07

</domain>

<decisions>
## Implementation Decisions

### Tree JSON Response Structure
- Each node represented as a `TreeNode` with `children: TreeNode[]` array (nested, not flat)
- Node attributes: `tag` (XML element name), `attributes` (dict of all XML attrs), `children` (nested nodes), `parent_id` (back-reference for navigation)
- Root response: `GameDataTreeResponse(roots: List[TreeNode], base_path, entity_type, file_path)`
- `roots` is a list because a single XML file may have multiple top-level entities (e.g., multiple SkillTreeInfo elements)

### Hierarchy Detection Strategy
- Parser handles TWO hierarchy styles and normalizes both into the same nested TreeNode structure:
  1. **XML-nested**: Direct child elements in XML become direct children in JSON (GimmickGroupInfo > GimmickInfo > SealData)
  2. **Reference-based (ParentId)**: Flat XML elements with ParentId/ParentNodeId attributes are post-processed into nested structure via parent-child resolution pass
- Detection is automatic — if elements have `ParentId` or `ParentNodeId` attributes, run the reference-resolution pass after initial XML parse
- Both styles produce identical nested JSON output — UI doesn't need to know which style the source XML used

### Mock Data Expansion Scope
- Three entity types get expanded nesting in fixtures:
  1. **SkillTreeInfo**: Deep ParentId-based nesting (3+ levels) based on `exampleofskillgamedata.txt` patterns — SkillNode children with ParentNodeId references
  2. **KnowledgeInfo**: KnowledgeList children linking child knowledge entries to parents
  3. **GimmickGroupInfo**: Already has XML-nested structure (GimmickGroupInfo > GimmickInfo > SealData) — verify existing fixtures are sufficient
- Remaining entity types (ItemInfo, CharacterInfo, RegionInfo, QuestInfo, SceneObjectData, SealDataInfo, FactionInfo) stay flat — they'll get tree treatment if/when real data shows nesting
- Each expanded fixture should have at least 3 levels of depth to exercise the tree walker

### API Design
- **New endpoint**: `POST /api/ldm/gamedata/tree` — returns hierarchical JSON tree for a single XML file
- **Existing endpoint preserved**: `POST /api/ldm/gamedata/rows` stays for flat grid extraction (used by current GameDev VirtualGrid)
- **New endpoint for folder tree**: `POST /api/ldm/gamedata/tree/folder` — returns combined tree for all XML files in a folder (needed for Phase 28 full folder loading)
- Request schema: `TreeRequest(path: str, max_depth: int = -1)` where -1 means unlimited depth
- Parser uses lxml `el.iter()`, `el.findall()`, and parent/child navigation (as per TREE-05 — like QACompiler generators)

### Claude's Discretion
- Exact TreeNode field names and schema details
- Whether to include a `node_count` summary field
- Test file organization within existing test structure
- Error handling for malformed XML nesting (self-closing tag issues noted in exampleofskillgamedata.txt)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Tree Walking Reference Implementation
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/skill.py` lines 259-340 — `build_knowledge_children_map()` is THE reference pattern for lxml tree walking with `.iter()` and parent/child resolution
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/exampleofskillgamedata.txt` — Real game data showing 3-level deep SkillNode nesting with ParentId references

### Current Gamedata Backend (extend these)
- `server/tools/ldm/services/gamedata_browse_service.py` — Current folder scanning + FolderNode tree + entity counting. Extend with tree builder.
- `server/tools/ldm/routes/gamedata.py` — Current endpoints (browse, columns, rows, save). Add tree endpoints.
- `server/tools/ldm/schemas/gamedata.py` — Current schemas (FolderNode, GameDataRow, BrowseRequest). Add TreeNode schemas.
- `server/tools/ldm/services/gamedata_edit_service.py` — Entity attribute editing with br-tag preservation

### XML Parsing Infrastructure
- `server/tools/ldm/services/xml_parsing.py` — XMLParsingEngine with sanitization + lxml parsing + StringIdConsumer pattern
- `server/tools/ldm/services/gamedata_browse_service.py` lines 23-38 — EDITABLE_ATTRS mapping per entity type

### Mock Fixtures (expand these)
- `tests/fixtures/mock_gamedata/StaticInfo/skillinfo/SkillTreeInfo.staticinfo.xml` — Current flat SkillNode list (needs ParentNodeId-based nesting)
- `tests/fixtures/mock_gamedata/StaticInfo/gimmickinfo/Item/GimmickInfo_Item_Chest.staticinfo.xml` — Already has XML-nested structure (GimmickGroupInfo > GimmickInfo > SealData)
- `tests/fixtures/mock_gamedata/StaticInfo/knowledgeinfo/` — KnowledgeInfo files needing KnowledgeList children

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `XMLParsingEngine.parse_file()` — strict-first + recover fallback lxml parsing (reuse for tree parsing)
- `gamedata_browse_service.scan_folder()` — recursive folder scanning with FolderNode tree (reuse for folder-level tree loading)
- `gamedata_browse_service.EDITABLE_ATTRS` — entity type to editable attributes mapping (attach to tree nodes)
- `StringIdConsumer` — document-order dedup pattern (may be useful for ensuring unique node IDs)
- `skill.py build_knowledge_children_map()` — parent→children map builder using `.iter()` (port this pattern)

### Established Patterns
- lxml `etree.parse()` with `recover=True` fallback for malformed XML
- `get_attr(elem, attr_variants)` for case-variant attribute lookup
- FastAPI Pydantic schemas with `model_config = ConfigDict(from_attributes=True)`
- All routes use `from loguru import logger` (never print)
- Services are stateless classes, instantiated per request

### Integration Points
- New tree endpoint connects to existing `gamedata.py` router (`/api/ldm/gamedata/tree`)
- TreeNode schema extends existing schemas in `gamedata.py`
- Tree parser reuses XMLParsingEngine from `xml_parsing.py`
- Mock fixtures live in `tests/fixtures/mock_gamedata/StaticInfo/` (established directory)

</code_context>

<specifics>
## Specific Ideas

- Parser MUST handle the triple-nesting edge case from `exampleofskillgamedata.txt` (SkillNode > SkillNode > SkillNode via ParentId chains)
- Self-closing tag malformation (`</>`) noted in real game data — parser should handle gracefully via lxml recover mode
- Reference-based hierarchy (ParentId) is MORE COMMON than XML-nested hierarchy in real game data — make sure this path is robust
- Keep the tree parser as a separate service class (e.g., `GameDataTreeService`) — don't bloat `gamedata_browse_service.py`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-tree-backend-mock-data*
*Context gathered: 2026-03-16*
