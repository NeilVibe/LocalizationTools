# Milestones

## v3.2 GameData Tree UI + Context Intelligence + Image Gen (Shipped: 2026-03-16)

**Phases:** 26-31 (6 phases, 12 plans)
**Requirements:** 25/25 complete (5 categories: TREE, IDX, CTX, IMG, NAV)
**Goal:** Rework Game Data page from flat grid to hierarchical XML tree navigator, add right-side context panel with TM/images/audio/AI context via 5-tier cascade search, generate AI images for Codex, and achieve sub-second lookup via multi-tier indexing.

**Phase structure:**
1. Phase 26: Navigation + DEV Parity (sidebar rename, folder picker, auto-load, file type separation)
2. Phase 27: Tree Backend + Mock Data (lxml tree walker API, expanded hierarchical mock fixtures)
3. Phase 28: Hierarchical Tree UI (expandable tree, node detail panel, cross-refs, visual polish)
4. Phase 29: Multi-Tier Indexing (hashtable + FAISS + Aho-Corasick, auto-glossary, <3s performance)
5. Phase 30: Context Intelligence Panel (TM suggestions, images, audio, 5-tier cascade search, cross-refs)
6. Phase 31: Codex AI Image Generation (Nano Banana / Gemini, entity-type prompts, batch mode)

---

## v3.1 Debug + Polish + Svelte 5 Migration (Shipped: 2026-03-16)

**Phases completed:** 4 phases, 19 plans
**Requirements:** 48/48 complete (4 categories: SV5, FIX, UX, TEST-E2E)

**Key accomplishments:**
1. **Svelte 5 Migration** -- 36 components purged of createEventDispatcher and on: directives, pure $props callbacks
2. **Bug Fixes** -- 12 runtime bugs fixed (GameDev upload-path, audio fallback, NPC nav, tooltip, loading states)
3. **UIUX Polish** -- 60 audit issues resolved (aria-expanded, tab dividers, PlaceholderImage, image fallback, text wrap)
4. **API E2E Testing** -- 834 test functions, 40 files, 275 endpoints, mock expansion to 10 StaticInfo types

**Archive:** [v3.1-ROADMAP.md](milestones/v3.1-ROADMAP.md) | [v3.1-REQUIREMENTS.md](milestones/v3.1-REQUIREMENTS.md)

---

## v3.0 Game Dev Platform + AI Intelligence (Shipped: 2026-03-15)

**Phases completed:** 7 phases, 14 plans
**Requirements:** 45/45 complete (9 categories)
**Post-milestone review:** 9 issues found and fixed (1 build-breaking, 2 critical, 6 important)

**Key accomplishments:**
1. **Mock Gamedata Universe** -- Generator script producing 352 entities across 6 types, 704 StringIDs, cross-reference chains, binary media stubs
2. **Category Clustering** -- Auto-classification from StringID prefixes, grid column, multi-select filter
3. **QA Pipeline** -- Term Check + Line Check inline badges, dismiss workflow, severity thresholds
4. **AI Translation Suggestions** -- Qwen3-powered ranked suggestions with blended confidence scores, click-to-accept
5. **Game Dev Grid + File Explorer** -- VS Code-like tree, hierarchical XML editing, dynamic columns per entity type
6. **Game World Codex** -- Interactive encyclopedia with semantic search, DDS/WEM media, cross-references
7. **Interactive World Map** -- d3-zoom SVG with positioned region nodes, route connections, Codex links
8. **AI Naming Coherence + Placeholders** -- FAISS similarity search, Qwen3 naming suggestions, styled SVG placeholders

**Archive:** [v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md) | [v3.0-REQUIREMENTS.md](milestones/v3.0-REQUIREMENTS.md)

---

## v2.0 Real Data + Dual Platform (Shipped: 2026-03-15)

**Phases completed:** 8 phases, 17 plans
**Timeline:** 2026-03-15 (single day sprint -- all phases planned, executed, reviewed, and fixed)
**Requirements:** 40/40 complete
**Tests:** 478 total LDM tests (254 new), zero regressions
**Post-milestone review:** 11 issues found and fixed (2 critical runtime crashes, 1 merge logic bug, 8 quality/security)

**Key accomplishments:**
1. **XML Parsing Foundation** -- XMLParsingEngine with lxml, 5-step sanitizer, language tables, StringIdConsumer, 3 bug fixes (offline TM visibility, TM paste, folder 404)
2. **Dual UI Mode** -- Auto-detect LocStr vs Game Dev file types, column switching, mode badge, state reset, inline editing guard
3. **Translator Merge** -- 4 match modes (strict->stringid_only->strorigin_only->fuzzy), 5 skip guards, cascade, ported from QuickTranslate
4. **8-Step Postprocess + Export** -- CJK-safe pipeline with br-tag defense, XML/Excel(14-col EU)/text export via ExportService
5. **Image & Audio Pipeline** -- DDS->PNG (Pillow native), WEM->WAV (vgmstream-cli), LRU/disk cache, API streaming endpoints
6. **Game Dev Merge** -- Novel parallel tree walk diff algorithm, position-based matching, in-place lxml modification, bulk_update extra_data
7. **AI Summaries** -- Qwen3-4B via Ollama (httpx async), per-StringID cache, graceful "AI unavailable" fallback, ContextTab integration
8. **E2E Validation + CLI** -- Full round-trip tests (parse->merge->export->re-parse->compare), CLI merge/export/detect commands

**Archive:** [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) | [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)

---

## v1.0 Demo-Ready CAT Tool (Shipped: 2026-03-15)

**Phases completed:** 7 phases, 20 plans
**Timeline:** 2026-03-14 (single day sprint -- all phases planned and executed)
**Requirements:** 42/42 complete

**Key accomplishments:**
1. **Stability Foundation** -- 451 parity tests across 9 repositories, 3 DB modes, schema drift guards, startup reliability with zero zombie processes
2. **Editor Core** -- Race-condition-free Ctrl+S save, 3-state status colors, virtual scroll 10K+ segments, XML export with br-tag preservation
3. **TM Workflow** -- Auto-mirror TM tree, leverage stats (exact/fuzzy/new), CJK-aware word diff, tabbed RightPanel
4. **Semantic Search** -- Model2Vec + FAISS semantic search endpoint, sub-second performance, AI-suggested badges in grid
5. **Visual Polish + MapData** -- BranchDrive settings modal, image/audio context tabs, tab fade-in transitions
6. **Contextual Intelligence & QA** -- Aho-Corasick entity detection, GlossaryService, Line Check, Term Check, ContextTab with EntityCards, QAFooter
7. **Offline Validation** -- Full offline workflow E2E, 3-mode factory routing, API smoke tests in SQLite mode

**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

---
