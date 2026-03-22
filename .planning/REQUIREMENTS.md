# Requirements: LocaNext

**Defined:** 2026-03-22
**Core Value:** Real, working localization workflows with zero cloud dependency, dual-mode for translators and game developers.

## v6.0 Requirements

Requirements for Architecture & Code Quality milestone. Each maps to roadmap phases.

### Component Decomposition

- [ ] **COMP-01**: VirtualGrid.svelte split into focused modules — virtual scroll, search/filter, cell editing, TM leverage, QA layer (each under 800 lines)
- [ ] **COMP-02**: FilesPage.svelte split into explorer navigation, context menu operations, and upload manager
- [ ] **COMP-03**: All split components maintain identical end-user behavior (no regression)

### Service Decomposition

- [ ] **SVC-01**: mega_index.py split into builder (XML parsing), indexes (35 dict construction), and lookup (O(1) retrieval API)
- [ ] **SVC-02**: codex_service.py split into entity registry and search modules
- [ ] **SVC-03**: gamedata_context_service.py split into reverse index and cross-ref resolver

### Route Thinning

- [ ] **ROUTE-01**: files.py business logic extracted to dedicated services (file validation, TM registration, merge coordination) — route file under 400 lines
- [ ] **ROUTE-02**: sync.py business logic extracted to services — route file under 400 lines

### Test Infrastructure

- [ ] **TEST-01**: Unit test structure created for backend services with conftest.py fixtures and mock DB layer
- [ ] **TEST-02**: Unit tests for mega_index (builder, lookup), codex_service, and gamedata_context_service — minimum 30 test cases
- [ ] **TEST-03**: Component test structure created for split Svelte components

### UI Bug Fixes

- [ ] **UIFIX-01**: Right-click context menu works on file explorer panel
- [ ] **UIFIX-02**: All known non-blocking issues from v5.1 audit addressed (audioContext residue, AI capabilities 404 handling)

## Future Requirements

### Performance Optimization
- **PERF-01**: VirtualGrid scroll performance benchmarked and optimized after split
- **PERF-02**: MegaIndex build time profiled and optimized

### Deep Refactoring
- **DEEP-01**: Service layer organized by domain (codex/, gamedata/, merge/, ai/, shared/)
- **DEEP-02**: Full route layer thinning (all 38 route files under 400 lines)

## Out of Scope

| Feature | Reason |
|---------|--------|
| New user-facing features | Architecture milestone — no feature additions |
| Database schema changes | Refactoring code structure, not data model |
| UI redesign | Split components maintain same visual appearance |
| Full test coverage (80%+) | Foundation only — 30+ tests for critical services |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-01 | Phase 58 | Pending |
| COMP-02 | Phase 59 | Pending |
| COMP-03 | Phase 60 | Pending |
| SVC-01 | Phase 56 | Pending |
| SVC-02 | Phase 56 | Pending |
| SVC-03 | Phase 56 | Pending |
| ROUTE-01 | Phase 57 | Pending |
| ROUTE-02 | Phase 57 | Pending |
| TEST-01 | Phase 60 | Pending |
| TEST-02 | Phase 60 | Pending |
| TEST-03 | Phase 60 | Pending |
| UIFIX-01 | Phase 59 | Pending |
| UIFIX-02 | Phase 59 | Pending |

**Coverage:**
- v6.0 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after roadmap creation*
