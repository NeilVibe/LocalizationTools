# P36: Test Mapping - Current to Proposed Structure

**Status:** PLANNING | **Created:** 2025-12-21

---

## Current Inventory Summary

| Category | Files | Functions (est.) |
|----------|-------|------------------|
| unit/ | 27 | ~300 |
| integration/ | 12 | ~150 |
| e2e/ | 8 | ~80 |
| security/ | 4 | ~50 |
| api/ | 7 | ~70 |
| fixtures/ | 12 | ~100 |
| cdp/ | 3 | ~30 |
| **TOTAL** | **73** | **~780** |

---

## Proposed Block Structure

```
tests/
├── blocks/                    # DOMAIN-based (parallel execution)
│   ├── db/                    # Database
│   ├── auth/                  # Authentication
│   ├── network/               # WebSocket, HTTP
│   ├── security/              # JWT, CORS, IP, Audit
│   ├── api/                   # API endpoints
│   ├── backend/               # Server, cache, utils
│   ├── processing/            # TM, embeddings, normalizer
│   ├── tools/                 # KR Similar, QuickSearch, XLS Transfer
│   └── logging/               # Logging
│
├── e2e/                       # Full workflows (sequential)
│
├── ui/                        # CDP browser tests
│
├── performance/               # Speed/stress tests (optional)
│
└── archive/                   # Old tests to review
```

---

## Detailed Test Mapping

### BLOCK: db/

**Purpose:** Database connectivity, queries, models, utilities

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_db_utils.py | unit/ | 8 | Session, normalization |
| test_dependencies_module.py | unit/ | 8 | DB init, engine, session |
| test_models.py | unit/ | 8 | User model CRUD |
| test_database_connectivity.py | integration/ | 6 | PostgreSQL connection |

**Total: 4 files, ~30 functions**

**Validation Checks:**
- [ ] PostgreSQL connectivity
- [ ] SQLite fallback works
- [ ] Session creation/cleanup
- [ ] Model CRUD operations
- [ ] Query performance < 100ms

---

### BLOCK: auth/

**Purpose:** Authentication, password hashing, JWT, sessions, permissions

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_auth_module.py | unit/ | 8 | Password hash/verify |
| test_user_management.py | unit/ | 8 | User CRUD, password change |
| test_auth_integration.py | integration/ | 6 | User creation, sessions |
| test_async_auth.py | integration/ | ? | Async auth |
| test_async_sessions.py | integration/ | ? | Session management |
| test_api_auth_integration.py | api/ | 6 | Login flow via API |

**Total: 6 files, ~40 functions**

**Validation Checks:**
- [ ] Password hashing (bcrypt)
- [ ] Password verification
- [ ] JWT token generation
- [ ] JWT token validation
- [ ] Session creation
- [ ] Session expiration
- [ ] Permission checks

---

### BLOCK: network/

**Purpose:** WebSocket, HTTP, CORS, connections

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_websocket.py | unit/ | 1 | Basic import |
| test_websocket_module.py | unit/ | 8 | Socket.IO setup |
| test_websocket_functions.py | unit/ | 8 | Emit functions |
| test_api_websocket.py | api/ | 5 | WS endpoints |

**Total: 4 files, ~22 functions**

**Validation Checks:**
- [ ] WebSocket connection
- [ ] Message emit/receive
- [ ] Client tracking
- [ ] Broadcast functions
- [ ] Connection cleanup

---

### BLOCK: security/

**Purpose:** JWT security, CORS, IP filtering, audit logging, XSS prevention

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_jwt_security.py | security/ | 10 | Secret key, config validation |
| test_cors_config.py | security/ | 10 | CORS origins, methods |
| test_ip_filter.py | security/ | 10 | IP range parsing, filtering |
| test_audit_logging.py | security/ | 10 | Event logging, severity |

**Total: 4 files, ~40 functions**

**Validation Checks:**
- [ ] Secret key not default
- [ ] CORS properly configured
- [ ] IP whitelist works
- [ ] Audit events logged
- [ ] No XSS vulnerabilities
- [ ] No SQL injection
- [ ] Rate limiting works

---

### BLOCK: api/

**Purpose:** REST API endpoints, error handling, responses

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_api_endpoints.py | integration/ | 6 | Basic endpoints |
| test_api_endpoints_detailed.py | integration/ | 6 | Search, status |
| test_api_true_simulation.py | integration/ | 6 | Health, docs |
| test_api_error_handling.py | api/ | 6 | Error responses |
| test_api_admin_simulation.py | api/ | 6 | Admin endpoints |
| test_api_full_system_integration.py | api/ | 6 | Full flow |
| test_api_tools_simulation.py | api/ | 6 | Tool endpoints |
| test_dashboard_api.py | integration/ | 6 | Dashboard stats |
| test_remote_logging.py | api/ | 6 | Remote log endpoint |

