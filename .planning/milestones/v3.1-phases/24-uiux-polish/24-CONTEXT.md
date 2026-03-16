# Phase 24: UIUX Polish - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning
**Source:** Brainstorming session + v3.0 review findings

<domain>
## Phase Boundary

Polish ALL v3.0 features for accessibility, visual consistency, and error state handling. Use the full UIUX skill stack: critique, audit, bolder, polish, harden, adapt, clarify, optimize. Every v3.0 feature must meet accessibility standards and look production-ready.

**Scope: 5 UX requirements + full UIUX review with skills**

</domain>

<decisions>
## Implementation Decisions

### Accessibility Fixes
- **UX-01**: FileExplorerTree folder buttons → add `aria-expanded` reflecting expand state
- **UX-02**: Navigation tab dividers → CSS covers all 5 tabs, not just first
- **UX-03**: CodexPage card images → fallback to PlaceholderImage on 404
- **UX-04**: PlaceholderImage → use div layout instead of foreignObject for Chromium/Electron compatibility
- **UX-05**: MapDetailPanel → long text wraps properly at all viewport sizes

### Full UIUX Review (using skills)
- **audit skill**: Comprehensive accessibility + performance + responsive + theming audit
- **critique skill**: Visual hierarchy, information architecture, emotional resonance assessment
- **harden skill**: Error handling, i18n support, text overflow, edge cases across all v3.0 features
- **clarify skill**: UX copy review — error messages, labels, empty states, loading text
- **adapt skill**: Responsive design check across screen sizes
- **optimize skill**: Loading speed, rendering, bundle size for v3.0 components

### Components to Review (all v3.0 features)
1. GameDevPage + FileExplorerTree
2. CodexPage + CodexEntityDetail + CodexSearchBar
3. WorldMapPage + MapCanvas + MapDetailPanel + MapTooltip
4. AISuggestionsTab + NamingPanel
5. CategoryFilter + QAInlineBadge
6. Navigation tabs (all 5)

### Claude's Discretion
- Which skill findings to implement vs defer
- Grouping by component vs by issue type
- Whether to add Storybook-style visual regression tests

</decisions>

<specifics>
## Specific Ideas

### PlaceholderImage foreignObject Fix (UX-04)
Current: Uses SVG foreignObject which breaks in Chromium-based Electron.
Fix: Replace with simple div+CSS layout that renders consistently.

### Tab Divider CSS (UX-02)
Current: Only `:first-child` gets the divider style.
Fix: Apply to all `:not(:last-child)` tabs.

</specifics>

<deferred>
## Deferred Ideas

- Full design system extraction (extract skill)
- Dark mode theming pass
- Animation/delight additions (animate/delight skills)
- Onboarding flow design (onboard skill)

</deferred>

---

*Phase: 24-uiux-polish*
*Context gathered: 2026-03-16 via brainstorming session*
