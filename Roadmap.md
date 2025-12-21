# LocaNext - Roadmap

**Build:** 315 (PENDING) | **Updated:** 2025-12-21 | **Status:** CI/CD Overhaul

---

## Current Status

All components operational. CI/CD cleaned up and enhanced. GitHub build in progress.

| Component | Status |
|-----------|--------|
| LDM (Language Data Manager) | WORKS |
| XLS Transfer | WORKS |
| Quick Search | WORKS |
| KR Similar | WORKS |
| CI/CD (Gitea + GitHub) | ENHANCED |

---

## Recent Completed Items

| Build | Tasks Completed |
|-------|-----------------|
| 315 | CI/CD cleanup, fresh start, test fix |
| 314 | UI-047 (TM status fix) |
| 312 | UI-045 (PresenceBar tooltip) |
| 311 | UI-044 (resizable columns) |
| 310 | UI-042/043 (simplified PresenceBar) |
| 308-309 | Major UI/UX cleanup (10 fixes) |
| 307 | BUG-031 (TM upload fix), Q-001 live-tested |

---

## CI/CD Build Modes

### Current Modes

| Mode | Trigger | What It Does |
|------|---------|--------------|
| `Build LIGHT` | Daily dev | ~285 tests, ~150MB installer, model downloads on first launch |
| `Build FULL` | Releases | ~285 tests, ~2GB installer, includes AI model |
| `TROUBLESHOOT` | Debug | Resume from checkpoint, iterative fixing |

### Proposed Enhancement (TODO)

| Mode | Tests | Installer | Use Case |
|------|-------|-----------|----------|
| `Build LIGHT` | ~285 essential | ~150MB | Daily development |
| `Build FULL` | ~285 essential | ~2GB+ | **OFFLINE-READY** - All deps + model + everything bundled |
| `Build TEST` | ALL (1500+) | No installer | Pre-release QA, comprehensive coverage |

**`Build FULL` Goal:** True offline installer - NO internet needed after install:
- All Python dependencies bundled
- Qwen model (2.3GB) included
- Model2Vec included
- VC++ Redistributable bundled
- Everything runs immediately, zero downloads

**`Build TEST` Goal:** Run every single test for maximum quality assurance before releases.

---

## P36: CI/CD Test Overhaul (TODO)

Reorganize tests into **beautiful blocks** for clear pipeline visualization.

| Block | Purpose | Status |
|-------|---------|--------|
| `db/` | Database tests | TODO |
| `auth/` | Authentication | TODO |
| `network/` | WebSocket, HTTP | TODO |
| `security/` | JWT, CORS, XSS | EXISTS |
| `processing/` | TM, embeddings, FAISS | TODO |
| `tools/` | KR Similar, QuickSearch, XLS | TODO |
| `logging/` | Server/client logging | TODO |
| `ui/` | API responses, events | TODO |
| `performance/` | Latency, throughput | NEW |

**Current:** 78 files, 1357 tests (scattered)
**Goal:** Organized blocks with clear coverage

**Details:** [P36_CICD_TEST_OVERHAUL.md](docs/wip/P36_CICD_TEST_OVERHAUL.md)

---

## CI/CD Discovery (Build 315)

| Platform | Test Strategy | Tests Run |
|----------|---------------|-----------|
| **Gitea** | Curated essential list | ~285 tests |
| **GitHub** | All unit/integration/e2e | ~500+ tests |

GitHub runs more comprehensive tests - caught broken `test_npc.py` that Gitea skipped!

---

## Architecture: Embedding Engines

**Important:** Different tools use different engines for good reasons.

| Tool | Engine | Why |
|------|--------|-----|
| **LDM TM Search** | Model2Vec (default) / Qwen (opt-in) | Real-time needs speed |
| **LDM Standard Pretranslation** | Model2Vec / Qwen (user choice) | Follows user toggle |
| **KR Similar Pretranslation** | **Qwen ONLY** | Quality > speed |
| **XLS Transfer Pretranslation** | **Qwen ONLY** | Quality > speed |

### Model2Vec: `potion-multilingual-128M`

| Metric | Value |
|--------|-------|
| Languages | **101** (including Korean) |
| Speed | **29,269 sentences/sec** |
| Dimension | 256 |
| License | MIT |

> The Fast/Deep toggle affects LDM TM search AND standard pretranslation.
> KR Similar / XLS Transfer pretranslation ALWAYS use Qwen.

---

## Future Vision: LDM as Mother App

**Goal:** Progressively merge monolith features into LDM (Svelte 5).

```
Current:
├── LDM ─────────── Main app (growing)
├── XLS Transfer ── Standalone tool
├── Quick Search ── Standalone tool
└── KR Similar ──── Standalone tool

Future:
├── LDM ─────────── Mother app (all features)
│   ├── TM Management (done)
│   ├── Pretranslation (done)
│   ├── QA Checks (done)
│   ├── Glossary Extraction (done)
│   └── ... more monolith features
│
└── Legacy Menu ─── Access to standalone tools
```

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Session state** | [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs** | [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **CI/CD docs** | [docs/cicd/CI_CD_HUB.md](docs/cicd/CI_CD_HUB.md) |
| **CDP Testing** | [testing_toolkit/cdp/README.md](testing_toolkit/cdp/README.md) |
| **Enterprise** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |

---

## Architecture

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Model2Vec (~128MB)            └─ Logs
├─ Qwen (2.3GB, opt-in)
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback)
```

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Check release/tag sync
./scripts/check_releases_status.sh

# Start backend
python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

# Playground install
./scripts/playground_install.sh --launch --auto-login

# Trigger builds
echo "Build LIGHT" >> GITEA_TRIGGER.txt   # Gitea
echo "Build LIGHT" >> BUILD_TRIGGER.txt   # GitHub
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8888 |
| Gitea | http://172.28.150.120:3000 |
| CDP | http://127.0.0.1:9222 |

---

*Build 315 | Updated 2025-12-21 | CI/CD Enhanced*