**Total: 9 files, ~54 functions**

**Validation Checks:**
- [ ] All endpoints respond
- [ ] Correct status codes
- [ ] Proper error messages
- [ ] Authentication required where needed
- [ ] Rate limiting on sensitive endpoints

---

### BLOCK: backend/

**Purpose:** Server startup, cache, utilities, async infrastructure

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_cache.py | unit/ | 7 | Cache manager |
| test_cache_module.py | unit/ | 8 | Cache imports |
| test_cache_extended.py | unit/ | 8 | Cache TTL, Redis |
| test_utils_file_handler.py | unit/ | 8 | File size, hash |
| test_utils_logger.py | unit/ | 8 | Logger init |
| test_utils_progress.py | unit/ | 8 | Progress tracker |
| test_server_startup.py | integration/ | 6 | Server routes |
| test_async_infrastructure.py | integration/ | 1 | Async compat |

**Total: 8 files, ~54 functions**

**Validation Checks:**
- [ ] Server starts successfully
- [ ] All routes registered
- [ ] Cache functions work
- [ ] File utilities work
- [ ] Logger initializes
- [ ] Progress tracking works

---

### BLOCK: processing/

**Purpose:** TM operations, embeddings, normalization, FAISS

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_tm_normalizer.py | unit/ | 8 | Text normalization |
| test_tm_search.py | unit/ | 8 | Search algorithms |
| test_tm_sync.py | unit/ | 8 | TM sync logic |
| test_npc.py | unit/ | 8 | NPC threshold |
| test_code_patterns.py | unit/ | 8 | Tag reconstruction |
| test_tm_real_model.py | integration/ | 6 | Real model tests |

**Total: 6 files, ~46 functions**

**Validation Checks:**
- [ ] Text normalization correct
- [ ] Newline handling
- [ ] Tag extraction
- [ ] Tag reconstruction
- [ ] Embedding generation
- [ ] FAISS index building
- [ ] Similarity search accurate

---

### BLOCK: tools/

**Purpose:** KR Similar, QuickSearch, XLS Transfer

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_kr_similar_core.py | unit/ | 8 | Core normalization |
| test_kr_similar_embeddings.py | unit/ | 8 | Embeddings |
| test_quicksearch_dictionary.py | unit/ | 8 | Dict manager |
| test_quicksearch_parser.py | unit/ | 8 | Text parser |
| test_quicksearch_qa_tools.py | unit/ | 8 | QA tools |
| test_quicksearch_searcher.py | unit/ | 8 | Searcher |
| test_quicksearch_tools.py | unit/ | 8 | Tools |
| test_xlstransfer_modules.py | unit/ | 8 | XLS modules |

**Total: 8 files, ~64 functions**

**Validation Checks:**
- [ ] KR Similar: Dictionary creation
- [ ] KR Similar: Similarity search
- [ ] QuickSearch: Dictionary load
- [ ] QuickSearch: Search functions
- [ ] XLS Transfer: Excel parsing
- [ ] XLS Transfer: Translation matching

---

### BLOCK: logging/

**Purpose:** Server logging, client logging, remote logging

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_logging_integration.py | integration/ | 6 | Log operations |

**Total: 1 file, ~6 functions**

**GAP IDENTIFIED:** Need more logging tests

**Validation Checks:**
- [ ] Log entries created
- [ ] Log levels correct
- [ ] Remote logging works
- [ ] Log rotation works
- [ ] Sensitive data not logged

---

### E2E: Full Workflows

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_complete_user_flow.py | e2e/ | 8 | Full user journey |
| test_full_simulation.py | e2e/ | 8 | Full workflow |
| test_kr_similar_e2e.py | e2e/ | 8 | KR Similar flow |
| test_quicksearch_e2e.py | e2e/ | 8 | QuickSearch flow |
| test_xlstransfer_e2e.py | e2e/ | 8 | XLS Transfer flow |
| test_production_workflows_e2e.py | e2e/ | 8 | Production scenarios |
| test_real_workflows_e2e.py | e2e/ | 8 | Real data |
| test_edge_cases_e2e.py | e2e/ | 8 | Edge cases |
| test_e2e_*.py | fixtures/ | ~60 | TM upload, search, pretranslate |

**Total: ~20 files, ~130 functions**

---

### UI: Browser Tests

| Current File | Current Location | Functions | Notes |
|--------------|------------------|-----------|-------|
| test_download_format.py | cdp/ | ~10 | Download tests |
| test_full_user_simulation.py | cdp/ | ~10 | User simulation |
| test_ultimate_smoke.py | cdp/ | ~10 | Smoke tests |

**Total: 3 files, ~30 functions**

---

## Coverage Gaps Identified

### CRITICAL GAPS

