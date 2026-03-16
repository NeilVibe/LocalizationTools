# Architecture Patterns

**Domain:** UI/UX Polish + Performance Optimization for Electron + Svelte 5 + Carbon Components
**Researched:** 2026-03-17
**Overall confidence:** HIGH (based on direct codebase analysis + Carbon/Svelte documentation)

## Current Architecture Snapshot

The app has 5 pages rendered via store-based navigation (`currentPage` in `navigation.js`), all wrapped in a Carbon `Theme` component using the `g100` dark theme. Each page is a full-height flex container. Key observations from codebase analysis:

| Page | Component | Scroll Strategy | State Pattern | Key Issue |
|------|-----------|----------------|---------------|-----------|
| **Files** | `FilesPage.svelte` | Native scroll on list | `$state` + API fetch | Solid, needs empty/error state polish |
| **Grid** | `GridPage.svelte` + `VirtualGrid.svelte` | Custom virtual scroll (height cache, cumulative positions) | `$state` + WebSocket + `ldmStore` | Best-engineered page; 1000+ line VirtualGrid |
| **Game Data** | `GameDevPage.svelte` | Split pane: tree + detail | `$state` + API fetch | Needs loading/empty states in tree |
| **Codex** | `CodexPage.svelte` | `overflow-y: auto` on content div, renders ALL entities | `$state` + API fetch | **CRITICAL: No virtualization, no lazy loading** |
| **World Map** | `WorldMapPage.svelte` | SVG canvas (d3-zoom) | `$state` + API fetch | Small data set, minimal issues |
| **TM** | `TMPage.svelte` | List with explorer grid | `$state` + API fetch | Needs consistency pass |

### CSS Token Usage Audit

The app uses Carbon `--cds-*` tokens extensively plus custom `--app-*` variables in `app.css`. However, pages define ad-hoc spacing values that drift:

| Token Category | CodexPage | GameDevPage | GridPage | Inconsistency |
|---------------|-----------|-------------|----------|---------------|
| Header padding | `12px 16px` | `0.5rem 0.75rem` | `0.5rem 1rem` | 3 different values |
| Content padding | `16px` | `1rem` | `0` (grid fills) | Mixed units |
| Border pattern | `1px solid var(--cds-border-subtle-01)` | Same | Same | Consistent (good) |
| Background | `var(--cds-layer-01)` | `var(--cds-layer-01)` | `var(--cds-layer-01)` | Consistent (good) |
| Focus outline | `2px solid var(--cds-focus)` | `2px solid var(--cds-focus)` | Via Carbon Button | Consistent (good) |
| Card radius | `6px` | N/A | N/A | Only Codex has cards |
| Transitions | `all 0.15s` | `all 0.15s ease` | Via Carbon | Mostly consistent |

## Recommended Architecture

### Layer 1: Design Token Foundation (Cross-Page Consistency)

Add shared layout tokens to `app.css` that all pages reference. This eliminates the spacing drift without refactoring existing components heavily.

**New tokens for `app.css`:**

```css
:root {
  /* Page layout tokens */
  --page-header-height: 48px;
  --page-header-padding: 0.75rem 1rem;
  --page-content-padding: 1rem;
  --page-gap: 0.75rem;

  /* Panel tokens */
  --panel-width-sm: 280px;
  --panel-width-md: 320px;
  --panel-width-max: 500px;
  --panel-border: 1px solid var(--cds-border-subtle-01);

  /* Card tokens */
  --card-radius: 6px;
  --card-padding: 0.625rem;
  --card-gap: 0.625rem;

  /* Transition tokens */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.2s ease;

  /* Skeleton tokens */
  --skeleton-bg: var(--cds-layer-02);
  --skeleton-shimmer-from: var(--cds-layer-02);
  --skeleton-shimmer-mid: var(--cds-layer-03);
}
```

**Rationale:** Tokens are non-breaking. Existing pages keep working. Each page audit adopts them incrementally.

### Layer 2: Shared UI State Components (3 New Components)

