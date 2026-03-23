# Requirements: LocaNext v7.0 Production-Ready Merge + Performance + UIUX

**Defined:** 2026-03-23
**Core Value:** Real, working localization workflows with zero cloud dependency

## v1 Requirements

### Merge Architecture

- [x] **MARCH-01**: Merge logic runs without sys.path injection or importlib hacks -- fully internalized, PyInstaller-safe
- [x] **MARCH-02**: All 3 match types (stringid_only, strict, strorigin_filename) work with internalized module
- [x] **MARCH-03**: Postprocess 8-step pipeline runs from internalized module
- [x] **MARCH-04**: SSE execute endpoint streams events correctly with internalized module

### Performance Monitoring

- [ ] **PERF-01**: Model2Vec embedding generation logs duration per batch
- [ ] **PERF-02**: FAISS/HNSW search logs duration per query
- [ ] **PERF-03**: TM entry add/edit logs duration including embedding + index update
- [ ] **PERF-04**: Merge preview/execute logs duration per step (scan, match, write)
- [ ] **PERF-05**: File upload logs duration and file size
- [ ] **PERF-06**: Performance summary accessible via API endpoint

### TM Auto-Update

- [ ] **TMAU-01**: TM entry add triggers automatic embedding generation
- [ ] **TMAU-02**: TM entry add triggers incremental HNSW add_items (no full rebuild)
- [ ] **TMAU-03**: TM entry edit triggers embedding re-computation + HNSW update
- [ ] **TMAU-04**: TM batch import triggers bulk embedding + HNSW batch add
- [ ] **TMAU-05**: Search returns updated results immediately after add/edit (no manual refresh)

### UIUX Quality

- [ ] **UIUX-01**: AI visual audit of all 5 main pages via Qwen Vision screenshots
- [ ] **UIUX-02**: Critical UIUX issues identified and fixed (alignment, spacing, contrast)
- [ ] **UIUX-03**: Merge modal polished (loading states, error states, edge cases)

## v2 Requirements

### Build Verification

- **BUILD-01**: PyInstaller bundle includes internalized merge module
- **BUILD-02**: Bundled app runs merge workflow end-to-end without QT source tree

### Extended Performance

- **PERF-07**: Performance regression alerts (if step exceeds baseline by >2x)
- **PERF-08**: Historical performance trending (store metrics over time)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full QT port (all features) | Only merge/transfer functions needed -- Sacred Scripts stay as reference |
| Cloud-based performance monitoring | Local logging only -- zero cloud dependency |
| Automated UIUX testing pipeline | Manual audit with AI assistance sufficient for v7.0 |
| Real-time performance dashboard UI | API endpoint + logs sufficient for v7.0 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MARCH-01 | Phase 61 | Complete |
| MARCH-02 | Phase 61 | Complete |
| MARCH-03 | Phase 61 | Complete |
| MARCH-04 | Phase 61 | Complete |
| PERF-01 | Phase 63 | Pending |
| PERF-02 | Phase 63 | Pending |
| PERF-03 | Phase 63 | Pending |
| PERF-04 | Phase 63 | Pending |
| PERF-05 | Phase 63 | Pending |
| PERF-06 | Phase 63 | Pending |
| TMAU-01 | Phase 62 | Pending |
| TMAU-02 | Phase 62 | Pending |
| TMAU-03 | Phase 62 | Pending |
| TMAU-04 | Phase 62 | Pending |
| TMAU-05 | Phase 62 | Pending |
| UIUX-01 | Phase 64 | Pending |
| UIUX-02 | Phase 64 | Pending |
| UIUX-03 | Phase 64 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after roadmap creation*
