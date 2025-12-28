# Code Review: QAMenuPanel.svelte

**Date:** 2025-12-28 | **Status:** REVIEWED

---

## Summary

QAMenuPanel.svelte is a slide-out panel for displaying and managing QA issues.

**Overall:** Good quality after recent fixes. A few minor issues to clean up.

---

## Issues Found

### 1. Unused Import (Minor)

**Line 11:** `onMount` is imported but never used.

```javascript
// CURRENT
import { createEventDispatcher, onMount } from "svelte";

// FIX
import { createEventDispatcher } from "svelte";
```

**Action:** Remove unused import.

---

### 2. Non-Reactive Store Access (Medium)

**Lines 18-19:** Using `get()` inside `$derived()` is not reactive.

```javascript
// CURRENT - Not reactive! get() only runs once
let API_BASE = $derived(get(serverUrl));

// OPTION A: Direct store access (if serverUrl is Svelte 5 compatible)
let API_BASE = $derived($serverUrl);

// OPTION B: Keep as constant (serverUrl doesn't change at runtime)
const API_BASE = get(serverUrl);
```

**Impact:** Low - serverUrl doesn't change at runtime, but pattern is incorrect.

**Action:** Change to `const API_BASE = get(serverUrl);` since it's a constant.

---

### 3. Mixed Event Handler Styles (Acceptable)

**Native elements:** Use Svelte 5 style (`onclick={}`)
**Carbon components:** Use Svelte 4 style (`on:click={}`)

```javascript
// Native element - Svelte 5 style (correct)
<div onclick={closePanel}>

// Carbon component - Svelte 4 style (correct - Carbon requirement)
<Button on:click={closePanel}>
```

**Status:** This is correct! Carbon components require `on:click` syntax.

---

## Good Patterns Found

### 1. Safe Property Access
```javascript
function getCurrentCheckType() {
  const index = selectedCheckType ?? 0;
  const type = checkTypes[index];
  return type?.id ?? "all";
}
```

### 2. Simple Timeout Pattern
```javascript
async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  // ... clean try/catch/finally
}
```

### 3. Error UI with Retry
```javascript
{#if errorMessage}
  <InlineNotification ... />
  <Button on:click={retryLoad}>Retry</Button>
{/if}
```

### 4. Single $effect() for Data Loading
```javascript
$effect(() => {
  if (open && fileId) {
    loadSummary();
    loadIssues(getCurrentCheckType());
  }
});
```

---

## Recommended Fixes

| Priority | Issue | Fix |
|----------|-------|-----|
| Low | Unused `onMount` import | Remove import |
| Low | `$derived(get(...))` pattern | Change to `const` |

---

## Final Assessment

**Quality:** Good
**Svelte 5 Compliance:** Good (proper use of $state, $effect, $props, $bindable)
**Carbon Integration:** Correct (using on:click for Carbon components)

---

*Code review complete*
