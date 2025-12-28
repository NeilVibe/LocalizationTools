# Code Review Lessons Learned

**Created:** 2025-12-28 | **Status:** ACTIVE

---

## Recent Debugging Sessions

This document captures lessons learned from debugging sessions to prevent similar issues in the future.

---

## Lesson 1: Use Existing O(1) Lookup Helpers

**Issue:** QA panel click wasn't navigating to correct row

**Root Cause:**
```javascript
// BAD: Linear search through sparse array
const row = rows.find(r => r && r.id === rowId);

// GOOD: O(1) lookup using existing helper
const row = getRowById(rowId);
```

**The Pattern:**
- VirtualGrid has `rowIndexById` Map for O(1) row lookups
- Helper functions exist: `getRowById(id)`, `getRowIndexById(id)`
- New code was using `rows.find()` instead of the optimized helpers

**Rule:** Before writing array search code, check if O(1) lookup helpers already exist.

---

## Lesson 2: String vs Number ID Comparison

**Issue:** Row IDs not matching between QA API and VirtualGrid

**Root Cause:**
```javascript
// QA API returns: row_id: 123 (number)
// VirtualGrid stores: row.id = "123" (string)

// BAD: Direct comparison fails
row.id === rowId  // "123" === 123 = false

// GOOD: Normalize to string
rowIndexById.get(rowId.toString())
```

**Rule:** Always use `.toString()` when looking up IDs that might be numbers.

---

## Lesson 3: Double-Click is Unreliable

**Issue:** Double-click on QA issues wasn't working

**Root Cause:**
- Single-click fires first, closes panel
- Double-click handler never gets triggered

**Solution:**
- Use single-click for all actions
- Don't rely on double-click when single-click closes the UI

**Rule:** If single-click closes a modal/panel, double-click won't work.

---

## Lesson 4: AbortController Complexity

**Issue:** QA panel freezing on click

**Root Cause:**
- Complex AbortController logic with event listeners
- Multiple $effect() blocks causing infinite loops
- Cleanup running on every state change

**Solution:**
```javascript
// BAD: Complex controller with listeners
const controller = new AbortController();
controller.signal.addEventListener('abort', () => { ... });

// GOOD: Simple per-request timeout
async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}
```

**Rule:** Keep AbortController usage simple - create per request, add timeout, cleanup.

---

## Lesson 5: Svelte 5 $effect() Side Effects

**Issue:** Multiple $effect() blocks causing unexpected behavior

**Root Cause:**
```javascript
// BAD: Multiple effects that interact
$effect(() => {
  if (open && fileId) loadData();
});

$effect(() => {
  if (!open) cancelAllRequests();  // Runs on mount too!
});
```

**Solution:**
- Minimize number of $effect() blocks
- Be aware $effect() runs on mount
- Put cleanup in explicit functions, not reactive effects

**Rule:** Svelte 5 $effect() runs on initialization - add guards for cleanup code.

---

## Lesson 6: Safe Property Access

**Issue:** "Cannot read properties of undefined (reading 'id')"

**Root Cause:**
```javascript
// BAD: Direct access without null check
checkTypes[selectedCheckType].id

// GOOD: Safe getter function
function getCurrentCheckType() {
  const index = selectedCheckType ?? 0;
  const type = checkTypes[index];
  return type?.id ?? "all";
}
```

**Rule:** Always add null checks when accessing array/object properties by index.

---

## Lesson 7: Stale Running Tasks

**Issue:** Tasks showing "RUNNING" for 1800+ minutes

**Root Cause:**
- Backend operations can crash without marking status
- No automatic cleanup of zombie tasks
- Clear History only clears completed/failed

**Solution:**
- Added `/operations/cleanup/stale` endpoint
- Marks tasks running > 60 min as failed
- Added "Clean Stale" button in Task Manager

**Rule:** Always have a way to cleanup stuck/zombie processes.

---

## Code Review Checklist

Use this checklist when reviewing code:

### Lookup Patterns
- [ ] Using O(1) lookup helpers where available
- [ ] String/number ID types match
- [ ] Array access has bounds checking

### Event Handlers
- [ ] Not relying on double-click when single-click closes UI
- [ ] AbortController usage is simple
- [ ] Cleanup functions are explicit, not in $effect()

### Svelte 5 Specific
- [ ] $effect() has guards for initialization
- [ ] $derived() for computed values
- [ ] $state() for reactive variables
- [ ] No mixing Svelte 4 and Svelte 5 patterns

### Error Handling
- [ ] Safe property access with ?. and ??
- [ ] Timeout on async operations
- [ ] User-visible error messages
- [ ] Retry capability for failed operations

### Resource Management
- [ ] Cleanup for stuck processes
- [ ] Cancel capability for long operations
- [ ] Proper AbortController cleanup

---

## Svelte 5 Pattern Reference

We use **Svelte 5** exclusively. Key patterns:

```javascript
// State
let value = $state(initialValue);

// Derived (computed)
let computed = $derived(expression);

// Props
let { prop = $bindable(default) } = $props();

// Effects (side effects)
$effect(() => {
  // Runs when dependencies change
  // Also runs on mount!
});

// Events
<button onclick={handler}>Click</button>  // lowercase!

// Dispatch (Svelte 5 style)
import { createEventDispatcher } from "svelte";
const dispatch = createEventDispatcher();
dispatch('eventName', data);
```

---

*Updated after each debugging session*
