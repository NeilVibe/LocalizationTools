# CLAUDE.md - LocaNext Navigation Hub

**Version:** 2512122330 | **Status:** 97% Complete | **LDM:** 67%

> **KEEP THIS FILE COMPACT.** Only essential info here. Details go in linked docs.

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Current task?** | [Roadmap.md](Roadmap.md) |
| **Last session context?** | [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **LDM tasks?** | [docs/wip/P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md) |
| **Known bugs?** | [docs/wip/ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **All WIP docs?** | [docs/wip/README.md](docs/wip/README.md) |
| **All docs index?** | [docs/README.md](docs/README.md) |

---

## Glossary

| Term | Meaning |
|------|---------|
| **RM** | Roadmap.md - global priorities |
| **WIP** | docs/wip/*.md - detailed task files |
| **LDM** | Language Data Manager (CAT tool, App #4) |
| **TM** | Translation Memory |
| **FAISS** | Vector index for semantic search |
| **CDP** | Chrome DevTools Protocol |

---

## Architecture

**PostgreSQL ONLY** - No SQLite for LocaNext data.

| PostgreSQL (Shared) | Local Disk (Heavy) |
|---------------------|-------------------|
| LDM rows, TM entries | FAISS indexes |
| Users, sessions | Embeddings (.npy) |
| Telemetry, glossaries | ML models |

- Port 6433 (PgBouncer) → 5432 (PostgreSQL)
- WebSocket for real-time sync
- Row locking for multi-user

**Details:** [docs/deployment/DEPLOYMENT_ARCHITECTURE.md](docs/deployment/DEPLOYMENT_ARCHITECTURE.md)

---

## Critical Rules

### 1. Monolith Code is Sacred
```
RessourcesForCodingTheProject/ scripts are FLAWLESS.
COPY logic exactly. ONLY change UI (tkinter → API).
```
Sources: `XLSTransfer0225.py`, `KRSIMILAR0124.py`, `QuickSearch0818.py`

### 2. Never Modify Backend Without Permission
Only create wrapper layers (API endpoints, GUI).
See: [docs/architecture/BACKEND_PRINCIPLES.md](docs/architecture/BACKEND_PRINCIPLES.md)

### 3. Logging is Mandatory
Use `logger`, NEVER `print()`.
See: [docs/development/LOGGING_PROTOCOL.md](docs/development/LOGGING_PROTOCOL.md)

### 4. Version Check Before Commit
```bash
python3 scripts/check_version_unified.py
```

### 5. WSL Cannot Access Windows CDP
WSL localhost ≠ Windows localhost. Use PowerShell:
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "..."
```
See: [docs/troubleshooting/WINDOWS_TROUBLESHOOTING.md](docs/troubleshooting/WINDOWS_TROUBLESHOOTING.md)

### 6. Always Dual Push
```bash
git push origin main && git push gitea main
```

### 7. Users Never Do Admin Work
Users just launch app and work. All config is admin/IT responsibility.
See: [docs/wip/P23_DATA_FLOW_ARCHITECTURE.md](docs/wip/P23_DATA_FLOW_ARCHITECTURE.md)

---

## Quick Commands

```bash
# Check servers are running (RUN FIRST!)
./scripts/check_servers.sh

# Start ALL servers (PostgreSQL + Backend)
./scripts/start_all_servers.sh

# Start backend only (if PostgreSQL already running)
python3 server/main.py

# Start backend with DEV_MODE (no auth required on localhost)
DEV_MODE=true python3 server/main.py

# Start desktop app
cd locaNext && npm run electron:dev

# Start admin dashboard
cd adminDashboard && npm run dev -- --port 5175

# Run tests (with server)
python3 scripts/create_admin.py && python3 server/main.py &
sleep 5 && RUN_API_TESTS=1 python3 -m pytest -v

# Trigger build
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> BUILD_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## URLs (When Running)

| Service | URL |
|---------|-----|
| Backend | http://localhost:8888 |
| API Docs | http://localhost:8888/docs |
| LocaNext | http://localhost:5176 |
| Admin | http://localhost:5175 |
| Gitea | http://localhost:3000 |

---

## Documentation Map

```
docs/
├── README.md                 # Index
├── getting-started/          # Onboarding
├── architecture/             # Design patterns
├── development/              # Coding guides
├── build/                    # Build & distribution
├── deployment/               # Deploy & ops
├── security/                 # Security guides
├── testing/                  # Test guides
├── troubleshooting/          # Debug guides
├── tools/                    # Tool-specific
├── code-review/              # Code review docs
│   ├── ISSUES_20251212.md    # ← Latest review issues
│   └── CODE_REVIEW_PROTOCOL.md
├── wip/                      # Work in progress
│   ├── SESSION_CONTEXT.md    # ← Last session state
│   ├── P17_LDM_TASKS.md      # ← LDM task tracker
│   └── ISSUES_TO_FIX.md      # ← Known bugs
└── history/                  # Archive
```

**Key Docs:**

| Topic | Document |
|-------|----------|
| Quick start | [docs/getting-started/QUICK_START_GUIDE.md](docs/getting-started/QUICK_START_GUIDE.md) |
| Add new app | [docs/development/ADD_NEW_APP_GUIDE.md](docs/development/ADD_NEW_APP_GUIDE.md) |
| Testing | [docs/testing/DEBUG_AND_TEST_HUB.md](docs/testing/DEBUG_AND_TEST_HUB.md) |
| Build | [docs/build/BUILD_AND_DISTRIBUTION.md](docs/build/BUILD_AND_DISTRIBUTION.md) |
| Security | [docs/security/SECURITY_HARDENING.md](docs/security/SECURITY_HARDENING.md) |
| Windows debug | [docs/troubleshooting/WINDOWS_TROUBLESHOOTING.md](docs/troubleshooting/WINDOWS_TROUBLESHOOTING.md) |

---

## Claude Behavior

1. **Be frank** - If an idea is bad, say so
2. **Cold, independent AI** - Think for yourself, give honest independent opinions
3. **Optimal solutions** - Lead with best approach
4. **Say "doesn't work"** - When it doesn't
5. **Don't command** - Present info, user decides

---

## New Session Checklist

1. **CHECK SERVERS FIRST:** `./scripts/check_servers.sh`
2. If not OK: `./scripts/start_all_servers.sh`
3. Check [Roadmap.md](Roadmap.md) for current priority
4. Check [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) for last state
5. Check [docs/wip/ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) for open bugs
6. Ask user what to work on

See: [docs/development/SERVER_MANAGEMENT.md](docs/development/SERVER_MANAGEMENT.md)

---

## Stats

- **Tests:** 912 (no mocks)
- **Endpoints:** 63+
- **Tools:** 4 (XLSTransfer, QuickSearch, KR Similar, LDM)
- **Database:** PostgreSQL + PgBouncer

---

*Last updated: 2025-12-12 | Hub file - details live in linked docs*
