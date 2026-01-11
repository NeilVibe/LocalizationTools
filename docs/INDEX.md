# Documentation Index

> **Single source of truth for all LocaNext documentation.**

---

## Quick Links

| Need | Location |
|------|----------|
| **Current bugs/issues** | [current/ISSUES_TO_FIX.md](current/ISSUES_TO_FIX.md) |
| **Session context** | [current/SESSION_CONTEXT.md](current/SESSION_CONTEXT.md) |
| **System architecture** | [architecture/ARCHITECTURE_SUMMARY.md](architecture/ARCHITECTURE_SUMMARY.md) |
| **Offline mode design** | [architecture/OFFLINE_ONLINE_MODE.md](architecture/OFFLINE_ONLINE_MODE.md) |
| **Debug protocol (GDP)** | [protocols/GRANULAR_DEBUG_PROTOCOL.md](protocols/GRANULAR_DEBUG_PROTOCOL.md) |

---

## Structure

```
docs/
├── INDEX.md              ← YOU ARE HERE
│
├── architecture/         # HOW THE SYSTEM WORKS
│   ├── ARCHITECTURE_SUMMARY.md    # Main architecture reference
│   ├── OFFLINE_ONLINE_MODE.md     # Offline/Online design
│   ├── TM_HIERARCHY_PLAN.md       # TM system design
│   └── ...
│
├── protocols/            # HOW TO DO THINGS (for Claude)
│   └── GRANULAR_DEBUG_PROTOCOL.md # GDP - microscopic logging
│
├── current/              # ACTIVE WORK
│   ├── ISSUES_TO_FIX.md          # Current bugs
│   └── SESSION_CONTEXT.md        # Session state
│
├── reference/            # STABLE REFERENCE DOCS
│   ├── enterprise/               # Enterprise deployment
│   ├── cicd/                     # CI/CD pipeline
│   ├── security/                 # Security docs
│   └── api/                      # API reference
│
├── guides/               # USER GUIDES
│   ├── tools/                    # Tool guides (LDM, XLSTransfer)
│   └── getting-started/          # Onboarding
│
└── archive/              # OLD DOCS (kept for reference)
    └── ...
```

---

## Architecture

| Doc | Description |
|-----|-------------|
| [ARCHITECTURE_SUMMARY.md](architecture/ARCHITECTURE_SUMMARY.md) | Complete system overview |
| [OFFLINE_ONLINE_MODE.md](architecture/OFFLINE_ONLINE_MODE.md) | Offline/Online mode design |
| [OFFLINE_ONLINE_SYNC.md](architecture/OFFLINE_ONLINE_SYNC.md) | Sync mechanism |
| [TM_HIERARCHY_PLAN.md](architecture/TM_HIERARCHY_PLAN.md) | TM assignment system |
| [BACKEND_PRINCIPLES.md](architecture/BACKEND_PRINCIPLES.md) | Backend design patterns |
| [ASYNC_PATTERNS.md](architecture/ASYNC_PATTERNS.md) | Async code patterns |

---

## Protocols

| Protocol | Purpose |
|----------|---------|
| [GRANULAR_DEBUG_PROTOCOL.md](protocols/GRANULAR_DEBUG_PROTOCOL.md) | GDP - Microscopic logging for bug hunting |

**Testing protocols** → See `testing_toolkit/` at project root

---

## Reference

### Enterprise Deployment
See [reference/enterprise/](reference/enterprise/) for full deployment guide.

### CI/CD
See [reference/cicd/](reference/cicd/) for pipeline docs.

### Security
See [reference/security/](reference/security/) for security hardening.

---

## Guides

| Guide | Description |
|-------|-------------|
| [LDM_GUIDE.md](guides/tools/LDM_GUIDE.md) | Language Data Manager usage |
| [XLSTRANSFER_GUIDE.md](guides/tools/XLSTRANSFER_GUIDE.md) | XLSTransfer tool usage |

---

## Related (Outside docs/)

| Location | Purpose |
|----------|---------|
| `CLAUDE.md` | Claude navigation hub (project root) |
| `Roadmap.md` | Current priorities (project root) |
| `testing_toolkit/` | Testing protocols and tools |
| `scripts/` | Shell wrappers and utilities |

---

*Last updated: 2026-01-11*
