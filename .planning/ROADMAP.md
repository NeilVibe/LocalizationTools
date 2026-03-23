# Roadmap: LocaNext v7.0 Production-Ready Merge + Performance + UIUX

## Overview

Make the merge pipeline production-ready by internalizing QuickTranslate logic (replacing sys.path adapter with PyInstaller-safe module), enabling automatic TM-to-FAISS flow on every edit/add, adding performance instrumentation across all hot paths, and polishing UIUX via AI-powered visual critique.

## Phases

- [ ] **Phase 61: Merge Internalization** - Internalize QT merge logic into LocaNext's own module (no sys.path, PyInstaller-safe) with all 3 match types, postprocess, and SSE
- [ ] **Phase 62: TM Auto-Update Pipeline** - Automatic embedding generation and incremental HNSW updates on every TM add/edit/batch import
- [ ] **Phase 63: Performance Instrumentation** - Duration logging across Model2Vec, FAISS, TM CRUD, merge, file upload, plus summary API endpoint
- [ ] **Phase 64: UIUX Quality Audit** - AI visual audit of all 5 pages via Qwen Vision, fix critical issues, polish merge modal

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
**Plans**: TBD

### Phase 62: TM Auto-Update Pipeline
**Goal**: Users get a fully automatic TM flow where every add/edit immediately updates embeddings and FAISS index -- search always returns current results with zero manual intervention
**Depends on**: Nothing (independent of Phase 61)
**Requirements**: TMAU-01, TMAU-02, TMAU-03, TMAU-04, TMAU-05
**Success Criteria** (what must be TRUE):
  1. Adding a new TM entry via the UI immediately generates its embedding and adds it to the HNSW index without any full rebuild
  2. Editing an existing TM entry re-computes the embedding and updates the HNSW index in-place (old vector removed, new vector inserted)
  3. Batch importing TM entries (e.g., from file upload) triggers bulk embedding generation and batch HNSW add_items in a single pass
  4. Searching for a term that was just added or edited returns the updated entry in the results without any manual refresh or page reload
**Plans**: TBD

### Phase 63: Performance Instrumentation
**Goal**: Every hot path in the application logs its duration so developers can identify bottlenecks and users can verify performance via API
**Depends on**: Phase 61, Phase 62
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06
**Success Criteria** (what must be TRUE):
  1. Model2Vec embedding generation, FAISS/HNSW search, and TM add/edit operations all emit structured log lines with duration in milliseconds
  2. Merge preview and execute operations log duration per step (scan, match, postprocess, write) with step-level granularity
  3. File upload operations log duration and file size in a single structured log line
  4. GET /api/performance/summary returns a JSON response with p50/p95/max timings for each instrumented operation over the last N requests
**Plans**: TBD

### Phase 64: UIUX Quality Audit
**Goal**: All 5 main pages pass AI-powered visual critique and the merge modal handles every edge case gracefully
**Depends on**: Phase 61, Phase 62, Phase 63
**Requirements**: UIUX-01, UIUX-02, UIUX-03
**Success Criteria** (what must be TRUE):
  1. Qwen Vision screenshots of all 5 main pages (Files, Game Dev, Codex, Map, TM) have been reviewed and all critical issues cataloged
  2. All critical UIUX issues (alignment, spacing, contrast, truncation) identified by the AI audit are fixed and verified with follow-up screenshots
  3. Merge modal handles loading states (spinner during preview/execute), error states (clear error message + retry), and edge cases (empty project, no matches found, cancelled merge) gracefully
**Plans**: TBD

## Progress

**Execution Order:**
Phase 61 first. Phase 62 can run in parallel with 61 (independent). Phase 63 after both 61 and 62. Phase 64 last.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 61. Merge Internalization | v7.0 | 0/0 | Not started | - |
| 62. TM Auto-Update Pipeline | v7.0 | 0/0 | Not started | - |
| 63. Performance Instrumentation | v7.0 | 0/0 | Not started | - |
| 64. UIUX Quality Audit | v7.0 | 0/0 | Not started | - |
