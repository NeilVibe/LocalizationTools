# LocaNext - Roadmap & Navigation Hub

**Build:** 285 | **Updated:** 2025-12-16 | **Status:** 97% Complete

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Start of session?** | [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Known bugs?** | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **WIP tasks?** | [docs/wip/README.md](docs/wip/README.md) |
| **How to do X?** | [docs/README.md](docs/README.md) |

---

## Current Status

```
LocaNext v25.1216.0900
├── Backend:     ✅ PostgreSQL + SQLite offline
├── Frontend:    ✅ Electron 39 + Svelte 5 + Vite 7
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── CI/CD:       ✅ 285 tests + smoke tests (GitHub + Gitea)
├── Offline:     ✅ Auto-fallback + indicator (needs prod test)
└── Installer:   ⚠️ Fixes ready, need build
```

---

## Priority Queue

### NOW: Bug Fixes (6 Open)

| Priority | Issue | Description |
|----------|-------|-------------|
| HIGH | BUG-009 | Installer no details (fix ready) |
| HIGH | BUG-010 | First-run window stuck (fix ready) |
| MEDIUM | UI-001 to UI-004 | UI/UX cleanup |

**Recently Implemented (Need Production Testing):**
- BUG-007: Offline auto-fallback (3s timeout, SQLite fallback)
- BUG-008: Online/Offline indicator + "Go Online" button

**Details:** [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)

### NEXT: P25 LDM UX (85% done)

- TM matching (Qwen + FAISS)
- QA checks
- Custom pickers

**Details:** [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md)

---

## Recently Completed

| What | When | Details |
|------|------|---------|
| Connectivity Tests | 2025-12-16 | 26 new tests for offline/online mode |
| P35 Svelte 5 Migration | 2025-12-16 | Fixed BUG-011 (connection issue) |
| CI Smoke Tests | 2025-12-16 | Svelte 5 + **PostgreSQL verification** |
| P34 Resource Protocol | 2025-12-16 | Zombie cleanup docs |
| CI Unification | 2025-12-15 | 285 tests, GitHub + Gitea |
| P33 Offline Mode | 2025-12-15 | SQLite fallback + auto-fallback |
| P32 Code Review | 2025-12-15 | 9/11 issues fixed |
| P28 NSIS Installer | 2025-12-14 | electron-builder NSIS |

---

## Architecture

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Qwen model (local, 2.3GB)     └─ Logs, telemetry
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-login)
```

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Start servers
./scripts/start_all_servers.sh

# Build frontend
cd locaNext && npm run build

# Run tests
python3 -m pytest tests/unit/ tests/integration/ -v

# Trigger CI build
echo "Build LIGHT" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| API Docs | http://localhost:8888/docs |
| Gitea | http://localhost:3000 |
| Admin Dashboard | http://localhost:5175 |

---

## Documentation Index

```
docs/
├── wip/                      # Active work
│   ├── SESSION_CONTEXT.md    # ← START HERE (last session state)
│   ├── ISSUES_TO_FIX.md      # ← Bug tracker
│   └── README.md             # ← WIP hub
├── getting-started/          # Onboarding
├── architecture/             # Design docs
├── development/              # Coding guides
├── build/                    # Build & CI
├── testing/                  # Test guides
└── troubleshooting/          # Debug help
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic from `RessourcesForCodingTheProject/`, only change UI
2. **Central = Text, Local = Heavy** - PostgreSQL for data, local for FAISS/Qwen
3. **Log Everything** - Use `logger`, never `print()`
4. **Fix Everything** - No deferring, no excuses, fix ALL issues

---

*Details live in linked docs. This file is navigation only.*