| Component | Purpose | Location | Lines (est.) |
|-----------|---------|----------|-------------|
| `PageHeader.svelte` | Consistent page header (icon + title + actions slot) | `lib/components/common/` | ~40 |
| `SkeletonCard.svelte` | Animated skeleton placeholder for card grids | `lib/components/common/` | ~50 |
| `InfiniteScroll.svelte` | IntersectionObserver sentinel for paginated loading | `lib/components/common/` | ~30 |

These are small, focused components (under 50 lines each). They do NOT replace existing page structure -- they provide building blocks pages can adopt.

### Layer 3: Codex Virtualization Strategy

The Codex page currently loads ALL entities into `entities = $state([])` and renders them in a CSS grid with `{#each entities as entity}`. With 5676+ mock entities, this creates thousands of DOM nodes and blocks the main thread.

**Recommended: Paginated IntersectionObserver (NOT full virtual scroll)**

Why NOT reuse VirtualGrid: VirtualGrid is a table with variable-height rows, inline editing, column management, row locking, and WebSocket sync. It is 1000+ lines of code tightly coupled to translation grid semantics. Codex is a card grid with images. Different paradigm.

Why NOT a new virtual scroll: Cards in a responsive CSS grid (`repeat(3, 1fr)` with media queries) have uniform height. Virtual scroll for uniform-height content in a multi-column grid layout is overkill -- the browser handles CSS grid reflow well with bounded DOM counts.

Why IntersectionObserver pagination: Load 50 cards per batch. Observe a sentinel element at the bottom. When it enters the viewport, load the next batch. Simple, proven, zero library dependencies.

```
[Search Bar]
[Type Tabs]
[Card Grid: first 50 cards]
[Card Grid: next 50 cards loaded on scroll]
[Skeleton cards x6]          <-- shown while loading next batch
[Sentinel div]               <-- IntersectionObserver target
```

**API change required:** `/api/ldm/codex/list/{entityType}` needs `offset` and `limit` query parameters. This is a backend wrapper change (allowed by project constraints -- "only wrapper layers").

### Component Boundaries

| Component | Responsibility | Communicates With | Status |
|-----------|---------------|-------------------|--------|
| `+layout.svelte` | Auth, theme, nav tabs, global toasts | All pages via stores | UNCHANGED |
| `app.css` | Design tokens, Carbon overrides, scrollbar, fonts | All components via CSS cascade | MODIFIED (add layout tokens) |
| `PageHeader.svelte` (NEW) | Standard page header with icon + title + action slots | Used by each page component | NEW |
| `InfiniteScroll.svelte` (NEW) | IntersectionObserver sentinel that fires callback when visible | CodexPage, potentially others | NEW |
| `SkeletonCard.svelte` (NEW) | Loading placeholder matching Codex card dimensions | CodexPage | NEW |
| `CodexPage.svelte` | Paginated entity loading, infinite scroll, skeleton states | CodexSearchBar, CodexEntityDetail, InfiniteScroll | MODIFIED (major) |
| `GameDevPage.svelte` | Split pane with tree + detail | FileExplorerTree, GameDataTree | MODIFIED (loading/empty states) |
| `GridPage.svelte` | Translation grid with TM side panel | VirtualGrid, RightPanel | MODIFIED (token adoption) |
| `WorldMapPage.svelte` | SVG map with d3-zoom | MapCanvas, MapTooltip | MODIFIED (minor token adoption) |
| `TMPage.svelte` | TM management with explorer grid | TMExplorerGrid | MODIFIED (token adoption) |
| `FilesPage.svelte` | File browser with explorer grid | ExplorerGrid, Breadcrumb | MODIFIED (empty/error states) |
| `VirtualGrid.svelte` | Virtual scroll for translation grid | GridPage only | UNCHANGED |

### Data Flow

#### Current Codex Flow (Problem)
```
onMount -> fetchTypes() -> fetchEntityList(type)
                           -> GET /api/ldm/codex/list/{type} returns ALL entities
                           -> entities = data.entities (full array, possibly 1000+)
                           -> {#each entities} renders ALL cards simultaneously
                           -> Images load ALL at once (N HTTP requests)
```

