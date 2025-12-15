# LocaNext - Development Roadmap

**Version**: 2512162245 | **Updated**: 2025-12-16 22:45 | **Status**: Build 283 ✅ Unified CI

> **Session Context**: [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)
> **WIP Tasks**: [docs/wip/README.md](docs/wip/README.md)
> **History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)

---

## Current Status

```
LocaNext v2512162245
├── Backend:     ✅ Working + SQLite offline mode (auto-login)
├── Frontend:    ✅ Electron 39 + Svelte 5 + Vite 7
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── Database:    ✅ PostgreSQL (online) + SQLite (offline auto-fallback)
├── CI/CD:       ✅ 255 tests unified (GitHub + Gitea identical)
├── Offline:     ✅ Full offline mode with auto-login
└── Distribution: ✅ NSIS installer works
```

---

## Current Priority: P25 LDM UX (Next)

**CI Unified + P33 + P32: ✅ COMPLETE** (Build 283 passed)
- Unified CI: GitHub and Gitea run identical 255 tests
- Linux: PostgreSQL (online mode) - 255 tests pass
- Windows: SQLite smoke test (offline mode) - auto-login works
- Code review: 9/11 issues fixed

**Next:** P25 LDM UX (85% complete)
- TM matching (Qwen + FAISS 5-tier)
- QA checks (Word Check, Line Check)
- Custom file pickers

---

## Next Priorities

### P25: LDM UX (85% Complete)

- TM matching (Qwen + FAISS 5-tier)
- QA checks (Word Check, Line Check)
- Custom file pickers

**Details:** [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md)

---

## Completed (Recent)

| Priority | What | Status |
|----------|------|--------|
| CI | Unified GitHub + Gitea (255 tests) | ✅ |
| P33 | Offline Mode + Auto-Login | ✅ |
| P32 | Code Review (9/11 fixed) | ✅ |
| P28 | NSIS Installer | ✅ |
| P27 | Svelte 5 + Modern Stack | ✅ |
| P26 | Security Vulnerabilities | ✅ |

---

## Architecture

```
LocaNext.exe (User PC)              Central PostgreSQL
├─ Electron + Svelte 5          →   ├─ All text data
├─ Embedded Python Backend          ├─ Users, sessions
├─ FAISS indexes (local)            ├─ LDM rows, TM entries
├─ Qwen model (local)               └─ Logs, telemetry
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-login, CI testing)
```

---

## Quick Commands

```bash
# Start servers
./scripts/start_all_servers.sh

# Build frontend
cd locaNext && npm run build

# Run tests (unified suite)
python3 -m pytest tests/unit/ tests/integration/ tests/security/ -v

# Test SQLite mode
DATABASE_MODE=sqlite python3 server/main.py
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic exactly, only change UI
2. **Central = Text, Local = Heavy** - PostgreSQL for data, local for FAISS/Qwen
3. **Log Everything** - Use `logger`, never `print()`
4. **Real Tests Only** - No mocks, TestClient with real API calls

---

*For session details: [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)*
