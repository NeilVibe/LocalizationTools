# LocaNext - Development Roadmap

**Version**: 2512140245 | **Updated**: 2025-12-14 | **Status**: Production Ready

> **Full History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)
> **Detailed Tasks**: [docs/wip/README.md](docs/wip/README.md) (WIP Hub)
> **Session Context**: [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)

---

## Current Status

```
LocaNext v2512140245
├── Backend:     ✅ 63+ API endpoints, async, WebSocket
├── Frontend:    ✅ Electron + Svelte (LocaNext Desktop)
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar + LDM 80%
├── Tests:       ✅ 912 total (595 unit pass, no mocks)
├── Security:    ⚠️ 39+ vulnerabilities identified (fix in progress)
├── CI/CD:       ✅ GitHub Actions + Gitea (hardened 2025-12-14)
├── Database:    ✅ PostgreSQL + PgBouncer (NO SQLite!)
└── Distribution: ✅ Auto-update enabled
```

---

## Priority Status Overview

| # | Priority | Name | Status | Doc |
|---|----------|------|--------|-----|
| **1** | P26 | Security Vulnerability Fix | 🔨 0% | [SECURITY_FIX_PLAN.md](docs/wip/SECURITY_FIX_PLAN.md) |
| 2 | P25 | LDM UX Overhaul | 🔨 85% | [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md) |
| 3 | P24 | Server Status Dashboard | ✅ Complete | [P24_STATUS_DASHBOARD.md](docs/wip/P24_STATUS_DASHBOARD.md) |
| 4 | P17 | LDM LanguageData Manager | 80% | [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md) |
| - | CI/CD | Hardening | ✅ Complete | Self-healing admin, robust builds |
| - | CODE REVIEW | Review 20251212 | ✅ CLOSED | [history/](docs/code-review/history/) |
| - | P22 | SQLite Removal | ✅ Phase 1 | [P22_PRODUCTION_PARITY.md](docs/wip/P22_PRODUCTION_PARITY.md) |
| - | P21 | Database Powerhouse | ✅ Complete | [P21_DATABASE_POWERHOUSE.md](docs/wip/P21_DATABASE_POWERHOUSE.md) |
| - | ISSUES | Bug Fixes | ✅ All Fixed | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |

---

## Active Development

### P26: Security Vulnerability Remediation (Priority #1)

**Status:** 0% | **Audit Complete** | **Fix Plan Ready**

39+ vulnerabilities identified across pip and npm dependencies. Incremental fix approach to avoid breaking changes.

**Vulnerability Summary:**

| Source | Total | Critical | High | Moderate | Low |
|--------|-------|----------|------|----------|-----|
| pip    | 28+   | 3        | ~7   | ~15      | ~3  |
| npm    | 11    | 0        | 1    | 7        | 3   |

**Critical (Fix ASAP):**
- **cryptography 3.4.8 → 42.0.2** - 8 CVEs, handles JWT/password hashing
- **starlette 0.38.6 → 0.47.2** - Path traversal, request smuggling
- **python-socketio 5.11.0 → 5.14.0** - WebSocket auth bypass

**Incremental Fix Plan:**
```
Phase 1: Safe pip fixes (no breaking changes)
  → requests, python-jose, python-multipart, oauthlib, configobj
  → Run tests → Verify no conflicts

Phase 2: Safe npm fixes
  → npm audit fix (glob, js-yaml)
  → Run tests → Verify no conflicts

Phase 3: Moderate risk (test thoroughly)
  → cryptography, starlette, python-socketio
  → Run FULL test suite → Test auth flows manually

Phase 4: High risk (major testing)
  → torch upgrade (test embeddings!)
  → electron upgrade (test desktop app!)
  → Full regression test

Phase 5: System level (coordinate with IT)
  → urllib3 (Ubuntu system package)
  → May need virtualenv or OS upgrade
```

**Documentation:**
- Full Audit: [SECURITY_VULNERABILITIES.md](docs/wip/SECURITY_VULNERABILITIES.md)
- Fix Plan: [SECURITY_FIX_PLAN.md](docs/wip/SECURITY_FIX_PLAN.md)

---

### P25: LDM UX Overhaul (85% Complete) - Priority #2

Comprehensive UX improvements based on user feedback.

