# Deployment Architecture

**Hybrid Model** | **SQLite + PostgreSQL** | **Local Processing + Central Monitoring**

---

## 🌐 PRODUCTION DEPLOYMENT MODEL

**IMPORTANT**: This is a **HYBRID deployment model** - understanding this is critical!

### How Users Get the App:

```
┌─────────────────────────────────────────────────────────────┐
│ USER'S PC (Windows .exe - Distributed to End Users)        │
├─────────────────────────────────────────────────────────────┤
│ LocalizationTools.exe (Electron app)                        │
│ ├─ Local SQLite Database (user's operations/files)         │
│ ├─ Embedded Backend (Python + FastAPI inside .exe)         │
│ ├─ ALL Processing Happens Locally (FAST, works OFFLINE)    │
│ └─ Optionally sends telemetry ⬆️ → Central Server          │
│    (logs, errors, usage stats - when internet available)   │
└─────────────────────────────────────────────────────────────┘
                                ⬆️ Telemetry
                                ⬇️ Updates
┌─────────────────────────────────────────────────────────────┐
│ CENTRAL SERVER (Your Server - Cloud/WSL2)                  │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL Database                                         │
│ ├─ Receives logs from ALL users                            │
│ ├─ Aggregates usage statistics                             │
│ ├─ Stores error reports                                    │
│ └─ Tracks app versions/updates                             │
│                                                             │
│ Admin Dashboard (Monitor all users)                        │
│ ├─ Real-time activity feed                                 │
│ ├─ Error tracking across all installations                 │
│ ├─ Usage statistics and analytics                          │
│ └─ Push updates to users                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ WHY BOTH SQLite AND PostgreSQL?

### SQLite (In User's .exe):
- ✅ Fast local operations (no network latency)
- ✅ Works completely OFFLINE
- ✅ No database server installation required
- ✅ User's data stays on their PC
- ✅ Each user has isolated database

### PostgreSQL (Central Server):
- ✅ Handles concurrent writes from many users
- ✅ Aggregates telemetry from all installations
- ✅ Powers Admin Dashboard
- ✅ Stores update information
- ✅ Reliable for production server

**This is NOT redundancy - they serve different purposes!**

---

## 💻 DEVELOPMENT/TESTING (Your WSL2 Environment)

```
Your WSL2 Environment:
├─ Backend Server: localhost:8888 (SQLite for now, PostgreSQL later)
├─ Browser Testing: localhost:5173 (tests the .exe functionality)
├─ Admin Dashboard: localhost:5175 (will connect to PostgreSQL)
└─ Goal: Test everything before building Windows .exe
```

### Testing Flow:
1. Test in browser (WSL2) → Validates all functionality
2. Build Windows .exe → Packages everything
3. Deploy central server with PostgreSQL → Receives telemetry
4. Distribute .exe to users → Each gets standalone app

---

## 🏢 THREE APPLICATIONS

### 1. LocaNext (Electron Desktop App) - ✅ COMPLETE
- **For**: End users who run tools
- **Tech Stack**: Electron + Svelte + Skeleton UI (matte dark theme)
- **Location**: `/locaNext/` folder
- **Features**:
  - Ultra-clean top menu (Apps dropdown + Tasks button)
  - Everything on one page (seamless UI/UX)
  - Modular sub-GUIs within same window
  - Task Manager (live progress tracking, history)
  - Local processing (user's CPU)
  - Sends logs to server
  - Authentication with "Remember Me"
  - Real-time WebSocket updates

### 2. Server Application (FastAPI Backend) - ✅ COMPLETE
- **For**: Central logging, monitoring, analytics
- **Tech Stack**: FastAPI + SQLAlchemy + Socket.IO
- **Location**: `server/`
- **Features**:
  - 38 API endpoints (19 async + 19 sync)
  - WebSocket real-time events
  - Comprehensive logging middleware
  - JWT authentication
  - PostgreSQL/SQLite support
  - Optional Redis caching
  - Optional Celery background tasks

### 3. Admin Dashboard (SvelteKit Web App) - ⏳ 85% COMPLETE
- **For**: Administrators to monitor usage and manage users
- **Tech Stack**: SvelteKit + Skeleton UI (matte dark theme)
- **Location**: `/adminDashboard/` folder
- **Features**:
  - Dashboard home with stats cards
  - User management (view, edit, delete)
  - Live activity feed (real-time WebSocket)
  - Statistics page with charts
  - Logs viewer with filters
  - Export to CSV/JSON
  - User detail pages

---

## 📚 Related Documentation

- **POSTGRESQL_SETUP.md** - PostgreSQL configuration guide
- **DEPLOYMENT.md** - Production deployment procedures
- **ENTERPRISE_DEPLOYMENT.md** - Enterprise-scale deployment
- **SECURITY_AND_LOGGING.md** - Security best practices
