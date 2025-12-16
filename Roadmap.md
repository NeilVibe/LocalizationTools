# LocaNext - Development Roadmap

**Version**: 2512160100 | **Updated**: 2025-12-16 01:00 | **Status**: 8 Issues Open

> **Session Context**: [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)
> **Issues**: [docs/wip/ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)
> **WIP Tasks**: [docs/wip/README.md](docs/wip/README.md)

---

## Current Status

```
LocaNext v2512160100
├── Backend:     ✅ Working (PostgreSQL)
├── Frontend:    ✅ Electron 39 + Svelte 5 + Vite 7
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar, LDM
├── CI/CD:       ✅ 255 tests unified (GitHub + Gitea)
├── Offline:     🔴 NOT WORKING - No auto-fallback
└── Distribution: ⚠️ Installer issues (fixes ready)
```

---

## Current Priority: BUG FIXES (CRITICAL)

**User testing revealed 8 issues.** Must fix before continuing P25.

### CRITICAL (Blocking)

| Issue | Description | Status |
|-------|-------------|--------|
| BUG-007 | Offline mode auto-fallback (3s timeout) | To Fix |
| BUG-008 | Online/Offline mode indicator | To Fix |

### HIGH (Fixes Ready - Need Build)

| Issue | Description | Status |
|-------|-------------|--------|
| BUG-009 | Installer shows no details | Fix Applied |
| BUG-010 | First-run window not closing | Fix Applied |

### MEDIUM (UI/UX)

| Issue | Description | Status |
|-------|-------------|--------|
| UI-001 | Remove light/dark toggle | To Fix |
| UI-002 | Reorganize Preferences | To Fix |
| UI-003 | TM activation via modal | To Fix |
| UI-004 | Remove TM from grid | To Fix |

**Details:** [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)

---

## After Bug Fixes: P25 LDM UX

- TM matching (Qwen + FAISS 5-tier)
- QA checks (Word Check, Line Check)
- Custom file pickers

**Details:** [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md)

---

## Completed (Recent)

| Priority | What | Status |
|----------|------|--------|
| P34 | Resource Check Protocol (Docker cleanup) | ✅ |
| CI | Unified GitHub + Gitea (255 tests) | ✅ |
| P33 | Offline Mode + Auto-Login (CI only) | ✅ |
| P32 | Code Review (9/11 fixed) | ✅ |
| P28 | NSIS Installer | ✅ |
| P27 | Svelte 5 + Modern Stack | ✅ |

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
OFFLINE: SQLite (single-user, auto-login) ← NEEDS FIX: Auto-fallback
```

---

## Quick Commands

```bash
# Start servers
./scripts/start_all_servers.sh

# Check servers
./scripts/check_servers.sh

# Build frontend
cd locaNext && npm run build

# Run tests
python3 -m pytest tests/unit/ tests/integration/ -v

# Test offline mode
DATABASE_MODE=sqlite python3 server/main.py
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic exactly, only change UI
2. **Central = Text, Local = Heavy** - PostgreSQL for data, local for FAISS/Qwen
3. **Log Everything** - Use `logger`, never `print()`
4. **Fix Everything** - No deferring, no excuses

---

*For session details: [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)*
