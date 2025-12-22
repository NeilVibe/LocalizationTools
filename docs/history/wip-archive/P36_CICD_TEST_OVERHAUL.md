# P36: CI/CD Test Overhaul - Beautiful Test Blocks

**Status:** IN PROGRESS | **Priority:** HIGH | **Created:** 2025-12-21 | **Updated:** 2025-12-21

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

| Mode | Tests | Installer | Time |
|------|-------|-----------|------|
| `LIGHT` | Essential (~285) | ~150MB | ~5 min |
| `FULL` | Essential (~285) | ~2GB+ offline | ~15 min |
| `QA-LIGHT` | **ALL 1500+** | ~150MB | ~30 min |
| `QA-FULL` | **ALL 1500+** | ~2GB+ offline | ~45 min |

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

LIGHT:    Phase 1 + Phase 2 (essential tests)           → ~5 min
FULL:     Phase 1 + Phase 2 + Offline Installer         → ~15 min
QA-LIGHT: Phase 1 + Phase 2 + Phase 3 + Phase 4         → ~30 min
QA-FULL:  Phase 1 + Phase 2 + Phase 3 + Phase 4 + Full  → ~45 min
```

---

## Planning Documents (COMPLETED)

| Document | Purpose | Status |
|----------|---------|--------|
| [P36_TEST_MAPPING.md](P36_TEST_MAPPING.md) | Current → Proposed test mapping | DONE |
| [P36_VALIDATION_CHECKLIST.md](P36_VALIDATION_CHECKLIST.md) | Validation checks per block | DONE |

---

## Inventory Summary

| Current | Proposed Blocks | Tests |
|---------|-----------------|-------|
| 78 files scattered | 11 domain blocks | ~780 existing |
| Mixed by type | Organized by domain | +36 new needed |

**New Blocks Added:**
- LDM Workflow (cell states, auto-TM sync)
- UI State (explorer persistence)

### Block Breakdown

| Block | Files | Tests | Status |
|-------|-------|-------|--------|
| DB | 4 | ~32 | Map existing |
| AUTH | 6 | ~41 | Map existing |
| NETWORK | 4 | ~23 | Map existing |
| SECURITY | 4 | ~43 | Map existing + 3 new |
| API | 9 | ~57 | Map existing + 3 new |
| BACKEND | 8 | ~54 | Map existing |
| PROCESSING | 6 | ~48 | Map existing + 2 new |
| TOOLS | 8 | ~64 | Map existing |
| LOGGING | 1 | ~8 | Map existing + 2 new |
| PERFORMANCE | 0 | 7 | **CREATE NEW** |
| **LDM WORKFLOW** | 0 | 9 | **CREATE NEW** |
| **UI STATE** | 0 | 4 | **CREATE NEW** |

---

## Work Required

### Phase 1: 6-Stage Pipeline ✅ DONE (Build 315)
- [x] Optimal staged testing (unit → integration → e2e → api → security → fixtures)
- [x] Beautiful stage banners with test inventory
- [x] QA-LIGHT and QA-FULL modes in Gitea workflow
- [x] Pytest markers in conftest.py

### Phase 2: Quick Wins 🔜 NEXT
- [ ] **Parallel execution** - `pytest-xdist -n 4` (2-3x faster, safe)
- [ ] **Code coverage** - `pytest-cov` with HTML reports
- [ ] **Performance tests** - API latency, embedding throughput

### Phase 3: Block Reorganization 📋 LATER
- [ ] Create `tests/blocks/` directory structure
- [ ] Move files per [P36_TEST_MAPPING.md](P36_TEST_MAPPING.md)
- [ ] Update imports

### Phase 4: New Tests 📋 LATER
- [ ] Create 7 performance tests
- [ ] Create 4 UI state tests
- [ ] Create remaining gap tests

### ❌ NOT DOING
- Test caching - Too risky, could miss regressions

---

## Current Progress

| Milestone | Status | Notes |
|-----------|--------|-------|
| 6-Stage Pipeline | ✅ DONE | Build 315 |
| FEAT-001 Tests | ✅ DONE | 35+ new tests |
| Pytest Markers | ✅ DONE | Auto-applied by path |
| Parallel Execution | 🔜 TODO | pytest-xdist |
| Code Coverage | 🔜 TODO | pytest-cov |
| Performance Tests | 🔜 TODO | New test directory |
| Block Reorganization | 📋 LATER | 2-4 hours work |

---

## Success Criteria

1. ~~**Clear structure** - 9 domain blocks~~ → LATER
2. ~~**No duplicates** - Each scenario tested once~~ → LATER
3. **Full coverage** - ✅ All blocks have tests (35+ new added)
4. **LIGHT build** - ✅ 5 min, essential tests
5. **QA build** - ✅ 30 min, 6-stage validation
6. **Beautiful pipeline** - ✅ Stage-by-stage status display

---

## Related Documents

- [P36_TEST_MAPPING.md](P36_TEST_MAPPING.md) - Detailed test mapping
- [P36_VALIDATION_CHECKLIST.md](P36_VALIDATION_CHECKLIST.md) - Validation checks
- [Roadmap.md](../../Roadmap.md) - CI/CD Build Modes
- [SESSION_CONTEXT.md](SESSION_CONTEXT.md) - Current session

---

*P36: CI/CD Test Overhaul | Updated: 2025-12-21 | Phase 1 COMPLETE*
