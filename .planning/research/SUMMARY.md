# Project Research Summary

**Project:** LocaNext v3.3 — UI/UX Polish + Performance
**Domain:** Desktop app UI polish and performance optimization (Electron + Svelte 5 + Carbon)
**Researched:** 2026-03-17
**Confidence:** HIGH

## Executive Summary

LocaNext v3.3 is a UI/UX polish and performance milestone for a shipping Electron desktop localization tool. The existing stack (Svelte 5 Runes, Carbon Components, FastAPI, FAISS, SQLite/PostgreSQL) is validated through v3.2 and requires zero new production dependencies. The research conclusion is unambiguous: every capability needed for this milestone already exists in the installed stack. The work is about using existing tools correctly and consistently, not adding new ones. Two dev-only dependencies (`stylelint` + `stylelint-value-no-unknown-custom-properties`) are the only additions, solely for CSS linting enforcement.

The recommended approach is a foundation-first, dependency-driven build order: design tokens in `app.css` first (unlocks all downstream work), three small shared micro-components second (PageHeader, SkeletonCard, InfiniteScroll — under 120 lines total), Codex revamp third (the single highest-impact change: replacing a full-list-fetch-and-render-all pattern that can hit 5000+ DOM nodes with paginated IntersectionObserver loading at 50/page), then a parallel cross-page polish pass across all 5 pages. Architecture research surfaced a concrete, specific implementation path for each change, including exact code patterns.

The key risks are not technical — the stack is well-understood. They are implementation discipline: CSS token replacement must be done value-by-value with before/after screenshots to avoid silent pixel-level layout breaks; IntersectionObserver instances must always be cleaned up in Svelte 5 `$effect` to prevent memory leaks on tab switching; and skeleton placeholder dimensions must exactly match real card dimensions to prevent layout shift when content loads. All three risks have clear, concrete prevention strategies documented in research.

## Key Findings

### Recommended Stack

Zero new production dependencies are needed. Carbon's `SkeletonText`, `SkeletonPlaceholder`, and `InlineLoading` (all in installed v0.95.2) cover all loading states. Native browser `IntersectionObserver` handles infinite scroll without any library. `loading="lazy"` on `<img>` tags handles lazy image loading natively. Svelte 5's `$effect` lifecycle handles observer cleanup cleanly. The codebase already uses these tools in several components — v3.3 extends their usage consistently to all 5 pages.

**Core technologies (no version changes):**
- Carbon Components Svelte 0.95.2 — SkeletonText/SkeletonPlaceholder for loading states — already installed, extend to Codex and all pages
- Native `IntersectionObserver` (browser API) — Codex infinite scroll sentinel — zero deps, Electron 39 Chromium fully supports it
- Native `loading="lazy"` (HTML attribute) — lazy image loading — zero JS, additive to IntersectionObserver pagination
- Svelte 5 `$effect` + `$props()` — component lifecycle and reactive state — Runes-only, no Svelte 4 patterns
- `stylelint` ^16.0.0 — CSS token consistency enforcement — dev dependency only

**Rejected additions (with rationale):** svelte-skeleton-loader (Carbon already covers this), @humanspeak/svelte-virtual-list (requires snippets syntax, incompatible with CSS Grid card layout), svelte-lazy-image (overkill for Electron; native API is simpler), Lighthouse CI (targets web metrics, not Electron desktop), GSAP (overkill for 150ms CSS transitions).

### Expected Features

**Must have (table stakes — app feels like a prototype without these):**
- Consistent skeleton loading states across all 5 pages — currently each page uses a different loading pattern
- Empty states with guidance — "no data" states must explain what to do, not just print a line of text
- Error states with retry buttons — API errors across pages have no recovery path
- CSS token consistency — hardcoded hex colors and pixel values break dark mode and create visual drift across pages

**Should have (differentiators):**
- Codex infinite scroll — browse 5676+ entities without pagination buttons or blocking wait
- Skeleton card grid — loading state mirrors exact layout of content, eliminating spinner-then-jump
- Lazy image loading — images load only when scrolled into view, not 1000 simultaneous HTTP requests
- Cross-page visual coherence — all 5 pages feel like one app (currently they feel like 5 separate apps with shared navigation)

