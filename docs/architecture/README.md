# Architecture Documentation

**Last Updated**: 2025-12-11

Core architectural principles and patterns for LocaNext.

---

## Documentation Tree

```
docs/architecture/
│
├── README.md ──────────────── THIS FILE (Index)
│
├── PLATFORM_PATTERN.md ────── Multi-tool platform approach
│   └── How to scale: 3 tools → 20+ tools
│
├── BACKEND_PRINCIPLES.md ──── "Backend is Flawless" rule
│   └── Wrapper pattern, don't modify core
│
└── ASYNC_PATTERNS.md ──────── Async/await patterns
    └── WebSocket, real-time updates
```

---

## Key Principles

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

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ USER'S PC (LocaNext.exe)                                    │
├─────────────────────────────────────────────────────────────┤
│ Electron + Svelte + Embedded Python Backend                 │
│                                                             │
│ LOCAL (Heavy Processing):                                   │
│ ├─ FAISS indexes                                            │
│ ├─ Embeddings                                               │
│ └─ Model inference                                          │
│                                                             │
│ → ALL TEXT DATA to Central PostgreSQL                       │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ CENTRAL SERVER                                              │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL + PgBouncer (1000 connections)                   │
│ ├─ ALL user data (LDM, TM, projects, rows)                  │
│ ├─ Real-time sync (WebSocket)                               │
│ └─ Logs, telemetry                                          │
│                                                             │
│ Admin Dashboard (Port 5175)                                 │
│ └─ Monitoring UI                                            │
│                                                             │
│ Gitea Server (Port 3000)                                    │
│ └─ Self-hosted Git + CI/CD                                  │
└─────────────────────────────────────────────────────────────┘
```

**Key Point**: PostgreSQL for ALL text data. Local disk only for heavy computed files (FAISS, embeddings).

---

## Related Docs

- [DEPLOYMENT_ARCHITECTURE.md](../deployment/DEPLOYMENT_ARCHITECTURE.md) - Full deployment model
- [PROJECT_STRUCTURE.md](../getting-started/PROJECT_STRUCTURE.md) - Complete file tree
- [P21_DATABASE_POWERHOUSE.md](../history/wip-archive/P21_DATABASE_POWERHOUSE.md) - Database performance (archived)

---

*For the full documentation tree, see [CLAUDE.md](../../CLAUDE.md)*
