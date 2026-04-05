# Testing Framework - LocalizationTools

**2,800+ tests. Organized by type and domain.**

---

## Test Structure

```
tests/
├── conftest.py                  # Shared fixtures and config
│
├── unit/                        # Unit tests (fast, isolated, no server)
│   ├── auth/                    # Auth module, user management
│   ├── cache/                   # Cache module
│   ├── client/                  # Client utilities (logger, progress, file handler)
│   ├── config/                  # Config module (CORS LAN mode)
│   ├── kr_similar/              # KR Similar core + embeddings
│   ├── ldm/                     # Language Data Manager (57 files - largest)
│   ├── middleware/               # Security headers middleware
│   ├── mock/                    # Mock universe structure, volume, media
│   ├── network/                 # Phase 113 network auth, subnet detection
│   ├── quicksearch/             # QuickSearch parser, dictionary, searcher, QA
│   ├── setup/                   # Setup wizard (network, runner, secrets)
│   ├── test_server/             # Server utils (cache, models, websocket, DB)
│   ├── tm/                      # TM normalizer, search, sync, embeddings, semantic
│   ├── websocket/               # WebSocket module + functions
│   └── xlstransfer/             # XLSTransfer modules
│
├── integration/                 # Integration tests (multiple components)
│   ├── api/                     # API endpoint integration (detailed, true sim, LDM, QA)
│   ├── merge/                   # Merge pipeline, match types, transfer adapter
│   ├── mock/                    # Mock gamedata pipeline, cross-ref, roundtrip
│   ├── offline/                 # Offline mode, bundle, API endpoints, workflow
│   ├── security/                # CORS LAN, security headers, auth password flow
│   ├── server_tests/            # Server startup, API endpoints, auth, dashboard, DB connectivity
│   └── tm/                      # TM with real model, EMB-003 routes
│
├── e2e/                         # End-to-end tests (full workflows)
│   ├── pretranslation/          # KR Similar, TM, XLS Transfer, QWEN validation
│   ├── stringid/                # StringID TM upload, PKL index, search, pretranslate
│   └── (root)                   # Complete user flows, edge cases, production workflows
│
├── api/                         # API-level tests (TestClient, no DB required)
│   ├── helpers/                 # API test helpers, fixtures, constants
│   └── test_*.py                # Auth, merge, search, TM, tools, worldmap, etc.
│
├── security/                    # Security-focused tests
│   ├── test_ip_filter.py        # IP range filtering (CIDR, proxy headers)
│   ├── test_cors_config.py      # CORS configuration (dev/prod modes)
│   ├── test_audit_logging.py    # Audit event logging
│   ├── test_jwt_security.py     # JWT/secret key security validation
│   └── test_connectivity_matrix.py  # WHO can connect, OWASP mapping
│
├── stability/                   # Repository stability (schema drift, zombie, startup)
├── performance/                 # API latency benchmarks
├── cdp/                         # Chrome DevTools Protocol (Windows app tests)
├── fixtures/                    # Test data ONLY (no test files)
│   ├── merge/                   # Merge fixture data
│   ├── mock_gamedata/           # Mock game universe (XML, sounds, textures)
│   ├── mock_uploads/            # Upload test files (Excel, tab-delimited)
│   ├── pretranslation/          # Pretranslation test data + helpers
│   ├── stringid/                # StringID test data + generators
│   └── xml/                     # XML test files
├── helpers/                     # Shared test utilities
└── archive/                     # Deprecated tests (kept for reference)
```

---

## Running Tests

```bash
# All tests
pytest

# By directory
pytest tests/unit/           # Fast unit tests
pytest tests/security/       # Security suite (144 tests)
pytest tests/api/            # API tests
pytest tests/integration/    # Integration tests (slower)
pytest tests/e2e/            # End-to-end (slowest)

# By domain
pytest tests/unit/tm/        # TM tests
pytest tests/unit/quicksearch/  # QuickSearch tests
pytest tests/integration/merge/ # Merge pipeline

# Specific test
pytest tests/security/test_connectivity_matrix.py -v

# With coverage
pytest tests/ --cov=server --cov-report=html

# Skip slow tests
pytest tests/ -m "not slow" --no-cov
```

---

## Key Test Suites

| Suite | Tests | What it covers |
|-------|-------|---------------|
| **Security** | 144 | IP filter, CORS, audit logging, JWT, connectivity matrix, OWASP map |
| **API** | 40+ files | All REST endpoints via TestClient |
| **LDM Unit** | 57 files | Language Data Manager services and routes |
| **Stability** | 13 files | Schema drift, zombie processes, startup, repos |
| **CDP** | 17 JS + 3 py | Windows Electron app automation |

---

## Conventions

- Test files: `test_*.py` (pytest auto-discovery)
- Fixtures: `tests/fixtures/` (data only, no test files)
- Helpers: `tests/helpers/` (shared utilities)
- Archive: `tests/archive/` (deprecated, not run by default)
- Use `Path(__file__).parent...` for relative paths, never hardcode

---

*Reorganized 2026-04-05. 2,800+ tests across 230+ files.*
