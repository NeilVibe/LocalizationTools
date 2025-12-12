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

## Review Process

### 1. Run Automated Scans
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

### 2. Create Issue List
Create `ISSUES_YYYYMMDD.md` with all findings.

### 3. Review Issues with User
Go through list, confirm priorities.

### 4. Fix One by One
Mark each issue fixed with one-liner summary.

### 5. Final Review
Run scans again, confirm issues resolved.

### 6. Commit
Commit with reference to issue list.

---

## Per-File Checklist

- [ ] Dead code?
- [ ] Duplicates elsewhere?
- [ ] Imports all used?
- [ ] Logger not print()?
- [ ] Factor Power applied?

---

## Review History

| Date | Issue List | Issues | Fixed |
|------|------------|--------|-------|
| 2025-12-12 | [ISSUES_20251212.md](ISSUES_20251212.md) | 9 | 0 |

---

*Update this protocol as process improves.*