#### Proposed Codex Flow (Solution)
```
onMount -> fetchTypes() -> fetchEntityPage(type, offset=0, limit=50)
                           -> entities = newBatch (first 50)
                           -> InfiniteScroll sentinel observed
                           -> User scrolls to bottom:
                              -> Show 6 SkeletonCards
                              -> fetchEntityPage(type, offset=50, limit=50)
                              -> entities = [...entities, ...newBatch]
                              -> Sentinel re-observed
                           -> Stop when response.length < limit
                           -> Images use native loading="lazy" on <img> tags
```

#### Cross-Page Token Flow
```
app.css (new layout tokens)
    |
    +--> PageHeader.svelte (uses --page-header-padding, --page-header-height)
    |       |
    |       +--> CodexPage (header with Book icon + "Game World Codex")
    |       +--> GameDevPage (header with GameConsole icon + "Game Data")
    |       +--> WorldMapPage (header with Earth icon + "World Map")
    |
    +--> Card styles (--card-radius, --card-padding, --card-gap)
    |       |
    |       +--> CodexPage entity cards
    |       +--> SkeletonCard placeholders (must match exactly)
    |
    +--> Panel styles (--panel-width-sm, --panel-border)
            |
            +--> GameDevPage explorer panel (currently hardcoded 280px)
            +--> GridPage RightPanel (currently uses bind:width={300})
```

## Patterns to Follow

### Pattern 1: IntersectionObserver with Svelte 5 $effect Cleanup

**What:** Use `$effect` for lifecycle-safe IntersectionObserver setup and teardown.
**When:** Codex infinite scroll, potentially lazy image loading.
**Confidence:** HIGH (native browser API + Svelte 5 $effect cleanup is well-documented)

```svelte
<!-- InfiniteScroll.svelte -->
<script>
  let { onloadmore = () => {}, loading = false, hasMore = true } = $props();
  let sentinel = $state(null);

  $effect(() => {
    if (!sentinel || !hasMore || loading) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          onloadmore();
        }
      },
      { rootMargin: '200px' }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  });
</script>

<div bind:this={sentinel} class="scroll-sentinel" aria-hidden="true">
  {#if loading}
    <slot name="loading" />
  {/if}
</div>
```

Key details:
- `rootMargin: '200px'` starts loading BEFORE the user reaches the bottom (prefetch feel).
- The `$effect` re-runs when `hasMore` or `loading` change, reconnecting/disconnecting the observer.
- Cleanup via `return () => observer.disconnect()` prevents memory leaks.

### Pattern 2: Skeleton States Matching Real Card Dimensions

**What:** Animated skeleton placeholders that match the exact layout of real content.
**When:** Codex card loading, any async grid loading.
**Why:** Prevents Cumulative Layout Shift (CLS). Users see the right-sized placeholder before content appears.

```svelte
<!-- SkeletonCard.svelte -->
<script>
  let { count = 6 } = $props();
</script>

{#each Array(count) as _, i (i)}
  <div class="skeleton-card">
    <div class="skeleton-image"></div>
    <div class="skeleton-lines">
      <div class="skeleton-line wide"></div>
      <div class="skeleton-line tag"></div>
      <div class="skeleton-line narrow"></div>
    </div>
  </div>
{/each}

<style>
  .skeleton-card {
    display: flex;
    gap: var(--card-gap, 10px);
    padding: var(--card-padding, 10px);
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: var(--card-radius, 6px);
  }
  .skeleton-image {
    width: 48px;
    height: 48px;
    flex-shrink: 0;
    border-radius: 4px;
    background: var(--skeleton-bg, var(--cds-layer-02));
    animation: shimmer 1.5s ease-in-out infinite;
  }
  .skeleton-lines {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
    justify-content: center;
  }
  .skeleton-line {
    height: 12px;
    border-radius: 2px;
    background: var(--skeleton-bg, var(--cds-layer-02));
    animation: shimmer 1.5s ease-in-out infinite;
  }
  .skeleton-line.wide { width: 70%; }
  .skeleton-line.tag { width: 40px; height: 16px; border-radius: 8px; }
  .skeleton-line.narrow { width: 85%; }
  @keyframes shimmer {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.8; }
  }
</style>
```

