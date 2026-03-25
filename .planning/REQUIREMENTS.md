# Requirements: LocaNext

**Defined:** 2026-03-25
**Core Value:** Real, working localization workflows with zero cloud dependency

## v11.0 Requirements

Requirements for Architecture & Test Infrastructure milestone. Enables safe future feature development by adding unit test coverage and decomposing the monolithic grid component.

### Test Infrastructure

- [ ] **TEST-01**: Vitest configured for Svelte 5 component testing with jsdom environment
- [ ] **TEST-02**: @testing-library/svelte installed and working with Svelte 5 runes ($state, $derived, $effect)
- [ ] **TEST-03**: Unit tests for tagDetector.js — all 6 patterns (combinedcolor, braced, color, memoq, placeholder, br-exclusion)
- [ ] **TEST-04**: Unit tests for TagText.svelte — pill rendering, combined pills, inline styles
- [ ] **TEST-05**: Unit tests for status color logic — 3-state scheme (empty/translated/confirmed)
- [ ] **TEST-06**: npm run test:unit script runs all component tests with coverage report

### VirtualGrid Decomposition

- [ ] **GRID-02**: VirtualGrid.svelte split into composable modules (target: no module > 800 lines)
- [ ] **GRID-03**: ScrollEngine module extracted — virtual scroll, row height calculation, viewport management
- [ ] **GRID-04**: CellRenderer module extracted — source/target/reference cell rendering, TagText integration
- [ ] **GRID-05**: SelectionManager module extracted — cell selection, keyboard navigation, multi-select
- [ ] **GRID-06**: InlineEditor module extracted — textarea editing, save/cancel, keyboard shortcuts
- [ ] **GRID-07**: StatusColors module extracted — 3-state status scheme, hover states, QA badge styling
- [ ] **GRID-08**: All existing E2E/Playwright tests pass after decomposition (zero regressions)

## Future Requirements

### TM Intelligence (v12.0 — Tribunal recommendation)

- **TM-06**: Contextual TM ranking (weight by file/scene context, speaker, recency)
- **TM-07**: Batch pre-translation with confidence scoring and threshold slider
- **TM-08**: One-click "pre-translate project" workflow

### Architecture (Deferred)

- **ARCH-02**: Split mega_index.py (1310 lines) into domain services

### Media Resolution

- **LDE2E-03**: Language data with images/audio resolves from Perforce-like paths

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend refactoring | v11.0 is frontend-only — backend is stable |
| New user-facing features | Architecture milestone — zero user-visible changes |
| mega_index.py split (ARCH-02) | Backend, lower urgency, defer to future |
| Tag pattern changes | v10.0 tag pills working correctly, don't touch |
| Performance optimization | Not the bottleneck — decomposition first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |
| TEST-03 | TBD | Pending |
| TEST-04 | TBD | Pending |
| TEST-05 | TBD | Pending |
| TEST-06 | TBD | Pending |
| GRID-02 | TBD | Pending |
| GRID-03 | TBD | Pending |
| GRID-04 | TBD | Pending |
| GRID-05 | TBD | Pending |
| GRID-06 | TBD | Pending |
| GRID-07 | TBD | Pending |
| GRID-08 | TBD | Pending |

**Coverage:**
- v11.0 requirements: 13 total
- Mapped to phases: 0
- Unmapped: 13 (pending roadmap)

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after initial definition*
