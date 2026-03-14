# LocaNext — Demo-Ready CAT Tool

## What This Is

LocaNext is a desktop localization management platform (Electron + FastAPI + Svelte 5) that provides a Language Data Manager (CAT tool) for game localization teams. It handles file uploads, translation memory management, semantic search, and XML-based language data editing. The goal is to make this production-quality and demo-ready for executive stakeholders.

## Core Value

The CAT tool must deliver a flawless end-to-end localization workflow — upload files, automatically organize TMs mirroring the folder structure, search/edit translations, and export — working seamlessly in both offline and online modes, polished enough to demo to executives.

## Requirements

### Validated

- ✓ FastAPI backend with async API endpoints — existing
- ✓ Svelte 5 frontend with Carbon Components — existing
- ✓ Electron desktop app packaging — existing
- ✓ DB Factory with Repository pattern abstracting offline/online into unified architecture — existing
- ✓ JWT authentication with offline mode token detection — existing
- ✓ WebSocket real-time sync infrastructure — existing
- ✓ FAISS vector indexing for semantic search — existing
- ✓ XML language data parsing with `<br/>` tag preservation — existing
- ✓ Dual CI/CD pipeline (Gitea for LocaNext, GitHub for NewScripts) — existing

### Active

- [ ] Server starts reliably without errors every time
- [ ] Offline mode (SQLite) works as a first-class mode — full feature parity
- [ ] Online mode (PostgreSQL) works for multi-user collaboration
- [ ] Mode switching is transparent via the DB abstraction layer
- [ ] File upload workflow functions end-to-end
- [ ] Folder creation and file organization works correctly
- [ ] TM tree auto-mirrors file explorer folder structure
- [ ] TM assignment to folders/files works through the mirrored tree
- [ ] Translation search (exact + semantic) returns correct results
- [ ] Translation editing and saving works reliably
- [ ] Export workflow produces correct output files
- [ ] MapDataGenerator integration — image/audio mapping visible in the main grid
- [ ] Complete UI rework — production-quality, executive-demo-ready
- [ ] Settings UI — branches, drives, metadata reading
- [ ] All existing DB Factory/Repository pattern implementations work correctly

### Out of Scope

- Legacy app parity testing (XLSTransfer, KRSimilar) — deferred to future milestone
- QuickSearch integration into LocaNext — deferred
- QuickTranslate integration into LocaNext — deferred
- ExtractAnything integration into LocaNext — deferred
- QACompiler integration into LocaNext — deferred
- LanguageDataExporter integration into LocaNext — deferred
- Mobile app — not planned
- Multi-language UI (LocaNext itself) — not planned

## Context

- LocaNext has a mature architecture (Repository pattern, DB Factory, 3-mode detection) but the implementation has gaps — server startup errors, incomplete workflows, TM tree not mirroring file structure
- The DB abstraction layer is designed but needs validation that both SQLite and PostgreSQL implementations actually work identically across all operations
- Offline mode takes priority over online for demos — the user needs to showcase the product to executives without depending on a server
- MapDataGenerator is a standalone Python+tkinter tool that needs organic integration into LocaNext's grid UI
- The existing UI uses Carbon Components (IBM design system) but needs a complete rework for visual polish and professional presentation
- Landing page already has cinematic design — the app itself needs to match that quality level

## Constraints

- **Svelte 5 Runes only**: `$state`, `$derived`, `$effect` — no Svelte 4 patterns
- **Optimistic UI mandatory**: UI updates instantly, server syncs in background
- **No backend modifications**: Only wrapper layers (API, GUI) around core logic
- **Logger only**: Never `print()`, always `logger`
- **XML newlines**: `<br/>` tags only, never `&#10;`
- **Sacred Scripts**: XLSTransfer, KR Similar, QuickSearch core logic — never modify
- **Excel libs**: xlsxwriter for writing, openpyxl only for reading
- **Build pipeline**: Gitea CI for LocaNext, GitHub Actions for NewScripts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Offline mode priority over online | Need to demo to executives without server dependency | — Pending |
| MapDataGenerator as first NewScripts integration | Image/audio mapping is most visual and impressive for demos | — Pending |
| Full UI rework in this milestone | Can't demo to executives with rough UI | — Pending |
| Defer legacy app parity testing | Focus resources on making CAT tool work first | — Pending |

---
*Last updated: 2026-03-14 after initialization*
