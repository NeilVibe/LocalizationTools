# LocaNext System Architecture

---

## System Overview

### DEPLOYMENT MODEL

**User's PC (Windows .exe)**
- LocaNext.exe (Electron desktop app)
- Embedded Python Backend Server
- Connects to Central PostgreSQL Database
- Local processing on user's CPU (FAST)
- Works with company network

**Central Server (Cloud/On-Premise)**
- FastAPI Server (Python 3.11+)
- **PostgreSQL Database** (ALL data)
- PgBouncer connection pooling (1000 connections)
- Admin Dashboard (web interface)

**Communication:**
- HTTPS (REST API) for data exchange
- WSS (WebSocket) for real-time updates

---

## Database: PostgreSQL Only

### Why PostgreSQL?

| Feature | Benefit |
|---------|---------|
| COPY TEXT bulk insert | 31,000 entries/second |
| Full-Text Search (tsvector) | Fast search |
| GIN trigram indexes | Similarity matching |
| PgBouncer pooling | 1000 concurrent connections |
| Enterprise reliability | Production-grade |
| Backup & Recovery | Built-in tools |

### Database Statistics

| Metric | Value |
|--------|-------|
| Tables | 17 |
| API Endpoints | 63+ |
| Tests | 912 |
| Bulk Insert Speed | 31K entries/sec |

---

## Communication Protocols

| Layer | Protocol | Port | Purpose |
|-------|----------|------|---------|
| API | REST/HTTPS | 443 | Data exchange |
| Real-time | WebSocket (WSS) | 443 | Live updates |
| Database | PostgreSQL | 5432 | Direct |
| Connection Pool | PgBouncer | 6433 | Pooled |

---

## Security Layers

### 1. IP RANGE FILTERING (Primary)
- Only company network IPs allowed (e.g., 192.168.11.0/24)
- All other IPs receive 403 Forbidden

### 2. CORS (Cross-Origin Resource Sharing)
- Whitelist of allowed origins only
- Blocks requests from unauthorized domains

### 3. JWT AUTHENTICATION
- Access Token: 30 minutes
- Refresh Token: 7 days
- Secure key generation required

### 4. TLS/HTTPS ENCRYPTION
- All data encrypted in transit
- TLS 1.2/1.3 supported

### 5. AUDIT LOGGING
- All login attempts logged
- Failed access attempts tracked
- 1 year retention

### 6. INPUT VALIDATION
- SQL Injection: Protected (SQLAlchemy ORM)
- XSS: Sanitized inputs
- Path Traversal: Blocked

---

## PostgreSQL Tables

| Table | Purpose |
|-------|---------|
| users | User accounts |
| projects | All projects |
| ldm_projects | LDM projects |
| ldm_files | Translation files |
| ldm_rows | Translation rows |
| ldm_translation_memory | TM databases |
| ldm_tm_entries | TM entries |
| telemetry_events | Usage tracking |
| audit_logs | Security logs |
| sessions | Login sessions |

**Total: 17 Tables**

---

## Application Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Desktop App | Electron + Svelte | User interface |
| Backend | FastAPI + Python | API + Processing |
| Database | **PostgreSQL** | ALL data storage |
| Connection Pool | PgBouncer | Performance |
| Real-time | Socket.IO | Live updates |
| Admin Dashboard | SvelteKit | Monitoring |

---

## Data Flow

### Step 1: User Action
User opens LDM, loads translation file

### Step 2: Database Query
- FastAPI queries PostgreSQL
- PgBouncer manages connections
- Full-text search for TM matches

### Step 3: Local Processing
- Python processes on user's CPU
- Translation memory suggestions
- Real-time updates via WebSocket

### Step 4: Save to Database
- Changes saved to PostgreSQL
- COPY TEXT for bulk operations
- Backup and safety checks

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
*Database: PostgreSQL with PgBouncer*
