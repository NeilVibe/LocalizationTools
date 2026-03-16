# Domain Pitfalls

**Domain:** UI/UX Polish + Performance for Electron + Svelte 5 App
**Researched:** 2026-03-17

## Critical Pitfalls

### Pitfall 1: CSS Token Replacement Breaking Layout
**What goes wrong:** Blindly replacing hardcoded values with Carbon tokens changes actual rendered values (e.g., replacing `padding: 12px` with `--cds-spacing-05` which is 16px).
**Why it happens:** Carbon spacing tokens use a specific scale (4, 8, 12, 16, 24, 32, 48) -- not every hardcoded value has an exact token match.
**Consequences:** Layout shifts, misaligned elements, broken responsive behavior.
**Prevention:** When replacing values, compare the actual pixel value of the Carbon token vs the hardcoded value. If no exact match exists, use the nearest token and verify visually. Document intentional deviations.
**Detection:** Before/after screenshots of each page at the same viewport size.

### Pitfall 2: IntersectionObserver Memory Leaks in Svelte 5
**What goes wrong:** Creating IntersectionObserver instances without cleaning them up when components unmount.
**Why it happens:** Svelte 5 actions need explicit `destroy()` cleanup. If the action is on an element inside an `{#each}` block that re-renders, observers pile up.
**Consequences:** Memory grows continuously when switching tabs or scrolling the Codex.
**Prevention:** Always return `{ destroy: () => observer.disconnect() }` from Svelte actions. Use a single shared observer for multiple elements (one observer, many `observe()` calls) rather than one observer per element.
**Detection:** DevTools Memory tab -- take heap snapshots before and after 10 tab switches.

### Pitfall 3: Pagination Breaks Entity Selection
**What goes wrong:** User selects entity, switches tab, comes back -- their entity list is reset to page 1.
**Why it happens:** Pagination state (current offset, loaded entities) is lost when tab switches because `fetchEntityList()` resets `entities = []`.
**Consequences:** User loses their scroll position and must scroll down again to find where they were.
**Prevention:** Cache loaded entities per tab in a Map. When switching back to a tab, restore from cache. Only re-fetch if data is stale.
**Detection:** Manual testing: scroll down in Items tab, switch to Characters, switch back. Items should restore.

## Moderate Pitfalls

### Pitfall 4: Skeleton Placeholder Height Mismatch
**What goes wrong:** Skeleton cards are a different height than real cards, causing visible "jump" when content loads.
**Prevention:** Match skeleton card dimensions exactly to real card dimensions. Use the same CSS classes for both skeleton and real cards.

### Pitfall 5: Lazy Loading Causing Visible Placeholder Flicker
**What goes wrong:** Images show placeholder -> blank -> loaded image, creating a triple state flash.
**Prevention:** Use `loading="lazy"` on `<img>` which handles this natively. For the PlaceholderImage -> real image pattern, keep the placeholder visible until `onload` fires on the real image.

### Pitfall 6: Stylelint Conflicts with Svelte Scoped Styles
**What goes wrong:** Stylelint doesn't understand Svelte's `<style>` blocks and `::global()` syntax out of the box.
**Prevention:** Use `postcss-html` parser with stylelint to properly parse Svelte files. Add `stylelint-config-html/svelte` to the config.

### Pitfall 7: Carbon Token Dark Mode Gaps
**What goes wrong:** Some Carbon tokens don't change between light and dark themes (e.g., `--cds-interactive-01` is the same blue in both). If you relied on contrast against a dark background, the blue-on-dark may be hard to read.
**Prevention:** Test every page in both light and dark themes after token migration. Focus on text readability and interactive element visibility.

## Minor Pitfalls

### Pitfall 8: Empty State Design Inconsistency
**What goes wrong:** Each developer/phase designs empty states differently -- different icons, different text styles, different button placements.
**Prevention:** Create a single `EmptyState` component used across all pages. Props: icon, title, description, optional action button.

### Pitfall 9: Scroll Position Reset on Re-render
**What goes wrong:** Svelte 5 reactivity causes the entity grid to re-render when state changes, resetting scroll position.
**Prevention:** Use `{#key}` blocks carefully. Don't replace the entire array when appending (use `entities.push(...newItems)` with Svelte 5 proxied arrays).

### Pitfall 10: Performance Regression from Token Migration
**What goes wrong:** CSS custom properties are slower to resolve than static values. With 1000+ DOM elements in VirtualGrid, this could add up.
**Prevention:** Don't tokenize values inside VirtualGrid cell rendering. VirtualGrid already works -- focus token migration on structural/layout CSS, not high-frequency cell styles.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| CSS token audit | #1 - Breaking layout with wrong token values | Before/after screenshots for every page |
| Codex revamp | #2 - IntersectionObserver leaks | Single shared observer, proper cleanup |
| Codex pagination | #3 - Losing scroll position on tab switch | Cache entities per tab |
| Loading states | #4 - Skeleton height mismatch | Same CSS classes for skeleton and real |
| Lazy images | #5 - Placeholder flicker | Keep placeholder until onload fires |
| Stylelint setup | #6 - Svelte parsing issues | Use postcss-html parser |
| Dark mode | #7 - Token contrast gaps | Test both themes after migration |

## Sources

- Codebase analysis of existing component patterns
- Svelte 5 action lifecycle (official docs)
- IntersectionObserver API gotchas (MDN)
- Carbon Design System theming documentation
- Experience from v3.1 UIUX audit (60 fixes)
