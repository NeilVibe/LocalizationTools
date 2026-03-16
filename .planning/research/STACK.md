# Technology Stack

**Project:** LocaNext v3.3 -- UI/UX Polish + Performance
**Researched:** 2026-03-17
**Scope:** NEW additions only for polish/performance. Existing validated stack is unchanged.

## Existing Stack (DO NOT RE-RESEARCH)

Already validated and shipping through v3.2:
- Electron 39 + Svelte 5.46 (Runes) + FastAPI + SQLite/PostgreSQL
- FAISS + Model2Vec for semantic search
- Qwen3-4B via Ollama (httpx async) for AI summaries
- lxml for XML parsing (XMLParsingEngine)
- Aho-Corasick for entity detection
- Pillow for DDS->PNG, vgmstream-cli for WEM->WAV
- Carbon Components Svelte 0.95.2 for UI (includes SkeletonText, SkeletonPlaceholder, InlineLoading)
- d3-selection + d3-zoom for World Map
- socket.io-client for WebSocket sync
- VirtualGrid.svelte (custom implementation for Language Data grid)

---

## Stack Additions for v3.3

### Zero New Dependencies Needed

The key finding of this research: **v3.3 requires ZERO new npm packages.** Every capability needed for UI/UX polish and performance optimization is achievable with existing dependencies plus native browser APIs.

**Rationale:** Adding dependencies to an Electron desktop app increases bundle size, introduces version conflicts, and creates maintenance burden. The existing stack already covers every need when used correctly.

---

### Skeleton Loading States: Use Carbon's Built-In Components

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `SkeletonText` | (in carbon-components-svelte 0.95.2) | Text placeholder during loading | Already used in GameDataContextPanel, FileExplorerTree, GameDataTree. Extend same pattern to CodexPage and TMPage. |
| `SkeletonPlaceholder` | (in carbon-components-svelte 0.95.2) | Image/card placeholder during loading | Available but unused. Use for Codex entity cards and image thumbnails during load. Supports custom sizing. |
| `InlineLoading` | (in carbon-components-svelte 0.95.2) | Spinner with status text | Already used everywhere. Keep for action feedback (saving, searching). |

**Pattern:** Replace bare `InlineLoading` spinners on CodexPage with proper skeleton layouts that match the final card grid shape. This gives much better perceived performance than a centered spinner.

**What NOT to add:**
- `svelte-skeleton-loader` -- unnecessary, Carbon covers this
- `@skeleton-elements/svelte` -- different design system, would clash with Carbon
- `skeleton.dev` (Skeleton UI) -- completely different UI framework, requires Tailwind

---

### Codex Virtualization: Custom Implementation, Not a Library

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Native `IntersectionObserver` | (browser API) | Viewport detection for lazy rendering | Zero dependencies. Svelte 5 actions make this trivial. Already in every Electron 39 Chromium. |
| Svelte 5 action: `use:lazyload` | (custom, ~30 lines) | Lazy-load entity cards as they scroll into view | A reusable Svelte action wrapping IntersectionObserver. Simpler and more controllable than any library. |

**Why NOT use a virtual list library:**
1. CodexPage uses a CSS Grid layout (not a flat list) -- virtual list libraries expect single-column or fixed-row lists
2. Entity cards have variable heights (description length varies)
3. The existing VirtualGrid.svelte already solves this for the data grid -- Codex needs a different approach (paginated loading with intersection observer, not row virtualization)
4. `@humanspeak/svelte-virtual-list` requires Svelte 5 snippets syntax which would require restructuring the card rendering
5. `@sveltejs/svelte-virtual-list` is unmaintained and Svelte 4 only

**Recommended approach for Codex:** Paginated API loading (fetch 50 entities per page) + IntersectionObserver sentinel at bottom of grid to trigger next page load. This is simpler, more robust, and works perfectly with CSS Grid.

---

