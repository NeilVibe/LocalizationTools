---
phase: 31-codex-ai-image-generation
plan: 01
subsystem: api
tags: [gemini, ai-image-generation, codex, fastapi, disk-cache]

# Dependency graph
requires:
  - phase: 19-game-world-codex
    provides: CodexService entity registry, CodexEntity schema, codex router
provides:
  - AIImageService with Gemini SDK wrapper and prompt templates
  - Disk cache by StrKey with metadata sidecar
  - REST endpoints for generate, serve, and status
  - CodexEntity schema with ai_image_url field
affects: [31-02-frontend-integration]

# Tech tracking
tech-stack:
  added: [google-genai (existing v1.67.0)]
  patterns: [entity-type-aware prompt templates, disk cache by StrKey, asyncio.to_thread for sync SDK]

key-files:
  created:
    - server/tools/ldm/services/ai_image_service.py
    - tests/unit/ldm/test_ai_image_service.py
  modified:
    - server/tools/ldm/routes/codex.py
    - server/tools/ldm/schemas/codex.py

key-decisions:
  - "Prompt templates stored as Python dict in service (not separate JSON file)"
  - "Grade glow keywords injected per entity Grade attribute for visual quality hints"
  - "StrKey sanitization via regex + path resolution check against CACHE_DIR"
  - "Image endpoints placed before search/entity routes for correct FastAPI path matching"

patterns-established:
  - "AI image disk cache: server/data/cache/ai_images/by_strkey/{strkey}/generated.png + metadata.json"
  - "Entity-type prompt templates with attribute placeholders and graceful degradation"

requirements-completed: [IMG-01, IMG-02, IMG-03]

# Metrics
duration: 4min
completed: 2026-03-16
---

# Phase 31 Plan 01: Gemini Image Backend Summary

**AIImageService with 5 entity-type prompt templates, disk caching by StrKey, and 3 REST endpoints for generate/serve/status**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-16T10:14:04Z
- **Completed:** 2026-03-16T10:18:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- AIImageService with Gemini SDK wrapper, graceful degradation when no API key
- 5 entity-type prompt templates with attribute placeholders (character, item, skill, region, gimmick)
- Disk cache by StrKey with PNG + metadata.json sidecar
- 3 new REST endpoints: status, generate (with asyncio.to_thread), serve (with 7-day Cache-Control)
- Entity detail endpoint enriched with ai_image_url when cached
- 25 unit tests passing with fully mocked Gemini API

## Task Commits

Each task was committed atomically:

1. **Task 1: AIImageService + prompt templates + disk cache + unit tests**
   - `426d975b` (test: TDD RED -- 25 failing tests)
   - `4cde6616` (feat: TDD GREEN -- service + schema implementation)
2. **Task 2: REST endpoints for generate, serve, and status** - `f98e94ec` (feat)

## Files Created/Modified
- `server/tools/ldm/services/ai_image_service.py` - AIImageService with Gemini client, prompt builder, disk cache, sanitization
- `server/tools/ldm/schemas/codex.py` - CodexEntity extended with optional ai_image_url field
- `server/tools/ldm/routes/codex.py` - 3 new endpoints: image-gen/status, generate-image, image serving
- `tests/unit/ldm/test_ai_image_service.py` - 25 unit tests covering all service behaviors

## Decisions Made
- Prompt templates stored as Python dict in service module (simpler than separate JSON, easy to version)
- Grade glow keywords ("Slight magical glow", "Brilliant golden divine radiance") injected per Grade attribute
- StrKey sanitization: regex strips dangerous chars + path resolution verified within CACHE_DIR
- Image generation endpoints placed before search/entity routes in router for correct FastAPI path matching

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- google.genai module has pydantic compatibility issue in global Python env, but project imports work fine and tests use sys.modules mocking to avoid the issue

## User Setup Required

None - GEMINI_API_KEY is optional. When absent, service reports available=false and generation endpoints return 503.

## Next Phase Readiness
- Backend ready for Plan 02 (frontend integration)
- All endpoints registered and importable
- Batch generation (IMG-04) deferred to Plan 02

---
*Phase: 31-codex-ai-image-generation*
*Completed: 2026-03-16*
