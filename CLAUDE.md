# CLAUDE.md - LocaNext Navigation Hub

**Version:** 2512191850 | **Build:** 303 | **Next:** 304 | **Issues:** 5

> **KEEP THIS FILE COMPACT.** Details in linked docs.

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Current task?** | [Roadmap.md](Roadmap.md) |
| **Session context?** | [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs?** | [docs/wip/ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **WIP docs?** | [docs/wip/README.md](docs/wip/README.md) |
| **Build → Test protocol?** | [testing_toolkit/MASTER_TEST_PROTOCOL.md](testing_toolkit/MASTER_TEST_PROTOCOL.md) ← START HERE |
| **Node.js CDP tests?** | [testing_toolkit/cdp/README.md](testing_toolkit/cdp/README.md) |
| **Enterprise deploy?** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |
| **All docs?** | [docs/README.md](docs/README.md) |

---

## Glossary

| Term | Meaning |
|------|---------|
| **RM** | Roadmap.md - global priorities |
| **WIP** | docs/wip/*.md - active task files |
| **IL** | Issue List (ISSUES_TO_FIX.md) |
| **LDM** | Language Data Manager (CAT tool, App #4) |
| **TM** | Translation Memory |
| **FAISS** | Vector index for semantic search |
| **CDP** | Chrome DevTools Protocol |
| **Playground** | Windows test: `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground` |

---

## Architecture

```
LocaNext.exe (User PC)          Central PostgreSQL
├─ Embedded Python Backend  ──→  ├─ ALL text data
├─ FAISS indexes (local)         ├─ Users, sessions
├─ Qwen model (local, 2.3GB)     └─ TM entries, logs
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback)
```

---

## Critical Rules

1. **Monolith is Sacred** - Copy `RessourcesForCodingTheProject/` logic exactly
2. **No Backend Mods** - Only wrapper layers (API, GUI)
3. **Logger Only** - Never `print()`, always `logger`
4. **Dual Push** - `git push origin main && git push gitea main`
5. **WSL ↔ Windows** - CDP tests run from Windows PowerShell (WSL2 can't reach Windows localhost)
6. **Fix Everything** - No defer, no excuses, fix all issues

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Start all
./scripts/start_all_servers.sh

# Backend only
python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

# Trigger build
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Playground install (with auto-login)
./scripts/playground_install.sh --launch --auto-login
```

---

## URLs

| Service | URL |
|---------|-----|
| Backend | http://localhost:8888 |
| API Docs | http://localhost:8888/docs |
| Gitea | http://172.28.150.120:3000 |

---

## Documentation

```
testing_toolkit/          # ← PRIMARY TESTING DOCS
├── MASTER_TEST_PROTOCOL.md  ← FULL WORKFLOW: Push→CI→Build→Install→Test
├── cdp/                     # Node.js CDP tests
│   ├── README.md               ← CDP test guide
│   └── *.js                    ← Test scripts
└── README.md                ← Testing overview

docs/
├── wip/                  # Active work
│   ├── SESSION_CONTEXT.md      ← Session state
│   ├── ISSUES_TO_FIX.md        ← Bug tracker
│   └── P25_LDM_UX_OVERHAUL.md  ← 85% done
├── testing/              # Detailed test guides
│   └── PLAYGROUND_INSTALL_PROTOCOL.md
├── enterprise/           # Company deployment
│   └── HUB.md
└── history/              # Archives
```

---

## New Session Checklist

1. `./scripts/check_servers.sh`
2. Read [Roadmap.md](Roadmap.md)
3. Read [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)
4. Check [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)
5. Ask user what to do

---

## Claude Behavior

1. **Be frank** - Bad idea? Say so
2. **Independent** - Give honest opinions
3. **Optimal first** - Best approach first
4. **Don't command** - Present info, user decides

---

## Stats

- **Build:** 303 (v25.1219.1829) | Next: 304
- **Tests:** ~273 in CI
- **Endpoints:** 65+
- **Tools:** 4 (XLSTransfer, QuickSearch, KR Similar, LDM)
- **Open Issues:** 5 (3 UI/UX, 2 decisions)

---

*Last updated: 2025-12-19 18:50 | Hub file - details in linked docs*
