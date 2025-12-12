# Code Review Protocol

**Frequency:** Weekly | **Owner:** Development Team

---

## Purpose

Weekly systematic review to eliminate:
- Dead code / unused files
- Duplicate logic
- Old + new code coexistence
- Parasitic imports
- Inconsistent patterns

---

## Folder Structure

```
docs/code-review/
├── CODE_REVIEW_PROTOCOL.md    ← This file (reusable process)
└── ISSUES_YYYYMMDD.md         ← Issue list per review session
```

---

## Review Process (2 Passes)

**A code review = 2 full passes. Pass 2 verifies Pass 1 fixes are clean.**

---

### PASS 1: Find & Fix

#### 1.1 Run Automated Scans
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

#### 1.2 Create Issue List
Create `ISSUES_YYYYMMDD.md` with all findings.

#### 1.3 Review Issues with User
Go through list, confirm priorities.

#### 1.4 Fix One by One
Mark each issue fixed with one-liner summary.

#### 1.5 Commit Pass 1
Commit fixes with reference to issue list.

---

### PASS 2: Verify Clean

#### 2.1 Re-run All Scans
Same scans as Pass 1 to verify fixes didn't introduce new issues.

#### 2.2 Check Fixed Issues
Verify each "FIXED" issue is actually resolved.

#### 2.3 Check for Regressions
- Did fixes break anything?
- Any new duplicates introduced?
- Imports still clean?

#### 2.4 Final Commit
Update issue list with Pass 2 results, commit.

---

### Summary

| Pass | Purpose |
|------|---------|
| Pass 1 | Find problems → List → Fix → Commit |
| Pass 2 | Verify fixes → Check regressions → Final commit |

---

## Per-File Checklist

- [ ] Dead code?
- [ ] Duplicates elsewhere?
- [ ] Imports all used?
- [ ] Logger not print()?
- [ ] Factor Power applied?

---

## Review History

| Date | Issue List | Issues | Fixed | Pass 2 |
|------|------------|--------|-------|--------|
| 2025-12-12 | [ISSUES_20251212.md](ISSUES_20251212.md) | 9 | 4 | ✓ Clean |

---

*Update this protocol as process improves.*