**Phase 1: Bug Fixes ✅**
- ✅ Target lock blocking editing (BUG-002)
- ✅ Upload tooltip z-index (BUG-003)
- ✅ Search bar icon requirement (BUG-004)
- ✅ Go to row removed (BUG-001)

**Phase 2: Grid Simplification ✅**
- ✅ Status column REMOVED → Using cell colors instead
- ✅ Default: Source + Target columns only
- ✅ Cell colors: teal=translated, blue=reviewed, green=approved

**Phase 3: Edit Modal Redesign ✅**
- ✅ BIG modal (85% width/height)
- ✅ Two-column layout: Source/Target left, TM panel right
- ✅ Shortcut bar at top (Ctrl+S, Ctrl+T, Tab, Esc)
- ✅ Keyboard shortcuts working (Ctrl+S=Confirm, Ctrl+T=Translate)

**Phase 4: Preferences Menu ✅**
- ✅ Column toggles: Index Number, String ID, Reference, TM
- ✅ TM selector (choose active TM)
- ✅ Reference file selector + match mode
- ✅ Settings persist in localStorage

**Phase 5: Download/Export ✅**
- ✅ Download endpoint + frontend menu
- ✅ Status filters (all, translated, reviewed)
- ✅ TXT/XML/Excel export

**Phase 6: Right-Click Context Menu ✅**
- ✅ Already exists in FileExplorer.svelte
- ✅ Download, Register as TM options

**Phase 7: Tasks Panel** (Existing)
- ✅ TaskManager.svelte with WebSocket updates
- ✅ Real-time progress tracking

**Phase 8: Reference Column ✅**
- ✅ Reference column in grid
- ✅ Load reference from project file
- ✅ Match by StringID or StringID+Source
- ✅ Preferences UI for reference settings

**Phase 9: TM Integration ✅**
- ✅ TMManager.svelte - list, delete, build indexes
- ✅ TMUploadModal.svelte - upload TM files
- ✅ TM Results column in grid (shows matches on hover)
- ✅ TM selector in Preferences

**Phase 10: TM Matching + QA Systems** (IN PROGRESS)

Two separate systems, both built from TM upload:

```
SYSTEM 1: TM MATCHING (WebTranslatorNew)
├── QWEN Embeddings + FAISS + PKL
├── 5-Tier Cascade + Single Threshold (92%)
├── Display: Perfect tiers = show if exists, Embedding = top 3
└── Purpose: Suggestions in Edit Modal

+ NPC (Neil's Probabilistic Check)
├── Reuses TM results (no extra Source matching)
├── Cosine similarity: User Target vs TM Targets
├── Threshold: 80% (lenient)
└── Purpose: Verify translation consistency

SYSTEM 2: QA CHECKS (QuickSearch)
├── Word Check: Aho-Corasick (scans full text, finds all terms)
├── Line Check: Dict lookup (split by \n, lookup each line)
└── Purpose: Find errors/inconsistencies
```

**Key Architecture:**
- Universal newline normalization (`\n`, `\\n`, `<br/>`, `&lt;br/&gt;` → `\n`)
- DB stores canonical `\n` format
- Embed BOTH Source AND Target (for NPC)

**TM DB Sync:**
```
DB = CENTRAL (always up-to-date)
├── Re-upload TM → INSERT/UPDATE/DELETE instantly
├── Ctrl+S confirm → INSERT or UPDATE (if TM active)
└── Multi-user: everyone updates same DB

FAISS = LOCAL (synced on demand)
├── [Synchronize TM] button
├── Pull DB → diff → embed new/changed only
└── Rebuild FAISS, Aho-Corasick, Line Dict
```

**Remaining Implementation:**
- [ ] TM DB Sync: 3 triggers (re-upload, Ctrl+S, [Synchronize TM])
- [ ] SYSTEM 1: QWEN + FAISS + 5-Tier (92% threshold)
- [ ] NPC: [NPC] button + Target embedding + cosine sim (80%)
- [ ] SYSTEM 2 Word Check: Aho-Corasick automaton (pyahocorasick)
- [ ] SYSTEM 2 Line Check: Dict lookup per line
- [ ] Universal newline normalizer
- [ ] QA panel in Edit Modal

**Skipped:** Spell/Grammar check (no MIT multi-lang library)

**Details:** [P25_LDM_UX_OVERHAUL.md](docs/wip/P25_LDM_UX_OVERHAUL.md)

