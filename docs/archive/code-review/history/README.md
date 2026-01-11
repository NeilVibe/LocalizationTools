# Code Review History

**Location:** `docs/code-review/history/`
**Protocol:** [CODE_REVIEW_PROTOCOL.md](../CODE_REVIEW_PROTOCOL.md)

---

## Closed Reviews

| Review ID | Closed | Fixed | Accept | Key Fixes |
|-----------|--------|-------|--------|-----------|
| [20251212](ISSUES_20251212.md) | 2025-12-13 | 36 | 30 | Async endpoints, security hardening, pg_trgm, JSONB |

---

## Quick Stats

- **Total Reviews:** 1
- **Total Fixed:** 36
- **Total Accepted:** 30

---

## Key Fixes by Review

### Review 20251212 (First Review)

| Category | Count | Details |
|----------|-------|---------|
| Async/Sync | 7 | TM endpoints + main.py now async |
| Security | 4 | Rate limiting, audit log, auth re-enabled |
| Scale | 4 | pg_trgm, chunked queries, shared engine |
| Data | 3 | JSONB migration, DEV_MODE |
| Code | 18 | Imports, guards, URLs, misc |

---

## Retention Policy

- **Keep:** 6 months
- **Archive older reviews:** Delete after 6 months
- **Last cleanup:** N/A (first review)

---

## How to Start New Review

```bash
# 1. Create new issue file with today's date
touch docs/code-review/ISSUES_YYYYMMDD.md

# 2. Follow protocol for PASS 1 + PASS 2
# See: CODE_REVIEW_PROTOCOL.md

# 3. When closed, archive here
mv ISSUES_YYYYMMDD.md history/

# 4. Update this README with summary
```

---

*See [CODE_REVIEW_PROTOCOL.md](../CODE_REVIEW_PROTOCOL.md) for full process*
