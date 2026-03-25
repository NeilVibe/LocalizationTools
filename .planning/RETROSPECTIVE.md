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

## Milestone: v9.0 — Build Validation + Real-World Testing

**Shipped:** 2026-03-25
**Phases:** 6 | **Plans:** 14

### What Was Built
1. Perforce-path mock gamedata universe (DDS/WEM/XML across 4 languages)
2. GitHub Actions Light Build CI pipeline with merge module verification
3. 63+ E2E tests covering language data upload, TM cascade, merge, QA, entity detection
4. Qwen3-VL visual audit of all 5 pages (8.6/10 average after fixes)
5. Windows installer verified on offline PC — file upload works end-to-end
6. 6 CVE security fixes + 12+ build hardening commits

### What Worked
- **Build-first mentality** — forcing actual Windows install exposed real bugs (PYTHONPATH, DATABASE_MODE, portproxy)
- **Qwen3-VL as reviewer** — caught type labels and status column issues human eyes missed
- **xfail strategy** — marking gamedata-dependent tests as xfail kept CI green while documenting real gaps
- **Light Build** — fast iteration cycle vs full 7-stage QA suite
- **Security audit early** — 6 CVEs fixed before they became deployment blockers

### What Was Inefficient
- STATE.md got stale during rapid build-fix-rebuild cycles (manual updates fell behind)
- 4 GitHub Actions builds failed before deps were right — each failure = 15min wait
- Portproxy conflict wasn't caught until Playground testing (WSL2 environment-specific)

### Patterns Established
- `DATABASE_MODE=sqlite` forced in Electron (never auto-detect for desktop)
- Post-build Model2Vec copy (EBUSY fix for extraResources)
- `resources/` in PYTHONPATH for embedded Python
- Light Build for fast CI iteration, full QA for milestones

### Key Lessons
- Windows testing must happen EARLY, not as last phase — environment issues compound
- Security audits should be routine (6 CVEs accumulated silently)
- Qwen3-VL should review EVERY visual change, not just at milestone end

### Cost Observations
- Model mix: 100% opus (quality profile)
- Sessions: 2 focused sessions (build hardening + verification)
- Notable: 14 plans in ~49 min total execution — 3.5 min average per plan

---

## Milestone: v10.0 — UI Polish + Tag Pill Redesign

**Shipped:** 2026-03-25
**Phases:** 3 | **Plans:** 3

### What Was Built
1. Combined color+format tag pills with dynamic hex-tinted inline styling and br-tag exclusion
2. Neutral grid background (#222222) replacing amber-dominant visual, status colors preserved
3. Qwen3-VL visual verification across all 5 LocaNext pages (avg 7.4/10)

### What Worked
- **Smallest milestone yet** — 3 phases, 3 plans, completed same day as planned
- **Tribunal for next direction** — 3-expert panel produced clear v11.0 recommendation
- **Qwen3-VL review** — automated visual QA catches issues humans miss
- **CSS-only changes** — zero backend risk, immediate HMR feedback

### What Was Inefficient
- Phase 82 (visual verification) required starting backend server manually — should auto-detect
- Qwen3-VL not on OpenViking port 8100, had to use Ollama directly — inconsistent stack
- Phase 81 plan was trivial (2-line CSS change) — could have been inlined without full GSD plan cycle

### Patterns Established
- `combinedcolor` as priority-0 pattern prevents braced pattern from claiming inner `{code}`
- Dynamic inline styles for hex colors rather than fixed CSS classes per color value
- Tribunal decision-making for strategic direction at milestone boundaries

### Key Lessons
- Small UI polish milestones are valuable — ship fast, validate with Qwen3-VL, move on
- Tribunal works best for strategic decisions, not tactical ones
- GSD overhead scales down well for small milestones (3 phases = ~2 hours total)

## Cross-Milestone Trends

| Metric | v1.0 | v9.0 | v10.0 |
|--------|------|------|-------|
| Phases | 7 | 6 | 3 |
| Plans | 20 | 14 | 3 |
| Requirements | 42 | 29 | 5 |
| Avg plan duration | ~10min | ~3.5min | ~5min |
| Rework incidents | 0 | 1 (STATE.md staleness) | 0 |