**Defer to v3.4+:**
- Smooth page transitions (CSS-only, nice-to-have, not blocking)
- Responsive panel resizing (desktop app with known viewport, low ROI)
- Full animation library, theme customization UI, Storybook, Lighthouse CI pipeline — all explicitly anti-features for this scope

### Architecture Approach

The recommended architecture adds 3 tiny shared components to `lib/components/common/` and ~20 CSS custom properties to `app.css`, then modifies 6 existing page components. Nothing architectural changes. The foundation is new layout tokens in `app.css` that eliminate spacing drift at its source (currently: CodexPage header uses `12px 16px`, GameDevPage uses `0.5rem 0.75rem`, GridPage uses `0.5rem 1rem` — all become `var(--page-header-padding)`). The Codex revamp is the major structural change: replace `{#each entities}` over the full array with paginated IntersectionObserver loading (50/page). `VirtualGrid.svelte` (1000+ lines, battle-tested for the translation grid) is explicitly left unchanged.

**Major components:**
1. `app.css` (modified) — New layout token layer (`--page-header-padding`, `--panel-width-*`, `--card-radius`, `--transition-fast`, `--skeleton-bg`); foundation for all downstream changes
2. `PageHeader.svelte` (new, ~40 lines) — Shared header with icon, title, action slot; eliminates 5 divergent header patterns across pages
3. `SkeletonCard.svelte` (new, ~50 lines) — Animated CSS-only shimmer placeholder matching entity card dimensions exactly
4. `InfiniteScroll.svelte` (new, ~30 lines) — IntersectionObserver sentinel with `$effect` cleanup; fires `onloadmore` when visible; `rootMargin: '200px'` for prefetch feel
5. `CodexPage.svelte` (major refactor) — Pagination state, InfiniteScroll integration, SkeletonCard, `loading="lazy"`, 4-state handling (error/loading/empty/content), tab entity caching via Map
6. Backend codex route (small addition) — `offset` and `limit` query params on `/api/ldm/codex/list/{type}`; wrapper-layer change only
7. Pages 2-5 (GameDevPage, GridPage, WorldMapPage, TMPage, FilesPage) — Incremental token adoption, consistent 4-state handling

### Critical Pitfalls

1. **CSS token replacement breaking layout** — Carbon spacing tokens (8, 16, 24, 32px...) don't have exact matches for every current hardcoded value. Prevention: compare actual pixel values before replacing; take before/after screenshots of each page at the same viewport. Document intentional deviations when no exact token exists.
2. **IntersectionObserver memory leaks in Svelte 5** — Observers created inside `{#each}` blocks accumulate if not disconnected. Prevention: single shared observer instance, always return cleanup in `$effect` (`return () => observer.disconnect()`). Detect via DevTools Memory tab heap snapshots before and after 10 tab switches.
3. **Pagination breaking entity scroll position on tab switch** — Resetting `entities = []` on tab change loses scroll state. Prevention: cache loaded entities per tab in a `Map`; restore from cache on tab return, only re-fetch if stale.
4. **Skeleton placeholder height mismatch** — Skeleton cards a different height than real cards cause visible layout shift on load. Prevention: `SkeletonCard.svelte` must use identical CSS classes and dimensions to real entity cards (48x48 image, same flex gap/padding/border-radius).
5. **Stylelint failing to parse Svelte files** — Stylelint doesn't understand `<style>` blocks and `::global()` out of the box. Prevention: use `postcss-html` parser + `stylelint-config-html/svelte` in `.stylelintrc.json`.

## Implications for Roadmap

The dependency graph discovered in research dictates phase order. Tokens must exist before components can use them. Components must exist before pages can adopt them. Codex (the hardest page) benefits from shared components being stable. Cross-page polish can fully parallelize once foundation is in place.

