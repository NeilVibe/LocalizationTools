---
phase: 19-game-world-codex
plan: 01
subsystem: api
tags: [fastapi, faiss, model2vec, lxml, pydantic, semantic-search, codex]

# Dependency graph
requires:
  - phase: 15-mock-gamedata-universe
    provides: StaticInfo XML files with 6 entity types and KnowledgeInfo cross-references
  - phase: 18-game-dev-grid
    provides: GameDataBrowseService patterns, XML parsing infrastructure
provides:
  - CodexService entity registry scanning 6 entity types from StaticInfo XML
  - KnowledgeKey cross-reference resolution for descriptions and image textures
  - FAISS semantic search index over all entities via Model2Vec
  - REST endpoints for search, entity detail, listing, and type counts
affects: [19-02-codex-frontend, 20-interactive-world-map]

# Tech tracking
tech-stack:
  added: []
  patterns: [entity-registry-singleton, knowledge-crossref-resolution, nested-xml-scanning]

key-files:
  created:
    - server/tools/ldm/schemas/codex.py
    - server/tools/ldm/services/codex_service.py
    - server/tools/ldm/routes/codex.py
    - tests/unit/ldm/test_codex_service.py
    - tests/unit/ldm/test_codex_route.py
  modified:
    - server/tools/ldm/router.py

key-decisions:
  - "Entity type detected from XML child tag names (CharacterInfo, ItemInfo, etc.) -- no config needed"
  - "GimmickGroupInfo parsed with nested scan for inner GimmickInfo/SealData Desc"
  - "FactionNode represents regions -- AliasName or StrKey used as name, KnowledgeKey for cross-ref"
  - "audio_key = entity.strkey for all entities -- audio keyed by StrKey convention"
  - "Module-level singleton pattern for CodexService -- same as GameDataBrowseService"

patterns-established:
  - "Nested XML scanning: recursive _scan_nested for entities inside wrapper elements"
  - "Cross-ref resolution: build knowledge_map then iterate non-knowledge entities"
  - "Related entities: group by source file, cap at 10 per entity"

requirements-completed: [CODEX-01, CODEX-02, CODEX-03, CODEX-04, CODEX-05]

# Metrics
duration: 6min
completed: 2026-03-15
---

# Phase 19 Plan 01: Codex Backend Summary

**CodexService entity registry with KnowledgeKey cross-ref resolution and FAISS semantic search across 352 entities (6 types), exposed via 4 REST endpoints**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-15T13:46:07Z
- **Completed:** 2026-03-15T13:52:24Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 6

## Accomplishments
- CodexService scans all StaticInfo XML files and builds registry with 352 entities across 6 types (character, item, skill, gimmick, knowledge, region)
- KnowledgeKey cross-references resolve descriptions and UITextureName image textures from KnowledgeInfo entities
- FAISS semantic search index built from entity names + descriptions via Model2Vec (256-dim)
- 4 REST endpoints: search, entity detail, entity listing, entity type counts
- 23 unit tests pass (16 service + 7 route)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1 RED: Failing service tests** - `d0049089` (test)
2. **Task 1 GREEN: CodexService implementation** - `5f4e16f7` (feat)
3. **Task 2 RED: Failing route tests** - `537915e0` (test)
4. **Task 2 GREEN: Codex routes + router registration** - `bf5b106a` (feat)

## Files Created/Modified
- `server/tools/ldm/schemas/codex.py` - Pydantic models: CodexEntity, CodexSearchResult/Response, CodexListResponse
- `server/tools/ldm/services/codex_service.py` - Entity registry, XML scanning, cross-ref resolution, FAISS search
- `server/tools/ldm/routes/codex.py` - REST endpoints for codex (search, entity, list, types)
- `server/tools/ldm/router.py` - Added codex_router registration
- `tests/unit/ldm/test_codex_service.py` - 16 service tests (scanning, cross-refs, FAISS, get/list)
- `tests/unit/ldm/test_codex_route.py` - 7 route integration tests

## Decisions Made
- Entity type detected from XML child tag names (CharacterInfo -> "character", etc.) -- follows existing gamedata patterns
- GimmickGroupInfo requires nested scan to extract inner GimmickInfo StrKey and SealData Desc
- FactionNode represents regions -- uses KnowledgeKey for cross-ref to get region name/description
- audio_key set to entity.strkey for all entities (consistent with audio keying convention)
- Module-level singleton pattern for CodexService (same as GameDataBrowseService)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test using nonexistent StrKey STR_CHAR_VARON**
- **Found during:** Task 2 (route tests)
- **Issue:** Test referenced STR_CHAR_VARON which exists in root-level sample file but not in StaticInfo/characterinfo
- **Fix:** Changed to STR_CHAR_0023 which exists in actual StaticInfo XML
- **Files modified:** tests/unit/ldm/test_codex_route.py
- **Verification:** Test passes with correct entity lookup
- **Committed in:** bf5b106a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test data correction. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CodexService provides all data for the Codex frontend (Plan 19-02)
- 4 REST endpoints ready for frontend consumption at /api/ldm/codex/*
- FAISS search index enables semantic search across all entity types
- Cross-references resolve descriptions and images for rich entity detail pages

---
*Phase: 19-game-world-codex*
*Completed: 2026-03-15*
