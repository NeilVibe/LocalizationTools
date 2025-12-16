# Work In Progress (WIP) Hub

**Purpose:** Detailed task breakdowns for active priorities. Roadmap.md stays high-level, WIP docs have the details.

---

## Priority Tiers

### Tier 0: CRITICAL BUGS (Must Fix First)
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| **BUGS** | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | 🔴 NOW | 7 issues (BUG-011 fixed!) |
| **P35** | [P35_SVELTE5_MIGRATION.md](P35_SVELTE5_MIGRATION.md) | ✅ DONE | Svelte 5 reactivity fix (BUG-011) |

### Tier 1: CORE (After Bug Fixes)
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| **P25** | [P25_LDM_UX_OVERHAUL.md](P25_LDM_UX_OVERHAUL.md) | ⏸️ PAUSED | TM matching, QA checks (85%) |

### Tier 2: LATER (Low Priority)
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| P17 | [P17_LDM_TASKS.md](P17_LDM_TASKS.md) | 80% | Custom pickers - features |

### Tier 3: Investigation / Protocol
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| **P34** | [P34_RESOURCE_CHECK_PROTOCOL.md](P34_RESOURCE_CHECK_PROTOCOL.md) | 🔵 NEW | Resource zombies + cleanup protocol |

### Reference / Complete
| Priority | Document | Status | Description |
|----------|----------|--------|-------------|
| CI | Unified GitHub + Gitea | ✅ Complete | 255 tests, both platforms |
| P33 | [P33_OFFLINE_MODE_CI_OVERHAUL.md](P33_OFFLINE_MODE_CI_OVERHAUL.md) | ✅ Complete | Offline mode + auto-login |
| P32 | [../code-review/ISSUES_20251215_LDM_API.md](../code-review/ISSUES_20251215_LDM_API.md) | ✅ Complete | Code review (9/11 fixed) |
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

**✅ JUST FIXED:**
- **BUG-011:** App stuck at "Connecting to LDM..." → **FIXED (P35 Svelte 5 migration)**
- See: [P35_SVELTE5_MIGRATION.md](P35_SVELTE5_MIGRATION.md)

**🔴 CRITICAL - FIX NEXT:**
- **BUG-007:** Offline mode auto-fallback (3s timeout)
- **BUG-008:** Online/Offline mode indicator
- See: [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md)

**⚠️ HIGH (Fixes Ready):**
- **BUG-009:** Installer no details (fix applied)
- **BUG-010:** First-run window not closing (fix applied)

**📋 MEDIUM (UI/UX):**
- UI-001: Remove light/dark toggle
- UI-002: Reorganize Preferences
- UI-003: TM activation via modal
- UI-004: Remove TM from grid

**⏸️ PAUSED (After Bug Fixes):**
- **P25:** LDM UX (85%) - TM matching, QA checks

**✅ RECENTLY COMPLETED:**
- **P35:** Svelte 5 Migration (BUG-011 fix)
- **P34:** Resource Check Protocol (Docker cleanup)
- **CI:** Unified GitHub + Gitea (255 tests)
- **P33:** Offline Mode + Auto-Login (CI only)

---

*Last Updated: 2025-12-16 01:50 KST*
