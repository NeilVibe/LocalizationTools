# Phase 93: Critical Debug Fixes - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three categories of bugs: (1) Codex page infinite API loop, (2) remote logger feedback cascade, (3) verify all v13.0 features work in DEV browser. All are debug/fix tasks — no new features.

</domain>

<decisions>
## Implementation Decisions

### DBG-01: Codex Infinite Loop Fix
- **D-01:** Root cause is the same pattern as BranchDriveSelector (commit 60e238cf): `$effect` triggers fetch → state update → re-render → `$effect` fires again
- **D-02:** Fix pattern: replace `$effect` fetch triggers with `onMount` for initial loads. Keep `$effect` only for debounced search (ItemCodexPage line 50 — this one is correct, has cleanup + setTimeout)
- **D-03:** Affected pages: `CodexPage.svelte` (line 85 — WebSocket `$effect` with fetch on complete), `ItemCodexPage.svelte` (search `$effect` is OK), check `CharacterCodexPage`, `RegionCodexPage`, `AudioCodexPage` for same pattern
- **D-04:** Use CDP deep monitor to measure call count BEFORE fix, then verify AFTER fix shows <=5 calls per page load
- **D-05:** The `tabCache` pattern in CodexPage (line 104-105: `tabCache.delete(); tabCache = new Map(tabCache)`) is suspicious — reassigning a Map could trigger reactivity cascade if it's `$state`. Check and fix if needed.

### DBG-02: Remote Logger Feedback Loop
- **D-06:** `remote-logger.js` intercepts `console.error` (line 81) and sends to `/api/v1/remote-logs/frontend`. If that endpoint returns 404 (route not mounted or backend down), the fetch failure may trigger another console.error → infinite cascade
- **D-07:** Fix: add a guard flag (`_isSending`) to prevent re-entrant calls. When inside `log()`, skip any recursive calls. Also add URL pattern check — never log errors about the remote-log endpoint itself.
- **D-08:** Add rate limiting: max 10 remote log calls per 5-second window. Drop excess silently.
- **D-09:** Backend endpoint: `server/api/remote_logging.py` + `server/services/remote_logging_service.py` — verify route is mounted and returns 200

### DBG-03: v13.0 E2E Verification
- **D-10:** Use DEV browser (localhost:5173) with CDP deep monitor, NOT Playwright
- **D-11:** Verification checklist (all must pass):
  1. Upload LanguageData file → grid renders without freeze
  2. Branch+Drive selector dropdowns visible in toolbar
  3. Change branch → validation shows green/red status
  4. Select a row → Image tab shows thumbnail OR fallback reason
  5. Select a row → Audio tab shows player OR fallback reason
  6. Select a row with TM loaded → TM context results appear
- **D-12:** Screenshot each verification step as evidence

### Claude's Discretion
- Exact rate limit numbers for remote logger (10/5s is suggestion, tune as needed)
- Whether to add a visual indicator when remote logging is disabled/degraded
- Order of fixing: Codex loop vs logger cascade (both are independent)

</decisions>

<specifics>
## Specific Ideas

- BranchDriveSelector fix (onMount instead of $effect) is the proven pattern — apply same fix to Codex pages
- CDP deep monitor (`testing_toolkit/cdp/deep_monitor.js`) is mandatory for measuring API call counts — it caught the 161k calls that code review missed
- The remote logger currently fails silently (line 38-40: catch block is empty) but the console.error interceptor can still cascade

</specifics>

<canonical_refs>
## Canonical References

### Infinite loop patterns (proven fixes)
- `locaNext/src/lib/components/ldm/BranchDriveSelector.svelte` line 28-30 — onMount pattern that fixed 161k API calls
- `memory/feedback_cdp_deep_monitor_debug.md` — CDP deep monitor technique
- `memory/feedback_svelte5_reactive_map_freeze.md` — $state(Map) freeze pattern

### Codex pages to fix
- `locaNext/src/lib/components/pages/CodexPage.svelte` — main codex, $effect at line 85
- `locaNext/src/lib/components/pages/ItemCodexPage.svelte` — $effect at line 50 (search debounce, likely OK)
- `locaNext/src/lib/components/pages/CharacterCodexPage.svelte` — $effect at line 50
- `locaNext/src/lib/components/pages/RegionCodexPage.svelte` — check for same pattern
- `locaNext/src/lib/components/pages/AudioCodexPage.svelte` — check for same pattern

### Remote logger
- `locaNext/src/lib/utils/remote-logger.js` — full file, 122 lines
- `server/api/remote_logging.py` — backend endpoint
- `server/services/remote_logging_service.py` — backend service

### Debug tools
- `testing_toolkit/cdp/deep_monitor.js` — CDP deep monitor for API call counting
- `testing_toolkit/DEV_MODE_PROTOCOL.md` — DEV testing protocol

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **BranchDriveSelector onMount fix** — exact same pattern to apply to Codex pages
- **CDP deep monitor** — ready to use for before/after measurement
- **StatusColors module** — already extracted, default color fix is Phase 94 not 93

### Established Patterns
- `onMount` for one-time data fetching (proven safe in Svelte 5)
- `$effect` with cleanup + setTimeout for debounced search (ItemCodexPage pattern)
- `$effect` WITHOUT cleanup for fetch = infinite loop risk

### Integration Points
- Codex pages use `getAuthHeaders()` from `$lib/utils/api.js`
- Remote logger initializes in `+layout.svelte` via `remoteLogger.init()`
- Backend codex routes in `server/tools/ldm/routes/codex.py` + 4 sub-routers

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 93-critical-debug-fixes*
*Context gathered: 2026-03-27*
