# P36: QA Validation Checklist

**Status:** PLANNING | **Created:** 2025-12-21

This document defines what each pipeline block must validate for PRISTINE quality.

---

## Block Validation Matrix

| Block | Unit | Integration | Error Handling | Performance | Security |
|-------|------|-------------|----------------|-------------|----------|
| DB | Yes | Yes | Yes | Yes | No |
| AUTH | Yes | Yes | Yes | No | Yes |
| NETWORK | Yes | Yes | Yes | Yes | No |
| SECURITY | Yes | Yes | Yes | No | Yes |
| API | Yes | Yes | Yes | Yes | Yes |
| BACKEND | Yes | Yes | Yes | Yes | No |
| PROCESSING | Yes | Yes | Yes | Yes | No |
| TOOLS | Yes | Yes | Yes | Yes | No |
| LOGGING | Yes | Yes | Yes | No | Yes |

---

## BLOCK: DB (Database)

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| DB-001 | PostgreSQL connection succeeds | Integration | < 1s |
| DB-002 | SQLite fallback works when PostgreSQL down | Integration | - |
| DB-003 | Session creation works | Unit | - |
| DB-004 | Session cleanup happens | Unit | - |
| DB-005 | User model CRUD works | Unit | - |
| DB-006 | TM model CRUD works | Unit | - |
| DB-007 | Project model CRUD works | Unit | - |
| DB-008 | Query returns within limit | Performance | < 100ms |
| DB-009 | Connection pool handles 10 concurrent | Performance | - |
| DB-010 | Graceful error on connection lost | Error | - |

### New Tests Needed

- [ ] DB-009: Connection pool stress test
- [ ] DB-010: Connection recovery test

---

## BLOCK: AUTH (Authentication)

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| AUTH-001 | Password hashing uses bcrypt | Unit | - |
| AUTH-002 | Password verification works | Unit | - |
| AUTH-003 | Wrong password rejected | Unit | - |
| AUTH-004 | JWT token generation works | Unit | - |
| AUTH-005 | JWT token validation works | Unit | - |
| AUTH-006 | Expired token rejected | Unit | - |
| AUTH-007 | Invalid token rejected | Unit | - |
| AUTH-008 | Session creation works | Integration | - |
| AUTH-009 | Session expiration enforced | Integration | - |
| AUTH-010 | User creation works | Integration | - |
| AUTH-011 | User deactivation works | Integration | - |
| AUTH-012 | Admin permissions enforced | Integration | - |
| AUTH-013 | Brute force protection | Security | 5 attempts/min |

### New Tests Needed

- [ ] AUTH-013: Rate limiting / brute force test

---

## BLOCK: NETWORK (WebSocket, HTTP)

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| NET-001 | Socket.IO server starts | Unit | - |
| NET-002 | Client connection works | Integration | - |
| NET-003 | Message emit works | Unit | - |
| NET-004 | Broadcast works | Unit | - |
| NET-005 | Client tracking accurate | Unit | - |
| NET-006 | Disconnection cleanup | Integration | - |
| NET-007 | CORS headers present | Integration | - |
| NET-008 | WS message latency | Performance | < 50ms |

### New Tests Needed

- [ ] NET-008: WebSocket latency measurement

---

## BLOCK: SECURITY

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| SEC-001 | Secret key not default | Unit | - |
| SEC-002 | Secret key length >= 32 | Unit | - |
| SEC-003 | CORS origins configured | Unit | - |
| SEC-004 | No wildcard CORS in production | Unit | - |
| SEC-005 | IP filter parses correctly | Unit | - |
| SEC-006 | IP filter blocks correctly | Integration | - |
| SEC-007 | Localhost always allowed | Unit | - |
| SEC-008 | Audit events logged | Unit | - |
| SEC-009 | Login attempts logged | Unit | - |
| SEC-010 | Failed logins logged | Unit | - |
| SEC-011 | No SQL injection possible | Security | - |
| SEC-012 | No XSS in responses | Security | - |
| SEC-013 | Sensitive data not in logs | Security | - |

### New Tests Needed

- [ ] SEC-011: SQL injection test
- [ ] SEC-012: XSS prevention test
- [ ] SEC-013: Log sanitization test

---

## BLOCK: API

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| API-001 | Health endpoint returns 200 | Unit | - |
| API-002 | Docs endpoint accessible | Unit | - |
| API-003 | Login returns token | Integration | - |
| API-004 | Invalid login returns 401 | Integration | - |
| API-005 | Protected endpoints require auth | Integration | - |
| API-006 | Admin endpoints require admin | Integration | - |
| API-007 | Error responses have correct format | Unit | - |
| API-008 | All tool endpoints work | Integration | - |
| API-009 | Dashboard stats endpoint works | Integration | - |
| API-010 | Response time acceptable | Performance | < 200ms |
| API-011 | Large payload handled | Performance | 10MB |
| API-012 | Concurrent requests handled | Performance | 50 req/s |

