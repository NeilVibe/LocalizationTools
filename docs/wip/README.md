# Work In Progress (WIP) Hub

**Purpose:** Track active tasks and link to detailed docs
**Updated:** 2025-12-16 09:00 KST

---

## Start Here

| Need | Go To |
|------|-------|
| **Last session state?** | [SESSION_CONTEXT.md](SESSION_CONTEXT.md) |
| **Bug list?** | [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) |
| **High-level roadmap?** | [Roadmap.md](../../Roadmap.md) |

---

## Current Status

```
Build 284 Running (2025-12-16)
├── P35 Svelte 5 Migration: ✅ DONE (BUG-011 fixed)
├── CI Smoke Tests: ✅ Added (check_svelte_build.sh)
├── Open Issues: 8 (2 CRITICAL, 2 HIGH, 4 MEDIUM)
└── Next: BUG-007/008 (offline mode)
```

---

## Priority Queue

### NOW: Bug Fixes

| Priority | Issue | Description | Status |
|----------|-------|-------------|--------|
| CRITICAL | BUG-007 | Offline mode auto-fallback | TO FIX |
| CRITICAL | BUG-008 | Online/Offline indicator | TO FIX |
| HIGH | BUG-009 | Installer no details | Fix Ready |
| HIGH | BUG-010 | First-run window stuck | Fix Ready |
| MEDIUM | UI-001-004 | UI/UX cleanup | TO FIX |

### NEXT: P25 LDM UX (Paused)

- TM matching (Qwen + FAISS)
- QA checks
- Custom pickers

---

## Document Index

### Active
| Doc | Status | Purpose |
|-----|--------|---------|
| [SESSION_CONTEXT.md](SESSION_CONTEXT.md) | Active | Claude handoff state |
| [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Active | Bug tracker |
| [P35_SVELTE5_MIGRATION.md](P35_SVELTE5_MIGRATION.md) | ✅ Done | Svelte 5 runes migration |
| [P34_RESOURCE_CHECK_PROTOCOL.md](P34_RESOURCE_CHECK_PROTOCOL.md) | Reference | Zombie process cleanup |

### Paused
| Doc | Status | Purpose |
|-----|--------|---------|
| [P25_LDM_UX_OVERHAUL.md](P25_LDM_UX_OVERHAUL.md) | 85% | TM matching, QA checks |
| [P17_LDM_TASKS.md](P17_LDM_TASKS.md) | 80% | LDM features |

### Completed
| Doc | Purpose |
|-----|---------|
| [P33_OFFLINE_MODE_CI_OVERHAUL.md](P33_OFFLINE_MODE_CI_OVERHAUL.md) | Offline mode + CI |
| [P27_STACK_MODERNIZATION.md](P27_STACK_MODERNIZATION.md) | Svelte 5 + Vite 7 |
| [P17_TM_ARCHITECTURE.md](P17_TM_ARCHITECTURE.md) | TM system design |

---

## Recently Completed

| Date | What | Details |
|------|------|---------|
| 2025-12-16 | P35 Svelte 5 | BUG-011 fixed, CI smoke test added |
| 2025-12-16 | P34 Resources | Zombie cleanup protocol |
| 2025-12-15 | CI Unification | 255 tests, GitHub + Gitea |
| 2025-12-15 | P33 Offline | SQLite fallback (CI only) |
| 2025-12-15 | P32 Code Review | 9/11 issues fixed |

---

## Quick Reference

### Check Build Status
```bash
# Gitea UI
http://localhost:3000/neilvibe/LocaNext/actions

# API
curl -s http://localhost:3000/api/v1/repos/neilvibe/LocaNext/actions/runners
```

### Trigger New Build
```bash
echo "Build LIGHT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

### Run Local Tests
```bash
./scripts/check_svelte_build.sh      # Svelte 5 check
python3 -m pytest tests/unit/ -v     # Unit tests
```

---

*Last Updated: 2025-12-16 09:00 KST*
