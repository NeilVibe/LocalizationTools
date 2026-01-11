# Work In Progress (WIP) Documentation

> Active work tracking for LocaNext development.

---

## Quick Links

| Doc | Purpose |
|-----|---------|
| [SESSION_CONTEXT.md](SESSION_CONTEXT.md) | Current session state, what's active |
| [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Bug tracker, open issues |
| [P10_DB_ABSTRACTION.md](P10_DB_ABSTRACTION.md) | DB Abstraction Layer implementation plan |

---

## Current Priority

**P10: DB Abstraction Layer** - Major architecture refactor

Transform the entire backend from inconsistent database patterns to unified Repository Pattern:
- All routes use repository interfaces
- Same code works online (PostgreSQL) and offline (SQLite)
- True offline parity

See: [P10_DB_ABSTRACTION.md](P10_DB_ABSTRACTION.md) for full plan

---

## Navigation

| Need | Go To |
|------|-------|
| Full roadmap | [Roadmap.md](../../Roadmap.md) |
| Architecture docs | [docs/architecture/](../architecture/) |
| Testing protocols | [testing_toolkit/](../../testing_toolkit/) |
| CI/CD docs | [docs/reference/cicd/](../reference/cicd/) |

---

## WIP File Naming

| Prefix | Meaning |
|--------|---------|
| `P##_` | Priority number (P10 = highest active) |
| `BUG-###_` | Bug fix documentation |
| `FEATURE-###_` | Feature implementation |

---

*Last updated: 2026-01-11*
