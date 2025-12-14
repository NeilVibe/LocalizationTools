# Work In Progress (WIP) Hub

**Purpose:** Detailed task breakdowns for active priorities. Roadmap.md stays high-level, WIP docs have the details.

---

## Active WIP Documents

| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| **P27** | [P27_STACK_MODERNIZATION.md](P27_STACK_MODERNIZATION.md) | ✅ Complete | Svelte 5 + Vite 7 + Electron 39 |
| **P26** | [SECURITY_FIX_PLAN.md](SECURITY_FIX_PLAN.md) | ✅ Complete | Security vulnerability remediation |
| **P25** | [P25_LDM_UX_OVERHAUL.md](P25_LDM_UX_OVERHAUL.md) | 85% | LDM UX improvements |
| **P22** | [P22_PRODUCTION_PARITY.md](P22_PRODUCTION_PARITY.md) | Phase 1 | SQLite removal - DEV = PRODUCTION |
| **P17** | [P17_LDM_TASKS.md](P17_LDM_TASKS.md) | 80% | LDM LanguageData Manager - task tracking |
| **P17** | [P17_TM_ARCHITECTURE.md](P17_TM_ARCHITECTURE.md) | Reference | TM System 9-Tier architecture spec |
| **SESSION** | [SESSION_CONTEXT.md](SESSION_CONTEXT.md) | Active | Last session state + current status |
| **ISSUES** | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Active | Known bugs + UI issues to fix |

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

**Active Work:**
- LDM UX: [P25_LDM_UX_OVERHAUL.md](P25_LDM_UX_OVERHAUL.md) - 85%
- LDM Core: [P17_LDM_TASKS.md](P17_LDM_TASKS.md) - 80%
- Bug Fixes: [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md)

**Recently Completed:**
- P27: Stack Modernization (Svelte 5 + Vite 7 + Electron 39)
- P26: Security Vulnerability Remediation
- CI/CD: GitHub + Gitea hardening

---

*Last Updated: 2025-12-14*