| Area | Issue | Priority |
|------|-------|----------|
| **Performance** | No latency/throughput tests | HIGH |
| **Logging** | Only 1 test file | MEDIUM |
| **Error Recovery** | No failure recovery tests | HIGH |
| **Stress Testing** | No concurrent user tests | MEDIUM |
| **Memory** | No memory leak tests | LOW |

### MISSING TESTS

1. **Performance Block (NEW)**
   - API response time < 200ms
   - Embedding generation speed
   - FAISS search speed
   - Database query speed
   - WebSocket message latency

2. **Error Recovery**
   - Database connection lost → reconnect
   - Model file corrupted → graceful error
   - Disk full → proper error message

3. **Stress Testing**
   - 100 concurrent API requests
   - Large file upload (100MB)
   - Large TM (1M entries)

---

## Proposed Migration Steps

### Phase 1: Create Structure
```bash
mkdir -p tests/blocks/{db,auth,network,security,api,backend,processing,tools,logging}
mkdir -p tests/performance
mkdir -p tests/archive
```

### Phase 2: Move Files

| From | To |
|------|----|
| unit/test_db_utils.py | blocks/db/ |
| unit/test_models.py | blocks/db/ |
| unit/test_auth_module.py | blocks/auth/ |
| security/*.py | blocks/security/ |
| ... | ... |

### Phase 3: Add Markers

```python
# blocks/db/test_connectivity.py
import pytest

@pytest.mark.db
@pytest.mark.unit
def test_connection():
    ...

@pytest.mark.db
@pytest.mark.integration
def test_reconnection():
    ...
```

### Phase 4: Create Performance Tests

```python
# performance/test_api_latency.py
import pytest
import time

@pytest.mark.performance
@pytest.mark.slow
def test_api_response_under_200ms(client):
    start = time.time()
    response = client.get("/health")
    elapsed = (time.time() - start) * 1000
    assert elapsed < 200, f"Response took {elapsed}ms"
```

---

## QA Pipeline Architecture

```
QA-LIGHT / QA-FULL PIPELINE
════════════════════════════════════════════════════════════════

PHASE 1: BLOCK TESTS (Parallel) ─────────────────────────────────
┌──────┐ ┌──────┐ ┌─────────┐ ┌──────────┐ ┌─────┐
│  DB  │ │ AUTH │ │ NETWORK │ │ SECURITY │ │ API │
│ ~30  │ │ ~40  │ │   ~22   │ │   ~40    │ │ ~54 │
└──────┘ └──────┘ └─────────┘ └──────────┘ └─────┘
┌─────────┐ ┌────────────┐ ┌───────┐ ┌─────────┐
│ BACKEND │ │ PROCESSING │ │ TOOLS │ │ LOGGING │
│   ~54   │ │    ~46     │ │  ~64  │ │   ~6    │
└─────────┘ └────────────┘ └───────┘ └─────────┘
                    ↓
PHASE 2: E2E TESTS (Sequential) ─────────────────────────────────
┌────────────────────────────────────────────────────────────────┐
│   Complete User Flows   │   Tool Workflows   │   Edge Cases   │
│          ~130 tests                                            │
└────────────────────────────────────────────────────────────────┘
                    ↓
PHASE 3: UI TESTS (Browser) ─────────────────────────────────────
┌────────────────────────────────────────────────────────────────┐
│   CDP Tests   │   Full User Simulation   │   Smoke Tests      │
│          ~30 tests                                             │
└────────────────────────────────────────────────────────────────┘
                    ↓
PHASE 4: PERFORMANCE (Optional) ─────────────────────────────────
┌────────────────────────────────────────────────────────────────┐
│   API Latency   │   DB Speed   │   Embedding Speed   │  Stress │
└────────────────────────────────────────────────────────────────┘
                    ↓
                SUCCESS → BUILD INSTALLER
════════════════════════════════════════════════════════════════

LIGHT:    Phase 1 (essential only, ~285 tests)     →  5 min
FULL:     Phase 1 (essential only) + installer     → 15 min
QA-LIGHT: Phase 1-4 (ALL tests, ~780+)             → 30 min
QA-FULL:  Phase 1-4 (ALL tests) + full installer   → 45 min
```

---

## Validation Checklist Template

Each block should validate:

```
□ IMPORTS     - All modules import without error
□ UNIT        - Individual functions work correctly
□ INTEGRATION - Components work together
□ ERRORS      - Errors handled gracefully
□ EDGE CASES  - Boundary conditions covered
□ PERFORMANCE - Speed within acceptable limits
```

---

## Next Steps

1. **Review this mapping** - Is it accurate?
2. **Decide on migration strategy** - Big bang or incremental?
3. **Create performance tests** - Fill the critical gap
4. **Update CI/CD workflow** - Implement QA modes
5. **Execute migration** - Move files, add markers

---

*P36 Test Mapping | Created 2025-12-21*
