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

### Block Structure (Hybrid Approach)

**Why Hybrid?**
- Unit/Integration tests live in block folders with pytest markers
- E2E tests stay separate (they span multiple blocks)
- Clear separation of "isolated" vs "full system" tests

```
tests/
├── blocks/                    # Organized by COMPONENT
│   │
│   ├── db/                    # Database block
│   │   ├── test_utils.py           # @pytest.mark.unit
│   │   ├── test_queries.py         # @pytest.mark.unit
│   │   ├── test_connectivity.py    # @pytest.mark.integration
│   │   └── test_sqlite_fallback.py # @pytest.mark.integration
│   │
│   ├── auth/                  # Authentication block
│   │   ├── test_jwt.py             # @pytest.mark.unit
│   │   ├── test_token_logic.py     # @pytest.mark.unit
│   │   ├── test_sessions.py        # @pytest.mark.integration
│   │   ├── test_permissions.py     # @pytest.mark.integration
│   │   └── test_rate_limiting.py   # @pytest.mark.integration
│   │
│   ├── network/               # Network block
│   │   ├── test_message_parsing.py # @pytest.mark.unit
│   │   ├── test_websocket.py       # @pytest.mark.integration
│   │   ├── test_http_endpoints.py  # @pytest.mark.integration
│   │   └── test_cors.py            # @pytest.mark.integration
│   │
│   ├── security/              # Security block
│   │   ├── test_jwt_security.py    # @pytest.mark.unit
│   │   ├── test_input_validation.py# @pytest.mark.unit
│   │   ├── test_ip_filter.py       # @pytest.mark.integration
│   │   ├── test_audit_logging.py   # @pytest.mark.integration
│   │   └── test_xss_prevention.py  # @pytest.mark.unit
│   │
│   ├── processing/            # Data processing block
│   │   ├── test_file_parsing.py    # @pytest.mark.unit
│   │   ├── test_tm_normalizer.py   # @pytest.mark.unit
│   │   ├── test_tm_operations.py   # @pytest.mark.integration
│   │   ├── test_embeddings.py      # @pytest.mark.integration
│   │   └── test_faiss_index.py     # @pytest.mark.integration
│   │
│   ├── tools/                 # Tools block
│   │   ├── test_kr_similar.py      # @pytest.mark.unit + integration
│   │   ├── test_quicksearch.py     # @pytest.mark.unit + integration
│   │   ├── test_xlstransfer.py     # @pytest.mark.unit + integration
│   │   └── test_ldm.py             # @pytest.mark.integration
│   │
│   ├── logging/               # Logging block
│   │   ├── test_server_logging.py  # @pytest.mark.unit
│   │   ├── test_client_logging.py  # @pytest.mark.unit
│   │   └── test_remote_logging.py  # @pytest.mark.integration
│   │
│   ├── ui/                    # UI block (API responses)
│   │   ├── test_api_responses.py   # @pytest.mark.unit
│   │   └── test_websocket_events.py# @pytest.mark.integration
│   │
│   └── performance/           # Performance block (NEW)
│       ├── test_api_latency.py     # @pytest.mark.slow
│       ├── test_db_query_speed.py  # @pytest.mark.slow
│       └── test_embedding_throughput.py # @pytest.mark.slow
│
├── e2e/                       # Cross-block workflows (SEPARATE)
│   ├── test_full_user_flow.py      # Auth + DB + UI
│   ├── test_tm_sync_workflow.py    # DB + Processing + Network
│   ├── test_pretranslation.py      # Tools + Processing + DB
│   └── test_complete_simulation.py # EVERYTHING
│
└── legacy/                    # Old tests (to review/delete)
```

### Test Type Definitions

| Type | Marker | Speed | Dependencies | Scope |
|------|--------|-------|--------------|-------|
| **Unit** | `@pytest.mark.unit` | Fast (<1s) | None/mocked | Single function |
| **Integration** | `@pytest.mark.integration` | Medium (1-5s) | Real DB/server | Component |
| **E2E** | `@pytest.mark.e2e` | Slow (5-30s) | Everything | Full workflow |
| **Slow** | `@pytest.mark.slow` | Very slow | Varies | Performance |

---

## Test Block Commands

```bash
# ============================================================
# BY BLOCK (Component)
# ============================================================
pytest tests/blocks/db/ -v           # All DB tests
pytest tests/blocks/auth/ -v         # All Auth tests
pytest tests/blocks/security/ -v     # All Security tests
pytest tests/blocks/network/ -v      # All Network tests
pytest tests/blocks/processing/ -v   # All Processing tests
pytest tests/blocks/tools/ -v        # All Tools tests

# ============================================================
# BY TYPE (Speed/Depth)
# ============================================================
pytest tests/blocks/ -m unit -v           # Fast unit tests only
pytest tests/blocks/ -m integration -v    # Integration tests
pytest tests/e2e/ -v                      # E2E workflows
pytest tests/blocks/ -m slow -v           # Performance tests

# ============================================================
# BUILD MODES
# ============================================================
# Build LIGHT (~5 min) - Essential tests
pytest tests/blocks/ -m "unit or integration" --ignore=tests/blocks/performance/

# Build TEST (~30 min) - EVERYTHING
pytest tests/blocks/ tests/e2e/ -v

# Quick smoke test (~1 min)
pytest tests/blocks/ -m unit -v
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
┌──────────────────────────────────────────────────────────────────────────┐
│                       CI/CD TEST PIPELINE                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1: UNIT TESTS (Fast, Parallel) ─────────────────────────────────  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│  │   DB   │ │  AUTH  │ │NETWORK │ │SECURITY│ │PROCESS │ │ TOOLS  │      │
│  │  unit  │ │  unit  │ │  unit  │ │  unit  │ │  unit  │ │  unit  │      │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘      │
│      │          │          │          │          │          │            │
│      └──────────┴──────────┴────┬─────┴──────────┴──────────┘            │
│                                 ▼                                        │
│  PHASE 2: INTEGRATION TESTS (Medium, Sequential) ─────────────────────   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│  │   DB   │ │  AUTH  │ │NETWORK │ │SECURITY│ │PROCESS │ │ TOOLS  │      │
│  │  integ │→│  integ │→│  integ │→│  integ │→│  integ │→│  integ │      │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘      │
│      │          │          │          │          │          │            │
│      └──────────┴──────────┴────┬─────┴──────────┴──────────┘            │
│                                 ▼                                        │
│  PHASE 3: E2E TESTS (Slow, Full System) ───────────────────────────────  │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  E2E: Full User Flow │ TM Sync │ Pretranslation │ Simulation │       │
│  └─────────────────────────────────┬────────────────────────────┘       │
│                                    ▼                                     │
│  PHASE 4: PERFORMANCE (Optional, Build TEST only) ─────────────────────  │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  PERF: API Latency │ DB Query Speed │ Embedding Throughput   │       │
│  └─────────────────────────────────┬────────────────────────────┘       │
│                                    ▼                                     │
│                          ┌─────────────────┐                             │
│                          │  BUILD INSTALLER │  (If all pass)             │
│                          └─────────────────┘                             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

BUILD LIGHT: Phase 1 + Phase 2 (skip Phase 3, 4)     → ~5 min
BUILD TEST:  Phase 1 + Phase 2 + Phase 3 + Phase 4   → ~30 min
BUILD FULL:  Phase 1 + Phase 2 + Offline Installer   → ~15 min
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
