# Requirements: LocaNext v3.3

**Defined:** 2026-03-17
**Core Value:** All 5 pages polished to production quality -- consistent, performant, beautiful, one unified app experience.

## v3.3 Requirements

### FND -- Design Foundation

- [x] **FND-01**: CSS custom properties defined in app.css for spacing scale, color tokens, shadow tokens, and border-radius -- all pages use tokens instead of hardcoded values
- [x] **FND-02**: Shared PageHeader component with consistent padding, title styling, and optional action slot used across all 5 pages
- [x] **FND-03**: Shared SkeletonCard component matching Codex card dimensions for loading states
- [x] **FND-04**: Shared EmptyState component (icon + headline + description + optional CTA) used when pages have no data
- [x] **FND-05**: Shared ErrorState component (error message + retry button) used for inline error recovery on all pages
- [x] **FND-06**: Shared InfiniteScroll component using IntersectionObserver with $effect cleanup for paginated loading

### CDX -- Codex Revamp

- [x] **CDX-01**: Codex loads entities in pages of 50 via paginated API (offset/limit) instead of loading all at once
- [x] **CDX-02**: IntersectionObserver sentinel triggers next page load as user scrolls near bottom
- [x] **CDX-03**: Skeleton cards show during page load, matching real card dimensions
- [x] **CDX-04**: Entity images use loading="lazy" with placeholder shown until image enters viewport
- [ ] **CDX-05**: Search-first UX -- search bar prominent at top, results update as user types with debounce
- [ ] **CDX-06**: Category tabs with counts, cached per tab so switching is instant
- [x] **CDX-07**: Codex feels like a polished encyclopedia -- consistent card sizes, smooth transitions, no layout shift

### GDT -- GameData Tree Polish

- [ ] **GDT-01**: GameData Tree page passes full UI/UX audit (spacing, colors, dark mode, empty states, loading states)
- [ ] **GDT-02**: Node detail panel has consistent spacing, proper typography hierarchy, and smooth transitions
- [ ] **GDT-03**: Context Intelligence Panel (right panel) has polished tabs, loading states, and empty states for each section
- [ ] **GDT-04**: Tree performance verified with 1000+ nodes -- no scroll lag, expand/collapse stays smooth

### LDG -- Language Data Grid Polish

- [ ] **LDG-01**: Language Data Grid passes full UI/UX audit (column alignment, status colors in dark mode, empty states)
- [ ] **LDG-02**: Loading states use skeleton rows matching grid dimensions instead of spinner
- [ ] **LDG-03**: Search/filter bar has consistent styling with other pages, clear feedback on empty results

### WMP -- World Map Polish

- [ ] **WMP-01**: World Map passes quick UI/UX audit (node styling, route lines, tooltips, dark mode)
- [ ] **WMP-02**: Empty state when no map data is loaded shows helpful message

### TMP -- TM Panel Polish

- [ ] **TMP-01**: TM Panel passes UI/UX audit (match percentages, diff highlighting, dark mode consistency)
- [ ] **TMP-02**: Loading and empty states for TM suggestions are polished

### XPG -- Cross-Page Consistency

- [ ] **XPG-01**: All 5 pages use the shared PageHeader component with consistent look
- [ ] **XPG-02**: Dark mode works consistently across all pages -- no hardcoded colors, no missing tokens
- [ ] **XPG-03**: Sidebar navigation has consistent active states, hover effects, and spacing
- [ ] **XPG-04**: Error handling is consistent -- all pages use ErrorState component with retry

### VER -- Verification

- [ ] **VER-01**: Playwright screenshots captured for all 5 pages in both light and dark mode (10 screenshots minimum)
- [ ] **VER-02**: Performance benchmark -- Codex loads 500 entities without visible lag, initial render under 1 second
- [ ] **VER-03**: No memory leaks -- opening and closing pages repeatedly shows stable memory usage
- [ ] **VER-04**: All existing API tests still pass after polish changes (zero regressions)

## Future Requirements

### Advanced Polish (v3.4+)

- **ADV-01**: Keyboard shortcuts overlay / command palette
- **ADV-02**: Custom scrollbar styling
- **ADV-03**: Animation library for complex transitions
- **ADV-04**: Themeable color scheme beyond dark/light

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full redesign / layout changes | Polish only -- structure stays, visual quality improves |
| New features / functionality | Pure UX quality pass, no new capabilities |
| Backend architectural changes | Only minimal Codex pagination param addition |
| Mobile responsiveness | Desktop-only Electron app |
| Accessibility audit (WCAG) | Carbon handles baseline a11y; deep audit is v3.4+ |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 32 | Complete |
| FND-02 | Phase 32 | Complete |
| FND-03 | Phase 32 | Complete |
| FND-04 | Phase 32 | Complete |
| FND-05 | Phase 32 | Complete |
| FND-06 | Phase 32 | Complete |
| CDX-01 | Phase 33 | Complete |
| CDX-02 | Phase 33 | Complete |
| CDX-03 | Phase 33 | Complete |
| CDX-04 | Phase 33 | Complete |
| CDX-05 | Phase 33 | Pending |
| CDX-06 | Phase 33 | Pending |
| CDX-07 | Phase 33 | Complete |
| GDT-01 | Phase 34 | Pending |
| GDT-02 | Phase 34 | Pending |
| GDT-03 | Phase 34 | Pending |
| GDT-04 | Phase 34 | Pending |
| LDG-01 | Phase 34 | Pending |
| LDG-02 | Phase 34 | Pending |
| LDG-03 | Phase 34 | Pending |
| WMP-01 | Phase 34 | Pending |
| WMP-02 | Phase 34 | Pending |
| TMP-01 | Phase 34 | Pending |
| TMP-02 | Phase 34 | Pending |
| XPG-01 | Phase 35 | Pending |
| XPG-02 | Phase 35 | Pending |
| XPG-03 | Phase 35 | Pending |
| XPG-04 | Phase 35 | Pending |
| VER-01 | Phase 36 | Pending |
| VER-02 | Phase 36 | Pending |
| VER-03 | Phase 36 | Pending |
| VER-04 | Phase 36 | Pending |

**Coverage:**
- v3.3 requirements: 32 total
- Mapped to phases: 32/32
- Unmapped: 0

---
*Requirements defined: 2026-03-17*
*Traceability updated: 2026-03-17 after roadmap creation*
