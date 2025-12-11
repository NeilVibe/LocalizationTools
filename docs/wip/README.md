# Work In Progress (WIP) Hub

**Purpose:** Detailed task breakdowns for active priorities. Roadmap.md stays high-level, WIP docs have the details.

---

## Active WIP Documents

| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| **P17** | [P17_LDM_TASKS.md](P17_LDM_TASKS.md) | 67% | LDM LanguageData Manager - task tracking |
| **P17** | [P17_TM_ARCHITECTURE.md](P17_TM_ARCHITECTURE.md) | Reference | TM System 9-Tier architecture spec |
| **P21** | [P21_DATABASE_POWERHOUSE.md](P21_DATABASE_POWERHOUSE.md) | Complete | Database optimization + PgBouncer |
| **P20** | [P20_MODEL_MIGRATION.md](P20_MODEL_MIGRATION.md) | Complete | Qwen embedding model migration |
| **P18** | [P_DB_OPTIMIZATION.md](P_DB_OPTIMIZATION.md) | Complete | PostgreSQL batch inserts + FTS |
| **P13** | [P13_GITEA_CACHE_PLAN.md](P13_GITEA_CACHE_PLAN.md) | Complete | Smart build cache v2.0 |
| **P13** | [P13_GITEA_TASKS.md](P13_GITEA_TASKS.md) | Complete | Gitea CI/CD setup tasks |
| **ISSUES** | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Active | Known bugs + UI issues to fix |
| **BACKLOG** | [P_TESTING_DOCS_IMPROVEMENTS.md](P_TESTING_DOCS_IMPROVEMENTS.md) | Backlog | Testing suite + docs improvements |

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

**Currently Active:**
- LDM Development: [P17_LDM_TASKS.md](P17_LDM_TASKS.md)
- Bug Fixes: [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md)

**Completed (Reference):**
- [P21_DATABASE_POWERHOUSE.md](P21_DATABASE_POWERHOUSE.md) - PgBouncer + COPY TEXT
- [P20_MODEL_MIGRATION.md](P20_MODEL_MIGRATION.md) - Qwen embedding
- [P13_GITEA_CACHE_PLAN.md](P13_GITEA_CACHE_PLAN.md) - Smart cache v2.0

**Other Resources:**
- [Presentations](../presentations/) - 3 consolidated images (Full Architecture, Licensing, Apps)

---

*Last Updated: 2025-12-11*
