# QA UIUX Overhaul

**Priority:** P1 | **Status:** PLANNING | **Created:** 2025-12-28

---

## Current Issues

### 1. Softlock / Can't Close
- Panel opens but user cannot leave
- Backdrop click doesn't work sometimes
- No escape key handling in all states
- Infinite loading with no timeout

### 2. Empty Results Display
- Says "issues found" but shows empty list
- No clear error message when API fails
- Loading state never ends

### 3. No Cancel Mechanism
- "Run Full QA" starts but can't be cancelled
- If API hangs, user is stuck
- No abort controller for fetch requests

---

## Proposed Fixes

### Phase 1: Critical Stability

1. **Add Request Timeouts**
   ```javascript
   const controller = new AbortController();
   const timeout = setTimeout(() => controller.abort(), 30000);

   fetch(url, { signal: controller.signal })
   ```

2. **Force Close Button**
   - Always visible X button
   - Works regardless of loading state
   - Cancels any pending requests

3. **Error State UI**
   - Show error message when API fails
   - Retry button
   - "Close anyway" option

### Phase 2: UX Improvements

1. **Loading Skeleton**
   - Show skeleton cards while loading
   - Prevents layout shift

2. **Progress Indicator**
   - "Checking row X of Y..."
   - Cancelable with button

3. **Empty State Clarity**
   - Distinguish "no issues" vs "error loading"
   - Different icons/messages

### Phase 3: Polish

1. **Keyboard Navigation**
   - Escape to close (always)
   - Arrow keys in issue list
   - Enter to jump to row

2. **Animation Improvements**
   - Smoother slide-in/out
   - Loading state transitions

---

## Files to Modify

| File | Changes |
|------|---------|
| `QAMenuPanel.svelte` | Add abort controller, timeout, error states |
| `LDM.svelte` | Handle panel close events properly |

---

## Success Criteria

- [ ] Panel can ALWAYS be closed
- [ ] Loading has 30s timeout
- [ ] Error states are clearly shown
- [ ] "Run Full QA" can be cancelled
- [ ] Empty results explained properly

---

*Priority: HIGH - Current state causes user frustration*