### New Tests Needed

- [ ] API-010: Response time benchmark
- [ ] API-011: Large payload test
- [ ] API-012: Concurrent request test

---

## BLOCK: BACKEND

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| BE-001 | Server starts successfully | Integration | < 5s |
| BE-002 | All routes registered | Unit | - |
| BE-003 | Cache manager initializes | Unit | - |
| BE-004 | Cache get/set works | Unit | - |
| BE-005 | Cache TTL enforced | Integration | - |
| BE-006 | File size calculation correct | Unit | - |
| BE-007 | File hash calculation correct | Unit | - |
| BE-008 | Logger initializes | Unit | - |
| BE-009 | Progress tracker works | Unit | - |
| BE-010 | Async/await compatibility | Integration | - |

### New Tests Needed

None identified.

---

## BLOCK: PROCESSING

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| PROC-001 | Text normalization correct | Unit | - |
| PROC-002 | Newline handling correct | Unit | - |
| PROC-003 | Windows line endings handled | Unit | - |
| PROC-004 | Tag extraction works | Unit | - |
| PROC-005 | Tag reconstruction works | Unit | - |
| PROC-006 | Embedding model loads | Integration | < 30s |
| PROC-007 | Embedding generation works | Unit | - |
| PROC-008 | FAISS index builds | Integration | - |
| PROC-009 | Similarity search accurate | Unit | > 0.8 |
| PROC-010 | TM sync insert works | Unit | - |
| PROC-011 | TM sync update works | Unit | - |
| PROC-012 | TM sync delete works | Unit | - |
| PROC-013 | Embedding speed acceptable | Performance | > 100/sec |
| PROC-014 | Search speed acceptable | Performance | < 100ms |

### New Tests Needed

- [ ] PROC-013: Embedding throughput test
- [ ] PROC-014: Search speed benchmark

---

## BLOCK: TOOLS

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| TOOL-001 | KR Similar: Module imports | Unit | - |
| TOOL-002 | KR Similar: Dictionary creation | Integration | - |
| TOOL-003 | KR Similar: Dictionary loading | Integration | - |
| TOOL-004 | KR Similar: Search works | Integration | - |
| TOOL-005 | KR Similar: Accuracy acceptable | Unit | > 0.85 |
| TOOL-006 | QuickSearch: Dictionary creation | Integration | - |
| TOOL-007 | QuickSearch: Dictionary loading | Integration | - |
| TOOL-008 | QuickSearch: Exact match works | Unit | - |
| TOOL-009 | QuickSearch: Contains search works | Unit | - |
| TOOL-010 | QuickSearch: StringID search works | Unit | - |
| TOOL-011 | XLS Transfer: Excel parsing works | Unit | - |
| TOOL-012 | XLS Transfer: Dictionary creation | Integration | - |
| TOOL-013 | XLS Transfer: Translation matching | Integration | - |
| TOOL-014 | XLS Transfer: Tag preservation | Unit | - |

### New Tests Needed

None identified - good coverage.

---

## BLOCK: LOGGING

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| LOG-001 | Log entry creation works | Unit | - |
| LOG-002 | Log levels correct | Unit | - |
| LOG-003 | Remote logging endpoint works | Integration | - |
| LOG-004 | Log querying works | Integration | - |
| LOG-005 | Sensitive data not logged | Security | - |
| LOG-006 | Log rotation works | Integration | - |

### New Tests Needed

- [ ] LOG-005: Sensitive data check
- [ ] LOG-006: Log rotation test

---

## BLOCK: LDM Workflow (Language Data Manager)

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| LDM-001 | File upload via API works | Integration | - |
| LDM-002 | File parsing creates cells | Unit | - |
| LDM-003 | Cell edit modal opens | UI | - |
| LDM-004 | Empty → pending on edit | Unit | - |
| LDM-005 | Pending → translated (Ctrl+T) | Integration | - |
| LDM-006 | Pending → reviewed (Ctrl+S) | Integration | - |
| LDM-007 | Auto-add to TM on confirm | Integration | - |
| LDM-008 | TM index rebuilds after confirm | Integration | < 5s |
| LDM-009 | Cell states persist after reload | Integration | - |
| LDM-010 | TM entry can be edited | Integration | - |
| LDM-011 | TM entry can be deleted | Integration | - |
| LDM-012 | TM index updates after edit | Integration | < 5s |

