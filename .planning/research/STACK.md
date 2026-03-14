# Technology Stack

**Project:** LocaNext Demo-Ready CAT Tool
**Researched:** 2026-03-14

## Recommended Stack

No stack changes recommended. The existing stack is competitive and well-suited. This document confirms what exists and identifies supporting libraries needed for the demo-ready milestone.

### Core Framework (Existing - Keep As-Is)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Electron | Current | Desktop shell | Cross-platform desktop app, already configured |
| Svelte 5 | Latest | Frontend framework | Runes reactivity, already in use, fast rendering |
| FastAPI | Current | Python backend | Async API, already serving all endpoints |
| Carbon Components | IBM | UI component library | Already integrated, professional look |

### Database (Existing - Keep As-Is)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | Current | Online multi-user DB | Production database, already configured |
| SQLite | Current | Offline single-user DB | Local-first, already configured |
| SQLAlchemy | Current | ORM for PostgreSQL | Already in repository pattern |

### AI/Search (Existing - Keep As-Is)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FAISS | Current | Vector similarity search | Semantic TM search, already integrated |
| Qwen | 2.3GB model | Local pretranslation | On-device ML, key differentiator |

### Supporting Libraries (New - For Demo-Ready Features)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| **svelte-virtual-list** or **tanstack-virtual** | Virtual scrolling for large file grids | Phase 1 — grid performance. Research which works best with Svelte 5 runes at implementation time |
| **diff-match-patch** | Word-level diff highlighting for fuzzy TM matches | Phase 2 — TM match display. Google's library, stable, lightweight |
| **d3-scale** or simple CSS | Match percentage color gradient (red > yellow > green) | Phase 2 — visual match indicators. Likely just CSS gradient, no library needed |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Frontend framework | Svelte 5 (keep) | React, Vue | Already built in Svelte 5, no reason to rewrite |
| UI library | Carbon (keep) | Tailwind, Skeleton UI | Already integrated, professional enterprise look |
| Virtual scrolling | tanstack-virtual | svelte-virtual-list, custom | TanStack has Svelte adapter, battle-tested. Needs Svelte 5 compatibility verification |
| Vector search | FAISS (keep) | pgvector, Milvus | FAISS is local (offline), already working, fast |
| Local ML | Qwen (keep) | Llama, Mistral | Already integrated, 2.3GB is reasonable size |

## Installation

No new core dependencies expected. Supporting libraries as needed per phase:

```bash
# Phase 1 — if virtual scrolling library chosen
cd locaNext && npm install @tanstack/svelte-virtual  # verify Svelte 5 compat first

# Phase 2 — diff highlighting
cd locaNext && npm install diff-match-patch
```

## Sources

- LocaNext ARCHITECTURE_SUMMARY.md — existing stack documentation
- LocaNext PROJECT.md — technology constraints
