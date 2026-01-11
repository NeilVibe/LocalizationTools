# Code Review: TaskManager.svelte

**Date:** 2025-12-28 | **Status:** REVIEWED

---

## Summary

TaskManager.svelte displays active and historical operations from both frontend and backend.

**Overall:** Good structure, but has hardcoded URLs that should use the API client.

---

## Issues Found

### 1. Hardcoded URLs (Medium Priority)

**Lines 197, 346:** Using hardcoded `localhost:8888` instead of API client.

```javascript
// CURRENT - Hardcoded URL
const response = await fetch('http://localhost:8888/api/progress/operations', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// SHOULD USE - API client (already imported!)
const response = await api.get('/api/progress/operations');
```

**Impact:** Will break in production if server URL changes.

**Action:** Replace hardcoded fetch calls with `api.get()` and `api.delete()`.

---

### 2. Duplicate Duration Calculation Logic

**Lines 46-57 and 132-158:** Same duration calculation in two places.

```javascript
// transformFrontendOperation (line 46)
if (seconds < 60) {
  duration = `${Math.round(seconds)}s`;
} else {
  const minutes = Math.floor(seconds / 60);
  // ...
}

// transformOperationToTask (line 132) - same logic!
if (seconds < 60) {
  duration = `${seconds}s`;
} else {
  const minutes = Math.floor(seconds / 60);
  // ...
}
```

**Action:** Extract to shared helper function `formatDuration(seconds, isRunning)`.

---

### 3. Missing Cleanup for Stale Tasks (Fixed!)

**Status:** Already fixed in this session.

Added `cleanupStaleTasks()` function and "Clean Stale" button.

---

## Good Patterns Found

### 1. Smart Update Prevention
```javascript
// Prevents UI flickering by only updating when tasks change
if (!areTasksEqual(backendTasks, newTasks)) {
  backendTasks = newTasks;
}
```

### 2. Proper Svelte 5 Derived
```javascript
let tasks = $derived((() => {
  // Complex merging logic
  return [...uniqueFrontendTasks, ...uniqueHistoryTasks, ...backendTasks].sort(...);
})());
```

### 3. Deduplication Logic
```javascript
const activeIds = new Set(frontendTasksList.map(t => t.id));
const uniqueFrontendTasks = frontendTasksList.filter(t => !backendIds.has(t.id));
```

### 4. WebSocket Integration
```javascript
unsubscribeOperationStart = websocket.onOperationStart((data) => {
  // Real-time updates
});
```

---

## Recommended Fixes

| Priority | Issue | Fix |
|----------|-------|-----|
| Medium | Hardcoded URLs (lines 197, 346) | Use `api.get()` / `api.delete()` |
| Low | Duplicate duration logic | Extract helper function |

---

## Hardcoded URL Note

The APIClient class only has a `request()` method, not `get()` or `delete()` helpers.
All endpoints use hardcoded `localhost:8888` URLs with manual fetch.

**Future Improvement:** Add `get()`, `post()`, `delete()` helper methods to APIClient:
```javascript
class APIClient {
  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}
```

**Current Pattern:** Use fetch with auth header (consistent with existing code)

---

## Final Assessment

**Quality:** Good
**Svelte 5 Compliance:** Good
**API Usage:** Needs improvement (hardcoded URLs)

---

*Code review complete*