### Phase 1: Design Token Foundation
**Rationale:** Every downstream change references CSS custom properties from `app.css`. Establishing tokens first ensures all components use the same values from day one. Non-breaking — existing pages continue to work while tokens are added. Stylelint setup here enforces token usage going forward.
**Delivers:** ~20 new layout CSS custom properties in `app.css`; stylelint dev tooling configured and passing
**Addresses:** Cross-page visual coherence (table stakes), dark mode consistency (table stakes), spacing/typography drift
**Avoids:** Pitfall #1 (broken layouts from wrong token values) — systematic value-by-value audit with screenshots before replacement

### Phase 2: Shared Micro-Components
**Rationale:** Three small reusable components (total ~120 lines) used across multiple pages. Must be stable before pages adopt them. Low-risk, high-leverage.
**Delivers:** `PageHeader.svelte` (~40 lines), `SkeletonCard.svelte` (~50 lines), `InfiniteScroll.svelte` (~30 lines) in `lib/components/common/`
**Uses:** Phase 1 tokens for styling; Svelte 5 `$props()` and `$effect` patterns throughout
**Avoids:** Pitfall #4 (skeleton height mismatch) — SkeletonCard designed to exactly match CodexPage entity card dimensions from the start

### Phase 3: Codex Revamp
**Rationale:** The highest-impact single change in the milestone. Currently renders ALL entities (up to 1000+ DOM nodes) with no lazy loading, a plain spinner during load, and all images fetching simultaneously. Must be addressed after Phase 1-2 components are ready since it depends on both InfiniteScroll and SkeletonCard.
**Delivers:** Paginated IntersectionObserver loading (50 entities/page), SkeletonCard integration, `loading="lazy"` on entity images, 4-state handling, tab entity cache (Map-based), backend `offset/limit` pagination
**Uses:** InfiniteScroll.svelte + SkeletonCard.svelte (Phase 2), Phase 1 layout tokens, backend wrapper-layer change
**Avoids:** Pitfall #2 (IO memory leaks) via single observer with `$effect` cleanup; Pitfall #3 (scroll position reset) via per-tab entity cache

### Phase 4: Cross-Page Polish (5 parallel sub-phases)
**Rationale:** Pages are independent of each other. Once Phase 1 tokens and Phase 2 PageHeader exist, all 5 remaining pages can be polished simultaneously by separate agent tasks. No page depends on another page's changes.
**Delivers:** Consistent 4-state handling (error/loading/empty/content) across all pages; Carbon token adoption; consistent spacing and typography
**Sub-phases (fully parallelizable):**
- 4a: GameDevPage — loading states for tree panel, empty state improvement, token adoption
- 4b: FilesPage — empty/error state standardization, token adoption
- 4c: TMPage — token adoption, 4-state handling consistency
- 4d: GridPage — token adoption (VirtualGrid itself unchanged, do not touch)
- 4e: WorldMapPage — minor token adoption, header consistency verification
**Addresses:** Consistent loading/empty/error states (all table stakes); Pitfall #8 (inconsistent empty states) with shared EmptyState pattern

### Phase 5: Visual Consistency Verification
**Rationale:** All changes must be validated together, not just per-phase. Screenshots of all 5 pages confirm visual cohesion before the milestone is called complete.
**Delivers:** Playwright screenshot pass across all 5 pages in both light and dark themes; memory leak test (DevTools heap snapshots before/after 10 Codex tab switches); before/after screenshot comparison confirming no layout regressions
**Avoids:** Pitfall #7 (dark mode contrast gaps from token migration) — both themes explicitly tested; Pitfall #1 regression detection

### Phase Ordering Rationale

- Tokens before components: no component should hardcode a value that a token should carry; changing tokens after components are built invalidates work
- Components before pages: reused building blocks must be stable and tested before multiple pages adopt them
- Codex before other pages: highest-impact change gets full focus; validates IntersectionObserver + pagination pattern before it spreads to other pages
- Pages 4a-4e in parallel: no cross-page dependencies once shared components are stable; all 5 apply the same patterns independently
- Verification last: validates the complete system holistically, not individual parts

### Research Flags

No phases require `/gsd:research-phase` — all patterns are well-documented and confidence is HIGH based on direct codebase analysis plus official Carbon/Svelte/MDN documentation.

