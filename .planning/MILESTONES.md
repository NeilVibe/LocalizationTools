# Milestones

## v2.0 Real Data + Dual Platform (Shipped: 2026-03-15)

**Phases completed:** 8 phases, 17 plans
**Timeline:** 2026-03-15 (single day sprint — all phases planned, executed, reviewed, and fixed)
**Requirements:** 40/40 complete
**Tests:** 478 total LDM tests (254 new), zero regressions
**Post-milestone review:** 11 issues found and fixed (2 critical runtime crashes, 1 merge logic bug, 8 quality/security)

**Key accomplishments:**
1. **XML Parsing Foundation** — XMLParsingEngine with lxml, 5-step sanitizer, language tables, StringIdConsumer, 3 bug fixes (offline TM visibility, TM paste, folder 404)
2. **Dual UI Mode** — Auto-detect LocStr vs Game Dev file types, column switching, mode badge, state reset, inline editing guard
3. **Translator Merge** — 4 match modes (strict→stringid_only→strorigin_only→fuzzy), 5 skip guards, cascade, ported from QuickTranslate
4. **8-Step Postprocess + Export** — CJK-safe pipeline with br-tag defense, XML/Excel(14-col EU)/text export via ExportService
5. **Image & Audio Pipeline** — DDS→PNG (Pillow native), WEM→WAV (vgmstream-cli), LRU/disk cache, API streaming endpoints
6. **Game Dev Merge** — Novel parallel tree walk diff algorithm, position-based matching, in-place lxml modification, bulk_update extra_data
7. **AI Summaries** — Qwen3-4B via Ollama (httpx async), per-StringID cache, graceful "AI unavailable" fallback, ContextTab integration
8. **E2E Validation + CLI** — Full round-trip tests (parse→merge→export→re-parse→compare), CLI merge/export/detect commands

**Archive:** [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) | [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)

---

## v1.0 Demo-Ready CAT Tool (Shipped: 2026-03-15)

**Phases completed:** 7 phases, 20 plans
**Timeline:** 2026-03-14 (single day sprint — all phases planned and executed)
**Requirements:** 42/42 complete

**Key accomplishments:**
1. **Stability Foundation** — 451 parity tests across 9 repositories, 3 DB modes, schema drift guards, startup reliability with zero zombie processes
2. **Editor Core** — Race-condition-free Ctrl+S save, 3-state status colors, virtual scroll 10K+ segments, XML export with br-tag preservation
3. **TM Workflow** — Auto-mirror TM tree, leverage stats (exact/fuzzy/new), CJK-aware word diff, tabbed RightPanel
4. **Semantic Search** — Model2Vec + FAISS semantic search endpoint, sub-second performance, AI-suggested badges in grid
5. **Visual Polish + MapData** — BranchDrive settings modal, image/audio context tabs, tab fade-in transitions
6. **Contextual Intelligence & QA** — Aho-Corasick entity detection, GlossaryService, Line Check, Term Check, ContextTab with EntityCards, QAFooter
7. **Offline Validation** — Full offline workflow E2E, 3-mode factory routing, API smoke tests in SQLite mode

**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

---

