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
- [x] **CDX-05**: Search-first UX -- search bar prominent at top, results update as user types with debounce
- [x] **CDX-06**: Category tabs with counts, cached per tab so switching is instant
- [x] **CDX-07**: Codex feels like a polished encyclopedia -- consistent card sizes, smooth transitions, no layout shift

### GDT -- GameData Tree Polish

- [x] **GDT-01**: GameData Tree page passes full UI/UX audit (spacing, colors, dark mode, empty states, loading states)
- [x] **GDT-02**: Node detail panel has consistent spacing, proper typography hierarchy, and smooth transitions
- [x] **GDT-03**: Context Intelligence Panel (right panel) has polished tabs, loading states, and empty states for each section
- [x] **GDT-04**: Tree performance verified with 1000+ nodes -- no scroll lag, expand/collapse stays smooth

### LDG -- Language Data Grid Polish

- [x] **LDG-01**: Language Data Grid passes full UI/UX audit (column alignment, status colors in dark mode, empty states)
- [x] **LDG-02**: Loading states use skeleton rows matching grid dimensions instead of spinner
- [x] **LDG-03**: Search/filter bar has consistent styling with other pages, clear feedback on empty results

### WMP -- World Map Polish

- [x] **WMP-01**: World Map passes quick UI/UX audit (node styling, route lines, tooltips, dark mode)
- [x] **WMP-02**: Empty state when no map data is loaded shows helpful message

### TMP -- TM Panel Polish

- [x] **TMP-01**: TM Panel passes UI/UX audit (match percentages, diff highlighting, dark mode consistency)
- [x] **TMP-02**: Loading and empty states for TM suggestions are polished

### XPG -- Cross-Page Consistency

- [x] **XPG-01**: All 5 pages use the shared PageHeader component with consistent look
- [x] **XPG-02**: Dark mode works consistently across all pages -- no hardcoded colors, no missing tokens
- [x] **XPG-03**: Sidebar navigation has consistent active states, hover effects, and spacing
- [x] **XPG-04**: Error handling is consistent -- all pages use ErrorState component with retry

### VER -- Verification

- [x] **VER-01**: Playwright screenshots captured for all 5 pages in both light and dark mode (10 screenshots minimum)
- [x] **VER-02**: Performance benchmark -- Codex loads 500 entities without visible lag, initial render under 1 second
- [x] **VER-03**: No memory leaks -- opening and closing pages repeatedly shows stable memory usage
- [x] **VER-04**: All existing API tests still pass after polish changes (zero regressions)

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
| CDX-05 | Phase 33 | Complete |
| CDX-06 | Phase 33 | Complete |
| CDX-07 | Phase 33 | Complete |
| GDT-01 | Phase 34 | Complete |
| GDT-02 | Phase 34 | Complete |
| GDT-03 | Phase 34 | Complete |
| GDT-04 | Phase 34 | Complete |
| LDG-01 | Phase 34 | Complete |
| LDG-02 | Phase 34 | Complete |
| LDG-03 | Phase 34 | Complete |
| WMP-01 | Phase 34 | Complete |
| WMP-02 | Phase 34 | Complete |
| TMP-01 | Phase 34 | Complete |
| TMP-02 | Phase 34 | Complete |
| XPG-01 | Phase 35 | Complete |
| XPG-02 | Phase 35 | Complete |
| XPG-03 | Phase 35 | Complete |
| XPG-04 | Phase 35 | Complete |
| VER-01 | Phase 36 | Complete |
| VER-02 | Phase 36 | Complete |
| VER-03 | Phase 36 | Complete |
| VER-04 | Phase 36 | Complete |

**Coverage:**
- v3.3 requirements: 32 total
- Mapped to phases: 32/32
- Unmapped: 0

## v3.5 Requirements -- WOW Showcase

### WOW -- XML Viewer Polish (Phase 37)

- [x] **WOW-01**: XML attributes have semantic color highlighting -- cross-refs blue, identity gold, editable green, stats cyan, media purple
- [x] **WOW-02**: Hovering a cross-ref attribute value for 300ms shows a mini-preview card with entity name, type badge, and thumbnail
- [x] **WOW-03**: Panel entrance has slide-in animation, tab switch has crossfade, image load has shimmer-to-reveal
- [x] **WOW-04**: Clicking an attribute value copies to clipboard with visual ripple feedback

### WOW -- Fantasy World Map (Phase 38)

- [ ] **WOW-05**: Map has parchment background via CSS gradients + ornamental SVG border frame
- [ ] **WOW-06**: 10 regions render as semi-transparent polygons with glow-on-hover and Korean names
- [ ] **WOW-07**: Each node type has a distinct SVG icon (castle, skull, shield, tent, compass, tree)
- [x] **WOW-08**: Routes animate on hover with travel-path effect and danger-level coloring
- [x] **WOW-09**: Click region -> smooth zoom-to-fit via d3 transition + detail panel slides in

### WOW -- Codex Enhancement (Phase 39)

- [x] **WOW-10**: Entity cards have glassmorphism (backdrop-filter blur + semi-transparent bg) with AI portrait
- [x] **WOW-11**: Hovering card produces parallax shift on background image
- [x] **WOW-12**: D3 force-directed graph shows entity relationships with typed link styles
- [x] **WOW-13**: Hovering graph node highlights connected nodes and dims unconnected

### WOW -- Cross-cutting Polish (Phase 40)

- [ ] **WOW-14**: Page navigation has crossfade transition
- [ ] **WOW-15**: All loading states use shimmer skeletons matching content dimensions
- [x] **WOW-16**: Ctrl+K opens command palette for global entity search
- [x] **WOW-17**: Toast notifications slide in from top-right with auto-dismiss

**v3.5 Coverage:**
- v3.5 requirements: 17 total
- Mapped to phases: 17/17
- Unmapped: 0

## Phase 41 Requirements -- Qwen3-TTS Korean Voice Generation

### TTS -- Text-to-Speech Voice Generation

- [ ] **TTS-01**: TTSService singleton with lazy Qwen3-TTS model loading (loads on first request, not on startup)
- [ ] **TTS-02**: 5 character voice profiles with distinct voice instructions (Elder Varon=wise/slow, Kira=cold/sharp, Grimjaw=gruff/strong, Lune=young/alert, Drakmar=mysterious/echoing)
- [ ] **TTS-03**: POST /api/ldm/codex/generate-voice/{strkey} generates .wav audio and returns audio URL with duration
- [ ] **TTS-04**: Generated audio cached on disk at mock_gamedata/audio/{strkey}.wav -- repeat calls return cached version without regeneration
- [ ] **TTS-05**: Codex entity detail shows "Generate Voice" button, loading state during generation, audio player with auto-play after generation, and regenerate option

**Phase 41 Coverage:**
- Phase 41 requirements: 5 total
- Mapped to plans: 5/5 (TTS-01..04 -> Plan 01, TTS-05 -> Plan 02)
- Unmapped: 0

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| TTS-01 | Phase 41 | 41-01 | Pending |
| TTS-02 | Phase 41 | 41-01 | Pending |
| TTS-03 | Phase 41 | 41-01 | Pending |
| TTS-04 | Phase 41 | 41-01 | Pending |
| TTS-05 | Phase 41 | 41-02 | Pending |

---
*Requirements defined: 2026-03-17*
*v3.5 WOW Showcase requirements added: 2026-03-17*
*Phase 41 TTS requirements added: 2026-03-18*
