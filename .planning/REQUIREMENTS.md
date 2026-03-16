# Requirements: LocaNext v3.3

**Defined:** 2026-03-17
**Core Value:** All 5 pages polished to production quality — consistent, performant, beautiful, one unified app experience.

## v3.3 Requirements

### FND — Design Foundation

- [ ] **FND-01**: CSS custom properties defined in app.css for spacing scale, color tokens, shadow tokens, and border-radius — all pages use tokens instead of hardcoded values
- [ ] **FND-02**: Shared PageHeader component with consistent padding, title styling, and optional action slot used across all 5 pages
- [ ] **FND-03**: Shared SkeletonCard component matching Codex card dimensions for loading states
- [ ] **FND-04**: Shared EmptyState component (icon + headline + description + optional CTA) used when pages have no data
- [ ] **FND-05**: Shared ErrorState component (error message + retry button) used for inline error recovery on all pages
- [ ] **FND-06**: Shared InfiniteScroll component using IntersectionObserver with $effect cleanup for paginated loading

### CDX — Codex Revamp

- [ ] **CDX-01**: Codex loads entities in pages of 50 via paginated API (offset/limit) instead of loading all at once
- [ ] **CDX-02**: IntersectionObserver sentinel triggers next page load as user scrolls near bottom
- [ ] **CDX-03**: Skeleton cards show during page load, matching real card dimensions
- [ ] **CDX-04**: Entity images use loading="lazy" with placeholder shown until image enters viewport
- [ ] **CDX-05**: Search-first UX — search bar prominent at top, results update as user types with debounce
- [ ] **CDX-06**: Category tabs with counts, cached per tab so switching is instant
- [ ] **CDX-07**: Codex feels like a polished encyclopedia — consistent card sizes, smooth transitions, no layout shift

### GDT — GameData Tree Polish

- [ ] **GDT-01**: GameData Tree page passes full UI/UX audit (spacing, colors, dark mode, empty states, loading states)
- [ ] **GDT-02**: Node detail panel has consistent spacing, proper typography hierarchy, and smooth transitions
- [ ] **GDT-03**: Context Intelligence Panel (right panel) has polished tabs, loading states, and empty states for each section
- [ ] **GDT-04**: Tree performance verified with 1000+ nodes — no scroll lag, expand/collapse stays smooth

### LDG — Language Data Grid Polish

- [ ] **LDG-01**: Language Data Grid passes full UI/UX audit (column alignment, status colors in dark mode, empty states)
- [ ] **LDG-02**: Loading states use skeleton rows matching grid dimensions instead of spinner
- [ ] **LDG-03**: Search/filter bar has consistent styling with other pages, clear feedback on empty results

### WMP — World Map Polish

- [ ] **WMP-01**: World Map passes quick UI/UX audit (node styling, route lines, tooltips, dark mode)
- [ ] **WMP-02**: Empty state when no map data is loaded shows helpful message

### TMP — TM Panel Polish

- [ ] **TMP-01**: TM Panel passes UI/UX audit (match percentages, diff highlighting, dark mode consistency)
- [ ] **TMP-02**: Loading and empty states for TM suggestions are polished

### XPG — Cross-Page Consistency

- [ ] **XPG-01**: All 5 pages use the shared PageHeader component with consistent look
- [ ] **XPG-02**: Dark mode works consistently across all pages — no hardcoded colors, no missing tokens
- [ ] **XPG-03**: Sidebar navigation has consistent active states, hover effects, and spacing
- [ ] **XPG-04**: Error handling is consistent — all pages use ErrorState component with retry

### VER — Verification

- [ ] **VER-01**: Playwright screenshots captured for all 5 pages in both light and dark mode (10 screenshots minimum)
- [ ] **VER-02**: Performance benchmark — Codex loads 500 entities without visible lag, initial render under 1 second
- [ ] **VER-03**: No memory leaks — opening and closing pages repeatedly shows stable memory usage
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
| Full redesign / layout changes | Polish only — structure stays, visual quality improves |
| New features / functionality | Pure UX quality pass, no new capabilities |
| Backend architectural changes | Only minimal Codex pagination param addition |
| Mobile responsiveness | Desktop-only Electron app |
| Accessibility audit (WCAG) | Carbon handles baseline a11y; deep audit is v3.4+ |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | TBD | Pending |
| FND-02 | TBD | Pending |
| FND-03 | TBD | Pending |
| FND-04 | TBD | Pending |
| FND-05 | TBD | Pending |
| FND-06 | TBD | Pending |
| CDX-01 | TBD | Pending |
| CDX-02 | TBD | Pending |
| CDX-03 | TBD | Pending |
| CDX-04 | TBD | Pending |
| CDX-05 | TBD | Pending |
| CDX-06 | TBD | Pending |
| CDX-07 | TBD | Pending |
| GDT-01 | TBD | Pending |
| GDT-02 | TBD | Pending |
| GDT-03 | TBD | Pending |
| GDT-04 | TBD | Pending |
| LDG-01 | TBD | Pending |
| LDG-02 | TBD | Pending |
| LDG-03 | TBD | Pending |
| WMP-01 | TBD | Pending |
| WMP-02 | TBD | Pending |
| TMP-01 | TBD | Pending |
| TMP-02 | TBD | Pending |
| XPG-01 | TBD | Pending |
| XPG-02 | TBD | Pending |
| XPG-03 | TBD | Pending |
| XPG-04 | TBD | Pending |
| VER-01 | TBD | Pending |
| VER-02 | TBD | Pending |
| VER-03 | TBD | Pending |
| VER-04 | TBD | Pending |

**Coverage:**
- v3.3 requirements: 32 total
- Mapped to phases: 0 (awaiting roadmap)
- Unmapped: 32

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after research synthesis*
