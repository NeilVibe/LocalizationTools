# P36: CI/CD Test Overhaul - Beautiful Test Blocks

**Status:** PLANNING | **Priority:** HIGH | **Created:** 2025-12-21

---

## Goal

Create a beautiful, organized CI/CD testing pipeline with clear **test blocks** for each system component. Enable `Build TEST` mode for comprehensive quality assurance.

---

## Current State

### Test Inventory

| Category | Files | Est. Functions | Coverage |
|----------|-------|----------------|----------|
| `tests/unit/` | 27 | ~400 | Modules |
| `tests/integration/` | 12 | ~200 | Server/API/DB |
| `tests/e2e/` | 8 | ~100 | Workflows |
| `tests/security/` | 4 | ~50 | Security |
| `tests/api/` | 7 | ~150 | Endpoints |
| `tests/fixtures/` | 12 | ~200 | Special cases |
| **TOTAL** | **78** | **~1357** | Mixed |

### Current Issues

1. **No clear grouping** - Tests scattered, hard to run by component
2. **Duplicates likely** - Similar tests in different locations
3. **Gaps unknown** - No coverage map
4. **No performance tests** - Missing entirely
5. **UI tests separate** - CDP (JavaScript), not in Python pipeline

---

## Proposed Test Blocks Architecture

### Block Structure

```
tests/
├── blocks/                    # NEW: Organized test blocks
│   ├── db/                    # Database block
│   │   ├── test_connectivity.py
│   │   ├── test_migrations.py
│   │   ├── test_queries.py
│   │   └── test_sqlite_fallback.py
│   │
│   ├── auth/                  # Authentication block
│   │   ├── test_jwt.py
│   │   ├── test_sessions.py
│   │   ├── test_permissions.py
│   │   └── test_rate_limiting.py
│   │
│   ├── network/               # Network block
│   │   ├── test_websocket.py
│   │   ├── test_http_endpoints.py
│   │   ├── test_cors.py
│   │   └── test_timeouts.py
│   │
│   ├── security/              # Security block
│   │   ├── test_jwt_security.py
│   │   ├── test_ip_filter.py
│   │   ├── test_audit_logging.py
│   │   ├── test_input_validation.py
│   │   └── test_xss_prevention.py
│   │
│   ├── processing/            # Data processing block
│   │   ├── test_file_parsing.py
│   │   ├── test_tm_operations.py
│   │   ├── test_embeddings.py
│   │   └── test_faiss_index.py
│   │
│   ├── tools/                 # Tools block
│   │   ├── test_kr_similar.py
│   │   ├── test_quicksearch.py
│   │   ├── test_xlstransfer.py
│   │   └── test_ldm.py
│   │
│   ├── logging/               # Logging block
│   │   ├── test_server_logging.py
│   │   ├── test_client_logging.py
│   │   └── test_remote_logging.py
│   │
│   ├── ui/                    # UI block (Python side)
│   │   ├── test_api_responses.py
│   │   └── test_websocket_events.py
│   │
│   └── performance/           # Performance block (NEW)
│       ├── test_api_latency.py
│       ├── test_db_query_speed.py
│       └── test_embedding_throughput.py
│
├── e2e/                       # End-to-end (keep as-is)
└── legacy/                    # Old tests (to review/migrate)
```

---

## Test Block Commands

```bash
# Run specific block
pytest tests/blocks/db/ -v           # Database only
pytest tests/blocks/security/ -v     # Security only
pytest tests/blocks/network/ -v      # Network only

# Run all blocks (Build TEST)
pytest tests/blocks/ -v              # All blocks

# Run with markers
pytest -m "db" -v                    # All DB-tagged tests
pytest -m "security" -v              # All security-tagged tests
pytest -m "fast" -v                  # All fast tests
pytest -m "slow" -v                  # All slow tests
```

---

## CI/CD Pipeline Integration

### Build Modes

| Mode | What Runs | Time |
|------|-----------|------|
| `Build LIGHT` | Essential blocks (~285 tests) | ~5 min |
| `Build TEST` | ALL blocks (1357+ tests) | ~30 min |
| `Build FULL` | Essential + creates offline installer | ~15 min |

### Pipeline Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                    CI/CD TEST PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │   DB    │  │  AUTH   │  │ NETWORK │  │SECURITY │            │
│  │  Block  │  │  Block  │  │  Block  │  │  Block  │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
│       │            │            │            │                  │
│       ▼            ▼            ▼            ▼                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │PROCESS- │  │  TOOLS  │  │ LOGGING │  │   UI    │            │
│  │  ING    │  │  Block  │  │  Block  │  │  Block  │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
│       │            │            │            │                  │
│       └────────────┴─────┬──────┴────────────┘                  │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │ PERFORMANCE │  (Optional, slow)             │
│                   │    Block    │                               │
│                   └──────┬──────┘                               │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │    E2E      │  (Full workflows)             │
│                   │   Tests     │                               │
│                   └──────┬──────┘                               │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │   BUILD     │  (If all pass)                │
│                   │  INSTALLER  │                               │
│                   └─────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Work Required

### Phase 1: Audit (2-3 hours)
- [ ] Review all 78 test files
- [ ] Identify duplicates
- [ ] Map coverage gaps
- [ ] List tests to delete/merge

### Phase 2: Reorganize (4-6 hours)
- [ ] Create `tests/blocks/` structure
- [ ] Move tests to appropriate blocks
- [ ] Add pytest markers (`@pytest.mark.db`, etc.)
- [ ] Update imports

### Phase 3: Fill Gaps (4-8 hours)
- [ ] Write missing performance tests
- [ ] Write missing error handling tests
- [ ] Write missing logging tests
- [ ] Improve network tests

### Phase 4: CI/CD Integration (2-3 hours)
- [ ] Update Gitea workflow for `Build TEST`
- [ ] Update GitHub workflow
- [ ] Add block-by-block reporting
- [ ] Add health badges

---

## Success Criteria

1. **Clear structure** - Any dev can find/add tests easily
2. **No duplicates** - Each scenario tested once
3. **Full coverage** - All components have test block
4. **Fast feedback** - LIGHT build in 5 min
5. **Comprehensive QA** - TEST build covers everything
6. **Beautiful pipeline** - Visual block-by-block status

---

## Questions to Resolve

1. Should CDP tests (JavaScript) be integrated into Python pipeline?
2. Should we use coverage tools (pytest-cov)?
3. Should we add mutation testing?
4. How to handle tests that need real model (2.3GB)?

---

## Related

- [Roadmap.md](../../Roadmap.md) - CI/CD Build Modes
- [SESSION_CONTEXT.md](SESSION_CONTEXT.md) - Current session
- [CI_CD_HUB.md](../cicd/CI_CD_HUB.md) - CI/CD documentation

---

*Created: 2025-12-21 | P36: CI/CD Test Overhaul*
