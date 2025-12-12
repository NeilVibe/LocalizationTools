# Code Review Protocol

**Owner:** Development Team

---

## Review Types

| Type | Frequency | Scope | Time |
|------|-----------|-------|------|
| **Quick Scan** | Weekly | Automated scans + surface issues | ~1 hour |
| **Deep Review** | Bi-weekly | Full code read, architecture, logic | ~4-8 hours |

---

## Purpose

Eliminate:
- Dead code / unused files
- Duplicate logic (Factor Power violations)
- Old + new code coexistence
- Parasitic imports
- Logic bugs, security issues
- Poor error handling
- Architectural problems

---

## Folder Structure

```
docs/code-review/
├── CODE_REVIEW_PROTOCOL.md    ← This file (reusable process)
├── ISSUES_YYYYMMDD.md         ← Issue list per review session
└── DEEP_REVIEW_YYYYMMDD.md    ← Deep review notes (bi-weekly)
```

---

# QUICK SCAN (Weekly)

**2 passes: Find & Fix, then Verify**

## Pass 1: Find & Fix

### 1.1 Run Automated Scans
```bash
cd /home/neil1988/LocalizationTools

# TODO/FIXME/HACK
grep -rn "TODO\|FIXME\|HACK" server/ --include="*.py" | wc -l

# print() (should be logger)
grep -rn "print(" server/ --include="*.py" | grep -v "file=sys.stderr" | wc -l

# Large files (>500 LOC)
find server/ -name "*.py" -exec wc -l {} \; | awk '$1 > 500' | sort -rn | head -10

# console.log (frontend)
grep -rn "console.log" locaNext/src/ --include="*.js" --include="*.svelte" | wc -l

# Duplicate functions
grep -rhn "^def \|^async def " server/ --include="*.py" | sed 's/.*def //' | sed 's/(.*$//' | sort | uniq -c | sort -rn | head -10
```

### 1.2 Create Issue List
Create `ISSUES_YYYYMMDD.md` with findings.

### 1.3 Fix One by One
Mark each fixed with one-liner.

### 1.4 Commit Pass 1

## Pass 2: Verify Clean

### 2.1 Re-run All Scans
### 2.2 Check Fixed Issues
### 2.3 Check for Regressions
### 2.4 Final Commit

---

# DEEP REVIEW (Bi-weekly)

**Full manual code review - read every file, check logic, architecture**

## Module Rotation

Review one module per session (rotate):

| Week | Module | Files |
|------|--------|-------|
| 1 | LDM | server/tools/ldm/, locaNext LDM components |
| 2 | XLSTransfer | server/tools/xlstransfer/, server/api/xlstransfer* |
| 3 | QuickSearch | server/tools/quicksearch/ |
| 4 | KR Similar | server/tools/kr_similar/ |
| 5 | Core/Auth | server/api/auth*, server/database/, server/utils/ |
| 6 | Frontend | locaNext/src/lib/, adminDashboard/ |

## Per-File Review Checklist

For EVERY file in the module:

### Code Quality
- [ ] Clear function names and purpose?
- [ ] Functions <50 lines? (split if larger)
- [ ] No dead code / commented code?
- [ ] No magic numbers? (use constants)
- [ ] Consistent style?

### Logic & Correctness
- [ ] Edge cases handled? (null, empty, invalid)
- [ ] Off-by-one errors?
- [ ] Race conditions? (async code)
- [ ] Correct error propagation?

### Error Handling
- [ ] All exceptions caught appropriately?
- [ ] Meaningful error messages?
- [ ] Errors logged?
- [ ] User-facing errors sanitized? (no stack traces)

### Security
- [ ] Input validation?
- [ ] SQL injection safe? (parameterized queries)
- [ ] No secrets in code?
- [ ] Auth checks on endpoints?

### Architecture
- [ ] Single responsibility?
- [ ] Factor Power applied? (no duplicates)
- [ ] Correct layer? (API vs service vs util)
- [ ] Dependencies minimal?

### Performance
- [ ] N+1 queries?
- [ ] Unnecessary loops?
- [ ] Large data in memory?
- [ ] Caching where needed?

## Deep Review Output

Create `DEEP_REVIEW_YYYYMMDD.md`:
```markdown
# Deep Review: [Module Name]

**Date:** YYYY-MM-DD
**Files Reviewed:** X

## Summary
- Critical issues: X
- Major issues: X
- Minor issues: X
- Suggestions: X

## File-by-File

### filename.py
- [CRITICAL] Description
- [MAJOR] Description
- [MINOR] Description
- [SUGGESTION] Description

## Action Items
1. [ ] Fix critical issue X
2. [ ] Fix major issue Y
```

---

## Review History

| Date | Type | Module | Issues | Fixed | Pass 2 |
|------|------|--------|--------|-------|--------|
| 2025-12-12 | Quick | All | 9 | 4 | ✓ Clean |

---

*Update this protocol as process improves.*
