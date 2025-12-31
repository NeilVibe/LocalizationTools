# Tips and Tricks

> Debug lessons learned from development sessions

---

## Screenshot Location (CRITICAL!)

**User screenshots are at:**
- Windows: `C:\Users\MYCOM\Pictures\Screenshots`
- WSL access: `/mnt/c/Users/MYCOM/Pictures/Screenshots/`

**ALWAYS check here first when user mentions screenshots!**

```bash
ls -lat "/mnt/c/Users/MYCOM/Pictures/Screenshots/" | head -10
```

---

## Common Bug Patterns

### 1. Cell Content Cut Off / Ugly Internal Scrollbar

**Symptoms:** Long content in grid cells is cut off, user has to scroll inside cell

**Check:**
1. `MAX_ROW_HEIGHT` in VirtualGrid.svelte (line ~30) - if too low, cells cap
2. `.cell-content` CSS - should NOT have `overflow-y: auto` or `max-height`
3. Height calculation constants must match actual CSS padding values

**Fix Example:**
```javascript
// VirtualGrid.svelte
const MAX_ROW_HEIGHT = 800; // Was 300 - too restrictive
const LINE_HEIGHT = 26;     // Must match CSS line-height
const CELL_PADDING = 24;    // Must match CSS padding (0.75rem * 2)
```

```css
/* VirtualGrid.svelte <style> */
.cell-content {
  /* NO overflow-y or max-height! */
  word-break: break-word;
  white-space: pre-wrap;
  line-height: 1.6;
  width: 100%;
}
```

---

### 2. TM Matches Shows "No results" Despite Active TM

**Symptoms:** TM MATCHES panel says "No TM matches found" even with 1000+ entries

**Check:**
1. Is `tm_id` being passed to `/api/ldm/tm/suggest`?
2. Look for `$preferences.activeTmId` in the fetch call
3. Server logs show `[TM-SUGGEST]` prefix with debug info

**Fix Example:**
```javascript
// Make sure tm_id is passed in EVERY TM fetch function
const params = new URLSearchParams({ source, threshold: '0.3' });
if ($preferences.activeTmId) {
  params.append('tm_id', $preferences.activeTmId.toString());
}
```

---

### 3. API Endpoint Ignoring Parameter

**Symptoms:** Frontend sends parameter but backend ignores it

**Debug Steps:**
1. Check frontend: is parameter actually in the URL? (Network tab)
2. Check backend endpoint signature: is parameter defined?
3. Check backend logic: is parameter actually used in the query?

**Example:** `/tm/suggest` had `tm_id` in signature but only searched `ldm_rows`, never `ldm_tm_entries` when `tm_id` was provided.

---

### 4. Toast Notification Spam

**Symptoms:** Too many toasts stacking up, same message repeated

**Fix:**
```javascript
// toastStore.js
const MAX_TOASTS = 3;
const DEDUPE_WINDOW = 2000; // ms
const recentToasts = new Map();

// Check for duplicate before adding
const key = `${message}-${category}`;
if (recentToasts.has(key)) return;
recentToasts.set(key, Date.now());
setTimeout(() => recentToasts.delete(key), DEDUPE_WINDOW);
```

---

### 5. Task Manager "Failed to load tasks" Error

**Symptoms:** Toast shows "Failed to load tasks" repeatedly

**Root Cause:** Network errors, auth issues, or server restarts

**Fix:** Silent failures for non-critical errors:
```javascript
// Only show notification for actual server errors (500-level)
const isAuthError = error.message.includes('401') || error.message.includes('403');
const isNetworkError = error.name === 'TypeError';
const isServerError = error.message.includes('500');

if (isServerError && !isAuthError && !isNetworkError) {
  showNotification('Task manager temporarily unavailable', 'warning');
}
// Otherwise fail silently - task manager is non-critical
```

---

## Performance Testing

### Upload Performance Test Script
Location: `testing_toolkit/dev_tests/test_upload_performance.js`

```bash
cd testing_toolkit/dev_tests
npm install form-data  # First time only
node test_upload_performance.js
```

Tests SMALL (371KB), MEDIUM (15.5MB), BIG (189MB) files with detailed logging.

---

## UI Polish Guidelines

### Spacious Feel
- Cell padding: `0.75rem 1rem` (not 0.5rem)
- Line height: `1.6` (not 1.4)
- Table header: `font-weight: 500`, `font-size: 0.8125rem`

### Clean Borders
- Use `border-subtle-01` not `border-strong-01` for most dividers
- Row separators should be subtle, not prominent

### No Uppercase Headers
- Table headers: `text-transform: none` for cleaner look
- Reduces visual noise

---

*Updated: 2025-12-31*
