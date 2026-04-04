# LocaNext - Professional Localization Platform

> **Unified desktop platform for game localization - 4 tools, 912 tests, production ready**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Electron](https://img.shields.io/badge/Electron-35.x-9feaf9.svg)](https://www.electronjs.org/)
[![Svelte](https://img.shields.io/badge/Svelte-4.x-ff3e00.svg)](https://svelte.dev/)
[![Tests](https://img.shields.io/badge/Tests-912%20passing-brightgreen.svg)](#test-coverage)

---

## What is LocaNext?

LocaNext consolidates multiple localization and translation tools into a **single desktop application**. Built for game development teams managing 500K+ translatable strings across 10-20 languages.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   BEFORE LocaNext                      AFTER LocaNext                       │
│   ════════════════                     ═══════════════                      │
│                                                                             │
│   ┌─────────┐ ┌─────────┐              ┌─────────────────────────────────┐  │
│   │ Script 1│ │ Script 2│              │                                 │  │
│   └────┬────┘ └────┬────┘              │         ┌─────────────────┐     │  │
│        │           │                   │         │                 │     │  │
│   ┌────┴────┐ ┌────┴────┐              │    ┌────┤    LocaNext     ├────┐│  │
│   │ Script 3│ │ Script 4│              │    │    │                 │    ││  │
│   └────┬────┘ └────┬────┘              │    │    └─────────────────┘    ││  │
│        │           │                   │    │             │             ││  │
│   ┌────┴────┐ ┌────┴────┐              │  ┌─┴─┐  ┌────┐  ┌┴───┐  ┌───┐  ││  │
│   │ Script 5│ │ Script 6│              │  │XLS│  │QS  │  │KRS │  │LDM│  ││  │
│   └─────────┘ └─────────┘              │  └───┘  └────┘  └────┘  └───┘  ││  │
│                                        │                                 │  │
│   • Scattered Python scripts           └─────────────────────────────────┘  │
│   • Manual command-line usage                                               │
│   • No central monitoring              • Single unified application         │
│   • No collaboration                   • Professional GUI                   │
│                                        • Central monitoring & logging       │
│                                        • Real-time collaboration            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LOCANEXT ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              ┌─────────────┐                                │
│                              │   USERS     │                                │
│                              └──────┬──────┘                                │
│                                     │                                       │
│             ┌───────────────────────┼───────────────────────┐               │
│             │                       │                       │               │
│             ▼                       ▼                       ▼               │
│     ┌───────────────┐       ┌───────────────┐       ┌───────────────┐       │
│     │  LocaNext     │       │  LocaNext     │       │  LocaNext     │       │
│     │  Desktop App  │       │  Desktop App  │       │  Desktop App  │       │
│     │  (Electron)   │       │  (Electron)   │       │  (Electron)   │       │
│     └───────┬───────┘       └───────┬───────┘       └───────┬───────┘       │
│             │                       │                       │               │
│             └───────────────────────┼───────────────────────┘               │
│                                     │                                       │
│                          HTTP/WebSocket                                     │
│                                     │                                       │
│                                     ▼                                       │
│     ┌───────────────────────────────────────────────────────────────┐       │
│     │                     COMPANY SERVER                             │       │
│     │                     (Single Machine)                           │       │
│     │  ┌─────────────────────────────────────────────────────────┐  │       │
│     │  │                                                         │  │       │
│     │  │  ┌─────────────────┐    ┌─────────────────┐            │  │       │
│     │  │  │   FastAPI       │    │   PostgreSQL    │            │  │       │
│     │  │  │   Backend       │◄──►│   Database      │            │  │       │
│     │  │  │   :8888         │    │   :5432         │            │  │       │
│     │  │  └─────────────────┘    └─────────────────┘            │  │       │
│     │  │          │                                              │  │       │
│     │  │          ▼                                              │  │       │
│     │  │  ┌─────────────────┐    ┌─────────────────┐            │  │       │
│     │  │  │   WebSocket     │    │   Gitea         │            │  │       │
│     │  │  │   Real-time     │    │   Auto-Update   │            │  │       │
│     │  │  │   Sync          │    │   :3000         │            │  │       │
│     │  │  └─────────────────┘    └─────────────────┘            │  │       │
│     │  │                                                         │  │       │
│     │  └─────────────────────────────────────────────────────────┘  │       │
│     │                                                               │       │
│     │  Resources: 2 CPU, 2GB RAM, 50GB disk                         │       │
│     │  Handles: 50+ concurrent users, 1M+ rows                      │       │
│     └───────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Tree

```
LocaNext Platform
│
├── 📱 Desktop Application (Electron + Svelte)
│   ├── Cross-platform (Windows, macOS, Linux)
│   ├── Auto-update capability
│   ├── Offline-capable tools
│   └── Professional UI/UX
│
├── 🖥️ Backend Server (FastAPI + Python)
│   ├── RESTful API (55+ endpoints)
│   ├── WebSocket real-time sync
│   ├── Async processing
│   └── Task queue management
│
├── 🗄️ Database (PostgreSQL)
│   ├── 29 tables
│   ├── 40+ optimized indexes
│   ├── Full-text search (tsvector)
│   ├── Connection pooling
│   └── Automatic backups
│
├── 🔄 Update Server (Gitea)
│   ├── Self-hosted releases
│   ├── Delta updates
│   └── Version management
│
└── 📊 Admin Dashboard (Svelte)
    ├── User management
    ├── Usage statistics
    ├── Audit logs
    └── Telemetry view
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   USER ACTION              SYSTEM FLOW                     RESULT           │
│   ───────────              ───────────                     ──────           │
│                                                                             │
│   1. Upload File           ┌────────────┐                                   │
│      (drag & drop)    ──►  │ Parse File │                                   │
│                            └─────┬──────┘                                   │
│                                  │                                          │
│                                  ▼                                          │
│                            ┌────────────┐                                   │
│                            │ Bulk Insert│  (20,000 rows/sec)                │
│                            └─────┬──────┘                                   │
│                                  │                                          │
│                                  ▼                                          │
│                            ┌────────────┐                                   │
│   2. Edit Cell        ──►  │ WebSocket  │                                   │
│      (real-time)           │ Broadcast  │                                   │
│                            └─────┬──────┘                                   │
│                                  │                                          │
│                     ┌────────────┼────────────┐                             │
│                     ▼            ▼            ▼                             │
│               ┌─────────┐  ┌─────────┐  ┌─────────┐                         │
│               │ User A  │  │ User B  │  │ User C  │  (all see update)       │
│               └─────────┘  └─────────┘  └─────────┘                         │
│                                                                             │
│   3. TM Search        ──►  5-Tier Cascade Search  ──►  Results in <50ms     │
│      (translation)         (Hash → Embedding → N-gram)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TECHNOLOGY STACK                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   FRONTEND                           BACKEND                                │
│   ════════                           ═══════                                │
│   ├── Electron 35.x                  ├── Python 3.10+                       │
│   │   └── Cross-platform desktop     │   └── Core runtime                   │
│   │                                  │                                      │
│   ├── Svelte 4.x                     ├── FastAPI 0.100+                     │
│   │   └── Reactive UI framework      │   └── Async API framework            │
│   │                                  │                                      │
│   ├── Tailwind CSS                   ├── SQLAlchemy 2.0                     │
│   │   └── Utility-first styling      │   └── ORM & database toolkit         │
│   │                                  │                                      │
│   └── Vite                           ├── Uvicorn                            │
│       └── Fast build tooling         │   └── ASGI server                    │
│                                      │                                      │
│                                      └── WebSocket                          │
│                                          └── Real-time communication        │
│                                                                             │
│   DATABASE                           INFRASTRUCTURE                         │
│   ════════                           ══════════════                         │
│   ├── PostgreSQL 14+                 ├── Gitea                              │
│   │   ├── Primary database           │   └── Self-hosted Git + releases     │
│   │   ├── Full-text search           │                                      │
│   │   └── Connection pooling         ├── GitHub Actions                     │
│   │                                  │   └── CI/CD pipeline                 │
│   └── PgBouncer                      │                                      │
│       └── Connection pooling (1000)  └── NSIS                               │
│                                          └── Windows installer              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tool Suite

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TOOL SUITE                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📊 XLSTransfer                                        Status: ✅    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  Purpose:  Transfer data between Excel files                        │   │
│  │  Features: • Batch processing (100+ files)                          │   │
│  │            • Column mapping                                         │   │
│  │            • Duplicate detection                                    │   │
│  │            • Progress tracking                                      │   │
│  │  Tests:    10/10 passed                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🔍 QuickSearch                                        Status: ✅    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  Purpose:  Fast dictionary/glossary lookup                          │   │
│  │  Features: • TXT and XML file support                               │   │
│  │            • Regex search                                           │   │
│  │            • Export results                                         │   │
│  │            • QA tools (glossary checking)                           │   │
│  │  Tests:    8/8 passed                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🔗 KR Similar                                         Status: ✅    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  Purpose:  Find similar Korean text strings                         │   │
│  │  Features: • Fuzzy matching algorithm                               │   │
│  │            • Configurable threshold                                 │   │
│  │            • Batch comparison                                       │   │
│  │            • 41,715 pairs tested                                    │   │
│  │  Tests:    10/10 passed                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📝 LDM (LanguageData Manager)                         Status: 60%   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  Purpose:  CAT tool for translation file management                 │   │
│  │  Features: • 1M+ row virtual scrolling                              │   │
│  │            • Real-time multi-user collaboration                     │   │
│  │            • Translation Memory (5-tier cascade)                    │   │
│  │            • Keyboard shortcuts                                     │   │
│  │  Scale:    103,500 rows in 50 seconds                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Translation Memory System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    5-TIER CASCADE TM SEARCH                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Input: "게임을 시작합니다" (Start the game)                                │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ TIER 1: Perfect Whole Match                                         │  │
│   │ ─────────────────────────────                                       │  │
│   │ Method:    SHA256 hash lookup                                       │  │
│   │ Speed:     O(1) - instant                                           │  │
│   │ Confidence: 100%                                                    │  │
│   │ If found:  STOP (best possible match)                               │  │
│   └──────────────────────────────────┬──────────────────────────────────┘  │
│                                      │ Not found                           │
│                                      ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ TIER 2: Whole Text Embedding (Semantic)                             │  │
│   │ ───────────────────────────────────────                             │  │
│   │ Method:    FAISS HNSW vector search                                 │  │
│   │ Speed:     ~10ms                                                    │  │
│   │ Threshold: ≥92% = PRIMARY match (high confidence)                   │  │
│   └──────────────────────────────────┬──────────────────────────────────┘  │
│                                      │ No high-confidence match            │
│                                      ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ TIER 3: Perfect Line Match                                          │  │
│   │ ─────────────────────────                                           │  │
│   │ Method:    Hash lookup per line                                     │  │
│   │ Use case:  Multi-line text with some matching lines                 │  │
│   └──────────────────────────────────┬──────────────────────────────────┘  │
│                                      ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ TIER 4: Line-by-Line Embedding                                      │  │
│   │ ──────────────────────────────                                      │  │
│   │ Method:    FAISS search per unmatched line                          │  │
│   └──────────────────────────────────┬──────────────────────────────────┘  │
│                                      ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ TIER 5: Word N-Gram Embedding                                       │  │
│   │ ───────────────────────────                                         │  │
│   │ Method:    1,2,3-word n-grams → embed → search                      │  │
│   │ Use case:  Partial phrase matching                                  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   DUAL THRESHOLD OUTPUT:                                                    │
│   ├── PRIMARY (≥92%): High confidence, safe to apply                       │
│   └── CONTEXT (49-92%): Reference only, needs human review                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Security

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY LAYERS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 1: NETWORK                                                          │
│   ════════════════                                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  ✅ IP Range Filtering                                              │  │
│   │     • Whitelist company IP ranges                                   │  │
│   │     • Block unauthorized access attempts                            │  │
│   │     • 24 security tests                                             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   LAYER 2: APPLICATION                                                      │
│   ════════════════════                                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  ✅ JWT Token Authentication                                        │  │
│   │     • Secure token-based auth                                       │  │
│   │     • Token expiration & refresh                                    │  │
│   │     • 22 security tests                                             │  │
│   │                                                                     │  │
│   │  ✅ CORS Protection                                                 │  │
│   │     • Origin validation                                             │  │
│   │     • Cross-site request prevention                                 │  │
│   │     • 11 security tests                                             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   LAYER 3: AUDIT & MONITORING                                               │
│   ═══════════════════════════                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  ✅ Comprehensive Audit Logging                                     │  │
│   │     • All login attempts logged                                     │  │
│   │     • Security events tracked                                       │  │
│   │     • Admin-viewable audit trail                                    │  │
│   │     • 29 security tests                                             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   LAYER 4: DATA PROTECTION                                                  │
│   ════════════════════════                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  ✅ Secrets Management                                              │  │
│   │     • Environment variable configuration                            │  │
│   │     • No hardcoded credentials                                      │  │
│   │     • .env.example template provided                                │  │
│   │                                                                     │  │
│   │  ✅ Dependency Security                                             │  │
│   │     • CI/CD audit on every build                                    │  │
│   │     • CRITICAL/HIGH vulnerabilities block deployment                │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   TOTAL SECURITY TESTS: 86                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Performance Benchmarks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PERFORMANCE BENCHMARKS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Operation                    Metric                   Result              │
│   ─────────────────────────────────────────────────────────────────────    │
│                                                                             │
│   FILE OPERATIONS                                                           │
│   ├── File upload (100k rows)  Time                    5 seconds            │
│   ├── Bulk insert rate         Rows/second             20,419               │
│   └── File re-upload (5% diff) Time savings            95% faster           │
│                                                                             │
│   SEARCH PERFORMANCE                                                        │
│   ├── Hash lookup (exact)      Response time           2.14 ms              │
│   ├── LIKE search              Response time           3.26 ms              │
│   ├── Full-text search         Response time           < 100 ms             │
│   └── Pattern search (866 hits) Response time          82.18 ms             │
│                                                                             │
│   SCALABILITY                                                               │
│   ├── Max rows per file        Tested                  1,000,000+           │
│   ├── Concurrent users         Supported               50+                  │
│   ├── TM entries               Tested                  700,000              │
│   └── WebSocket connections    Simultaneous            100+                 │
│                                                                             │
│   MEMORY USAGE                                                              │
│   ├── Desktop app              RAM                     ~150 MB              │
│   ├── Backend server           RAM                     ~200 MB              │
│   └── PostgreSQL               RAM                     ~300 MB              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Test Coverage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TEST COVERAGE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Category                    Tests       Status                            │
│   ─────────────────────────────────────────────────────────────────────    │
│   Unit Tests                    377        ✅ All passing                   │
│   API Simulation Tests          168        ✅ All passing                   │
│   Frontend E2E (Playwright)     164        ✅ All passing                   │
│   E2E Integration               115        ✅ All passing                   │
│   Security Tests                 86        ✅ All passing                   │
│   ─────────────────────────────────────────────────────────────────────    │
│   TOTAL                         912        ✅ ALL PASSING                   │
│                                                                             │
│   Test Philosophy: TRUE SIMULATION (No mocks for core functions)            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Run tests:

```bash
# Quick tests
python3 -m pytest

# Full tests with server
python3 scripts/create_admin.py
python3 server/main.py &
sleep 5
RUN_API_TESTS=1 python3 -m pytest -v
```

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** with PgBouncer

### Installation

```bash
# Clone repository
git clone git@github.com:<GIT_USER>/LocalizationTools.git
cd LocalizationTools

# Backend setup
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd locaNext && npm install && cd ..
cd adminDashboard && npm install && cd ..

# Create admin user
python3 scripts/create_admin.py
```

### Running

```bash
# Terminal 1: Backend (port 8888)
python3 server/main.py

# Terminal 2: Desktop app
cd locaNext && npm run electron:dev

# Terminal 3: Admin dashboard (optional, port 5175)
cd adminDashboard && npm run dev -- --port 5175
```

### Access Points

| Service | URL |
|---------|-----|
| API Documentation | http://localhost:8888/docs |
| Health Check | http://localhost:8888/health |
| Admin Dashboard | http://localhost:5175 |

---

## Project Structure

```
LocalizationTools/
├── locaNext/                    # Desktop app (Electron + Svelte)
│   ├── electron/                # Electron main process
│   │   ├── health-check.js      # Startup verification
│   │   ├── repair.js            # Auto-repair system
│   │   └── updater.js           # Auto-update from GitHub/Gitea
│   └── src/                     # Svelte frontend
│       ├── routes/              # App pages (ldm/, xlsTransfer/, etc.)
│       └── lib/                 # Shared components
│
├── server/                      # Backend (FastAPI)
│   ├── main.py                  # Entry point
│   ├── api/                     # REST endpoints
│   ├── database/                # SQLAlchemy models (29 tables)
│   └── tools/                   # Tool implementations
│       ├── xlstransfer/
│       ├── quicksearch/
│       ├── kr_similar/
│       └── ldm/                 # LanguageData Manager
│
├── adminDashboard/              # Admin UI (Svelte)
│
├── tests/                       # 912 tests
│
├── docs/                        # Documentation
│   ├── wip/                     # Work in progress (detailed tasks)
│   └── ...                      # Architecture, guides, etc.
│
├── Roadmap.md                   # High-level priorities (RM)
└── CLAUDE.md                    # Navigation hub
```

---

## CI/CD - Dual Build System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CI/CD PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DUAL BUILD SYSTEM (Production + Local Test)                               │
│                                                                             │
│       Developer              GitHub              Gitea (Local)              │
│       ─────────              ──────              ─────────────              │
│           │                    │                      │                     │
│           │  git push          │                      │                     │
│           ├───────────────────►│                      │                     │
│           │                    │                      │                     │
│           │                    │  BUILD_TRIGGER.txt   │                     │
│           │                    │──────────┐           │                     │
│           │                    │          ▼           │                     │
│           │                    │    ┌──────────┐      │                     │
│           │                    │    │ GitHub   │      │                     │
│           │                    │    │ Actions  │      │                     │
│           │                    │    └────┬─────┘      │                     │
│           │                    │         │            │                     │
│           │                    │         ▼            │                     │
│           │                    │   [Windows EXE]      │                     │
│           │                    │   [Auto-Update]      │                     │
│           │                    │                      │                     │
│           │  git push gitea    │                      │                     │
│           ├──────────────────────────────────────────►│                     │
│           │                    │                      │                     │
│           │                    │      GITEA_TRIGGER   │                     │
│           │                    │      ──────────┐     │                     │
│           │                    │                ▼     │                     │
│           │                    │         ┌──────────┐ │                     │
│           │                    │         │ Gitea    │ │                     │
│           │                    │         │ Actions  │ │                     │
│           │                    │         └────┬─────┘ │                     │
│           │                    │              │       │                     │
│           │                    │              ▼       │                     │
│           │                    │        [Test Build]  │                     │
│                                                                             │
│   Build Time: ~10 min (GitHub) | ~1 min (Gitea with cache)                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Build commands:**

```bash
# Production build (GitHub)
echo "Build LIGHT vXXXX" >> BUILD_TRIGGER.txt
git push origin main

# Test build (Gitea)
echo "Build LIGHT vXXXX" >> GITEA_TRIGGER.txt
git push gitea main
```

---

## Project Status

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PROJECT STATUS                                      │
│                          December 2025                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   COMPONENT                           STATUS          PROGRESS              │
│   ─────────────────────────────────────────────────────────────────────    │
│                                                                             │
│   Backend (FastAPI)                   ✅ COMPLETE      ████████████ 100%    │
│   ├── 55+ API endpoints                                                     │
│   ├── WebSocket real-time                                                   │
│   ├── Async processing                                                      │
│   └── Task management                                                       │
│                                                                             │
│   Frontend (Electron)                 ✅ COMPLETE      ████████████ 100%    │
│   ├── Desktop application                                                   │
│   ├── Auto-update                                                           │
│   └── Cross-platform                                                        │
│                                                                             │
│   XLSTransfer                         ✅ COMPLETE      ████████████ 100%    │
│   QuickSearch                         ✅ COMPLETE      ████████████ 100%    │
│   KR Similar                          ✅ COMPLETE      ████████████ 100%    │
│                                                                             │
│   LDM (LanguageData Manager)          🔄 IN PROGRESS   ███████░░░░░  60%    │
│   ├── Core features complete                                                │
│   ├── TM system in progress                                                 │
│   └── 82/140 tasks done                                                     │
│                                                                             │
│   Security                            ✅ COMPLETE      ████████████ 100%    │
│   ├── 7/7 core features                                                     │
│   └── 86 tests passing                                                      │
│                                                                             │
│   CI/CD                               ✅ COMPLETE      ████████████ 100%    │
│   ├── GitHub Actions                                                        │
│   └── Gitea Actions                                                         │
│                                                                             │
│   Database (PostgreSQL)               ✅ COMPLETE      ████████████ 100%    │
│   ├── Phase 1 optimizations done                                            │
│   └── Phase 2 (incremental updates) planned                                 │
│                                                                             │
│   ─────────────────────────────────────────────────────────────────────    │
│   OVERALL PROJECT                     🟢 PRODUCTION    ██████████░░  90%    │
│                                          READY                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Documentation

| Document | Description |
|----------|-------------|
| **[CLAUDE.md](CLAUDE.md)** | Navigation hub - start here |
| **[Roadmap.md](Roadmap.md)** | High-level priorities (RM) |
| **[docs/EXECUTIVE_SUMMARY.md](docs/EXECUTIVE_SUMMARY.md)** | For management/stakeholders |
| **[docs/wip/P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md)** | LDM detailed tasks (WIP) |
| **[docs/getting-started/](docs/getting-started/)** | Onboarding guides |
| **[docs/architecture/](docs/architecture/)** | Technical design |
| **[docs/security/](docs/security/)** | Security documentation |

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md) for project navigation
2. Check [Roadmap.md](Roadmap.md) for current priorities
3. Follow [docs/development/CODING_STANDARDS.md](docs/development/CODING_STANDARDS.md)
4. Run tests before committing

---

## License

**Internal Project - Company Use Only**

All dependencies are MIT/Apache 2.0 licensed (free for commercial use).

---

**Version:** 25.1213.1540 (December 2025) | **Lines of Code:** ~19,000+ | **API Endpoints:** 55+ | **Database Tables:** 29

Built for efficient localization workflows.
