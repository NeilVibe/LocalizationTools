---
phase: 21-ai-naming-coherence-placeholders
plan: 01
subsystem: api
tags: [naming, faiss, ollama, qwen3, codex, pydantic, fastapi]

requires:
  - phase: 19-game-world-codex
    provides: CodexService with FAISS search across all entity types
  - phase: 17-ai-translation-suggestions
    provides: AISuggestionService pattern for Ollama integration and caching
provides:
  - NamingCoherenceService with find_similar_names (FAISS) and suggest_names (Qwen3)
  - Pydantic schemas for naming similarity and suggestion responses
  - REST endpoints at /api/ldm/naming/* with auth protection
affects: [21-02-placeholders, frontend-naming-panel]

tech-stack:
  added: []
  patterns: [naming-coherence-service-singleton, codex-service-delegation]

key-files:
  created:
    - server/tools/ldm/services/naming_coherence_service.py
    - server/tools/ldm/schemas/naming.py
    - server/tools/ldm/routes/naming.py
    - tests/unit/ldm/test_naming_service.py
    - tests/unit/ldm/test_naming_route.py
  modified:
    - server/tools/ldm/router.py

key-decisions:
  - "Cache key is entity_type:name (simpler than md5 hash since names are short)"
  - "Prompt includes /no_think tag for speed (naming suggestions are creative, not analytical)"
  - "Temperature 0.8 for naming suggestions (higher than 0.7 for translations -- more creative)"

patterns-established:
  - "CodexService delegation: services can import _get_codex_service from routes/codex for FAISS access"
  - "Naming prompt pattern: include existing similar names as context for pattern-aware suggestions"

requirements-completed: [AINAME-01, AINAME-02, AINAME-03]

duration: 4min
completed: 2026-03-15
---

# Phase 21 Plan 01: AI Naming Coherence Backend Summary

**NamingCoherenceService with FAISS entity similarity search via CodexService and Qwen3 AI naming suggestions with caching and graceful Ollama fallback**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T14:50:38Z
- **Completed:** 2026-03-15T14:55:10Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- NamingCoherenceService finds similar entity names via CodexService FAISS search and generates AI naming alternatives via Qwen3
- In-memory caching by entity_type:name prevents redundant Ollama calls
- Graceful fallback returns empty suggestions with status="unavailable" when Ollama is down
- REST endpoints registered at /api/ldm/naming/* with auth protection
- 14 unit tests (9 service + 5 route) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: NamingCoherenceService + Pydantic schemas + unit tests** - `774d2fa4` (feat)
2. **Task 2: Naming REST endpoints + router registration + route tests** - `09d15a5e` (feat)

## Files Created/Modified
- `server/tools/ldm/services/naming_coherence_service.py` - Core service with find_similar_names + suggest_names
- `server/tools/ldm/schemas/naming.py` - Pydantic models for naming requests/responses
- `server/tools/ldm/routes/naming.py` - REST endpoints for similar names, suggestions, status
- `server/tools/ldm/router.py` - Router registration for naming endpoints
- `tests/unit/ldm/test_naming_service.py` - 9 service unit tests
- `tests/unit/ldm/test_naming_route.py` - 5 route unit tests

## Decisions Made
- Cache key is entity_type:name (simpler than md5 hash since entity names are short strings)
- Prompt includes /no_think tag for speed (naming is creative, not analytical)
- Temperature 0.8 for naming (higher than 0.7 for translations -- more creative variety)
- CodexService accessed via lazy import from routes/codex to avoid circular dependencies

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Naming coherence backend complete, ready for frontend panel integration
- Plan 02 (placeholder detection) can proceed independently

---
*Phase: 21-ai-naming-coherence-placeholders*
*Completed: 2026-03-15*