Dimensions match `entity-card` in CodexPage exactly: 48x48 image, flex layout, same padding/gap/radius.

### Pattern 3: PageHeader for Consistent Page Chrome

**What:** A shared header component all applicable pages use for their top bar.
**When:** Pages with a standard header (Codex, Game Dev, World Map). NOT for pages with complex custom toolbars (GridPage).

```svelte
<!-- PageHeader.svelte -->
<script>
  let { icon = undefined, title = '', children } = $props();
</script>

<div class="page-header">
  <div class="header-title">
    {#if icon}
      <svelte:component this={icon} size={24} />
    {/if}
    <h1>{title}</h1>
  </div>
  <div class="header-actions">
    {@render children?.()}
  </div>
</div>

<style>
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--page-header-padding, 0.75rem 1rem);
    background: var(--cds-layer-01);
    border-bottom: var(--panel-border, 1px solid var(--cds-border-subtle-01));
    flex-shrink: 0;
    min-height: var(--page-header-height, 48px);
  }
  .header-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--cds-text-01);
  }
  .header-title h1 {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
</style>
```

This replaces ad-hoc `.codex-header`, `.explorer-header` with one reusable component.

### Pattern 4: Native Image Lazy Loading

**What:** Use `loading="lazy"` on all `<img>` tags in card grids.
**When:** CodexPage entity cards (every card has a thumbnail image).
**Why:** Zero JavaScript needed. Browser handles viewport detection natively.

```svelte
<img
  src="{API_BASE}{entity.ai_image_url}"
  alt={entity.name}
  class="card-thumb"
  loading="lazy"
  onerror={handleImageError}
/>
```

This is additive to IntersectionObserver pagination. Pagination controls card rendering (DOM nodes). `loading="lazy"` controls image network requests for already-rendered cards. They complement each other.

### Pattern 5: Paginated API with Frontend Accumulation

**What:** Backend returns paginated results, frontend accumulates them into the reactive array.
**When:** Codex entity lists.

```svelte
let entities = $state([]);
let currentPage = $state(0);
let hasMore = $state(true);
let loadingMore = $state(false);
const PAGE_SIZE = 50;

async function fetchEntityPage(entityType, page) {
  if (loadingMore) return;
  loadingMore = true;
  try {
    const response = await fetch(
      `${API_BASE}/api/ldm/codex/list/${entityType}?offset=${page * PAGE_SIZE}&limit=${PAGE_SIZE}`,
      { headers: getAuthHeaders() }
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const batch = data.entities || [];

    if (page === 0) {
      entities = batch;
    } else {
      entities = [...entities, ...batch];
    }
    hasMore = batch.length === PAGE_SIZE;
    currentPage = page;
  } finally {
    loadingMore = false;
  }
}

function loadMore() {
  if (hasMore && !loadingMore) {
    fetchEntityPage(activeTab, currentPage + 1);
  }
}
```

On tab change: reset `entities = []`, `currentPage = 0`, `hasMore = true`, then `fetchEntityPage(newTab, 0)`.

### Pattern 6: Consistent 4-State Handling

**What:** Every data-fetching component handles exactly 4 states: error, loading, empty, content.
**When:** All pages and panels that make API calls.

```svelte
{#if apiError}
  <div class="state-error">
    <WarningAlt size={32} />
    <p>{apiError}</p>
    <Button kind="ghost" size="small" on:click={retry}>Retry</Button>
  </div>
{:else if loading}
  <SkeletonCard count={6} />
{:else if items.length === 0}
  <div class="state-empty">
    <svelte:component this={emptyIcon} size={48} />
    <p>{emptyMessage}</p>
  </div>
{:else}
  <!-- Content -->
{/if}
```

Currently: CodexPage has error and loading but uses a plain `<p>` for empty. GameDevPage has an empty placeholder but no error state. WorldMapPage has both. TMPage has loading but minimal empty state. Standardize all 5.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Reusing VirtualGrid for Card Grids
**What:** Trying to adapt VirtualGrid for the Codex card layout.
**Why bad:** VirtualGrid is 1000+ lines of variable-height row virtualization with inline editing, column management, row locking, WebSocket sync, and sparse array paging. Codex is a CSS grid of uniform-height cards. Forcing table semantics onto card layout creates brittle, unmaintainable code.
**Instead:** Use IntersectionObserver + pagination for the card grid. Simple and sufficient.

