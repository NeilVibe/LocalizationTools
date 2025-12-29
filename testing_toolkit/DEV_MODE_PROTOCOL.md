# Dev Mode Testing Protocol

**Fast iteration testing via Vite dev server - no Windows build needed**

**Updated:** 2025-12-28 | **Purpose:** UI/Frontend Development Testing

---

## Overview

```
                         DEV MODE (localhost:5173)
                         ├─ Instant reload (<1s)
                         ├─ Full hot-module replacement
                         ├─ No build required
                         └─ Test ALL UI features

WHEN TO USE:
├─ UI changes (Svelte components)
├─ Style changes (CSS)
├─ Frontend logic
├─ Search/filter testing
├─ Color display testing
└─ Quick iteration cycles

WHEN NOT TO USE:
├─ Electron-specific features
├─ File system operations
├─ Desktop app packaging
└─ Final release validation (use MASTER_TEST_PROTOCOL.md)
```

---

## Quick Start (30 seconds)

```bash
# Terminal 1: Backend
cd /home/neil1988/LocalizationTools
DEV_MODE=true python3 server/main.py

# Terminal 2: Frontend
cd /home/neil1988/LocalizationTools/locaNext
npm run dev

# Browser: http://localhost:5173
# Login: admin / admin123
```

---

## Phase 1: Start Servers

### 1.1 Backend Server

```bash
cd /home/neil1988/LocalizationTools

# Option A: Standard (with rate limits)
python3 server/main.py

# Option B: Dev mode (no rate limits - RECOMMENDED)
DEV_MODE=true python3 server/main.py
```

**Verify:**
```bash
curl -s http://localhost:8888/health | jq
```

Expected output:
```json
{
  "status": "online",
  "server": "PostgreSQL",  // or "SQLite" for offline
  "version": "..."
}
```

### 1.2 Frontend Dev Server

```bash
cd /home/neil1988/LocalizationTools/locaNext
npm run dev
```

**Output:**
```
  VITE v5.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### 1.3 Verify Both Running

```bash
# Quick check
ps aux | grep -E "(vite|python3 server/main)" | grep -v grep

