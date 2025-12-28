# Session Context

**Updated:** 2025-12-28 03:15 | **Build:** 409+ | **Issues:** UI-077 duplicates OPEN

---

## ACTIVE NOW

### Search Bar - FIXED (2025-12-28)

**Status:** VERIFIED WORKING

**Root Cause:** THREE compounding issues:
1. TypeScript syntax in non-TS Svelte file (caused compile error)
2. `bind:value` with `$state()` fights Playwright input
3. Effect resetting searchTerm on every run (not just fileId change)

**Fix Applied:**
1. Removed TypeScript casts from `<script>` block
2. Changed to `oninput` handler instead of `bind:value`
3. Added previousFileId tracking to prevent unintended resets

**Verified:** 10,000 rows → 4 rows when searching "5000"

---

### Test Data Setup - DONE

- Deleted 3 duplicate `test_10k.txt` files (30,000 rows)
- Uploaded real test data: `sample_language_data.txt` (63 rows, PAColor tags)
- File ID: 118 in Project 8 "Playwright Test Project"

### Color Display - VERIFIED WORKING

- 23 colored spans rendered
- 21 gold spans (`<PAColor0xffe9bd23>`)
- 0 raw tags visible
- **UI-078 FIXED**

### Duplicate Name Prevention - CONFIRMED MISSING

- **UI-077 OPEN:** Verified - duplicates ARE allowed
- **Files:** DUPLICATES ALLOWED (needs fix)
- **Folders:** DUPLICATES ALLOWED (needs fix)
- **Projects:** Blocked by DB constraint (but returns 500, not clean 400)
- **Needs fix** in `files.py`, `folders.py`, `projects.py`

### DEV Testing Efficiency - ASSESSED

- **20-30x faster** than Windows build cycle
- Code change → Test: 15 seconds
- Full debug cycle: 30 seconds
- See: `testing_toolkit/dev_tests/EFFICIENCY_REPORT.md`

---

### DEV Mode Testing Protocol - READY

**Location:** `testing_toolkit/DEV_MODE_PROTOCOL.md`

**Key Sections:**
- Phase 9: Svelte 5 Debugging (CRITICAL)
- Phase 9.8: Case Study - Search Bar Bug Fix
- Phase 10: Git Push Protocol (Gitea on/off)
- Phase 11: Testing Utilities Library

**Helpers Created:** `testing_toolkit/dev_tests/helpers/`
- `login.ts` - Login, navigate, get API token
- `ldm-actions.ts` - Select project/file, search, edit modal
- `database.py` - DB access using server config
- `api.py` - REST API helper with auth

---

## PENDING TASKS

1. **UI-077:** Add duplicate name prevention for files/folders/TMs
2. **Advanced Search:** Add search mode dropdown (Contain/Exact/Not Contain/Fuzzy)
3. **Color Display:** Test ColorText.svelte with real data
4. **Dev Utils:** Create reusable Playwright helpers

---

## IMPORTANT PATTERNS

### Database Access (CORRECT)
```python
# Use server config - NOT hardcoded credentials
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools/server')
from config import DATABASE_URL
engine = create_engine(DATABASE_URL)
```

### API Access (CORRECT)
```python
import requests
resp = requests.post('http://localhost:8888/api/auth/login',
    json={'username': 'admin', 'password': 'admin123'})
token = resp.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}
```

### Svelte 5 Input Handling (CORRECT)
```svelte
<!-- NO bind:value - use oninput only -->
<input
  oninput={(e) => { searchTerm = e.target.value; }}
/>
```

---

## FILES CHANGED

| File | Change |
|------|--------|
| VirtualGrid.svelte | Fixed search, oninput handler, previousFileId tracking |
| DEV_MODE_PROTOCOL.md | Added case study, git protocol |
| ISSUES_TO_FIX.md | UI-076 marked FIXED |
| sample_language_data.txt | Real test data (63 rows) |
| tests/*.spec.ts | Playwright test files for search |

---

*Last updated: 2025-12-28 02:45 KST*
