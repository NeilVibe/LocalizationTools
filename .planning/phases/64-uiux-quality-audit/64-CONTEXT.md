# Phase 64: UIUX Quality Audit - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

AI-powered visual audit of all 5 main pages + merge modal edge case hardening. Two parts: (1) screenshot review with Qwen Vision critique, (2) code fixes for merge modal loading/error/edge states.

</domain>

<decisions>
## Implementation Decisions

### Visual Audit (UIUX-01, UIUX-02)
- Requires dev servers running (currently NOT running)
- Screenshots via Playwright MCP → Qwen3-VL review → catalog issues → fix → verify
- 5 pages: Files, Game Dev, Codex, Map, TM
- This is a human_needed item — servers must be started manually

### Merge Modal Hardening (UIUX-03)
- Can be done without live servers — code-level improvements
- Loading states: spinner during preview/execute
- Error states: clear error message + retry button
- Edge cases: empty project, no matches found, cancelled merge
- The merge modal is in the Svelte frontend (locaNext/src/)

### Claude's Discretion
- Specific loading indicator design (spinner, skeleton, progress bar)
- Error message wording and retry UX
- Edge case handling approach (empty state illustrations, toast messages)
- Which issues from visual audit are "critical" vs "minor"

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- locaNext/src/ — Svelte 5 frontend with runes
- Merge modal component (need to locate)
- server/api/merge.py — merge endpoints (SSE streaming for execute)
- Carbon Components for UI library

### Established Patterns
- Svelte 5 Runes ($state, $derived, $effect)
- Optimistic UI mandatory
- SSE streaming for long operations
- {#each items as item (item.id)} — always use keys

### Integration Points
- Merge modal consumes /api/merge/preview and /api/merge/execute
- SSE events: progress, log, complete, error, ping

</code_context>

<specifics>
## Specific Ideas

- Dev servers NOT running — visual audit (UIUX-01/02) must be deferred to human testing
- Merge modal code hardening (UIUX-03) can proceed without servers

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
