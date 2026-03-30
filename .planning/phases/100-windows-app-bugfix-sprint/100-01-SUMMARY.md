---
phase: 100-windows-app-bugfix-sprint
plan: 01
subsystem: api
tags: [megaindex, audio, wem, language-routing, image-fallback, korean, context-service]

requires:
  - phase: 98-mega-graft
    provides: MegaIndex 7-phase build, D10 WEM scanning, R1 Korean name reverse lookup
provides:
  - 3 per-language WEM dicts (D10a/b/c) for EN/KR/ZH audio folders
  - 3 per-language C3 dicts for language-aware StringID->audio routing
  - LANG_TO_AUDIO constant mapping 13 language codes to 3 audio folders
  - Language-aware audio API methods (get_audio_path_by_stringid_for_lang, get_audio_path_by_event_for_lang)
  - Korean text fallback in image resolution chain via R1 reverse lookup
  - match_method field in context response for frontend badge display
affects: [frontend-audio-panel, frontend-image-panel, context-panel]

tech-stack:
  added: []
  patterns: [per-language-dict-pattern, lang-routing-constant, korean-text-fallback-chain]

key-files:
  created: []
  modified:
    - server/tools/ldm/services/mega_index_helpers.py
    - server/tools/ldm/services/mega_index.py
    - server/tools/ldm/services/mega_index_data_parsers.py
    - server/tools/ldm/services/mega_index_builders.py
    - server/tools/ldm/services/mega_index_api.py
    - server/tools/ldm/services/mapdata_service.py
    - server/tools/ldm/services/context_service.py
    - server/tools/ldm/routes/context.py
    - server/tools/ldm/routes/mapdata.py

key-decisions:
  - "LANG_TO_AUDIO placed in mega_index_helpers.py to avoid circular imports between mega_index.py and mega_index_api.py"
  - "Cache key in mapdata_service includes language to prevent stale cross-language cache hits"
  - "C2 (entity-based audio) stays English-only since it is entity-based not file-language-based"
  - "Korean text fallback uses first R1 match (greedy) for simplicity"

patterns-established:
  - "Per-language dict pattern: wem_by_event_{en,kr,zh} with backward compat alias to _en"
  - "Language routing via LANG_TO_AUDIO constant derived from MDG config.py"
  - "match_method field in resolve_chain for frontend to display match type badge"

requirements-completed: [BUG-5, BUG-6]

duration: 7min
completed: 2026-03-30
---

# Phase 100 Plan 01: Multi-Language Audio + Image Korean Fallback Summary

**3-folder audio routing (EN/KR/ZH) matching MDG config.py pattern, plus Korean text R1 fallback for image resolution with match_method badge**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-30T06:56:39Z
- **Completed:** 2026-03-30T07:04:05Z
- **Tasks:** 8
- **Files modified:** 9

## Accomplishments
- Multi-language audio: 13 language codes route to 3 audio folders (EN/KR/ZH) via LANG_TO_AUDIO constant
- Per-language WEM scanning: 3 separate dicts built during Phase 1, 3 per-language C3 dicts during Phase 7
- Korean text image fallback: when StringID has no direct entity, tries Korean StrOrigin via R1 reverse lookup
- Language parameter wired through all 4 audio endpoints (context, audio, audio/stream, combined)
- match_method field distinguishes "stringid" vs "korean_text" matches for frontend badge

## Task Commits

Each task was committed atomically:

1. **Task 8: Move LANG_TO_AUDIO to mega_index_helpers.py** - `396eafee` (feat)
2. **Task 1: Add per-language WEM dicts to MegaIndex.__init__** - `3452b839` (feat)
3. **Task 2: Scan 3 audio folders in DataParsersMixin** - `26ca5c7c` (feat)
4. **Task 3: Build per-language C3 dicts in BuildersMixin** - `2419dbfd` (feat)
5. **Task 4: Add language-aware audio API to ApiMixin** - `2633292f` (feat)
6. **Task 5: Wire language-aware audio into mapdata_service.py** - `7964c31d` (feat)
7. **Task 6: Wire language through context_service + routes** - `d07d66c8` (feat)
8. **Task 7: Korean text fallback in image chain (BUG-6)** - `498cf16c` (feat)

## Files Created/Modified
- `server/tools/ldm/services/mega_index_helpers.py` - Added LANG_TO_AUDIO constant (13 langs -> 3 folders)
- `server/tools/ldm/services/mega_index.py` - Added D10a/b/c and C3a/b/c per-language dicts to __init__, 3-folder audio path resolution in build()
- `server/tools/ldm/services/mega_index_data_parsers.py` - New _scan_wem_files_all_languages and _scan_wem_into methods
- `server/tools/ldm/services/mega_index_builders.py` - _build_stringid_to_audio_path builds 3 per-language C3 dicts
- `server/tools/ldm/services/mega_index_api.py` - get_audio_path_by_stringid_for_lang and get_audio_path_by_event_for_lang
- `server/tools/ldm/services/mapdata_service.py` - get_audio_context accepts file_language, routes through language-aware API
- `server/tools/ldm/services/context_service.py` - Korean text fallback in resolve_chain, match_method field, file_language param
- `server/tools/ldm/routes/context.py` - Language query parameter on GET /context/{string_id}
- `server/tools/ldm/routes/mapdata.py` - Language query parameter on audio/stream, audio, and combined context endpoints

## Decisions Made
- LANG_TO_AUDIO placed in mega_index_helpers.py to avoid circular imports (mega_index.py and mega_index_api.py both need it)
- Cache key in mapdata_service includes language (`string_id:file_language`) to prevent stale cross-language cache hits
- C2 (entity-based audio) stays English-only since it resolves via knowledge_key not file language
- Korean text fallback uses first R1 match for simplicity (greedy approach)
- Task 8 executed first (dependency: other tasks need LANG_TO_AUDIO)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed stale STRINGID_ATTRS import**
- **Found during:** Task 1 (MegaIndex.__init__ modifications)
- **Issue:** mega_index.py imported STRINGID_ATTRS from mega_index_helpers.py but it doesn't exist there (lives in xml_parsing.py)
- **Fix:** Removed the import from the re-export list
- **Files modified:** server/tools/ldm/services/mega_index.py
- **Verification:** Python import succeeds without error
- **Committed in:** 3452b839 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Pre-existing broken import, had to be fixed to proceed. No scope creep.

## Issues Encountered
None

## Known Stubs
None - all data paths are fully wired to real MegaIndex lookups.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Audio panel can now play correct language audio when frontend passes file_language parameter
- Image panel can show Korean text fallback images with match_method badge
- Frontend needs to pass language parameter in API calls (separate frontend task)
- BUG-7 through BUG-12 ready for Plan 02

---
*Phase: 100-windows-app-bugfix-sprint*
*Completed: 2026-03-30*
