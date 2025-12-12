# P26: LocaNext Full Source Code Review

**Priority:** P26 | **Status:** Pending | **Created:** 2025-12-12

**Frequency:** Weekly (or after major changes)

---

## Purpose

Systematic review of the entire codebase to identify and eliminate:
- Dead code / unused files
- Duplicate logic / copy-paste blocks
- Old code coexisting with replacement code
- Parasitic imports / dependencies
- Inconsistent patterns
- Technical debt

---

## Review Checklist

### 1. DEAD CODE
- [ ] Unused imports
- [ ] Unused functions/classes
- [ ] Commented-out code blocks
- [ ] Files not referenced anywhere
- [ ] Deprecated endpoints still present

### 2. DUPLICATES
- [ ] Same logic in multiple files
- [ ] Copy-pasted functions with minor changes
- [ ] Multiple implementations of same feature
- [ ] Redundant utility functions

### 3. OLD + NEW COEXISTENCE
- [ ] Old implementation not removed after new one added
- [ ] Legacy compatibility shims that are no longer needed
- [ ] Multiple versions of same component
- [ ] Outdated patterns alongside new patterns

### 4. PARASITES
- [ ] Unused npm packages in package.json
- [ ] Unused pip packages in requirements.txt
- [ ] Imports that aren't used
- [ ] Dependencies that could be removed

### 5. INCONSISTENCIES
- [ ] Mixed sync/async patterns (should be consistent)
- [ ] Different error handling styles
- [ ] Inconsistent naming conventions
- [ ] Mixed logging approaches (logger vs print)

### 6. ARCHITECTURE
- [ ] Files in wrong directories
- [ ] Circular imports
- [ ] God files (too many responsibilities)
- [ ] Missing abstractions

---

## Areas to Review

### Backend (server/)

| Area | Files | Priority | Status |
|------|-------|----------|--------|
| **API endpoints** | server/api/*.py | High | [ ] Pending |
| **Tools** | server/tools/*/ | High | [ ] Pending |
| **Database** | server/database/*.py | Medium | [ ] Pending |
| **Utils** | server/utils/*.py | Medium | [ ] Pending |
| **Config** | server/config.py | Low | [ ] Pending |

### Frontend (locaNext/)

| Area | Files | Priority | Status |
|------|-------|----------|--------|
| **Components** | src/lib/components/*.svelte | High | [ ] Pending |
| **LDM Components** | src/lib/components/ldm/*.svelte | High | [ ] Pending |
| **Stores** | src/lib/stores/*.js | Medium | [ ] Pending |
| **API Client** | src/lib/api/*.js | Medium | [ ] Pending |
| **Utils** | src/lib/utils/*.js | Low | [ ] Pending |

### Tests

| Area | Files | Priority | Status |
|------|-------|----------|--------|
| **Unit tests** | tests/unit/*.py | Medium | [ ] Pending |
| **CDP tests** | tests/cdp/*.py | Low | [ ] Pending |
| **Integration** | tests/integration/*.py | Low | [ ] Pending |

### Shared

| Area | Files | Priority | Status |
|------|-------|----------|--------|
| **Scripts** | scripts/*.py, scripts/*.sh | Low | [ ] Pending |
| **Config files** | *.json, *.yaml | Low | [ ] Pending |
| **Documentation** | docs/**/*.md | Low | [ ] Pending |

---

## Known Issues to Check

### High Priority
- [ ] `server/tools/xlstransfer/progress_tracker.py` - Now duplicated by `server/utils/progress_tracker.py`?
- [ ] Multiple WebSocket emit patterns
- [ ] Sync vs Async database access patterns

### Medium Priority
- [ ] Old API patterns vs new base_tool_api pattern
- [ ] Multiple file upload handlers?
- [ ] Unused Carbon components imports

### Low Priority
- [ ] Comments that don't match code
- [ ] TODO comments that are done
- [ ] Console.log / print statements that should be logger

---

## Review Process

### Step 1: Automated Scan
```bash
# Find unused imports (Python)
# Find unused exports (JS)
# Find duplicate function names
# Find TODO/FIXME/HACK comments
```

### Step 2: Manual Review
- Read through each file in priority order
- Note issues in this document
- Mark fixed items

### Step 3: Refactor
- Remove dead code
- Consolidate duplicates
- Update patterns to be consistent

### Step 4: Test
- Run full test suite
- Manual smoke test
- Verify no regressions

---

## Review Log

### Review #1 - 2025-12-12
**Reviewer:** Claude
**Status:** Not started
**Findings:**
- (To be filled during review)

**Actions Taken:**
- Created `server/utils/progress_tracker.py` - unified progress tracking with context manager
- Old `server/tools/xlstransfer/progress_tracker.py` - CANDIDATE FOR REMOVAL (check usage first)

---

## Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Python files | ? | ? | ? |
| Total Svelte files | ? | ? | ? |
| Lines of code | ? | ? | ? |
| Unused imports | ? | ? | ? |
| Duplicate blocks | ? | ? | ? |

---

## Schedule

| Date | Type | Notes |
|------|------|-------|
| 2025-12-12 | Initial setup | Created this document |
| 2025-12-19 | Weekly review #1 | TBD |
| 2025-12-26 | Weekly review #2 | TBD |

---

*This document should be updated after each review session.*
