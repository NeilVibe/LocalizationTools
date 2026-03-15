# Phase 22: Svelte 5 Migration - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning
**Source:** Brainstorming session + codebase audit

<domain>
## Phase Boundary

Migrate all Svelte 4 event patterns to Svelte 5 Runes. Zero createEventDispatcher, zero on: directives (except Carbon interop). This is the foundation phase — must complete before Phase 23 (Bug Fixes) because fixes will touch the same components.

**Scope: 69 Svelte files total, ~29 files need changes.**

</domain>

<decisions>
## Implementation Decisions

### Migration Pattern
- Replace `createEventDispatcher` + `dispatch('event', data)` → `$props` callback pattern: `let { onevent } = $props()`
- Replace `on:click={handler}` → `onclick={handler}` (Svelte 5 native)
- Replace `e.detail` access → direct callback parameters
- Carbon components (`<Button on:click>`, `<TextInput on:change>`) are EXEMPT — Carbon library requires on: syntax until upstream upgrades

### Priority Order (by complexity and dependency)
1. **VirtualGrid.svelte** — most complex (20 dispatch calls), many consumers depend on it
2. **LDM.svelte** — primary consumer of VirtualGrid events, must update bindings
3. **TMManager.svelte** (17 on: directives) + TMDataGrid (6)
4. **QuickSearch.svelte** (24 on: directives) + KRSimilar (14) + XLSTransfer (14)
5. **All remaining components** — FilesPage, GridPage, TMPage, modals, etc.

### Files Requiring Migration

**18 files with createEventDispatcher:**
- AccessControl, Breadcrumb, ExplorerGrid, FilePickerDialog, PretranslateModal
- QAMenuPanel, RightPanel, TMDataGrid, TMManager, TMQAPanel, TMTab
- TMUploadModal, TMViewer, VirtualGrid, FilesPage, GridPage, TMPage

**29 files with on: directives (151 total occurrences)**

**8 files with e.detail access (12 occurrences)**

### Already Migrated (Reference Implementations)
- AISuggestionsTab → onApplySuggestion
- CategoryFilter → onchange
- CodexEntityDetail → onsimilar
- CodexSearchBar → onresult
- MapDetailPanel → onClose
- NamingPanel → onApply
- QAInlineBadge → onDismiss

### Claude's Discretion
- Exact callback naming conventions (follow existing pattern: `on` + PascalCase event name)
- Whether to batch files by wave or by component tree depth
- Test verification approach (grep-based verification of zero legacy patterns)

</decisions>

<specifics>
## Specific Ideas

### VirtualGrid Dispatch Map (20 calls → 20 callbacks)
```
dispatch('inlineEditStart', {...}) → onInlineEditStart({...})
dispatch('rowUpdate', {rowId}) → onRowUpdate({rowId})
dispatch('rowSelect', {row}) → onRowSelect({row})
dispatch('confirmTranslation', {...}) → onConfirmTranslation({...})
dispatch('dismissQA', {...}) → onDismissQA({...})
dispatch('runQA', {...}) → onRunQA({...})
dispatch('addToTM', {...}) → onAddToTM({...})
```

### GameDevPage.svelte line 253 — already broken
```svelte
on:inlineEditStart={handleInlineEditStart}  <!-- Svelte 4, needs migration -->
```
This uses `e.detail` (line 167) — must convert to direct callback params.

</specifics>

<deferred>
## Deferred Ideas

- Carbon Components Svelte 5 upgrade (external dependency — out of scope per REQUIREMENTS.md)
- Full type annotations for all callback props (nice-to-have, not required)

</deferred>

---

*Phase: 22-svelte-5-migration*
*Context gathered: 2026-03-16 via brainstorming session*
