# LocaNext - Roadmap

**Build:** 298 (v25.1217.2220) | **Updated:** 2025-12-18 | **Status:** 100% Complete | **Open Issues:** 0

---

## Current Status

All components operational. No active bugs.

| Component | Status |
|-----------|--------|
| LDM (Language Data Manager) | WORKS |
| XLS Transfer | WORKS |
| Quick Search | WORKS |
| KR Similar | WORKS |

---

## Future Vision: LDM as Mother App

**Goal:** Progressively merge monolith features into LDM (Svelte 5).

```
Current Architecture:
┌─────────────────────────────────────────────────────┐
│  LocaNext (Electron + Svelte 5)                     │
│  ├── LDM ─────────── Main app (growing)             │
│  ├── XLS Transfer ── Standalone tool                │
│  ├── Quick Search ── Standalone tool                │
│  └── KR Similar ──── Standalone tool                │
└─────────────────────────────────────────────────────┘

Future Architecture:
┌─────────────────────────────────────────────────────┐
│  LocaNext (Electron + Svelte 5)                     │
│  ├── LDM ─────────── Mother app (all features)      │
│  │   ├── File Management                            │
│  │   ├── TM Management (done)                       │
│  │   ├── Pretranslation (done)                      │
│  │   ├── QA Checks (from QuickSearch - done)        │
│  │   ├── Glossary Extraction (done)                 │
│  │   ├── Batch Operations (future)                  │
│  │   ├── Reports & Analytics (future)              │
│  │   └── ... more monolith features                 │
│  │                                                  │
│  └── Legacy Menu ─── Access to standalone tools     │
│      ├── XLS Transfer                               │
│      ├── Quick Search                               │
│      └── KR Similar                                 │
└─────────────────────────────────────────────────────┘
```

### Already Merged into LDM
- TM Management (viewer, export, confirm)
- Pretranslation pipeline (3 engines)
- QA checks (from Quick Search)
- Glossary extraction
- Task Manager (22 operations)

### Future Candidates
- Batch file operations
- Advanced reporting
- More monolith functions as needed

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Session state?** | [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs?** | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **CDP Testing?** | [testing_toolkit/cdp/README.md](testing_toolkit/cdp/README.md) |
| **Enterprise?** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |
| **History?** | [docs/history/](docs/history/) |

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
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| Gitea | http://172.28.150.120:3000 |
| CDP | http://127.0.0.1:9222 |

---

*Build 298 history: [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)*
