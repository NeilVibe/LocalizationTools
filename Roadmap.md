# LocaNext - Roadmap & Navigation Hub

**Build:** 298 (v25.1217.2220) | **Updated:** 2025-12-17 22:45 KST | **Status:** 100% Complete | **Open Issues:** 0

---

## Current Status

**Build 298 released. All features complete. Playground ready for testing.**

| Component | Status |
|-----------|--------|
| Standard TM | WORKS |
| XLS Transfer | WORKS |
| KR Similar | WORKS |
| TM Viewer | WORKS |
| TM Export | WORKS |
| TM Confirm | WORKS |
| Global Toasts | WORKS |
| Task Manager | WORKS (22 ops) |

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Session state?** | [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs?** | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **WIP tasks?** | [docs/wip/README.md](docs/wip/README.md) |
| **Enterprise deploy?** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |

---

## Build 298 Features

| Feature | Description |
|---------|-------------|
| **TM Viewer** | Paginated grid, sort, search, inline edit |
| **TM Confirm** | memoQ-style entry confirmation workflow |
| **TM Export** | TEXT/Excel/TMX with column selection |
| **Global Toasts** | Notifications on any page |
| **Metadata Options** | 7 columns in dropdown |

---

## Recently Completed

| What | When |
|------|------|
| Build 298 (TM Viewer, Export, Confirm, Toasts) | 2025-12-17 |
| Lazy import fix (server startup) | 2025-12-17 |
| E2E tests (20 tests, 3 engines) | 2025-12-17 |
| Task Manager (22 operations) | 2025-12-17 |
| Pipeline bug fixes (6 critical) | 2025-12-17 |

---

## Architecture

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Qwen model (local, 2.3GB)     └─ Logs
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback)
```

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Playground install
./scripts/playground_install.sh --launch --auto-login

# Trigger build
echo "Build LIGHT" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| API Docs | http://localhost:8888/docs |
| Gitea | http://172.28.150.120:3000 |
| CDP | http://127.0.0.1:9222 |

---

*Details live in linked docs. This file is navigation only.*
