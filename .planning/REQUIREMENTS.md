# Requirements: LocaNext

**Defined:** 2026-03-25
**Core Value:** Real, working localization workflows with zero cloud dependency

## v11.0 Requirements

Requirements for Architecture & Test Infrastructure milestone. Enables safe future feature development by adding unit test coverage and decomposing the monolithic grid component.

### Test Infrastructure

- [x] **TEST-01**: Vitest configured for Svelte 5 component testing with jsdom environment
- [x] **TEST-02**: @testing-library/svelte installed and working with Svelte 5 runes ($state, $derived, $effect)
- [x] **TEST-03**: Unit tests for tagDetector.js — all 6 patterns (combinedcolor, braced, color, memoq, placeholder, br-exclusion)
- [x] **TEST-04**: Unit tests for TagText.svelte — pill rendering, combined pills, inline styles
- [x] **TEST-05**: Unit tests for status color logic — 3-state scheme (empty/translated/confirmed)
- [x] **TEST-06**: npm run test:unit script runs all component tests with coverage report

### VirtualGrid Decomposition

- [x] **GRID-02**: VirtualGrid.svelte split into composable modules (target: no module > 800 lines)
- [x] **GRID-03**: ScrollEngine module extracted — virtual scroll, row height calculation, viewport management
- [x] **GRID-04**: CellRenderer module extracted — source/target/reference cell rendering, TagText integration
- [x] **GRID-05**: SelectionManager module extracted — cell selection, keyboard navigation, multi-select
- [ ] **GRID-06**: InlineEditor module extracted — textarea editing, save/cancel, keyboard shortcuts
- [x] **GRID-07**: StatusColors module extracted — 3-state status scheme, hover states, QA badge styling
- [ ] **GRID-08**: All existing E2E/Playwright tests pass after decomposition (zero regressions)

## Future Requirements

### TM Intelligence (v12.0 — Tribunal recommendation)

- **TM-06**: Contextual TM ranking (weight by file/scene context, speaker, recency)
- **TM-07**: Batch pre-translation with confidence scoring and threshold slider
- **TM-08**: One-click "pre-translate project" workflow

### LAN Server Mode (Demo/Sync — future milestone)

- **LAN-01**: Installer "Admin Advanced" button → "Set up as LAN Server for Sync" option
- **LAN-02**: Installer shows available network interfaces, user picks their IP address
- **LAN-03**: Installer configures PostgreSQL `listen_addresses` and `pg_hba.conf` for LAN trust (internal IP range, no password)
- **LAN-04**: Backend binds to `0.0.0.0:8888` (not localhost) when LAN server mode enabled
- **LAN-05**: Client Settings UI: "Online Server" section with IP input field (like FileZilla) to connect to LAN server
- **LAN-06**: WebSocket sync works over LAN between server machine and client machines
- **LAN-07**: Robust Windows App offline testing — upload and test files in stable offline environment

**Context:** For demo/presentation purposes. User's machine becomes the central server, other internal machines connect via IP. Down the line this will be replaced by a dedicated server setup. Existing architecture already supports this (CENTRAL_SERVER_URL, configurable postgres_host, repository pattern with factory injection, Socket.IO sync). Main work: installer config + Settings UI + PostgreSQL LAN exposure.

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
| TEST-01 | Phase 83 | Complete |
| TEST-02 | Phase 83 | Complete |
| TEST-03 | Phase 83 | Complete |
| TEST-04 | Phase 83 | Complete |
| TEST-05 | Phase 83 | Complete |
| TEST-06 | Phase 83 | Complete |
| GRID-02 | Phase 84 | Complete |
| GRID-03 | Phase 84 | Complete |
| GRID-04 | Phase 84 | Complete |
| GRID-05 | Phase 84 | Complete |
| GRID-06 | Phase 84 | Pending |
| GRID-07 | Phase 84 | Complete |
| GRID-08 | Phase 85 | Pending |

**Coverage:**
- v11.0 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after roadmap creation (Phase 83-85)*
