# Architecture Documentation

**Last Updated**: 2025-12-05

Core architectural principles and patterns for LocaNext.

---

## 📚 Documentation Tree

```
docs/architecture/
│
├── README.md ──────────────── THIS FILE (Index)
│
├── 🏛️ PLATFORM_PATTERN.md ─── Multi-tool platform approach
│   └── How to scale: 3 tools → 20+ tools
│
├── 🔧 BACKEND_PRINCIPLES.md ── "Backend is Flawless" rule
│   └── Wrapper pattern, don't modify core
│
└── ⚡ ASYNC_PATTERNS.md ────── Async/await patterns
    └── WebSocket, real-time updates
```

---

## 🔑 Key Principles

### 1. Backend is Flawless
- **NEVER** modify backend core without confirmed bug
- Create wrapper layers (API, GUI) instead
- See: [BACKEND_PRINCIPLES.md](BACKEND_PRINCIPLES.md)

### 2. Platform Approach
- Host 10-20+ tools in one app
- Each tool is independent module under `server/tools/`
- See: [PLATFORM_PATTERN.md](PLATFORM_PATTERN.md)

### 3. Async by Default
- All new endpoints should be async
- Use `AsyncSession` for database
- See: [ASYNC_PATTERNS.md](ASYNC_PATTERNS.md)

---

## 🏗️ System Architecture

```
QUAD ENTITY ARCHITECTURE
│
├── Entity 1: Desktop App (Port 8888)
│   └── Electron + Svelte + FastAPI + SQLite
│
├── Entity 2: Central Server (Port 9999)
│   └── Telemetry receiver + PostgreSQL
│
├── Entity 3: Admin Dashboard (Port 5175)
│   └── Monitoring UI + Svelte
│
└── Entity 4: Gitea Server (Port 3000) [FUTURE]
    └── Self-hosted Git + CI/CD
```

---

## 📖 Related Docs

- [DEPLOYMENT_ARCHITECTURE.md](../DEPLOYMENT_ARCHITECTURE.md) - Hybrid SQLite/PostgreSQL
- [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - Complete file tree
- [Roadmap.md](../../Roadmap.md) - Development plan

---

*For the full documentation tree, see [CLAUDE.md](../../CLAUDE.md)*
