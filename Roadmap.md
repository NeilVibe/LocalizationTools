# LocaNext - Development Roadmap

**Version**: 2512111200 | **Updated**: 2025-12-11 | **Status**: Production Ready

> **Full History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)
> **Detailed Tasks**: [docs/wip/README.md](docs/wip/README.md) (WIP Hub)
> **Known Issues**: [docs/wip/ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)

---

## Current Status

```
LocaNext v2512111200
├── Backend:     ✅ 55+ API endpoints, async, WebSocket
├── Frontend:    ✅ Electron + Svelte (LocaNext Desktop)
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar + LDM 60%
├── Tests:       ✅ 912 total (no mocks)
├── Security:    ✅ 86 tests (IP filter, CORS, JWT, audit)
├── CI/CD:       ✅ GitHub Actions + Gitea (FULLY WORKING!)
├── Database:    ✅ PostgreSQL 14 + PgBouncer (31K entries/sec)
└── Distribution: ✅ Auto-update enabled
```

---

## Priority Status Overview

| Priority | Name | Status | WIP Doc |
|----------|------|--------|---------|
| **P17** | LDM LanguageData Manager | 60% | [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md) |
| **P21** | Database Powerhouse | ✅ Complete | [P21_DATABASE_POWERHOUSE.md](docs/wip/P21_DATABASE_POWERHOUSE.md) |
| **P20** | Embedding Model Migration | ✅ Complete | [P20_MODEL_MIGRATION.md](docs/wip/P20_MODEL_MIGRATION.md) |
| **P18** | Database Optimization | ✅ Complete | [P_DB_OPTIMIZATION.md](docs/wip/P_DB_OPTIMIZATION.md) |
| **P13** | Gitea CI/CD + Smart Cache | ✅ Complete | [P13_GITEA_CACHE_PLAN.md](docs/wip/P13_GITEA_CACHE_PLAN.md) |
| **ISSUES** | Bug Fixes | Active | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |

---

## Active Development

### P17: LDM LanguageData Manager (60%)

Professional CAT tool with 5-tier cascade TM search.

**What's Done:**
- ✅ Virtual scroll grid (1M+ rows)
- ✅ File Explorer (projects, folders)
- ✅ Real-time WebSocket sync
- ✅ Basic TM panel + keyboard shortcuts
- ✅ Row locking for multi-user

**What's Next:**
- Phase 7: Full TM System (5-Tier Cascade)
- Phase 8: Nice View (pattern rendering)

**Details:** [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md) | [P17_TM_ARCHITECTURE.md](docs/wip/P17_TM_ARCHITECTURE.md)

---

### Known Issues (0 Open)

All known issues have been resolved. See [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) for history.

**Recently Fixed (2025-12-11):**
- ISSUE-001: Tooltip z-index
- ISSUE-002: File upload progress
- ISSUE-003/004: Tasks button icon + cursor
- ISSUE-005: LDM default app routing

---

## Recently Completed

### P21: Database Powerhouse ✅ (2025-12-10)
- PgBouncer 1.16 - 1000 connections
- COPY TEXT - 31K entries/sec
- PostgreSQL tuned for 32GB RAM

### P20: Embedding Model Migration ✅ (2025-12-09)
- Unified to Qwen3-Embedding-0.6B
- HNSW index for O(log n) search
- 100+ language support

### P13.12: Smart Build Cache v2.0 ✅ (2025-12-09)
- Hash-based invalidation
- Build time: ~1.5 min (from cache)

### P13.11: Gitea Windows Build ✅ (2025-12-09)
- Patched act_runner v15 (NUL byte fix)
- Non-ephemeral mode (6-month token)
- Automated cleanup

---

## Future Priorities

| Priority | Name | Description |
|----------|------|-------------|
| P19 | Platform UI/UX Overhaul | Modern UI, themes, keyboard shortcuts |
| P22 | Performance Monitoring | Real-time dashboards, alerts |
| P23 | Plugin System | Third-party tool integration |

---

## Quick Commands

```bash
# Start servers
python3 server/main.py           # Backend (8888)
cd locaNext && npm run electron:dev  # Desktop app

# Testing
RUN_API_TESTS=1 python3 -m pytest -v

# Build (GitHub)
echo "Build LIGHT vXXXX" >> BUILD_TRIGGER.txt && git push origin main

# Build (Gitea)
echo "Build LIGHT vXXXX" >> GITEA_TRIGGER.txt && git push gitea main
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic exactly, only change UI
2. **Backend is Flawless** - Never modify core without permission
3. **Log Everything** - Use `logger`, never `print()`
4. **Test with Real Data** - No mocks for core functions
5. **Version Before Build** - Run `check_version_unified.py`

---

## Documentation Structure

```
Roadmap.md (THIS FILE)      ← Big picture overview
    │
    └── docs/wip/           ← Detailed task breakdowns
        ├── README.md       ← WIP Hub index
        ├── P17_*.md        ← LDM tasks
        ├── P18_*.md        ← Database optimization
        ├── P20_*.md        ← Model migration
        ├── P21_*.md        ← Database powerhouse
        └── ISSUES_TO_FIX.md ← Bug tracker
```

---

*For detailed history, see [ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)*
*For all tasks, see [docs/wip/README.md](docs/wip/README.md)*