### Lazy Image Loading: Native Browser API

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `loading="lazy"` attribute | (HTML native) | Defer offscreen image loading | Built into every modern browser. Electron 39's Chromium fully supports it. Zero JS needed. |
| `IntersectionObserver` action | (browser API) | Advanced lazy loading with placeholder swap | For cases where `loading="lazy"` isn't sufficient (e.g., PlaceholderImage -> real image transition). |

**Implementation:** Add `loading="lazy"` to all `<img>` tags in entity cards. For the PlaceholderImage-to-real-image swap pattern already in CodexPage, wrap with an IntersectionObserver action that only starts fetching when the card enters the viewport.

**What NOT to add:**
- `svelte-lazy-image` -- overkill for an Electron app where there's a single known viewport
- `svelte-lazy-loader` -- same reasoning, native API is better controlled

---

### CSS Consistency: Carbon Design Tokens + Stylelint

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Carbon CSS custom properties | (in carbon-components-svelte 0.95.2) | Design tokens for spacing, colors, typography | Already available via `--cds-*` variables. Many components use them inconsistently -- audit needed, not new tooling. |
| `stylelint` | ^16.0.0 | CSS linting and consistency enforcement | Dev dependency only. Catches hardcoded colors/spacing that should use Carbon tokens. |
| `stylelint-value-no-unknown-custom-properties` | ^6.0.0 | Catch typos in `--cds-*` variable names | Prevents referencing non-existent Carbon tokens (silent failures in CSS). |

**Key insight:** The consistency problem is not missing tooling -- it's inconsistent use of existing Carbon tokens. The codebase mixes hardcoded values (`#0f62fe`, `12px`, `0.875rem`) with Carbon variables (`var(--cds-interactive-01)`, `var(--cds-spacing-05)`). A stylelint rule can enforce token usage going forward, but the main work is an audit pass replacing hardcoded values.

**What NOT to add:**
- `postcss` / `postcss-custom-properties` -- not needed, Carbon tokens work natively
- Token CSS -- different design system, conflicts with Carbon
- Style Dictionary -- enterprise-grade token management, overkill for this project

---

### Performance Auditing: Lighthouse CI (Dev Only)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Chrome DevTools (built into Electron) | (available) | Performance profiling, memory leaks, layout shifts | Already available. Open with Ctrl+Shift+I in dev mode. No installation needed. |
| Playwright performance assertions | (in @playwright/test 1.57.0) | Automated performance regression checks | Already installed. Use `page.evaluate(() => performance.getEntriesByType('navigation'))` for load timing. |

**Why NOT Lighthouse CI:**
Lighthouse is designed for web pages served over HTTP, not Electron apps. It measures First Contentful Paint, Largest Contentful Paint, etc. against web standards that don't apply to a desktop app loaded from `file://` or `localhost`. The meaningful performance metrics for LocaNext are:
- Time to interactive after page switch (measured via Playwright)
- Virtual grid scroll FPS (measured via DevTools Performance panel)
- Memory usage after loading 5000+ entities (measured via `process.memoryUsage()` or DevTools Memory tab)
- API response times (already logged by FastAPI)

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Skeleton loading | Carbon SkeletonText/SkeletonPlaceholder | svelte-skeleton-loader | Different design language, Carbon already has this |
| Virtual list (Codex) | Pagination + IntersectionObserver | @humanspeak/svelte-virtual-list | Codex uses CSS Grid, not flat list; variable card heights |
| Lazy images | Native `loading="lazy"` + custom action | svelte-lazy-image | Overkill for Electron; native API is simpler and more reliable |
| CSS audit | stylelint + custom rules | Token CSS / Style Dictionary | Enterprise tools for design systems, not single-app polish |
| Perf testing | Playwright + DevTools | Lighthouse CI | Lighthouse targets web, not Electron desktop apps |
| Animation | CSS transitions (already used) | GSAP / svelte-motion | Transitions are subtle polish, not complex animations |

---

## Installation

```bash
# Dev dependencies only -- zero new production dependencies
cd locaNext
npm install -D stylelint stylelint-value-no-unknown-custom-properties
```

That's it. Two dev dependencies for CSS linting. Everything else is already available.

