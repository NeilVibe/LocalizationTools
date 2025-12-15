# Work In Progress (WIP) Hub

**Purpose:** Detailed task breakdowns for active priorities. Roadmap.md stays high-level, WIP docs have the details.

---

## Priority Tiers

### Tier 1: CORE (Current Focus)
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| **P32** | [../code-review/ISSUES_20251215_LDM_API.md](../code-review/ISSUES_20251215_LDM_API.md) | 🔴 CURRENT | 10 code review issues in LDM API |

### Tier 2: LATER (Low Priority)
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| P25 | [P25_LDM_UX_OVERHAUL.md](P25_LDM_UX_OVERHAUL.md) | 85% | TM matching, QA - features |
| P17 | [P17_LDM_TASKS.md](P17_LDM_TASKS.md) | 80% | Custom pickers - features |

### Reference / Complete
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| P33 | [P33_OFFLINE_MODE_CI_OVERHAUL.md](P33_OFFLINE_MODE_CI_OVERHAUL.md) | ✅ Complete | Offline mode + CI overhaul |
| P27 | [P27_STACK_MODERNIZATION.md](P27_STACK_MODERNIZATION.md) | ✅ Complete | Svelte 5 + Vite 7 + Electron 39 |
| P26 | [SECURITY_FIX_PLAN.md](SECURITY_FIX_PLAN.md) | ✅ Complete | Security vulnerability remediation |
| P17 | [P17_TM_ARCHITECTURE.md](P17_TM_ARCHITECTURE.md) | Reference | TM System architecture spec |
| SESSION | [SESSION_CONTEXT.md](SESSION_CONTEXT.md) | Active | Last session state |
| ISSUES | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Active | Known bugs |

## Completed (Reference)

| Priority | Document | Description |
|----------|----------|-------------|
| P21 | [P21_DATABASE_POWERHOUSE.md](P21_DATABASE_POWERHOUSE.md) | Database optimization + PgBouncer |
| P20 | [P20_MODEL_MIGRATION.md](P20_MODEL_MIGRATION.md) | Qwen embedding model migration |
| P18 | [P_DB_OPTIMIZATION.md](P_DB_OPTIMIZATION.md) | PostgreSQL batch inserts + FTS |
| P13 | [../history/P13_GITEA_CACHE_PLAN.md](../history/P13_GITEA_CACHE_PLAN.md) | Smart build cache v2.0 |
| P13 | [../history/P13_GITEA_TASKS.md](../history/P13_GITEA_TASKS.md) | Gitea CI/CD setup tasks |
| BACKLOG | [P_TESTING_DOCS_IMPROVEMENTS.md](P_TESTING_DOCS_IMPROVEMENTS.md) | Testing suite + docs improvements |

---

## Document Hierarchy

```
Roadmap.md (ROOT)           ← BIG PICTURE: "What priorities exist?"
    │
    └── docs/wip/           ← DETAILS: "How to implement each priority"
        ├── README.md       ← THIS FILE (hub index)
        ├── P17_*.md        ← LDM development tasks
        ├── P18_*.md        ← Database optimization
        ├── P20_*.md        ← Model migration
        ├── P21_*.md        ← Database powerhouse
        └── ISSUES_TO_FIX.md ← Bug tracker
```

---

## Rules

1. **Roadmap.md** = Status overview only (~200 lines)
   - One paragraph + status per priority
   - Link to WIP doc for details
   - NO detailed task lists in Roadmap

2. **WIP docs** = Full implementation details
   - Task checklists with [x] checkboxes
   - Technical specs + diagrams
   - Updated DURING development

3. **ISSUES_TO_FIX.md** = Bug/issue tracker
   - UI bugs, UX problems
   - Categorized by area
   - Linked from here

---

## Quick Navigation

**Current Session:** [SESSION_CONTEXT.md](SESSION_CONTEXT.md)

**🔴 CURRENT FOCUS:**
- **P32:** [../code-review/ISSUES_20251215_LDM_API.md](../code-review/ISSUES_20251215_LDM_API.md)
  - 10 code review issues in LDM API
  - 1 CRITICAL, 3 HIGH, 5 MEDIUM/LOW

**✅ RECENTLY COMPLETED:**
- **P33:** Offline Mode + CI Overhaul (100%)

**Low Priority (Later):**
- P25/P17: LDM features

---

*Last Updated: 2025-12-16*
