---
paths:
  - "locaNext/src/**/*.svelte"
  - "locaNext/src/**/*.svelte.ts"
---

# Svelte 5: NEVER use $state() for Map/Set/Array caches in render paths

Three proven infinite loop / freeze incidents from this codebase:

## Pattern: $state(new Map()) + reassignment = infinite loop

```javascript
// BAD — causes infinite re-render cascade
let cache = $state(new Map());
cache.set(key, value);
cache = new Map(cache);  // TRIGGERS REACTIVITY → re-render → re-fetch → re-set → LOOP

// GOOD — plain Map, mutate in place
let cache = new Map();
cache.set(key, value);  // No reactivity, read imperatively
```

## Incidents
1. **rowHeightCache** — `$state(new Map())` caused O(n^2) re-render cascade on 103k rows. Fix: plain Map.
2. **tabCache (CodexPage)** — `$state(new Map())` + `new Map(tabCache)` reassignment caused 822 API calls. Fix: plain Map, remove reassignment.
3. **BranchDriveSelector** — `$effect(() => validatePaths())` updating `$state` caused 161,424 API calls. Fix: `onMount()`.

## Rules
1. **Caches/lookup maps** — ALWAYS plain `new Map()`, never `$state(new Map())`
2. **One-time initialization** — use `onMount()`, not `$effect()` that reads reactive state
3. **$effect with fetch** — MUST have cleanup function OR use debounce+setTimeout. Raw `$effect → fetch → state update` = infinite loop
4. **>10k iterations** — use `$state.snapshot()` to avoid proxy overhead (130ms → 4ms)
