# Roadmap: LocaNext v8.0 Tag Visualizer + Service Layer Extraction

## Overview

MemoQ-style tag pills for translators (Phase 73 — user-facing, do first) + service layer extraction from 6 thick API modules (Phases 69-72 — architecture).

## Phases

- [ ] **Phase 73: Regex Tag Visualizer** - MemoQ-style inline tag pills ({0}, %1#, \n → colored badges) in VirtualGrid editor
- [ ] **Phase 69: Stats & Rankings Service** - Extract StatsService + RankingsService from stats.py (1371) + rankings.py (608)
- [ ] **Phase 70: Auth Service** - Extract AuthService from auth_async.py (629)
- [ ] **Phase 71: Telemetry & Remote Logging** - Extract TelemetryService + RemoteLoggingService (1185 lines)
- [ ] **Phase 72: Infrastructure Services** - Extract DbHealth + Health + Progress services (1009 lines)

## Phase Details

### Phase 61: Merge Internalization
**Goal**: Merge logic runs as a self-contained LocaNext module without any sys.path injection, importlib hacks, or dependency on the QT source tree -- ready for PyInstaller bundling
**Depends on**: Nothing (first phase)
**Requirements**: MARCH-01, MARCH-02, MARCH-03, MARCH-04
**Success Criteria** (what must be TRUE):
  1. Merge executes successfully with no sys.path manipulation anywhere in the import chain -- the internalized module lives under server/services/ and imports cleanly
  2. All 3 match types (stringid_only, strict, strorigin_filename) produce identical merge output to the v6.0 sys.path adapter when run against the same test data
  3. The 8-step postprocess pipeline runs from the internalized module and produces output identical to QuickTranslate standalone
  4. SSE merge execution endpoint streams progress events correctly using the internalized module (no regressions from v6.0)
**Plans:** 2/2 plans complete

Plans:
- [x] 61-01-PLAN.md -- Create server/services/merge/ package with 14 QT modules + internal config
- [x] 61-02-PLAN.md -- Rewire transfer_adapter.py, remove old hacks, integration tests

### Phase 62: TM Auto-Update Pipeline
**Goal**: Users get a fully automatic TM flow where every add/edit immediately updates embeddings and FAISS index -- search always returns current results with zero manual intervention
**Depends on**: Nothing (independent of Phase 61)
**Requirements**: TMAU-01, TMAU-02, TMAU-03, TMAU-04, TMAU-05
**Success Criteria** (what must be TRUE):
  1. Adding a new TM entry via the UI immediately generates its embedding and adds it to the HNSW index without any full rebuild
  2. Editing an existing TM entry re-computes the embedding and updates the HNSW index in-place (old vector removed, new vector inserted)
  3. Batch importing TM entries (e.g., from file upload) triggers bulk embedding generation and batch HNSW add_items in a single pass
  4. Searching for a term that was just added or edited returns the updated entry in the results without any manual refresh or page reload
**Plans:** 3/3 plans complete

Plans:
- [x] 62-01-PLAN.md -- Extend FAISSManager with IDMap2 support + create InlineTMUpdater service
- [x] 62-02-PLAN.md -- Wire inline updates into CRUD endpoints + batch import + search consistency
- [x] 62-03-PLAN.md -- Gap closure: Add line-level FAISS persistence to InlineTMUpdater (Tier 4 fix)

### Phase 63: Performance Instrumentation
**Goal**: Every hot path in the application logs its duration so developers can identify bottlenecks and users can verify performance via API
**Depends on**: Phase 61, Phase 62
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06
**Success Criteria** (what must be TRUE):
  1. Model2Vec embedding generation, FAISS/HNSW search, and TM add/edit operations all emit structured log lines with duration in milliseconds
  2. Merge preview and execute operations log duration per step (scan, match, postprocess, write) with step-level granularity
  3. File upload operations log duration and file size in a single structured log line
  4. GET /api/performance/summary returns a JSON response with p50/p95/max timings for each instrumented operation over the last N requests
**Plans:** 2/2 plans complete

Plans:
- [x] 63-01-PLAN.md -- Create PerfTimer utility + instrument all hot paths (embedding, FAISS, TM CRUD, merge, upload)
- [x] 63-02-PLAN.md -- Create GET /api/performance/summary endpoint with p50/p95/max stats

### Phase 64: UIUX Quality Audit
**Goal**: All 5 main pages pass AI-powered visual critique and the merge modal handles every edge case gracefully
**Depends on**: Phase 61, Phase 62, Phase 63
**Requirements**: UIUX-01, UIUX-02, UIUX-03
**Success Criteria** (what must be TRUE):
  1. Qwen Vision screenshots of all 5 main pages (Files, Game Dev, Codex, Map, TM) have been reviewed and all critical issues cataloged
  2. All critical UIUX issues (alignment, spacing, contrast, truncation) identified by the AI audit are fixed and verified with follow-up screenshots
  3. Merge modal handles loading states (spinner during preview/execute), error states (clear error message + retry), and edge cases (empty project, no matches found, cancelled merge) gracefully
**Plans:** 1/2 plans complete

Plans:
- [x] 64-01-PLAN.md -- Harden merge modal: preview retry, zero-match guard, AbortController cancel, error recovery, adaptive done messaging
- [ ] 64-02-PLAN.md -- AI visual audit of all 5 pages via Qwen Vision (requires live servers)

## Progress

**Execution Order:**
Phase 61 first. Phase 62 can run in parallel with 61 (independent). Phase 63 after both 61 and 62. Phase 64 last.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 61. Merge Internalization | v7.0 | 2/2 | Complete    | 2026-03-23 |
| 62. TM Auto-Update Pipeline | v7.0 | 3/3 | Complete    | 2026-03-23 |
| 63. Performance Instrumentation | v7.0 | 2/2 | Complete    | 2026-03-23 |
| 64. UIUX Quality Audit | v7.0 | 1/2 | Complete    | 2026-03-23 |
