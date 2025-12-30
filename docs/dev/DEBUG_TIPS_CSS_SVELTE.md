# Debug Tips: CSS + Svelte 5 Frontend

> Lessons learned from UI-083 Column Resize debugging session (2025-12-30)

---

## The Golden Debug Flow

```
SYMPTOM → HYPOTHESIS → LOG → OBSERVE → NARROW → FIX → VERIFY
```

### Real Example: "Invisible Bar Moving But Cells Not Resizing"

```
1. SYMPTOM
   User: "I see something moving but cells don't resize"

2. HYPOTHESIS
   - State not updating?
   - Template not reactive?
   - Wrong element being modified?

3. LOG
   Added: console.log('[RESIZE] index:', indexColumnWidth + 'px');

4. OBSERVE
   Logs showed: "[RESIZE] index: 90px" ← State IS updating!

5. NARROW
   State updates → DOM should update → But doesn't → CSS override?

6. FOUND IT
   CSS: flex: 0 0 60px;     ← FIXED width via flex
   HTML: style="width: 90px" ← Being IGNORED!

7. FIX
   CSS: flex: none;         ← Defer to inline style

8. VERIFY
   Playwright test: Width changed 345px → 390px ✓
```

---

## CSS vs JavaScript: Who Wins?

### The Override Hierarchy

```
1. !important              ← Nuclear option (avoid)
2. Inline style attribute  ← JavaScript controls this
3. ID selector (#id)
4. Class selector (.class) ← CSS controls this
5. Element selector (div)
```

### The Flex Trap

```css
/* PROBLEM: flex shorthand sets width */
.cell { flex: 0 0 60px; }  /* flex-basis: 60px - FIXED! */

/* Your JavaScript: */
element.style.width = '90px';  /* IGNORED! flex-basis wins */

/* SOLUTION: Let JavaScript win */
.cell { flex: none; }  /* No flex sizing */
/* OR */
.cell { flex: 0 0 auto; }  /* Use width property */
```

### Quick Reference

| CSS Property | Overrides width? | Solution |
|--------------|------------------|----------|
| `flex: 0 0 60px` | YES | Use `flex: none` |
| `min-width` | YES (minimum) | Remove or use `min-width: 0` |
| `max-width` | YES (maximum) | Remove or increase |
| `width: 60px` | YES | Remove from CSS |
| `flex: 1` | Partially | Use `flex: none` for fixed |

---

## Svelte 5 Reactivity Patterns

### $derived vs $derived.by

```javascript
// SIMPLE expression - use $derived
let doubled = $derived(count * 2);

// COMPLEX logic - use $derived.by
let positions = $derived.by(() => {
  const result = {};
  if (showIndex) result.index = indexWidth;
  if (showStringId) result.stringId = indexWidth + stringIdWidth;
  return result;
});
```

### State Objects vs Simple State

```javascript
// RISKY: Object state can have reactivity issues
let state = $state({ active: false, column: null });
// Replacing whole object: state = { active: true, column: 'x' }
// Can cause stale closures in event handlers!

// SAFER: Simple state variables
let isActive = $state(false);
let column = $state(null);
// Direct assignment: isActive = true; column = 'x';
// Event handlers always see current value
```

### Template Reactivity

```svelte
<!-- WRONG: Function call may not re-evaluate -->
{#each items as item}
  <div style="left: {calculatePosition(item)}px">
{/each}

<!-- RIGHT: Pre-computed reactive value -->
{#each items as item}
  <div style="left: {positions[item] || 0}px">
{/each}
```

---

## Debug Logging Patterns

### Targeted Logging

```javascript
// BAD: Too verbose
console.log('resize', event, state, element, everything);

// GOOD: Focused with prefix
console.log('[RESIZE] START:', column, 'value:', startValue);
console.log('[RESIZE] MOVE:', newValue);
console.log('[RESIZE] STOP');
```

### State vs DOM Verification

```javascript
// 1. Log state change
console.log('[STATE] indexWidth:', indexColumnWidth);

// 2. Log DOM result (in browser console)
document.querySelector('.cell.row-num').style.width
document.querySelector('.cell.row-num').getBoundingClientRect().width

// If STATE changes but DOM doesn't → CSS override!
```

---

## Common Gotchas

### 1. Event Listener Stale Closures

```javascript
// PROBLEM: Handler captures old state
function setup() {
  const startValue = currentValue; // Captured!
  document.addEventListener('mousemove', (e) => {
    // startValue is stale if currentValue changed
  });
}

// SOLUTION: Use module-level state
let resizeStartValue = $state(0);
function startResize() {
  resizeStartValue = currentValue; // Fresh assignment
}
```

### 2. ResizeObserver for Container Width

```javascript
// Container width changes need to update positions
resizeObserver = new ResizeObserver(() => {
  containerWidth = containerEl.clientWidth;
});
resizeObserver.observe(containerEl);
```

### 3. Cleanup Event Listeners

```javascript
function stopResize() {
  isResizing = false;
  // CRITICAL: Remove listeners or they accumulate!
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
}
```

---

