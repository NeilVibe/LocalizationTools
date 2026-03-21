---
phase: 45-megaindex-foundation-infrastructure
plan: 02
subsystem: infra
tags: [ai-detection, model2vec, faiss, ollama, tts, svelte5, runes, fastapi]

requires:
  - phase: none
    provides: standalone foundation service
provides:
  - AICapabilityService for runtime AI engine detection (5 engines)
  - GET/POST /api/ldm/ai-capabilities endpoint
  - Svelte 5 Runes aiCapabilityStore with reactive state
  - AICapabilityBadges component for settings UI
affects: [offline-bundle, codex-audio, codex-item, ai-suggestions, tts-features]

tech-stack:
  added: []
  patterns: [singleton-service-with-probe, svelte5-module-level-state-store]

key-files:
  created:
    - server/tools/ldm/services/ai_capability_service.py
    - server/tools/ldm/routes/ai_capabilities.py
    - locaNext/src/lib/stores/aiCapabilityStore.ts
    - locaNext/src/lib/components/settings/AICapabilityBadges.svelte
  modified:
    - server/tools/ldm/router.py
    - server/tools/ldm/routes/__init__.py
    - locaNext/src/lib/components/PreferencesModal.svelte

key-decisions:
  - "Named route file ai_capabilities.py to avoid conflict with existing capabilities.py (admin user capabilities)"
  - "Used module-level $state in .ts file for Svelte 5 Runes store pattern (not Svelte 4 writable)"
  - "Auto-probe on module import so capabilities are available immediately on app start"

patterns-established:
  - "AI engine probe pattern: try/except per engine, never crashes, returns available/unavailable"
  - "Svelte 5 module-level $state store: export reactive state + async refresh function from .ts"

requirements-completed: [INFRA-02, INFRA-03]

duration: 4min
completed: 2026-03-21
---

# Phase 45 Plan 02: AI Capability Service Summary

**Runtime AI engine detection service with 5-engine probes, FastAPI endpoint, and Svelte 5 reactive capability badges in Settings UI**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-21T11:31:34Z
- **Completed:** 2026-03-21T11:35:40Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- AICapabilityService probes Model2Vec, FAISS, Ollama, TTS, and fal.ai at runtime without crashing
- API endpoint at /api/ldm/ai-capabilities returns structured JSON with capability status
- Svelte 5 Runes store auto-probes on import, providing global reactive capability state
- Settings page (PreferencesModal) shows live green/red/yellow badges for each AI engine with refresh button

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AICapabilityService + API endpoint** - `3718515b` (feat)
2. **Task 2: Create Svelte capability store + Settings page badges** - `922df86b` (feat)

## Files Created/Modified
- `server/tools/ldm/services/ai_capability_service.py` - Singleton service with 5 engine probes
- `server/tools/ldm/routes/ai_capabilities.py` - GET / and POST /refresh endpoints
- `server/tools/ldm/router.py` - Route registration
- `server/tools/ldm/routes/__init__.py` - Export registration
- `locaNext/src/lib/stores/aiCapabilityStore.ts` - Svelte 5 Runes reactive store
- `locaNext/src/lib/components/settings/AICapabilityBadges.svelte` - Visual badges component
- `locaNext/src/lib/components/PreferencesModal.svelte` - Integration of badges into settings

## Decisions Made
- Named route file `ai_capabilities.py` (not `capabilities.py`) because `capabilities.py` already exists for admin user capability management (EXPLORER-009)
- Used Svelte 5 module-level `$state` in `.ts` file rather than Svelte 4 `writable()` pattern used by existing stores
- Auto-probe on module import ensures capabilities are available immediately when any component imports the store

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Route file naming conflict with existing capabilities.py**
- **Found during:** Task 1 (reading existing router.py)
- **Issue:** Plan specified `capabilities.py` but that file already exists for admin user capabilities (EXPLORER-009)
- **Fix:** Named new file `ai_capabilities.py` with prefix `/ai-capabilities` instead of `/capabilities`
- **Files modified:** server/tools/ldm/routes/ai_capabilities.py
- **Verification:** Both route files coexist, no naming conflict
- **Committed in:** 3718515b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Route naming adjusted to avoid conflict with existing code. API path is `/api/ldm/ai-capabilities` instead of `/api/ldm/capabilities`. No scope creep.

## Issues Encountered
None

## Known Stubs
None - all data sources are wired to live backend probes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AICapabilityService ready for any component to check engine availability before using AI features
- Store importable from any Svelte component via `$lib/stores/aiCapabilityStore`
- Endpoint can be called from CLI or other tools for capability introspection

---
*Phase: 45-megaindex-foundation-infrastructure*
*Completed: 2026-03-21*
