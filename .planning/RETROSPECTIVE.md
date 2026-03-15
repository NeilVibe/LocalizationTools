# Retrospective

## Milestone: v1.0 — Demo-Ready CAT Tool

**Shipped:** 2026-03-15
**Phases:** 7 | **Plans:** 20

### What Was Built
1. 451+ repository parity tests across 9 interfaces, 3 DB modes, with schema drift guards
2. Production-quality translation grid with virtual scroll, race-condition-free save, 3-state status colors
3. TM auto-mirror tree, leverage stats, CJK-aware word diff, tabbed side panel
4. Model2Vec + FAISS semantic search with sub-second performance and AI-suggested badges
5. MapDataGenerator image/audio context tabs with BranchDrive settings
6. Aho-Corasick entity detection, GlossaryService, Line Check, Term Check, QAFooter, ContextTab
7. Full offline workflow E2E validation with 3-mode factory routing

### What Worked
- **GSD phase structure** — clear dependency ordering prevented rework
- **Test-first approach** — each phase shipped with validation, no regressions
- **Reuse strategy** — QuickSearch/QuickCheck patterns (AC automaton, noise filter) ported cleanly
- **Single-day sprint** — focused execution without context switches
- **Mock fixtures** — enabled rapid iteration without real game data dependencies

### What Was Inefficient
- Phase 5.1 directory naming (`051-`) not detected by GSD CLI tools — had to manually verify
- STATE.md accumulated duplicate frontmatter blocks during rapid execution
- Some decisions accumulated in STATE.md that should have been in PROJECT.md from the start

### Patterns Established
- `isConfirming` + `isCancellingEdit` double-guard for async Svelte 5 confirm flows
- Multi-key index pattern (StrKey/StringID/KnowledgeKey → same entry)
- Service degradation pattern (return empty, not errors, when unconfigured)
- FastAPI `dependency_overrides` for route-level test isolation
- `socketio.ASGIApp.other_asgi_app` for TestClient access to inner FastAPI

### Key Lessons
- v1.0 is scaffold — real validation happens when wiring actual XML game data in v2.0
- Schema drift between SQLite/PostgreSQL should be documented and tested, not assumed matching
- Carbon Components need significant CSS overrides for executive-quality polish

### Cost Observations
- Model mix: 100% opus (quality profile)
- Sessions: ~3-4 focused sessions
- Notable: 20 plans in ~3.5 hours average — GSD parallelization worked well

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 7 |
| Plans | 20 |
| Requirements | 42 |
| Avg plan duration | ~10min |
| Rework incidents | 0 |