## The "State Updates But Nothing Happens" Checklist

1. [ ] Is the state actually updating? (Add console.log)
2. [ ] Is the template using that state? (Check binding)
3. [ ] Is CSS overriding the change? (Check flex, min/max-width)
4. [ ] Is the element even in the DOM? (Check conditionals)
5. [ ] Is there a parent element blocking it? (Check overflow, display)

---

## Quick Wins

```css
/* Let JavaScript control sizing */
.dynamic-width {
  flex: none;
  /* width controlled by style="width: {value}px" */
}

/* Prevent content from forcing size */
.cell {
  min-width: 0;
  overflow: hidden;
}

/* Debug: See what's happening */
.debug {
  outline: 2px solid red !important;
}
```

---

## Optimistic UI Pattern (File Explorer Session)

### The Problem: Slow Feedback

```javascript
// BAD: User waits for server
async function handleDrop(file, folder) {
  const response = await fetch('/api/move');  // 200-500ms wait
  if (response.ok) {
    await loadProjectTree();  // Another 100-300ms
  }
}
// User sees: Click... wait... wait... done
```

### The Solution: Update UI First

```javascript
// GOOD: Instant feedback, sync in background
async function handleDrop(file, folder) {
  // 1. UPDATE UI IMMEDIATELY
  moveNodeInTree(treeNodes, file.id, folder.id);
  treeNodes = [...treeNodes];  // Force reactivity!

  // 2. SYNC TO SERVER IN BACKGROUND
  const response = await fetch('/api/move');

  // 3. REVERT IF FAILED
  if (!response.ok) {
    await loadProjectTree();  // Reload truth from server
  }
}
// User sees: Click... done! (server syncs invisibly)
```

### Svelte 5 Array Reactivity Trick

```javascript
// PROBLEM: Mutating array doesn't trigger reactivity
treeNodes.push(newNode);  // UI won't update!
treeNodes.splice(i, 1);   // UI won't update!

// SOLUTION: Reassign after mutation
treeNodes.push(newNode);
treeNodes = [...treeNodes];  // NOW UI updates!

// OR use the new Svelte 5 way with $state.raw
let treeNodes = $state([]);
// Mutations auto-trigger if you use $state (not $state.raw)
```

---

## Tree Traversal Helpers

```javascript
// Find and REMOVE node from nested tree (returns removed node)
function removeNodeFromTree(nodes, fileId) {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i].data.id === fileId) {
      return nodes.splice(i, 1)[0];  // Remove and return
    }
    if (nodes[i].children?.length) {
      const found = removeNodeFromTree(nodes[i].children, fileId);
      if (found) return found;
    }
  }
  return null;
}

// Find folder node by id (doesn't modify)
function findFolderNode(nodes, folderId) {
  for (const node of nodes) {
    if (node.data.type === 'folder' && node.data.id === folderId) {
      return node;
    }
    if (node.children?.length) {
      const found = findFolderNode(node.children, folderId);
      if (found) return found;
    }
  }
  return null;
}
```

---

## DB Pattern: O(n) Tree Building

```python
# BAD: O(n*m) - nested loops kill performance
def build_tree_slow(folders):
    for folder in folders:
        # This is O(m) for EACH folder = O(n*m) total!
        children = [f for f in folders if f.parent_id == folder.id]

# GOOD: O(n) - pre-build lookup dict
def build_tree_fast(folders):
    # Build lookup: O(n)
    by_parent = defaultdict(list)
    for folder in folders:
        by_parent[folder.parent_id].append(folder)

    # Now lookups are O(1)
    def recurse(parent_id):
        return [
            {"id": f.id, "children": recurse(f.id)}
            for f in by_parent.get(parent_id, [])  # O(1)!
        ]
    return recurse(None)
```

---

## API Gotcha: Query Params vs JSON Body

```javascript
// WRONG: Sending JSON body when API expects query param
await fetch(`/api/files/${id}/move`, {
  method: 'PATCH',
  body: JSON.stringify({ folder_id: 123 })  // Server ignores this!
});

// RIGHT: Check the API signature first
// FastAPI: def move(file_id: int, folder_id: int = None)  ← Query param!
await fetch(`/api/files/${id}/move?folder_id=123`, {
  method: 'PATCH'
});

// TIP: Always check backend route definition:
// - `folder_id: int = Body(...)` → JSON body
// - `folder_id: int = None` or `Query(...)` → Query param
```

---

## Backend Changes: Server Restart Required!

```
SYMPTOM: "Not found" error from API, but endpoint code exists

CHECK: curl localhost:8888/openapi.json | grep "your-endpoint"

If endpoint NOT listed → SERVER NEEDS RESTART!

# Restart server (DEV mode)
pkill -f "python.*server/main.py"
cd /path/to/project && DEV_MODE=true python3 server/main.py &

# Verify endpoints loaded
curl localhost:8888/openapi.json | grep "your-endpoint"
```

**Why?** FastAPI loads routes at startup. New endpoints won't exist until server restarts.

---

*Updated from UI-083 + File Explorer + Rename sessions | 2025-12-30*
