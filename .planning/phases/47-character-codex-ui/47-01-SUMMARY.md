---
phase: 47-character-codex-ui
plan: 01
subsystem: api
tags: [fastapi, pydantic, character-codex, mega-index, knowledge-resolution]

requires:
  - phase: 45-mega-index-foundation
    provides: MegaIndex singleton with character entity lookups
  - phase: 46-item-codex-ui
    provides: Item Codex endpoint pattern and KnowledgePassEntry schema
provides:
  - Character Codex backend API (3 endpoints at /codex/characters)
  - Pydantic schemas for character cards, detail, categories, paginated list
  - UseMacro parsing (race/gender extraction)
  - Filename-based category extraction
affects: [47-02 character codex frontend, codex UI components]

tech-stack:
  added: []
  patterns: [filename-based category grouping, use_macro parsing for race/gender]

key-files:
  created:
    - server/tools/ldm/schemas/codex_characters.py
    - server/tools/ldm/routes/codex_characters.py
  modified:
    - server/tools/ldm/router.py

key-decisions:
  - "Reused KnowledgePassEntry from codex_items schemas via import"
  - "Category extraction from filename prefix (characterinfo_npc -> NPC)"
  - "Race/gender parsed from use_macro with known token lookup sets"

patterns-established:
  - "Filename-based category grouping: strip prefix + suffix, uppercase"
  - "UseMacro parsing: split by underscore, match against known race/gender tokens"

requirements-completed: [CHAR-01, CHAR-02, CHAR-03, CHAR-04]

duration: 2min
completed: 2026-03-21
---

# Phase 47 Plan 01: Character Codex Backend Summary

**3 FastAPI endpoints for character browsing with race/gender parsing, filename categories, and 3-pass knowledge resolution**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T12:24:11Z
- **Completed:** 2026-03-21T12:26:11Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Character Codex API with paginated list, detail, and categories endpoints
- UseMacro parsing extracts race/gender from "Macro_NPC_Human_Male" patterns
- Filename-based category grouping (characterinfo_npc.xml -> NPC)
- Search across name, StrKey, use_macro, age, job, and translated name

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic schemas for Character Codex API** - `9b8a0ab1` (feat)
2. **Task 2: FastAPI routes for Character Codex + router registration** - `8104a3aa` (feat)

## Files Created/Modified
- `server/tools/ldm/schemas/codex_characters.py` - Pydantic models (card, detail, category, list)
- `server/tools/ldm/routes/codex_characters.py` - 3 endpoints with helpers for macro parsing and category extraction
- `server/tools/ldm/router.py` - Added codex_characters_router registration

## Decisions Made
- Reused KnowledgePassEntry from codex_items schemas via import (DRY)
- Category extracted from source filename prefix with uppercase normalization
- Race/gender parsed from use_macro using known token lookup sets (extensible)
- Image URL falls back to ui_icon_path when knowledge texture unavailable

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all endpoints fully wired to MegaIndex data.

## Next Phase Readiness
- Character Codex backend complete, ready for 47-02 frontend implementation
- All 3 endpoints auth-gated and following Item Codex pattern exactly

---
*Phase: 47-character-codex-ui*
*Completed: 2026-03-21*
