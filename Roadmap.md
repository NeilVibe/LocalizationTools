# LocaNext - Development Roadmap

**Version**: 2512152100 | **Updated**: 2025-12-15 21:00 | **Status**: P33 Build 281 In Progress

> **Session Context**: [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)
> **WIP Tasks**: [docs/wip/README.md](docs/wip/README.md)
> **History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)

---

## Current Status

```
LocaNext v2512151600
├── Backend:     ✅ Working + SQLite offline mode (auto-detect)
├── Frontend:    ✅ Electron 39 + Svelte 5 + Vite 7
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── Database:    ✅ PostgreSQL (online) + SQLite (offline auto-fallback)
├── CI/CD:       ✅ 256 real tests (Linux + Windows smoke)
├── Offline:     ✅ Full structure preservation + Sync
└── Distribution: ✅ NSIS installer works
```

---

## Current Priority: P33 Offline Mode (Build 281 In Progress)

| Phase | Status | What |
|-------|--------|------|
| 1 | ✅ | SQLite backend (FlexibleJSON, auto-fallback) |
| 2 | ✅ | Auto-detection (PostgreSQL unreachable → SQLite) |
| 3 | ✅ | Tabbed sidebar (Files/TM tabs) |
| 4 | ✅ | Online/Offline badges in toolbar |
| 5 | ✅ | Go Online + Upload to Server modal |
| 6 | ✅ | CI overhaul (256 real tests) |
| 7 | ✅ | extra_data JSONB + Sync endpoints |
| 8 | ✅ | Windows smoke test uses auto-detect |
| 9 | 🔄 | **Offline auto-login (LOCAL user + auto_token)** - Build 281 |

**NEW - Offline Auto-Access (Build 281):**
- Backend creates `LOCAL` user automatically in SQLite mode
- Health endpoint returns `auto_token` for instant login
- Frontend skips login screen in offline mode
- No credentials needed - straight to app

**Testing Architecture:**
- **Linux CI:** 257 tests with real PostgreSQL
- **Windows CI:** Installer + Backend smoke test (SQLite + LOCAL auto-login)
- **Manual:** ULTIMATE smoke test (CDP) for full E2E

**Check Build 281:**
```bash
curl -s "http://localhost:3000/neilvibe/LocaNext/actions/runs/281/jobs/2/logs" | grep -E "(PASS|FAIL|smoke)" | tail -10
```

**Details:** [P33_OFFLINE_MODE_CI_OVERHAUL.md](docs/wip/P33_OFFLINE_MODE_CI_OVERHAUL.md)

---

## Next Priorities

### P32: Code Review Issues (LOW PRIORITY)

10 issues remaining in `server/tools/ldm/api.py`:
- ~~1 CRITICAL (SQL injection)~~ ✅ FIXED
- 1 CRITICAL (response format)
- 3 HIGH (deprecated asyncio)
- 5 MEDIUM/LOW

**Do after P33 build verification.**

**Details:** [docs/code-review/ISSUES_20251215_LDM_API.md](docs/code-review/ISSUES_20251215_LDM_API.md)

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
