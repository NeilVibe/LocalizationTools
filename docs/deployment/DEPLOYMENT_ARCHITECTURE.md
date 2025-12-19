# Deployment Architecture

**Central PostgreSQL** | **Local Heavy Processing** | **Shared Data + Real-time Sync**

---

## PRODUCTION DEPLOYMENT MODEL

```
┌─────────────────────────────────────────────────────────────┐
│ USER'S PC (Windows .exe)                                    │
├─────────────────────────────────────────────────────────────┤
│ LocaNext.exe (Electron app)                                 │
│ ├─ Embedded Backend (Python + FastAPI)                      │
│ ├─ LOCAL HEAVY PROCESSING:                                  │
│ │   ├─ FAISS indexes (server/data/ldm_tm/)                  │
│ │   ├─ Embeddings generation                                │
│ │   ├─ File parsing                                         │
│ │   └─ Model inference (Qwen)                               │
│ │                                                           │
│ └─ ALL TEXT DATA → Central PostgreSQL                       │
│     ├─ LDM rows (source/target)                             │
│     ├─ TM entries                                           │
│     ├─ Projects, files metadata                             │
│     └─ Logs, telemetry                                      │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ ALL DATA (PostgreSQL connection)
                        │ WebSocket (real-time sync)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ CENTRAL SERVER                                              │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL + PgBouncer                                      │
│ ├─ ALL user data (LDM, TM, projects, files, rows)           │
│ ├─ 1000 connections via PgBouncer                           │
│ ├─ Real-time sync (multiple users same file)                │
│ ├─ Logs, telemetry, sessions                                │
│ └─ 100+ users, 1M rows each = no problem                    │
│                                                             │
│ Admin Dashboard                                             │
│ ├─ Monitor all users                                        │
│ ├─ View logs, errors                                        │
│ └─ Usage statistics                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## WHY THIS ARCHITECTURE?

### Central PostgreSQL (ALL text data):
- Multiple users work on SAME file simultaneously
- Real-time sync via WebSocket
- Data never lost (server backup)
- Admin can monitor everything
- PgBouncer handles 1000 connections

### Local Processing (Heavy computation):
- FAISS indexes built on user's PC
- Embeddings computed locally
- File parsing done locally
- Model inference (Qwen) runs locally
- Only TEXT data travels over network

---

## WHAT GOES WHERE

| Data Type | Location | Why |
|-----------|----------|-----|
| LDM rows (source/target text) | PostgreSQL | Shared, synced, backed up |
| TM entries | PostgreSQL | Shared across users |
| Projects, folders, files metadata | PostgreSQL | Shared |
| Users, sessions, auth | PostgreSQL | Centralized |
| Logs, telemetry | PostgreSQL | Admin monitoring |
| FAISS indexes (.index files) | Local disk | Heavy, rebuildable from DB |
| Hash lookups (.pkl files) | Local disk | Heavy, rebuildable from DB |
| Embeddings (.npy files) | Local disk | Heavy, rebuildable from DB |
| ML models (Qwen) | Local disk | Large, downloaded once |

---

## THREE APPLICATIONS

### 1. LocaNext (Electron Desktop App)
- **For**: End users who run tools
- **Tech Stack**: Electron + Svelte + Carbon UI
- **Location**: `/locaNext/`
- **Features**:
  - Apps: XLSTransfer, QuickSearch, KR Similar, LDM
  - Task Manager (live progress tracking)
  - Local heavy processing (user's CPU)
  - Connects to Central PostgreSQL
  - Real-time WebSocket sync

### 2. Server Application (FastAPI Backend)
- **For**: API, database, real-time sync
- **Tech Stack**: FastAPI + SQLAlchemy + PostgreSQL
- **Location**: `/server/`
- **Features**:
  - 63+ API endpoints
  - WebSocket real-time events
  - JWT authentication
  - PgBouncer connection pooling

### 3. Admin Dashboard (SvelteKit Web App)
- **For**: Administrators to monitor usage
- **Tech Stack**: SvelteKit + Carbon UI
- **Location**: `/adminDashboard/`
- **Features**:
  - User management
  - Live activity feed
  - Logs viewer
  - Telemetry statistics

---

## DATABASE CONFIGURATION

### Central Server
```
PostgreSQL: port 5432
PgBouncer:  port 6433 (connection pooling)

Capacity:
- 1000 client connections (via PgBouncer)
- 100 database connections (pool)
- 100+ users simultaneous
- 1M rows per user = no problem
```

### User's PC (.env)
```bash
POSTGRES_HOST=your-central-server.com
POSTGRES_PORT=6433
POSTGRES_USER=localization_admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=localizationtools
DATABASE_TYPE=postgresql
```

---

## Related Documentation

- **POSTGRESQL_SETUP.md** - PostgreSQL + PgBouncer configuration
- **history/wip-archive/P21_DATABASE_POWERHOUSE.md** - Database performance (archived)
- **DEPLOYMENT.md** - Production deployment procedures
- **ENTERPRISE_DEPLOYMENT.md** - Enterprise-scale deployment