**Standard patterns (skip research-phase):**
- **Phase 1 (Tokens):** CSS custom property patterns well-documented; Carbon token names verified from official docs; `stylelint` setup is standard
- **Phase 2 (Components):** Svelte 5 `$props()` / `$effect` patterns are established; IntersectionObserver is a web standard; full implementation code provided in ARCHITECTURE.md
- **Phase 3 (Codex):** Pagination + IntersectionObserver is well-documented pattern; exact implementation code provided in ARCHITECTURE.md with specific line references to current CodexPage
- **Phase 4 (Cross-page):** Each page applies patterns from Phases 1-2 independently; no novel patterns
- **Phase 5 (Verification):** Playwright already installed; screenshot comparison is established practice in this project

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies — all existing tools verified in production through v3.2; Carbon skeleton components already used in 3 existing components |
| Features | HIGH | Derived from direct codebase analysis of 70+ Svelte components with specific line references; Carbon docs verified |
| Architecture | HIGH | Based on reading actual source files (`CodexPage.svelte` 747 lines, `VirtualGrid.svelte` 1000+ lines, etc.) with specific integration points identified |
| Pitfalls | HIGH | Grounded in v3.1 UIUX audit experience (60 fixes), Svelte 5 action lifecycle docs, MDN IntersectionObserver documentation, Carbon theming docs |

**Overall confidence:** HIGH

### Gaps to Address

- **Backend pagination endpoint:** The codex list route needs `offset`/`limit` query params. This is a wrapper-layer change (allowed by project constraints). Pattern is standard FastAPI; no blocking unknowns but needs a plan-time implementation note in Phase 3.
- **Exact token value mapping:** Some hardcoded values won't have exact Carbon token equivalents (e.g., `padding: 12px` vs Carbon's `--cds-spacing-05` at 16px). Each must be evaluated individually during Phase 1. Not blocking — requires careful per-component comparison rather than blind replacement.
- **Stylelint Svelte 5 compatibility:** The `postcss-html` parser integration needs verification against the project's Vite/Svelte build setup. Likely trivial but should be confirmed at the start of Phase 1 before stylelint is wired into the dev workflow.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `CodexPage.svelte` (747 lines), `VirtualGrid.svelte` (1000+ lines), `GameDevPage.svelte` (527 lines), `GridPage.svelte` (469 lines), `app.css` (310 lines), `+layout.svelte` (683 lines)
- [IntersectionObserver API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) — rootMargin, threshold, memory management
- [HTML `loading="lazy"` - MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#loading) — native lazy loading in Chromium
- [Carbon Components Svelte - SkeletonPlaceholder](https://svelte.carbondesignsystem.com/components/SkeletonPlaceholder) — available in installed v0.95.2
- [Carbon Components Svelte - SkeletonText](https://svelte.carbondesignsystem.com/components/SkeletonText) — available in installed v0.95.2
- [Carbon Design System Color Tokens](https://carbondesignsystem.com/elements/color/tokens/) — `--cds-*` token naming and exact pixel values
- [Carbon Themes Code Reference](https://carbondesignsystem.com/elements/themes/code/) — g100 dark theme CSS custom property implementation
- [stylelint-value-no-unknown-custom-properties](https://github.com/csstools/stylelint-value-no-unknown-custom-properties) — established CSS linting tool

### Secondary (MEDIUM confidence)
- [@humanspeak/svelte-virtual-list](https://github.com/humanspeak/svelte-virtual-list) — evaluated and rejected (requires snippets syntax, incompatible with CSS Grid card layout)
- [Lazy Load with Svelte and IntersectionObserver](https://www.danyelkoca.com/en/blog/lazy-load-with-svelte-and-intersection-observer) — IO lifecycle patterns in Svelte
- [Svelte Intersection Observer Patterns - Reuters Graphics](https://reuters-graphics.github.io/example_svelte-graph-patterns/observer/) — IO with reactive state patterns
- v3.1 UIUX audit (60 fixes across the app) — baseline for pitfall identification and pattern confidence

---
*Research completed: 2026-03-17*
*Ready for roadmap: yes*