---

### P24: Server Status Dashboard ✅ COMPLETE

Real-time health monitoring for Central Server.

**Backend API:**
- ✅ `GET /api/health/simple` - green/orange/red status
- ✅ `GET /api/health/status` - detailed metrics (auth required)
- ✅ `GET /api/health/ping` - ultra-simple ping/pong

**Frontend:**
- ✅ ServerStatus.svelte - visual health modal
- ✅ Auto-refresh every 30 seconds
- ✅ API, Database, WebSocket indicators

**Details:** [P24_STATUS_DASHBOARD.md](docs/wip/P24_STATUS_DASHBOARD.md)

---

### P17: LDM LanguageData Manager (80%)

Professional CAT tool with real-time collaboration.

**What's Done:**
- ✅ Virtual scroll grid (1M+ rows)
- ✅ File Explorer (projects, folders)
- ✅ Real-time WebSocket sync + Row locking
- ✅ TM Database + TMManager + TMIndexer
- ✅ TM Upload UI (TMManager, TMUploadModal)
- ✅ Reference column + TM column
- ✅ Preferences with TM/Reference selectors

**What's Next:**
- Custom Excel picker (column selection)
- Custom XML picker (attribute selection)
- QA: Glossary, Inconsistency, Numbers checks

**Details:** [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md)

---

### Known Issues ✅ ALL FIXED

| ID | Status | Description |
|----|--------|-------------|
| ~~BUG-001~~ | ✅ Fixed | Go to row removed |
| ~~BUG-002~~ | ✅ Fixed | Target lock blocking editing |
| ~~BUG-003~~ | ✅ Fixed | Upload tooltip z-index |
| ~~BUG-004~~ | ✅ Fixed | Search bar requires icon click |
| ~~ISSUE-011~~ | ✅ Fixed | TM Upload UI (TMManager, TMUploadModal) |
| ~~ISSUE-013~~ | ✅ Fixed | WebSocket locking re-enabled |

**Details:** [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Development (localhost)          │
├─────────────────────────────────────────┤
│  LocaNext Desktop                       │
│       ↓                                 │
│  FastAPI Backend (localhost:8888)       │
│       ↓                                 │
│  PostgreSQL (localhost:5432)            │
│       ↓                                 │
│  Local Indexes (FAISS, embeddings)      │
└─────────────────────────────────────────┘

Central = PostgreSQL (text data)
Local = Heavy processing (FAISS, ML - rebuildable)
```

---

## Recently Completed (2025-12-14)

### CI/CD Hardening ✅
All "forever" fixes - eliminated failure modes entirely:
- **Server persistence:** `nohup` + `disown` for background server in CI
- **Fast startup:** Lazy import SentenceTransformer (28s → 4.2s)
- **Self-healing admin:** Auto-reset credentials if corrupted by tests
- **Robust Windows build:** Use env vars, no network calls for version

### Security Audit ✅
- Full vulnerability scan of pip + npm dependencies
- 39+ vulnerabilities documented with CVE details
- Prioritized fix plan created (5 phases)
- See: `docs/wip/SECURITY_VULNERABILITIES.md`, `docs/wip/SECURITY_FIX_PLAN.md`

### P25 Phases 6-9 ✅ (2025-12-12)
- Phase 6: Right-click menu (already existed)
- Phase 8: Reference column with file selector + match modes
- Phase 9: TM integration with TMManager, TMUploadModal, TM column
- Preferences enhanced: TM selector, Reference selector

### P24: Server Status Dashboard ✅
- health.py API (simple, status, ping endpoints)
- ServerStatus.svelte modal
- LDM toolbar integration

---

## Quick Commands

```bash
# Start servers
./scripts/start_all_servers.sh
# OR manually:
python3 server/main.py

# Start frontend
cd locaNext && npm run electron:dev

# Testing
python3 -m pytest tests/unit/ -v  # 595 tests

# Check session context
cat docs/wip/SESSION_CONTEXT.md
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic exactly, only change UI
2. **PostgreSQL Only** - No SQLite in LocaNext core
3. **Central = Text, Local = Heavy** - Data architecture
4. **Log Everything** - Use `logger`, never `print()`
5. **localhost OK for dev** - Server URL config is for production

---

*For session context, see [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)*
