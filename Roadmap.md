# LocaNext - Roadmap

**Build:** 298 (v25.1217.2220) | **Updated:** 2025-12-18 | **Status:** 100% Complete

---

## Current Status

All components operational. All optimizations complete.

| Component | Status |
|-----------|--------|
| LDM (Language Data Manager) | WORKS |
| XLS Transfer | WORKS |
| Quick Search | WORKS |
| KR Similar | WORKS |

---

## Completed Items

| # | Task | Status |
|---|------|--------|
| 1 | PERF-001 + PERF-002 (FAISS optimization) | ✅ Tested |
| 2 | FEAT-005 (Model2Vec for LDM TM) | ✅ Complete |
| 3 | BUG-023 (TM status display) | ✅ Fixed |

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

## Completed Details

### PERF-001 + PERF-002: FAISS Optimization - ✅ TESTED

| ID | Description | Result |
|----|-------------|--------|
| PERF-001 | Incremental HNSW | 5x faster for small additions |
| PERF-002 | FAISS factorization | 12 copies → 1 FAISSManager |

---

### FEAT-005: Model2Vec Default Engine - ✅ COMPLETE

**Model:** `minishlab/potion-multilingual-128M` (101 languages incl Korean)

| Metric | Model2Vec | Qwen |
|--------|-----------|------|
| Speed | 29,269/sec | ~600/sec |
| Memory | ~128MB | ~2.3GB |

**UI:** TM Manager toolbar → Fast/Deep toggle

**Details:** [FAISS_OPTIMIZATION_PLAN.md](docs/wip/FAISS_OPTIMIZATION_PLAN.md)

---

### BUG-023: TM Status Shows "Pending" - ✅ FIXED

**Culprit:** `MODEL_NAME` undefined in `tm_indexer.py` caused `NameError` during build.

**Fix:** Replaced with `self._engine.name`

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
| **FAISS/Model2Vec plan** | [FAISS_OPTIMIZATION_PLAN.md](docs/wip/FAISS_OPTIMIZATION_PLAN.md) |
| **CDP Testing** | [testing_toolkit/cdp/README.md](testing_toolkit/cdp/README.md) |
| **Enterprise** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |

---

## Architecture

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Model2Vec (~128MB) ← potion-multilingual-128M       └─ Logs
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

# Start backend
python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

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

*Build 298 | Updated 2025-12-19*
