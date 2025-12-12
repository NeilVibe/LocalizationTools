# P26: LocaNext Full Source Code Review

**Priority:** P26 | **Status:** In Progress | **Created:** 2025-12-12

**Frequency:** Weekly (Sunday or after major changes)

---

## Codebase Stats

| Metric | Count |
|--------|-------|
| Python files (server/) | 80 |
| Svelte files | 19 |
| JS files | 12 |
| Test files | 70 |
| **Python LOC** | 27,211 |
| **Svelte LOC** | 11,515 |
| **JS LOC** | 2,228 |
| **Total LOC** | ~41,000 |

---

## Known Issues Found (Initial Scan)

### CRITICAL: Duplicate Progress Trackers
```
server/tools/xlstransfer/progress_tracker.py  ← OLD (XLSTransfer specific)
server/utils/progress_tracker.py              ← NEW (unified, context manager)
server/utils/client/progress.py               ← UNKNOWN (check usage)
server/api/progress_operations.py             ← API endpoints (keep)
```
**Action:** Migrate xlstransfer to use new unified tracker, remove old one.

### print() Statements: 98 found
Should be `logger.info()` etc. Many in:
- progress_tracker.py (uses `print(..., file=sys.stderr)`)
- Various tool files

### TODO/FIXME Comments: 7 found
Need to review and either fix or remove.

---

## Review Order (Priority)

### Week 1: Core Infrastructure
| # | Area | Files | Est. Time | Status |
|---|------|-------|-----------|--------|
| 1 | **Progress tracking** | 4 files | 30 min | [ ] |
| 2 | **WebSocket utils** | server/utils/websocket.py | 20 min | [ ] |
| 3 | **Database models** | server/database/*.py | 30 min | [ ] |
| 4 | **Config** | server/config.py | 15 min | [ ] |

### Week 2: API Layer
| # | Area | Files | Est. Time | Status |
|---|------|-------|-----------|--------|
| 5 | **Base Tool API** | server/api/base_tool_api.py | 30 min | [ ] |
| 6 | **LDM API** | server/tools/ldm/api.py | 45 min | [ ] |
| 7 | **Progress API** | server/api/progress_operations.py | 20 min | [ ] |
| 8 | **Other APIs** | server/api/*.py (rest) | 60 min | [ ] |

### Week 3: Tools
| # | Area | Files | Est. Time | Status |
|---|------|-------|-----------|--------|
| 9 | **XLSTransfer** | server/tools/xlstransfer/*.py | 60 min | [ ] |
| 10 | **QuickSearch** | server/tools/quicksearch/*.py | 45 min | [ ] |
| 11 | **KR Similar** | server/tools/kr_similar/*.py | 45 min | [ ] |
| 12 | **LDM handlers** | server/tools/ldm/*.py | 45 min | [ ] |

### Week 4: Frontend
| # | Area | Files | Est. Time | Status |
|---|------|-------|-----------|--------|
| 13 | **LDM Components** | locaNext/src/lib/components/ldm/*.svelte | 60 min | [ ] |
| 14 | **Other Components** | locaNext/src/lib/components/*.svelte | 45 min | [ ] |
| 15 | **Stores** | locaNext/src/lib/stores/*.js | 30 min | [ ] |
| 16 | **API Client** | locaNext/src/lib/api/*.js | 30 min | [ ] |

---

## Automated Scan Commands

Run these before manual review:

```bash
# === FIND TODO/FIXME/HACK ===
grep -rn "TODO\|FIXME\|HACK" server/ --include="*.py"

# === FIND print() (should be logger) ===
grep -rn "print(" server/ --include="*.py" | grep -v "file=sys.stderr"

# === FIND DUPLICATE FUNCTION NAMES ===
grep -rn "^def \|^async def " server/ --include="*.py" | cut -d: -f2 | sort | uniq -d

# === FIND UNUSED IMPORTS (manual check needed) ===
# Use IDE or pylint for accurate detection

# === FIND LARGE FILES (>500 lines) ===
find server/ -name "*.py" -exec wc -l {} \; | awk '$1 > 500' | sort -rn

# === FRONTEND: console.log ===
grep -rn "console.log" locaNext/src/ --include="*.js" --include="*.svelte"

# === FRONTEND: Unused imports ===
# Use ESLint or IDE
```

---

## Review Checklist Per File

For each file reviewed:

- [ ] **Dead code:** Unused functions, commented blocks
- [ ] **Duplicates:** Same logic elsewhere?
- [ ] **Imports:** All used? Correct source?
- [ ] **Logging:** Uses logger, not print()?
- [ ] **Error handling:** Consistent pattern?
- [ ] **Naming:** Follows conventions?
- [ ] **Comments:** Accurate? Not stale?
- [ ] **Type hints:** Present where useful?

---

## Specific Issues to Fix

### 1. Progress Tracker Consolidation
**Files:**
- `server/tools/xlstransfer/progress_tracker.py` - OLD
- `server/utils/progress_tracker.py` - NEW (keep)
- `server/utils/client/progress.py` - CHECK

**Action:**
1. Check what uses old progress_tracker
2. Migrate to new TrackedOperation
3. Delete old file

### 2. print() to logger Migration
**Target:** 98 print statements → 0

**Pattern:**
```python
# OLD
print(f"[PROGRESS] {msg}", file=sys.stderr)

# NEW
logger.info(msg)
```

### 3. Sync/Async Consistency
**Issue:** Some tools are sync, some async. DB access mixed.

**Check:**
- Is there unnecessary sync code in async functions?
- Are we using `asyncio.run()` from sync correctly?

---

## Review Log

### Session 1: 2025-12-12 (Initial Scan)
**Duration:** 15 min
**Findings:**
- 98 print statements need migration
- 7 TODO comments to review
- 3-4 progress tracking implementations (duplicates)
- New unified TrackedOperation created

**Actions:**
- Created `server/utils/progress_tracker.py` (unified)
- Need to migrate old usages

---

### Session 2: TBD
**Duration:**
**Findings:**

**Actions:**

---

## Cleanup Candidates

Files that might be deletable after migration:

| File | Reason | Blocked By |
|------|--------|------------|
| `server/tools/xlstransfer/progress_tracker.py` | Replaced by unified | Check usages |
| `server/utils/client/progress.py` | Unknown purpose | Check usages |

---

## Weekly Metrics

| Week | Files Reviewed | Issues Found | Issues Fixed | LOC Removed |
|------|----------------|--------------|--------------|-------------|
| 1 | 0 | 0 | 0 | 0 |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |

---

## Quick Commands

```bash
# Start review session
cd /home/neil1988/LocalizationTools
code .  # or your editor

# Run automated checks
grep -rn "TODO\|FIXME" server/ --include="*.py"
grep -rn "print(" server/ --include="*.py" | wc -l

# After fixes - run tests
python3 -m pytest tests/unit/ -v --tb=short
```

---

*Last updated: 2025-12-12*
