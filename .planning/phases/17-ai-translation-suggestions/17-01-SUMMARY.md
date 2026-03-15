---
phase: 17-ai-translation-suggestions
plan: 01
subsystem: api
tags: [ollama, qwen3, embedding, model2vec, faiss, httpx, pydantic, fastapi]

requires:
  - phase: 13-ai-summaries
    provides: AISummaryService singleton pattern, Ollama REST API integration
  - phase: 16-category-clustering
    provides: CategoryService for entity type detection from StringID prefix

provides:
  - AISuggestionService singleton with generate_suggestions, blended confidence, caching
  - REST endpoint GET /api/ldm/ai-suggestions/{string_id} for translation suggestions
  - REST endpoint GET /api/ldm/ai-suggestions/status for service health

affects: [17-02-frontend-suggestion-panel, 18-game-dev-grid, 19-codex]

tech-stack:
  added: []
  patterns: [blended-confidence-scoring, embedding-similarity-enrichment, structured-ollama-output]

key-files:
  created:
    - server/tools/ldm/services/ai_suggestion_service.py
    - server/tools/ldm/routes/ai_suggestions.py
    - tests/unit/ldm/test_ai_suggestion_service.py
    - tests/unit/ldm/test_ai_suggestion_route.py
    - tests/integration/test_ai_suggestions_e2e.py
  modified:
    - server/tools/ldm/router.py
    - server/tools/ldm/routes/__init__.py

key-decisions:
  - "Blended confidence formula: 0.4 * max_embedding_similarity + 0.6 * llm_confidence"
  - "Cache key includes md5 hash of source_text to invalidate on text changes"
  - "FAISS similarity search is enrichment-only -- graceful empty return when unavailable"
  - "Route registered in router.py following existing aggregation pattern (not __init__.py)"

patterns-established:
  - "Blended scoring: combine embedding similarity with LLM confidence for ranked suggestions"
  - "Enrichment pattern: _find_similar_segments wraps all embedding/FAISS in try/except, never crashes"

requirements-completed: [AISUG-01, AISUG-02, AISUG-04, AISUG-05]

duration: 7min
completed: 2026-03-15
---

# Phase 17 Plan 01: AI Suggestion Service Summary

**Ollama/Qwen3 translation suggestion backend with blended confidence scores (0.4 embedding + 0.6 LLM), Model2Vec FAISS enrichment, in-memory caching, and graceful fallback**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-15T12:24:03Z
- **Completed:** 2026-03-15T12:31:49Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- AISuggestionService generates 3 ranked translation suggestions via Ollama with structured JSON output
- Blended confidence scoring combines embedding similarity (Model2Vec FAISS) with LLM certainty
- REST endpoint at /api/ldm/ai-suggestions/{string_id} with entity type auto-detection and context params
- 23 tests total: 14 unit (service) + 5 unit (route) + 4 integration (full pipeline)

## Task Commits

Each task was committed atomically:

1. **Task 1: AISuggestionService with embedding blend + unit tests (TDD)** - `8094fece` (test+feat)
2. **Task 2: AI Suggestions REST endpoint + route tests + integration test (TDD)** - `cb8c10cd` (feat)

## Files Created/Modified
- `server/tools/ldm/services/ai_suggestion_service.py` - Singleton service with generate_suggestions, _find_similar_segments, _blend_confidence, caching
- `server/tools/ldm/routes/ai_suggestions.py` - REST endpoint with entity type detection and context parsing
- `server/tools/ldm/router.py` - Router registration for ai_suggestions_router
- `server/tools/ldm/routes/__init__.py` - Export ai_suggestions_router
- `tests/unit/ldm/test_ai_suggestion_service.py` - 14 unit tests for service
- `tests/unit/ldm/test_ai_suggestion_route.py` - 5 route tests
- `tests/integration/test_ai_suggestions_e2e.py` - 4 integration tests covering full pipeline

## Decisions Made
- Blended confidence formula: 0.4 * max_embedding_similarity + 0.6 * llm_confidence (per AISUG-02)
- Cache key includes md5 hash of source_text (not just string_id) to prevent stale cache
- FAISS similarity search is enrichment-only -- entire _find_similar_segments wrapped in try/except
- Route registered in router.py (actual pattern) rather than routes/__init__.py (plan spec)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Router registration in router.py instead of __init__.py**
- **Found during:** Task 2
- **Issue:** Plan specified registering in routes/__init__.py, but codebase uses router.py for include_router()
- **Fix:** Registered in both router.py (actual registration) and __init__.py (export)
- **Files modified:** server/tools/ldm/router.py, server/tools/ldm/routes/__init__.py

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Followed actual codebase convention. No scope creep.

## Issues Encountered
- Pre-existing test failure in test_glossary_service.py (character count mismatch) -- unrelated to this plan, not a regression

## User Setup Required

None - no external service configuration required. Ollama/Qwen3 must be running locally (already a project requirement from Phase 13).

## Next Phase Readiness
- AI suggestion backend ready for frontend consumption (Plan 02)
- Endpoint contract: GET /api/ldm/ai-suggestions/{string_id}?source_text=X&target_lang=KR
- Response: {"suggestions": [{text, confidence, reasoning}], "status": "generated"|"cached"|"unavailable"|"error"}

---
*Phase: 17-ai-translation-suggestions*
*Completed: 2026-03-15*