### New Tests Needed

- [ ] LDM-004: Cell state empty → pending
- [ ] LDM-005: Cell state pending → translated
- [ ] LDM-006: Cell state pending → reviewed
- [ ] LDM-007: Auto-sync TM on confirm
- [ ] LDM-008: Index rebuild trigger
- [ ] LDM-009: State persistence test
- [ ] LDM-010: TM entry edit
- [ ] LDM-011: TM entry delete
- [ ] LDM-012: Index update after edit

---

## BLOCK: UI State

### Must Pass

| ID | Check | Type | Threshold |
|----|-------|------|-----------|
| STATE-001 | File explorer project selection persists | Integration | - |
| STATE-002 | File explorer expanded folders persist | Integration | - |
| STATE-003 | TM explorer selection persists | Integration | - |
| STATE-004 | TM explorer filter state persists | Integration | - |
| STATE-005 | Scroll positions persist after tab switch | Integration | - |

### New Tests Needed

- [ ] STATE-001: Project selection persistence
- [ ] STATE-002: Folder expansion persistence
- [ ] STATE-003: TM selection persistence
- [ ] STATE-004: Filter state persistence

---

## E2E: Full Workflows

### Must Pass

| ID | Check | Type |
|----|-------|------|
| E2E-001 | Complete user registration → login → use tool → logout | Flow |
| E2E-002 | TM upload → index → search | Flow |
| E2E-003 | TM pretranslation workflow | Flow |
| E2E-004 | KR Similar full workflow | Flow |
| E2E-005 | QuickSearch full workflow | Flow |
| E2E-006 | XLS Transfer full workflow | Flow |
| E2E-007 | Edge cases handled gracefully | Error |
| E2E-008 | **File viewer → edit cell → confirm → auto-add TM** | Flow |
| E2E-009 | **Cell state machine full cycle** | Flow |

---

## UI: Browser Tests

### Must Pass

| ID | Check | Type |
|----|-------|------|
| UI-001 | App loads in browser | Smoke |
| UI-002 | Login form works | Integration |
| UI-003 | Main navigation works | Integration |
| UI-004 | Tool interfaces load | Integration |
| UI-005 | File download works | Integration |

---

## PERFORMANCE: Benchmarks

### Must Pass

| ID | Check | Threshold |
|----|-------|-----------|
| PERF-001 | API health check | < 50ms |
| PERF-002 | Login endpoint | < 200ms |
| PERF-003 | TM search (1k entries) | < 100ms |
| PERF-004 | TM search (100k entries) | < 500ms |
| PERF-005 | Embedding generation | > 100 texts/sec |
| PERF-006 | File upload (10MB) | < 5s |
| PERF-007 | Concurrent requests (50) | No failures |

---

## Summary: Test Counts by Block

| Block | Existing | New Needed | Total |
|-------|----------|------------|-------|
| DB | 30 | 2 | 32 |
| AUTH | 40 | 1 | 41 |
| NETWORK | 22 | 1 | 23 |
| SECURITY | 40 | 3 | 43 |
| API | 54 | 3 | 57 |
| BACKEND | 54 | 0 | 54 |
| PROCESSING | 46 | 2 | 48 |
| TOOLS | 64 | 0 | 64 |
| LOGGING | 6 | 2 | 8 |
| **LDM Workflow** | 0 | 9 | 9 |
| **UI State** | 0 | 4 | 4 |
| E2E | 130 | 2 | 132 |
| UI | 30 | 0 | 30 |
| PERFORMANCE | 0 | 7 | 7 |
| **TOTAL** | **516** | **36** | **552** |

---

## Priority: New Tests to Create

### CRITICAL Priority (must have for QA)

1. **LDM-007: Auto-add to TM on confirm** - Core workflow
2. **LDM-005/006: Cell state transitions** - pending→translated→reviewed
3. PERF-001 to PERF-007: Performance benchmarks
4. **E2E-008: File viewer → confirm → TM** - Full LDM workflow

### HIGH Priority (should have)

1. LDM-008: TM index rebuild after confirm
2. LDM-009: Cell state persistence
3. LDM-010/011: TM entry edit/delete
4. SEC-011: SQL injection test
5. SEC-012: XSS prevention test
6. API-012: Concurrent request test

### MEDIUM Priority (nice to have)

1. STATE-001 to STATE-004: Explorer state persistence
2. DB-009: Connection pool test
3. DB-010: Connection recovery
4. AUTH-013: Brute force protection
5. LOG-005: Sensitive data check

### LOW Priority

1. NET-008: WebSocket latency
2. LOG-006: Log rotation

---

*P36 Validation Checklist | Created 2025-12-21*