# Or use script
./scripts/check_servers.sh
```

---

## Phase 2: Login & Navigate

### 2.1 Login

| URL | http://localhost:5173 |
|-----|----------------------|
| Username | admin |
| Password | admin123 |

### 2.2 Navigate to LDM

1. After login, click **LDM** in navigation
2. Or go directly: http://localhost:5173/ldm

---

## Phase 3: Test Data Setup

### 3.1 Import Test File

The test fixture is pre-loaded with real data:
- **Location:** `tests/fixtures/sample_language_data.txt`
- **Rows:** 63 entries from real game localization data
- **Features:**
  - Color codes: `<PAColor0xffe9bd23>text<PAOldColor>`
  - Scene changes: `{ChangeScene(...)}`
  - Audio voices: `{AudioVoice(...)}`
  - Text bindings: `{TextBind:...}`
  - Normal strings (no tags)

### 3.2 Color Code Examples in Test Data

| Pattern | Example |
|---------|---------|
| Golden Yellow | `<PAColor0xffe9bd23>2시간 동안<PAOldColor>` |
| Warning Yellow | `<PAColor0xFFf3d900>※ 사용 방법<PAOldColor>` |
| Orange Yellow | `<PAColor0xffffc62b>트리와 벽난로<PAOldColor>` |
| Red | `<PAColor0xFFff0000>의뢰를 받습니다<PAOldColor>` |
| Light Blue | `<PAColor0xFF96D4FC>사용처<PAOldColor>` |
| Green | `<PAColor0xff57f426>획득처<PAOldColor>` |
| Purple | `<PAColor0xffb793ff>강화<PAOldColor>` |

### 3.3 Upload via UI

1. In LDM, click **Upload** button
2. Select: `tests/fixtures/sample_language_data.txt`
3. Wait for import completion
4. File appears in file tree

---

## Phase 4: Feature Testing

### 4.1 Search Bar Testing

**Current Status:** Basic contain search

**Test Steps:**
1. Open a file in LDM
2. Locate search bar (top right of grid)
3. Type search term
4. Wait 300ms for debounce
5. Verify rows filter

**Search Test Cases:**

| Search Term | Expected Result |
|-------------|-----------------|
| `색` | Korean rows containing "색" |
| `Colorant` | French rows with "Colorant" |
| `PAColor` | Rows with color codes |
| `100%` | Rows with percentage values |
| `Valencia` | Rows mentioning Valencia |

**Console Logs (F12):**
```
searchTerm changed via effect {from: "", to: "색"}
handleSearch triggered {searchTerm: "색"}
handleSearch executing search {searchTerm: "색"}
```

### 4.2 Color Display Testing

**Test Steps:**
1. Open file with color codes
2. Look at Source and Target columns
3. Verify colored text renders

**Expected:**
- `<PAColor0xffe9bd23>` → Golden yellow text
- `<PAOldColor>` → End of colored segment
- Tags should NOT be visible as raw text
- Should see colored spans in cells

**Console Logs:**
```
ColorText rendering: {text: "<PAColor0xffe9bd23>100%<PAOldColor>", segments: [...]}
```

### 4.3 Virtual Grid Testing

| Test | Action | Expected |
|------|--------|----------|
| Scroll | Scroll down fast | Smooth rendering, no blank rows |
| Row hover | Mouse over row | Row highlight |
| Cell click | Click source/target | Cell selection |
| Double-click | Double-click target | Edit mode opens |

### 4.4 Edit Mode Testing

1. Double-click a target cell
2. Verify edit panel opens
3. Make a change
4. Click Save
5. Verify change persists

---

## Phase 5: Playwright Headless Tests

### 5.1 Run Search Test

```bash
cd /home/neil1988/LocalizationTools/locaNext
npx playwright test tests/search-test.spec.ts --reporter=list
```

### 5.2 Run All Tests

```bash
npx playwright test --reporter=list
```

### 5.3 Screenshots Location

Tests save screenshots to `/tmp/`:
- `test_01_login_form.png`
- `test_02_after_login.png`
- `test_03_ldm_page.png`
- `test_04_file_clicked.png`
- `test_05_search_typed.png`
- `test_06_search_results.png`

**View screenshots:**
```bash
# From WSL
explorer.exe /tmp/
# Or copy to Windows
cp /tmp/test_*.png /mnt/c/Users/neil/Desktop/
```

### 5.4 Custom Test Script

```javascript
// tests/dev-test.spec.ts
import { test, expect } from '@playwright/test';

