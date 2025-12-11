# LocaNext System Architecture

---

## System Overview

```
+==================================================================================+
|                              LOCANEXT PLATFORM                                    |
+==================================================================================+

     +-------------------------+          +-------------------------+
     |      USER'S PC          |          |     CENTRAL SERVER      |
     |     (Windows .exe)      |          |    (Cloud/On-Premise)   |
     +-------------------------+          +-------------------------+
     |                         |          |                         |
     |  +-------------------+  |   HTTPS  |  +-------------------+  |
     |  |   LocaNext.exe    |  |  ------> |  |  FastAPI Server   |  |
     |  |   (Electron)      |  |  <------ |  |  (Python 3.11+)   |  |
     |  +-------------------+  |   WSS    |  +-------------------+  |
     |           |             |          |           |             |
     |           v             |          |           v             |
     |  +-------------------+  |          |  +-------------------+  |
     |  |  Embedded Python  |  |          |  |    PostgreSQL     |  |
     |  |  Backend Server   |  |          |  |    Database       |  |
     |  +-------------------+  |          |  +-------------------+  |
     |           |             |          |           |             |
     |           v             |          |           v             |
     |  +-------------------+  |          |  +-------------------+  |
     |  |  SQLite (Local)   |  |          |  |  Admin Dashboard  |  |
     |  |  User Data Only   |  |          |  |  (Web Interface)  |  |
     |  +-------------------+  |          |  +-------------------+  |
     |                         |          |                         |
     +-------------------------+          +-------------------------+
```

---

## Communication Protocols

| Layer | Protocol | Port | Purpose |
|-------|----------|------|---------|
| API | REST/HTTPS | 443 | Data exchange |
| Real-time | WebSocket (WSS) | 443 | Live updates |
| Database | PostgreSQL | 5432 | Central storage |
| Local DB | SQLite | - | Offline data |

---

## Security Protocols

```
+------------------------------------------------------------------+
|                    SECURITY LAYERS                                |
+------------------------------------------------------------------+
|                                                                   |
|  1. IP RANGE FILTERING (Primary)                                  |
|     - Only company network IPs allowed (e.g., 192.168.11.0/24)    |
|     - All other IPs receive 403 Forbidden                         |
|                                                                   |
|  2. CORS (Cross-Origin Resource Sharing)                          |
|     - Whitelist of allowed origins only                           |
|     - Blocks requests from unauthorized domains                   |
|                                                                   |
|  3. JWT AUTHENTICATION                                            |
|     - Access Token: 30 minutes                                    |
|     - Refresh Token: 7 days                                       |
|     - Secure key generation required                              |
|                                                                   |
|  4. TLS/HTTPS ENCRYPTION                                          |
|     - All data encrypted in transit                               |
|     - TLS 1.2/1.3 supported                                       |
|                                                                   |
|  5. AUDIT LOGGING                                                 |
|     - All login attempts logged                                   |
|     - Failed access attempts tracked                              |
|     - 1 year retention                                            |
|                                                                   |
|  6. INPUT VALIDATION                                              |
|     - SQL Injection: Protected (SQLAlchemy ORM)                   |
|     - XSS: Sanitized inputs                                       |
|     - Path Traversal: Blocked                                     |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Database Architecture

```
+------------------------------------------------------------------+
|                    DATABASE STRUCTURE                             |
+------------------------------------------------------------------+

USER'S LOCAL (SQLite)              CENTRAL SERVER (PostgreSQL)
+---------------------+            +---------------------------+
| users               |            | users                     |
| projects            |            | projects (aggregated)     |
| files               |            | telemetry_events          |
| translation_memory  |            | telemetry_tool_events     |
| sessions            |            | sessions (all users)      |
+---------------------+            | audit_logs                |
                                   | error_reports             |
                                   +---------------------------+

17 Tables Total | 63+ API Endpoints | 912 Tests
```

---

## Application Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Desktop App | Electron + Svelte | User interface |
| Backend | FastAPI + Python | API + Processing |
| Database | PostgreSQL/SQLite | Data storage |
| Real-time | Socket.IO | Live updates |
| Admin | SvelteKit | Monitoring |

---

## Data Flow

```
USER ACTION                    PROCESSING                    RESULT
+-----------+    +-------------------------------------+    +--------+
| User      | -> | Local Backend                       | -> | Output |
| uploads   |    | (Python processes on user's CPU)    |    | file   |
| Excel     |    | - No data sent to cloud             |    |        |
+-----------+    | - Works offline                     |    +--------+
                 | - Fast (no network latency)         |
                 +-------------------------------------+
                              |
                              | (Optional) Telemetry
                              v
                 +-------------------------------------+
                 | Central Server                      |
                 | - Usage statistics                  |
                 | - Error tracking                    |
                 | - Update distribution               |
                 +-------------------------------------+
```

---

## Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Unit Tests | 377+ | PASS |
| API Tests | 168 | PASS |
| Security Tests | 86 | PASS |
| E2E Tests | 164 | PASS |
| **Total** | **912** | **100%** |

---

*LocaNext v2512110832*