### Anti-Pattern 2: Component-Scoped Ad-Hoc Spacing
**What:** Each page defining its own `padding: 12px` / `padding: 0.5rem 0.75rem` in scoped `<style>`.
**Why bad:** Visual inconsistency across pages. Currently: CodexPage header = `12px 16px`, GameDevPage header = `0.5rem 0.75rem`, GridPage toolbar = `0.5rem 1rem`.
**Instead:** Use shared CSS custom properties from `app.css`. All pages reference `var(--page-header-padding)`.

### Anti-Pattern 3: Loading State Diversity
**What:** Each page using different loading patterns -- CodexPage uses `InlineLoading description="Loading Codex entity types..."`, GameDevPage uses a custom pulse-dot animation, WorldMapPage uses `InlineLoading description="Loading world map..."`.
**Why bad:** Users learn patterns. Inconsistent loading states make 5 pages feel like 5 different apps.
**Instead:** Standardize: skeleton cards for grids, `InlineLoading` with consistent description format for single items, consistent empty/error containers.

### Anti-Pattern 4: Full Entity List Fetch Without Pagination
**What:** `GET /api/ldm/codex/list/{type}` returning ALL entities at once.
**Why bad:** With 5676 mock entities across 10 directories, some types have 1000+ entries. All rendered at once = thousands of DOM nodes, blocked main thread, scroll jank, all images loading simultaneously.
**Instead:** Paginated endpoint with `offset`/`limit`, frontend infinite scroll.

### Anti-Pattern 5: Skeleton Dimension Mismatch
**What:** Skeleton placeholders that are a different size than the real content.
**Why bad:** Causes layout shift when real content replaces skeletons. Grid reflows, content jumps.
**Instead:** SkeletonCard dimensions MUST match entity-card dimensions exactly (48x48 image, same flex gap, same padding, same border-radius).

### Anti-Pattern 6: Wrapping Every Page in a Generic PageShell
**What:** Creating a `<PageShell>` wrapper component that forces all pages into one layout.
**Why bad:** GridPage has a complex custom toolbar with TM indicator, back button, and action buttons. GameDevPage has a split-pane layout. Forcing them into a single wrapper either constrains the layout or becomes so flexible it adds nothing.
**Instead:** Use `PageHeader.svelte` as an opt-in component for the header area only. Each page keeps its own layout structure but adopts shared tokens.

## Integration Points Summary

### NEW Files (3 components)

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `lib/components/common/PageHeader.svelte` | ~40 | Consistent page header with icon, title, action slots |
| `lib/components/common/SkeletonCard.svelte` | ~50 | Animated loading placeholder matching card dimensions |
| `lib/components/common/InfiniteScroll.svelte` | ~30 | IntersectionObserver sentinel for paginated loading |

### MODIFIED Files

| File | Change Scope | What Changes |
|------|-------------|--------------|
| `app.css` | Small addition | ~20 new CSS custom properties for layout consistency |
| `CodexPage.svelte` | **Major refactor** | Pagination state, InfiniteScroll integration, SkeletonCard usage, `loading="lazy"` on images, 4-state handling, tab reset logic |
| Backend codex list route | Small addition | `offset` and `limit` query parameters for pagination |
| `GameDevPage.svelte` | Moderate | Loading states for tree panel, empty state improvement, token adoption |
| `GridPage.svelte` | Token adoption | Replace hardcoded spacing with CSS custom properties |
| `WorldMapPage.svelte` | Minor | Adopt layout tokens, verify header consistency |
| `TMPage.svelte` | Token adoption | Adopt layout tokens, verify header consistency |
| `FilesPage.svelte` | Moderate | Empty/error state standardization, token adoption |

### UNCHANGED Files

