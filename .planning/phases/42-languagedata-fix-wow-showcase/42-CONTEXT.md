# Phase 42: LanguageData Fix + WOW Showcase - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** User direction + live debugging session

<domain>
## Phase Boundary

Fix the broken LanguageData (LDM) grid editor (regression — was working before), create 3-format mock data for showcase (Excel, TXT tabulated, XML), and add a rich right panel with TM 6-tier cascade, images, audio, and AI context. Goal: demonstrate multi-format support and translation workflow capabilities to executives.

**Two stages:**
1. **Fix first** — Systematic API debugging + frontend fix to restore LDM grid functionality
2. **Showcase second** — Mock data creation + right panel enhancements for WOW demo

</domain>

<decisions>
## Implementation Decisions

### Stage 1: Fix LDM Grid (Regression)
- Grid editor opens but shows "No file selected" even after double-clicking a file
- File explorer navigation works (platforms → projects → files) via double-click
- Backend API health is OK, file list endpoints return 422 (validation errors)
- GDP-level debugging needed: API call tracing, backend logs, frontend state inspection
- **Approach:** API test first (curl), Playwright second (always)
- Must test all file operations: upload, open, edit, save

### Stage 2: Mock Data (3 Formats)
- **Excel (.xlsx):** StringID + Source (ENG) + Translation (KR) + metadata columns (Status, Translator, ReviewState)
- **TXT tabulated (.txt):** Tab-separated with StringID, Source, Translation, metadata
- **XML (.loc.xml):** Standard LocStr format with StringID, Str (source), translation attributes
- Each mock file: ~20-30 strings, enough to showcase grid + right panel features
- Content: game-themed strings matching the Codex universe (characters, items, regions)
- Metadata showcases: AI-translated, Human-reviewed, Machine-translated, Needs-review statuses
- Files should demonstrate different use cases (UI strings, dialogue, item descriptions)

### Stage 3: Right Panel Enhancements
- **TM with 6-tier cascade:** Split line / whole match, exact + fuzzy + semantic
- Already have TM infrastructure from v1.0-v3.1 — wire it to the showcase mock data
- **Images:** Show character/item images in right panel when string relates to a known entity
- **Audio:** Play character voice (from Phase 41 TTS) when string relates to a character
- **AI Context:** Korean AI context using Qwen3 (already built for Codex — reuse pattern)
- Right panel tabs: TM | Image | Audio | AI Context | AI Suggest (already exist in UI!)

### Mock Data Design for WOW Effect
- Mock TM entries pre-loaded that match the mock file strings (high similarity scores)
- Cross-reference mock strings with Codex entities (Character_ElderVaron → show portrait + voice)
- Include strings with varying translation quality to show status tracking
- Include strings with <br/> tags to demonstrate linebreak handling
- Include Korean descriptions that match TM entries to show cascade working

### Claude's Discretion
- Exact number of strings per mock file
- TM entry count and similarity distribution
- Which specific strings to include for maximum demo impact
- Loading skeleton patterns
- Error state designs

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### LDM Backend (fix targets)
- `server/tools/ldm/routes/files.py` — File CRUD endpoints, upload/open/save
- `server/tools/ldm/routes/rows.py` — Row loading, editing, saving
- `server/tools/ldm/services/` — All LDM services
- `server/tools/ldm/schemas/` — Pydantic schemas for LDM

### LDM Frontend (fix targets)
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` — Main grid editor (1000+ lines, DO NOT refactor)
- `locaNext/src/lib/components/pages/LDMPage.svelte` — LDM page wrapper
- `locaNext/src/lib/components/ldm/FileExplorer.svelte` — File browser

### Right Panel (existing)
- `locaNext/src/lib/components/ldm/ReferencePanel.svelte` — Right panel with TM/Image/Audio/AI tabs
- `server/tools/ldm/routes/tm.py` — TM endpoints
- `server/tools/ldm/services/tm_service.py` — TM service with 6-tier cascade

### Mock Data Patterns
- `tests/fixtures/mock_gamedata/` — Existing mock data pattern to follow
- `server/tools/ldm/services/codex_service.py` — Entity registry for cross-referencing

### Project Rules
- `CLAUDE.md` — loguru logger, Svelte 5 runes, optimistic UI, <br/> = newlines in XML
- `testing_toolkit/api_test_protocol.sh` — API testing patterns

</canonical_refs>

<specifics>
## Specific Ideas

- Showcase must support 3 file formats: Excel, TXT tabulated, XML — proving LocaNext is format-agnostic
- As long as files have StringID + Source + Translation, we can open them
- Metadata support: AI-translated, human-reviewed, machine-translated statuses
- Right panel should feel like a professional CAT tool (SDL Trados, memoQ level)
- TM cascade: exact → fuzzy → semantic, split by line and whole
- Cross-reference with Codex: when editing a character string, show the character portrait + voice
- All about the WOW effect for executive demo — every feature must look polished

</specifics>

<deferred>
## Deferred Ideas

- Real file upload from local filesystem (browser API) — future
- Multi-user concurrent editing demo — future
- Export back to original format — future
- QA checks integration in right panel — future

</deferred>

---

*Phase: 42-languagedata-fix-wow-showcase*
*Context gathered: 2026-03-18*
