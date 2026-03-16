# Feature Landscape

**Domain:** UI/UX Polish + Performance for Desktop Localization App
**Researched:** 2026-03-17

## Table Stakes

Features users expect from a polished desktop app. Missing = feels like a prototype.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Consistent loading states | Users see blank screens as broken | Low | Use SkeletonText/SkeletonPlaceholder from Carbon (already available) |
| Empty states with guidance | "No data" should explain what to do | Low | Each page needs a designed empty state, not just "No entities found" |
| Error states with recovery | Errors should offer retry/help | Low | Add retry buttons to API error states across all pages |
| Consistent spacing/typography | Mixed spacing feels unprofessional | Med | Audit all 70+ components for Carbon token usage |
| Dark mode consistency | Hardcoded colors break in dark mode | Med | Replace hardcoded hex values with `--cds-*` tokens |
| Keyboard navigation | Desktop app users expect keyboard control | Low | Tab ordering, Enter to select, Escape to close -- partially done |
| Responsive panels | Sidebar/detail panels should resize gracefully | Med | Some panels have fixed widths that break at certain sizes |

## Differentiators

Features that elevate beyond "works" to "impressive."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Codex infinite scroll | Browse 5000+ entities without pagination buttons | Med | IntersectionObserver sentinel + paginated API |
| Skeleton card grid | Loading state mirrors exact layout of content | Low | Much better perceived performance than a spinner |
| Lazy image loading | Images load only when scrolled into view | Low | Native `loading="lazy"` + IntersectionObserver for PlaceholderImage swap |
| Smooth page transitions | Pages don't flash/jump on switch | Low | CSS transitions on content areas (subtle, 150ms) |
| Cross-page visual coherence | All 5 pages feel like ONE app | High | The main deliverable -- systematic token audit |

## Anti-Features

Features to explicitly NOT build for v3.3.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full animation library (GSAP) | Overkill for polish pass, increases bundle | Use CSS transitions only (already in use) |
| Custom design system | Carbon is the system, don't fight it | Enforce Carbon tokens consistently |
| Lighthouse CI pipeline | Measures web metrics, not Electron metrics | Use Playwright + DevTools for meaningful perf |
| Theme customization UI | Users don't need to pick themes | Carbon's g90/g100 dark theme is the theme |
| Virtual scrolling for Codex | CSS Grid + variable heights = poor fit | Use pagination + lazy loading instead |
| Component documentation (Storybook) | Maintenance burden, 70+ components | Carbon docs are the reference |

## Feature Dependencies

```
CSS Token Audit --> Dark Mode Consistency (tokens fix dark mode)
Codex Pagination API --> Codex Infinite Scroll (backend needed first)
Skeleton Components --> Loading State Consistency (pattern established first)
Empty State Design --> Error State Design (same pattern, different content)
```

## MVP Recommendation

Prioritize:
1. Cross-page CSS token audit (fixes dark mode + spacing + typography in one pass)
2. Codex revamp (pagination + skeleton + lazy images -- highest visual impact)
3. Loading/empty/error state consistency across all 5 pages
4. Keyboard navigation audit

Defer:
- Smooth page transitions (nice-to-have, not critical)
- Responsive panel resizing (desktop app with known viewport)

## Sources

- Codebase analysis of existing 70+ Svelte components
- Carbon Design System component documentation
- PROJECT.md v3.3 target features
