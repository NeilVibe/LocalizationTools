# Phase 44: WOW Data Wiring - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** 4-scout Hive research + auto-discuss

<domain>
## Phase Boundary

Wire backend code to fully leverage Phase 43's rich mockdata. Fix the codex relationship graph to show typed links, auto-initialize Right Panel services with mock data paths in DEV mode, fix TM 500 error, and add CharacterDesc fallback for codex descriptions. NO new features — wiring existing code to existing data.

</domain>

<decisions>
## Implementation Decisions

### Codex Relationship Graph (codex_service.py)
- **FactionKey fix:** Collect all unique FactionKey values during entity scan, create synthetic faction nodes so `member_of` links can resolve
- **CharacterKey fix:** Build a `_key_to_strkey` mapping during `_extract_entity()` (Key attr → StrKey). In `get_relationships()`, if `target_strkey not in entity_index`, try `_key_to_strkey.get(target_strkey)` as fallback
- **KnowledgeKey fix:** Add separate loop in `get_relationships()` that reads `entity.knowledge_key` directly (since it's stripped from attributes by `_SKIP_ATTRS`) and creates "knows" links
- **RegionInfo tag:** Add `"RegionInfo": ("region", "RegionName", "KnowledgeKey")` to `ENTITY_TAG_MAP` so regioninfo_showcase entities are parsed
- **Related link reduction:** When typed links exist between two entities, skip the "related" link for the same pair (deduplicate at the source→target level regardless of rel_type)
- Target: 20+ typed links across 5 relationship types

### Right Panel Auto-Init (DEV mode only)
- **MapDataService:** Add mock data auto-init in DEV mode at startup — populate `_strkey_to_image` with showcase entity StrKeys → mock texture PNG mappings
- **Audio index:** Build `_strkey_to_audio` mapping from VoicePath attributes in characterinfo XML (audio files may not exist but the wiring should be there)
- **GlossaryService:** Call `glossary_service.initialize(paths)` at startup with `tests/fixtures/mock_gamedata/StaticInfo/` paths for each entity folder
- **DEV_MODE guard:** All auto-init behind `DEV_MODE=true` environment variable check
- No frontend changes needed — tabs are already correctly wired

### TM 500 Error (tm_crud.py + schemas/tm.py)
- **TMLike wrapper fix:** Change `self.status = data.get("status", "ready")` to `self.status = data.get("status") or "ready"` — handles both missing key AND None value
- **Schema fix:** Change `status: str` to `status: str = "ready"` in TMResponse (keep it non-Optional but with default)
- Apply same pattern to all TMLike usages (get_tm, list_tms)

### Codex Description Fallback (codex_service.py)
- Add `CharacterDesc` as direct fallback for character entities before the generic `DescriptionKR` fallback
- Makes characters self-sufficient without relying on KnowledgeInfo cross-refs
- Line ~183: `if not description and tag == "CharacterInfo": description = element.get("CharacterDesc")`

### Claude's Discretion
- Exact synthetic faction node attributes (just strkey + name is enough)
- Whether to suppress ALL related links when typed links exist, or just reduce them
- Exact DEV mode initialization order (startup lifespan vs lazy first-request)
- Audio fallback behavior when .wem files don't exist

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Codex Service (relationship graph)
- `server/tools/ldm/services/codex_service.py` — Lines 33-44 (ENTITY_TAG_MAP, _SKIP_ATTRS), 136-199 (_extract_entity), 417-511 (get_relationships), 429-447 (entity_index builder), 450-461 (REL_TYPE_MAP), 464-488 (typed link loop), 490-508 (related link loop)

### Right Panel Services
- `server/tools/ldm/services/mapdata_service.py` — MapDataService singleton, initialize(), _strkey_to_image, _strkey_to_audio (no builder)
- `server/tools/ldm/services/glossary_service.py` — GlossaryService singleton, initialize(paths)
- `server/tools/ldm/services/context_service.py` — ContextService, depends on glossary + mapdata
- `server/tools/ldm/routes/mapdata.py` — Lines 93-107 (thumbnail mock fallback pattern to reuse)

### TM Fix
- `server/tools/ldm/routes/tm_crud.py` — Line 200 (TMLike status fallback), line 239
- `server/tools/ldm/schemas/tm.py` — Line 16 (TMResponse status field)

### Server Startup
- `server/main.py` — Lifespan function for auto-init

### Project Rules
- `CLAUDE.md` — loguru, DEV_MODE, never restart servers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mapdata.py` lines 93-107: Mock texture fallback pattern — reuse for image index auto-init
- `codex_service.py` ENTITY_TAG_MAP: Add RegionInfo following same (tag, name_attr, knowledge_attr) pattern
- DEV_MODE env var already used throughout codebase for dev-specific behavior

### Established Patterns
- Singleton services with lazy initialization (MapDataService, GlossaryService)
- `_SKIP_ATTRS` for attributes that get special handling vs going into generic attributes dict
- REL_TYPE_MAP for attribute→relationship-type mapping

### Integration Points
- `server/main.py` lifespan function — add DEV mode auto-init calls
- `codex_service.py` get_relationships — modify typed link resolution + add related link dedup
- `tm_crud.py` TMLike class — fix status None handling

</code_context>

<specifics>
## Specific Ideas

- The relationship graph is the crown jewel of the demo — it MUST show a clear Sage Order vs Dark Cult cluster with typed edges
- Right panel lighting up with images and context when clicking a row is the "wow moment" for executive demos
- TM fix is a one-liner but blocks the entire TM management UI

</specifics>

<deferred>
## Deferred Ideas

- Audio playback from generated TTS voices in right panel — future phase
- Real Perforce path initialization for production — not needed for demo
- Faction entities as first-class Codex type — overkill for now, synthetic nodes suffice

</deferred>

---

*Phase: 44-wow-data-wiring*
*Context gathered: 2026-03-18*