| File | Why Unchanged |
|------|--------------|
| `VirtualGrid.svelte` | Already well-engineered; virtual scroll works perfectly for its use case |
| `+layout.svelte` | Navigation structure and global chrome are correct |
| All stores | No store changes needed for this milestone |
| All API utilities | Infrastructure is solid |

## Build Order (Dependency-Aware)

```
Phase 1: Design Tokens in app.css
    |     (no dependencies, foundation for everything)
    |
    +--> Phase 2: Shared Components (PageHeader, SkeletonCard, InfiniteScroll)
    |       |     (depends on tokens for styling)
    |       |
    |       +--> Phase 3: Codex Revamp
    |       |     (depends on InfiniteScroll + SkeletonCard + backend pagination)
    |       |     (highest impact: performance fix + UX improvement)
    |       |
    |       +--> Phase 4: Cross-Page Polish (all 5 pages)
    |             (depends on PageHeader + tokens)
    |             (each page is independent -- can parallelize)
    |             4a: GameDevPage loading/empty states
    |             4b: FilesPage empty/error states
    |             4c: TMPage token adoption + state handling
    |             4d: GridPage token adoption
    |             4e: WorldMapPage verification pass
    |
    +--> Phase 5: Visual Consistency Verification
          (depends on all above completing)
          (screenshot comparison across all 5 pages)
```

**Why this order:**

1. **Design tokens FIRST** -- every component references them. Changing tokens after components are built invalidates work.
2. **Shared components SECOND** -- reused across multiple pages. Must be stable before pages adopt them.
3. **Codex revamp THIRD** -- highest impact change. The performance problem (rendering 1000+ cards) is the worst UX issue in the entire app. Uses both shared components and backend change.
4. **Cross-page polish FOURTH** -- incremental adoption of patterns from phases 1-2. Pages are independent of each other (parallelizable as 4a-4e).
5. **Verification LAST** -- validates all changes together via screenshots of all 5 pages side by side.

**Parallelization:** Phases 4a through 4e are fully independent and can run as parallel agent tasks (one per page).

## Scalability Considerations

| Concern | Current (100 entities) | At 1K entities | At 10K entities |
|---------|----------------------|----------------|-----------------|
| Codex card rendering | All rendered (OK but wasteful) | Jank (too many DOM nodes) | Broken (OOM likely) |
| With pagination (50/page) | 50 DOM nodes | 50 initial, accumulates on scroll | 50 initial, bounded growth |
| Image loading | All at once | 1000 HTTP requests simultaneously | Unusable |
| With `loading="lazy"` | ~10-15 concurrent | ~10-15 concurrent | ~10-15 concurrent |
| VirtualGrid (Grid page) | Already virtualized | Fine | Fine (battle-tested) |
| World Map (SVG) | 14 nodes | Fine up to ~500 | Would need node clustering |
| Design tokens | Zero runtime cost | Zero runtime cost | Zero runtime cost |
| Skeleton animation | Lightweight CSS-only | Same | Same |

## Sources

- Direct codebase analysis: `CodexPage.svelte` (747 lines), `VirtualGrid.svelte` (1000+ lines), `GameDevPage.svelte` (527 lines), `GridPage.svelte` (469 lines), `WorldMapPage.svelte`, `TMPage.svelte`, `FilesPage.svelte`, `+layout.svelte` (683 lines), `app.css` (310 lines)
- [Carbon Design System Color Tokens](https://carbondesignsystem.com/elements/color/tokens/) -- Token naming conventions and `--cds-` prefix system
- [Carbon Components Svelte Theme](https://svelte.carbondesignsystem.com/components/Theme) -- Theme component, g100 dark theme usage
- [Carbon Themes Code Reference](https://carbondesignsystem.com/elements/themes/code/) -- CSS custom property implementation patterns
- [Lazy Load with Svelte and IntersectionObserver](https://www.danyelkoca.com/en/blog/lazy-load-with-svelte-and-intersection-observer) -- IO lifecycle pattern in Svelte
- [Svelte Intersection Observer Patterns](https://reuters-graphics.github.io/example_svelte-graph-patterns/observer/) -- IO with reactive state
- [IntersectionObserver API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) -- rootMargin, threshold options
