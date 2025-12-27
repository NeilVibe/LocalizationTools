# Manual Search Test Checklist

**Date:** 2025-12-28
**Purpose:** Verify search works with real user typing (Playwright has Svelte 5 compatibility issue)

---

## Prerequisites

1. Backend running: `DEV_MODE=true python3 server/main.py`
2. Frontend running: `npm run dev` (in locaNext folder)
3. Browser open: http://localhost:5173

---

## Test Steps

### 1. Login
- [ ] Go to http://localhost:5173
- [ ] Enter: admin / admin123
- [ ] Click Login

### 2. Navigate to LDM
- [ ] Click LDM in navigation
- [ ] Wait for page to load

### 3. Open a File
- [ ] Click on "Playwright Test Project"
- [ ] Click on any test file (e.g., test_10k.txt)
- [ ] Wait for data to load (should show "10,000 rows")

### 4. Test Search - Basic
- [ ] Click in search box ("Search source, target, or StringID...")
- [ ] Type: `Item`
- [ ] Wait 500ms for debounce

**Expected:** Row count should DECREASE (filtered results)

### 5. Test Search - Clear
- [ ] Clear the search box (backspace or X button)
- [ ] Wait 500ms

**Expected:** Row count should return to original (e.g., 10,000)

### 6. Test Search - Korean
- [ ] Type: `항목` (Korean word)
- [ ] Wait 500ms

**Expected:** Should show Korean rows only

### 7. Browser Console Check
- Open DevTools (F12) → Console
- [ ] Should see: `searchTerm changed via effect {from: "", to: "Item"}`
- [ ] Should see: `handleSearch triggered`
- [ ] Should see: `loadRows with search {searchTerm: "Item"}`

---

## Results

| Test | Pass/Fail | Notes |
|------|-----------|-------|
| Basic search filters rows | | |
| Clear restores all rows | | |
| Korean search works | | |
| Console logs appear | | |

---

## If Search DOESN'T Work

Check these:
1. Console errors?
2. Network tab - is API call made with `search` param?
3. Does `searchTerm` state update when typing?

---

*Manual test doc for Svelte 5 search verification*