---

## Carbon Token Reference (For Polish Audit)

These are the Carbon Design System tokens that MUST be used consistently across all 5 pages:

### Spacing
| Token | Value | Use For |
|-------|-------|---------|
| `--cds-spacing-03` | 8px | Tight gaps (icon-to-text, inline elements) |
| `--cds-spacing-05` | 16px | Standard padding (cards, panels, sections) |
| `--cds-spacing-07` | 32px | Large gaps (section separators) |

### Colors
| Token | Use For |
|-------|---------|
| `--cds-text-01` | Primary text |
| `--cds-text-02` | Secondary/muted text |
| `--cds-layer-01` | Card/panel backgrounds |
| `--cds-layer-02` | Nested backgrounds |
| `--cds-layer-hover-01` | Hover states |
| `--cds-border-subtle-01` | Light borders |
| `--cds-border-strong-01` | Emphasis borders |
| `--cds-interactive-01` | Primary actions, active indicators |
| `--cds-focus` | Focus rings (accessibility) |

### Typography
| Token | Use For |
|-------|---------|
| `--cds-heading-03` | Page titles |
| `--cds-body-short-01` | Body text (0.875rem/20px) |
| `--cds-label-01` | Small labels (0.75rem) |

**Known inconsistencies to fix:**
- CodexPage uses hardcoded `font-size: 1.125rem` for h1 instead of Carbon heading tokens
- Multiple components use `font-size: 0.875rem` / `0.75rem` directly instead of type tokens
- Some borders use `1px solid` with hardcoded colors instead of `--cds-border-subtle-01`
- Several hover backgrounds use `var(--cds-layer-hover-01)` correctly but others don't

---

## Integration Points

### Where New Patterns Connect to Existing Code

1. **Skeleton loading in CodexPage** -- Replace the `{#if loadingList}` block (line 425-428) that shows a centered InlineLoading with a skeleton card grid matching the `entity-grid` layout
2. **Pagination for Codex** -- Backend already has `/api/ldm/codex/list/{type}` returning all entities. Add `?offset=0&limit=50` pagination support server-side, consume with IntersectionObserver sentinel client-side
3. **Lazy images** -- Add `loading="lazy"` to existing `<img>` elements in CodexPage entity cards (lines 437, 449) and CodexEntityDetail
4. **CSS token audit** -- Systematic pass through all 70+ `.svelte` files replacing hardcoded values with Carbon tokens
5. **Stylelint config** -- Add `.stylelintrc.json` at `locaNext/` root, integrate with existing dev workflow

### Files Most Affected

| File | Changes |
|------|---------|
| `CodexPage.svelte` | Skeleton grid, pagination, lazy images, token cleanup |
| `CodexEntityDetail.svelte` | Skeleton loading for detail view, lazy images |
| `GridPage.svelte` | Loading/empty/error state consistency |
| `GameDevPage.svelte` | Loading state audit, token cleanup |
| `TMPage.svelte` | Loading state audit, token cleanup |
| `WorldMapPage.svelte` | Quick verification pass only |
| All 70+ components | CSS token consistency pass |

---

## Sources

- [Carbon Components Svelte - SkeletonPlaceholder](https://svelte.carbondesignsystem.com/components/SkeletonPlaceholder) -- MEDIUM confidence (official docs)
- [Carbon Components Svelte - SkeletonText](https://svelte.carbondesignsystem.com/components/SkeletonText) -- MEDIUM confidence (official docs)
- [@humanspeak/svelte-virtual-list](https://github.com/humanspeak/svelte-virtual-list) -- HIGH confidence (evaluated and rejected for good reasons)
- [stylelint-value-no-unknown-custom-properties](https://github.com/csstools/stylelint-value-no-unknown-custom-properties) -- HIGH confidence (established tool)
- [MDN IntersectionObserver API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) -- HIGH confidence (web standard)
- [HTML loading="lazy"](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#loading) -- HIGH confidence (web standard)
- Codebase analysis of existing Carbon token usage -- HIGH confidence (direct observation)
