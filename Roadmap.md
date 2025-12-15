# LocaNext - Development Roadmap

**Version**: 2512160600 | **Updated**: 2025-12-16 06:00 | **Status**: P33 Complete, P32 Next

> **Session Context**: [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)
> **WIP Tasks**: [docs/wip/README.md](docs/wip/README.md)
> **History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)

---

## Current Status

```
LocaNext v2512160600
├── Backend:     ✅ Working + SQLite offline mode (auto-detect)
├── Frontend:    ✅ Electron 39 + Svelte 5 + Vite 7
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── Database:    ✅ PostgreSQL (online) + SQLite (offline auto-fallback)
├── CI/CD:       ✅ 256 real tests (Linux + Windows smoke)
├── Offline:     ✅ Full offline mode with auto-login
└── Distribution: ✅ NSIS installer works
```

---

## Current Priority: Build Verification

**P32 Code Review: ✅ COMPLETE** (9/11 fixed, 2 LOW deferred)
- All CRITICAL, HIGH, MEDIUM issues fixed
- [Details](docs/code-review/ISSUES_20251215_LDM_API.md)

**P33 Smoke Test:** Fixed IPv4/IPv6 bug, awaiting build verification

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
| P33 | Offline Mode + CI Overhaul | 100% ✅ |
| P28 | NSIS Installer | ✅ |
| P27 | Svelte 5 + Modern Stack | ✅ |
| P26 | Security Vulnerabilities | ✅ |
| P24 | Server Status Dashboard | ✅ |

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
OFFLINE: SQLite (single-user, CI testing)
```

---

## Quick Commands

```bash
# Start servers
./scripts/start_all_servers.sh

# Build frontend
cd locaNext && npm run build

# Run tests
python3 -m pytest tests/integration/test_api_true_simulation.py tests/security/ -v

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