test('search and color display', async ({ page }) => {
  // Login
  await page.goto('http://localhost:5173');
  await page.fill('input[placeholder*="username"]', 'admin');
  await page.fill('input[placeholder*="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);

  // Navigate to LDM
  await page.goto('http://localhost:5173/ldm');
  await page.waitForTimeout(2000);

  // Take screenshot
  await page.screenshot({ path: '/tmp/ldm_test.png' });

  // Check for colored spans
  const coloredSpans = await page.$$('span[style*="color"]');
  console.log(`Found ${coloredSpans.length} colored spans`);
});
```

---

## Phase 6: Browser DevTools Debugging

### 6.1 Open DevTools

| Browser | Shortcut |
|---------|----------|
| Chrome/Edge | F12 or Ctrl+Shift+I |
| Firefox | F12 or Ctrl+Shift+I |

### 6.2 Console Tab

Watch for these logs:

**Search:**
```
searchTerm changed via effect {from: "", to: "test"}
handleSearch triggered {searchTerm: "test"}
```

**Color Parsing:**
```
ColorText rendering: {text: "...", segments: [...]}
```

**API Calls:**
```
loadRows with search {searchTerm: "test"}
```

### 6.3 Network Tab

Filter: `XHR` to see API calls

| Endpoint | Purpose |
|----------|---------|
| `/api/ldm/rows` | Load grid data |
| `/api/ldm/files` | File tree |
| `/api/ldm/search` | Search results |

### 6.4 Elements Tab

Find colored spans:
```
span[style*="color: rgb"]
```

---

## Phase 7: Troubleshooting

### 7.1 Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Port 5173 in use | Previous vite running | `pkill -f vite` |
| Port 8888 in use | Previous backend | `pkill -f "python3 server/main"` |
| Rate limited (429) | Too many login attempts | Clear audit log (see below) |
| Login fails | Backend not running | Start backend first |
| No files in LDM | No data imported | Upload test file |
| Search not working | Bug in VirtualGrid | Check console for errors |
| Colors not rendering | ColorText bug | Check console logs |

**Rate Limiting Fix:** The rate limiter uses `server/data/logs/security_audit.log` with a 15-min window. To reset immediately:
```bash
echo "" > /home/neil1988/LocalizationTools/server/data/logs/security_audit.log
```

### 7.2 Kill Everything

```bash
pkill -f "vite dev"
pkill -f "python3 server/main"
```

### 7.3 Full Restart

```bash
# Kill all
pkill -f "vite dev" ; pkill -f "python3 server/main"

# Wait
sleep 2

# Restart backend
cd /home/neil1988/LocalizationTools
DEV_MODE=true python3 server/main.py &

# Wait for backend
sleep 3

# Restart frontend
cd /home/neil1988/LocalizationTools/locaNext
npm run dev
```

---

## Phase 8: API Testing

### 8.1 Direct API Calls

```bash
# Health check
curl http://localhost:8888/health

# Get files (requires auth)
curl -X GET "http://localhost:8888/api/ldm/files" \
  -H "Authorization: Bearer <token>"

# Search (requires auth)
curl -X GET "http://localhost:8888/api/ldm/rows?search=color" \
  -H "Authorization: Bearer <token>"
```

### 8.2 Swagger UI

Visit: http://localhost:8888/docs

- Interactive API testing
- Try endpoints directly
- See request/response schemas

---

## Checklist: Full Test Cycle

- [ ] Backend running (`curl localhost:8888/health`)
- [ ] Frontend running (`http://localhost:5173`)
- [ ] Login works (admin/admin123)
- [ ] Navigate to LDM
- [ ] File tree visible
- [ ] Click file to open
- [ ] Grid renders with rows
- [ ] Scroll works smoothly
- [ ] Color tags render as colored text
- [ ] Search bar visible
- [ ] Search filters rows
- [ ] Double-click opens edit mode
- [ ] Edit and save works
- [ ] No console errors

---

## Comparison: Dev Mode vs Build Mode

| Aspect | Dev Mode (localhost:5173) | Build Mode (Playground) |
|--------|---------------------------|-------------------------|
| Speed | Instant reload | 15+ min build cycle |
| Use case | UI development | Final validation |
| Electron | No | Yes |
| File system | Limited | Full |
| PostgreSQL | Yes (same server) | Yes |
| SQLite | Via backend | Via backend |

---

## Files Reference

| File | Purpose |
|------|---------|
| `locaNext/src/lib/components/ldm/VirtualGrid.svelte` | Main grid component |
| `locaNext/src/lib/components/ldm/ColorText.svelte` | Color tag parser |
| `locaNext/src/lib/components/ldm/Search.svelte` | Search component |
| `tests/fixtures/sample_language_data.txt` | Test data with colors |
| `locaNext/tests/search-test.spec.ts` | Playwright search test |

---

## Phase 9: Svelte 5 Debugging (CRITICAL)

### 9.1 Svelte 5 + $state() Specifics

Svelte 5 uses runes (`$state`, `$effect`, `$derived`). Key debugging differences:

```javascript
// Svelte 5 state declaration
let searchTerm = $state("");

// Effect that watches state
$effect(() => {
  const term = searchTerm;  // Access to track
  console.log("State changed:", term);
});
```

### 9.2 Debug/Fix Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                    EFFECTIVE DEBUG CYCLE                     │
├─────────────────────────────────────────────────────────────┤
│  1. IDENTIFY  →  Console logs + Network tab                 │
│  2. ISOLATE   →  Find exact line causing issue              │
│  3. FIX       →  Make minimal change                        │
│  4. VERIFY    →  Refresh browser (Vite HMR)                 │
│  5. REPEAT    →  If not fixed, go to step 1                 │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Console Snippets for Debugging

Paste these in browser console (F12):

**Check Svelte state:**
```javascript
// Find all inputs and their values
document.querySelectorAll('input').forEach((inp, i) => {
  console.log(`Input ${i}:`, inp.placeholder, '=', inp.value);
});
```

**Monitor input events:**
```javascript
// Watch for input events on search
document.querySelector('input[placeholder*="Search"]')
  ?.addEventListener('input', e => console.log('Input event:', e.target.value));
```

**Test API directly:**
```javascript
// Test search API call
fetch('/api/ldm/rows?file_id=110&offset=0&limit=50&search=Item')
  .then(r => r.json())
  .then(d => console.log('Search results:', d.length, 'rows'));
```

### 9.4 Playwright + Svelte 5 Issue

**KNOWN ISSUE:** Playwright's `fill()` doesn't work reliably with Svelte 5's `bind:value`.

**Symptoms:**
- `fill()` returns success but value is empty
- `inputValue()` returns "" after fill
- State resets immediately

**Root Cause:**
Svelte 5's reactive binding immediately syncs DOM with `$state()`, overwriting Playwright's changes.

**Workarounds:**

1. **Use page.evaluate()** to directly modify state:
```javascript
await page.evaluate(() => {
  // Access Svelte component internals (if exposed)
  window.__svelteDebug?.setSearchTerm?.('test');
});
```

2. **Dispatch proper InputEvent:**
```javascript
await page.evaluate(() => {
  const input = document.querySelector('input[placeholder*="Search"]');
  const nativeSetter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype, 'value'
  ).set;
  nativeSetter.call(input, 'test');
  input.dispatchEvent(new InputEvent('input', { bubbles: true, data: 'test' }));
});
```

3. **Manual testing preferred** for Svelte 5 state-dependent features

### 9.5 Quick Debug Commands

```bash
# Watch Vite console for errors
# (In terminal running npm run dev)

# Check if HMR is working
# Browser console should show: [vite] hot updated: /path/to/file.svelte

# Force full reload if HMR stuck
# Ctrl+Shift+R in browser

# Check for TypeScript errors
cd locaNext && npm run check
```

### 9.6 Common Svelte 5 Gotchas

| Issue | Wrong | Right |
|-------|-------|-------|
| State not updating | `value={state}` | `bind:value={state}` |
| Effect not firing | No dependency access | Access state in effect body |
| Event handler | `on:click={fn()}` | `on:click={fn}` or `on:click={() => fn()}` |
| Derived not reactive | `let x = state * 2` | `let x = $derived(state * 2)` |

### 9.7 Debugging Checklist

When something doesn't work:

- [ ] Check browser console for errors
- [ ] Check Network tab - is API being called?
- [ ] Check API response - is data correct?
- [ ] Add `console.log` in effect/handler
- [ ] Verify `$state` variable is being accessed in `$effect`
- [ ] Try manual test in browser before Playwright
- [ ] Check Vite terminal for compilation errors

### 9.8 CASE STUDY: Search Bar Bug Fix (2025-12-28)

**Problem:** Search bar input accepted text but rows never filtered.

**Root Cause:** Multiple issues compounding:

1. **TypeScript in non-TS Svelte file**
   - Used `as HTMLInputElement` in `<script>` (not `<script lang="ts">`)
   - Caused Vite compilation error silently

2. **`bind:value` with `$state()`**
   - Playwright's `fill()` and Svelte's reactive binding fight each other
   - Svelte immediately resets DOM value to match state
   - Fix: Use `oninput` handler instead of `bind:value`

3. **Effect resetting state on every run**
   ```javascript
   // WRONG - resets searchTerm on EVERY effect run
   $effect(() => {
     if (fileId) {
       searchTerm = "";  // Runs whenever ANY dependency changes!
       loadRows();
     }
   });

   // RIGHT - only reset when fileId actually changes
   let previousFileId = $state(null);
   $effect(() => {
     if (fileId && fileId !== previousFileId) {
       previousFileId = fileId;
       searchTerm = "";
       loadRows();
     }
   });
   ```

**Fix Steps:**
1. Removed TypeScript syntax (`as HTMLInputElement`) from plain `<script>` block
2. Changed `bind:value={searchTerm}` to `oninput={(e) => { searchTerm = e.target.value; }}`
3. Added previous value tracking to prevent unintended resets

**Verification:**
```bash
npx playwright test tests/search-verified.spec.ts --reporter=list
# Result: 10,000 rows -> 4 rows (searching "5000") = WORKING
```

---

## Phase 10: Git Push Protocol (Gitea Resource Management)

When pushing to Git for builds:

```bash
# 1. Start Gitea if needed for push
sudo systemctl start gitea
sleep 5

# 2. Push to both remotes
git add -A
git commit -m "Fix: description"
git push origin main      # GitHub
git push gitea main       # Gitea (triggers CI)

# 3. Stop Gitea to save resources (optional)
sudo systemctl stop gitea

# 4. Monitor build via database
python3 -c "import sqlite3; ..."
```

**Note:** Gitea only needs to be running during `git push gitea`. Once pushed, the CI runner picks up the job and Gitea can be stopped.

---

## Phase 11: Testing Utilities Library

### Location: `testing_toolkit/dev_tests/helpers/`

### Available Helpers

| File | Purpose |
|------|---------|
| `login.ts` | Login, get API token, navigate to LDM |
| `ldm-actions.ts` | Select project/file, search, edit modal |
| `database.py` | Direct DB access (uses server config) |
| `api.py` | REST API helper with auth |

### Playwright Test Example

```typescript
import { test } from '@playwright/test';
import { loginAndGoToLDM } from '../helpers/login';
import { selectFirstProject, selectFirstFile, typeSearch, getRowCount } from '../helpers/ldm-actions';

test('search filters rows', async ({ page }) => {
  await loginAndGoToLDM(page);
  await selectFirstProject(page);
  await selectFirstFile(page);

  const before = await getRowCount(page);
  await typeSearch(page, 'Valencia');
  const after = await getRowCount(page);

  console.log(`Filtered: ${before} -> ${after}`);
});
```

### Database Access (Python)

```python
# CORRECT: Use server config
from helpers.database import get_db_connection, get_files_for_project

files = get_files_for_project(8)
for f in files:
    print(f"  ID: {f[0]}, Name: {f[1]}")
```

### API Access (Python)

```python
from helpers.api import LDMApi

api = LDMApi()
api.login()
projects = api.get_projects()
files = api.get_files(project_id=8)
```

### Common Patterns

| Action | Helper |
|--------|--------|
| Login | `login(page)` |
| Go to LDM | `navigateToLDM(page)` |
| Select file | `selectFirstFile(page)` |
| Type search | `typeSearch(page, 'term')` |
| Get row count | `getRowCount(page)` |
| Open edit | `openEditModal(page, rowIndex)` |
| Screenshot | `screenshot(page, 'label')` |

---

## Resource Management

### Background Task Cleanup

```bash
# Check for orphan tasks
ls -la /tmp/claude/*/tasks/

# Clean old task files (older than 1 hour)
find /tmp/claude/*/tasks/ -type f -mmin +60 -delete

# Check for zombie processes
ps aux | grep -E "(node|python|playwright)" | grep -v grep
```

### Stop Unused Services

```bash
# Stop Gitea (not needed for dev testing)
sudo systemctl stop gitea

# Check resource usage
htop
```

---

---

## Phase 12: Efficiency Assessment

### Speed Comparison

| Task | DEV Testing | Windows Build |
|------|-------------|---------------|
| Code change | 1s (HMR) | 15+ min |
| Run test | 12-15s | 5+ min |
| Debug cycle | 30s | 20+ min |

**DEV Testing is 20-30x faster for UI development.**

### What Works
- Instant HMR feedback
- Playwright headless tests
- Real data (63 rows with PAColor)
- Server config for DB access
- `oninput` for Svelte 5

### What Doesn't Work
- Hardcoded DB credentials
- `bind:value` with `$state`
- TypeScript in non-TS Svelte files
- Effects without previous value tracking

See: `dev_tests/EFFICIENCY_REPORT.md` for full details.

---

## Phase 13: CRITICAL SOLUTIONS (Life-Changing Insights)

> **MEMORIZE THESE.** Each solution represents hours of debugging pain condensed into a single rule.

### ⚠️ CS-001: Svelte 5 Input Handling

**NEVER use `bind:value` with `$state()` in Playwright tests.**

```svelte
<!-- WRONG - Playwright fill() fails -->
<input bind:value={searchTerm} />

<!-- RIGHT - Works with Playwright -->
<input oninput={(e) => { searchTerm = e.target.value; }} />
```

**Why:** Svelte 5's reactive binding fights with Playwright's synthetic events. The state resets immediately.

---

### ⚠️ CS-002: Effect Previous Value Tracking

**ALWAYS track previous values in effects that reset state.**

```javascript
// WRONG - Resets on every effect run
$effect(() => {
  if (fileId) {
    searchTerm = "";  // DISASTER: runs on ANY state change
    loadRows();
  }
});

// RIGHT - Only reset when value actually changes
let previousFileId = $state(null);
$effect(() => {
  if (fileId && fileId !== previousFileId) {
    previousFileId = fileId;
    searchTerm = "";
    loadRows();
  }
});
```

**Why:** Effects re-run when ANY tracked dependency changes. Without previous value tracking, unrelated state changes trigger unwanted resets.

---

### ⚠️ CS-003: No TypeScript in Non-TS Files

**NEVER use TypeScript syntax in plain `<script>` blocks.**

```svelte
<!-- WRONG - Causes silent compile error -->
<script>
  const value = (e.target as HTMLInputElement).value;
</script>

<!-- RIGHT - Plain JavaScript -->
<script>
  const value = e.target.value;
</script>

<!-- OR use TypeScript properly -->
<script lang="ts">
  const value = (e.target as HTMLInputElement).value;
</script>
```

**Why:** Vite silently fails. No error in console. Code just doesn't execute.

---

### ⚠️ CS-004: Database Access Pattern

**NEVER hardcode database credentials.**

```python
# WRONG - Will fail with wrong password
from sqlalchemy import create_engine
engine = create_engine("postgresql://admin:admin123@localhost:5432/localization")

# RIGHT - Use server config
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools/server')
from config import DATABASE_URL
engine = create_engine(DATABASE_URL)
```

**Why:** Server config contains actual credentials. Hardcoding leads to authentication failures.

---

### ⚠️ CS-005: Trust the Evidence

**ALWAYS verify with HARD EVIDENCE before assuming something is broken.**

| Evidence Type | How to Get It |
|---------------|---------------|
| Screenshot | `await page.screenshot({ path: '/tmp/test.png' })` |
| Console log | `page.on('console', msg => ...)` |
| Row count | `await page.textContent('.row-count')` |
| DOM state | `await page.evaluate(() => document.querySelector(...))` |

**Case Study (2025-12-28):**
- User said "search is not working"
- Deep debug test showed: 63 rows → 9 rows with "Valencia" search
- Screenshot confirmed filtered results
- **Search WAS working.** Evidence proved it.

**Why:** Don't trust feelings. Don't trust assumptions. Get screenshots. Get numbers. Get PROOF.

---

### ⚠️ CS-006: Deep Debug Test Pattern

When something "isn't working," use this comprehensive test pattern:

```javascript
test('deep debug feature', async ({ page }) => {
  // 1. Capture ALL console logs
  const allLogs = [];
  page.on('console', msg => allLogs.push(`[${msg.type()}] ${msg.text()}`));

  // 2. Take screenshots at EVERY step
  await page.screenshot({ path: '/tmp/debug_01_step.png' });

  // 3. Get NUMERIC evidence
  const before = await page.textContent('.row-count');
  // ... do action ...
  const after = await page.textContent('.row-count');

  // 4. Check DOM state directly
  const state = await page.evaluate(() => {
    const input = document.getElementById('my-input');
    return { value: input?.value, id: input?.id };
  });

  // 5. Print summary with NUMBERS
  console.log(`Before: ${before}, After: ${after}`);
  console.log(`Logs related to feature:`, allLogs.filter(l => l.includes('feature')));
});
```

**Why:** Comprehensive evidence gathering finds the real issue faster than guessing.

---

### ⚠️ CS-007: Search Results Empty Cells Bug

**When search filters correctly but cells show shimmer/empty, check array indexing.**

**Symptoms:**
- Search shows "2 rows" ✓
- But cells are empty (shimmer placeholders)
- DOM query finds 0 matches for search term

**Root Cause:** API returns original `row_num` values (e.g., 4, 11), but frontend stores at those indices:
```javascript
// WRONG - search results stored at wrong indices
const index = row.row_num - 1;  // row_num=4 → index=3, row_num=11 → index=10
rows[index] = rowData;          // But virtual scroll renders index 0, 1...
```

**Fix:** Use sequential indices for search results:
```javascript
const isSearching = searchTerm && searchTerm.trim();
const pageStartIndex = (page - 1) * PAGE_SIZE;
data.rows.forEach((row, pageIndex) => {
  // For search: sequential index (0, 1, 2...)
  // For normal: original row_num - 1
  const index = isSearching ? (pageStartIndex + pageIndex) : (row.row_num - 1);
  rows[index] = rowData;
});
```

**Debug Steps That Found This:**
```bash
# 1. Run targeted Playwright test with console capture
npx playwright test tests/search-proue.spec.ts --reporter=list

# 2. Query database to see actual row_num values
python3 << 'EOF'
import sys
sys.path.insert(0, 'server')
from sqlalchemy import create_engine, text
from config import DATABASE_URL
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT id, row_num, target FROM ldm_rows
        WHERE file_id = 118
        AND LOWER(target) LIKE '%proue%'
    """))
    for r in result.fetchall():
        print(f"row_num: {r[1]}, target: {r[2][:50]}")
EOF

# 3. Compare: API returns row_num=4,11 but frontend expects 0,1
```

**Key Insight:** When debugging "data not rendering" issues:
1. Check if filtering works (count changes) ✓
2. Check if data exists (database query) ✓
3. Check WHERE data is stored (array indices) ← THIS WAS THE BUG

---

### CS-008: Fire-and-Forget Functions

**Never call `.catch()` on a function that doesn't return a Promise.**

```javascript
// ldm.js - unlockRow is fire-and-forget
export function unlockRow(fileId, rowId) {
  websocket.send('ldm_unlock_row', { ... });
  // NO RETURN - returns undefined
}

// WRONG - crashes silently with TypeError
unlockRow(fileId, rowId).catch(() => {});
// TypeError: Cannot read properties of undefined (reading 'catch')

// RIGHT - just call it
unlockRow(fileId, rowId);
```

**Symptoms:**
- Function appears to do nothing
- No visible error (TypeError hidden)
- Code after the `.catch()` call doesn't execute

**Debug Approach:**
1. Add console.log at every line
2. Wrap in try-catch to expose hidden TypeError
3. Check if function returns Promise or undefined

---

### ⚠️ CS-009: Rate Limiting State Persistence (2025-12-29)

**Server restart does NOT clear rate limits. State is in a file, not memory.**

**Symptoms:**
- Login returns 429 Too Many Requests
- Restarting backend doesn't help
- Clearing browser cache doesn't help
- Waiting 15+ minutes works (but wastes time)

**Root Cause:** Rate limiter stores failed login attempts in `server/data/logs/security_audit.log`, not in memory.

**Instant Fix:**
```bash
echo "" > /home/neil1988/LocalizationTools/server/data/logs/security_audit.log
```

**Key Insight:** When debugging "server-side state" issues:
1. **Memory state** = clears on restart
2. **File state** = persists through restarts
3. **Database state** = persists through restarts

**Always ask:** "Where is this state stored?" Don't assume memory.

---

### ⚠️ CS-010: Playwright Selector Reliability (2025-12-29)

**NEVER use generic type selectors. Use semantic selectors.**

```javascript
// WRONG - Fragile, may not find input
await page.fill('input[type="text"]', 'value');

// RIGHT - Reliable, uses actual placeholder text
await page.getByPlaceholder('Enter your username').fill('value');

// ALSO RIGHT - Uses accessible role
await page.getByRole('textbox', { name: /username/i }).fill('value');
```

**Selector Reliability Hierarchy:**
1. `getByTestId('my-id')` - Best (explicit test ID)
2. `getByPlaceholder('...')` - Great (visible text)
3. `getByRole('button', { name: /submit/i })` - Great (semantic)
4. `getByText('Submit')` - Good (visible text)
5. `locator('#my-id')` - OK (ID selector)
6. `locator('input[type="text"]')` - **AVOID** (fragile)

**Why generic selectors fail:**
- Multiple inputs of same type on page
- Type attribute may not exist
- Framework may use different attributes

---

### Quick Reference Card

| Problem | Solution |
|---------|----------|
| Playwright can't fill input | Use `oninput` not `bind:value` |
| State resets unexpectedly | Track previous value in effect |
| Code silently fails | Check for TS syntax in non-TS file |
| DB auth fails | Use server config, not hardcoded |
| "Not working" claim | Get screenshots, get PROOF |
| Search shows count but empty cells | Check array indexing (row_num vs sequential) |
| Function appears to do nothing | Check if calling `.catch()` on non-Promise |
| Rate limit 429 after restart | Clear `security_audit.log` (state in file!) |
| Selector timeout | Use `getByPlaceholder` or `getByRole` |

---

## Phase 14: Effective Debug Commands

### DO: Targeted Database Queries
```bash
# Query specific data to understand what API returns
python3 << 'EOF'
import sys
sys.path.insert(0, 'server')
from sqlalchemy import create_engine, text
from config import DATABASE_URL
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    # Your query here
    result = conn.execute(text("SELECT * FROM ldm_rows WHERE ... LIMIT 5"))
    for r in result.fetchall():
        print(r)
EOF
```

### DO: Playwright Tests with Full Evidence
```javascript
// Capture console, screenshot at every step, query DOM state
const allLogs = [];
page.on('console', msg => allLogs.push(`[${msg.type()}] ${msg.text()}`));

await page.screenshot({ path: '/tmp/debug_01.png' });

// Check DOM state directly
const state = await page.evaluate(() => {
  return document.querySelectorAll('.cell.target').length;
});
```

### DON'T: Guess or Assume
```bash
# DON'T just restart and hope it works
# DON'T assume the bug is where you think it is
# DON'T skip database verification
```

### DON'T: Hardcode Credentials
```python
# WRONG
engine = create_engine("postgresql://admin:wrongpassword@localhost:5432/db")

# RIGHT
from config import DATABASE_URL
engine = create_engine(DATABASE_URL)
```

---

*Dev Mode Protocol | Fast UI Testing | No Build Required*
*Updated: 2025-12-28 with CS-007 Search Indexing Bug + Phase 14 Debug Commands*
