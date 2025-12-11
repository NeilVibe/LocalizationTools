# P23: Data Flow Architecture - Local ↔ Central Server

**Priority:** P23 | **Status:** 🔴 CRITICAL GAPS | **Created:** 2025-12-11

---

## ⚠️ CRITICAL FINDING

**The current architecture is NOT ready for Central Server deployment!**

### Current State (ALL localhost)

```
EVERYTHING ON SAME MACHINE:

LocaNext Desktop
    ↓
fetch('http://localhost:8888/...')  ← HARDCODED!
    ↓
FastAPI Backend (localhost:8888)
    ↓
PostgreSQL (localhost:5432)
```

**Problem:** When deployed to production with a Central Server, the app won't know where to connect!

---

## What NEEDS to be Built

### Phase 0: Server URL Configuration (SIMPLIFIED!)

**Current:** `http://localhost:8888` hardcoded everywhere

**New Approach:** Admin-configured, IP-based authorization

```
┌─────────────────────────────────────────────────────────────┐
│                    CONNECTION FLOW                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Admin configures Central Server IP (once)               │
│     └── Server .env: ALLOWED_IP_RANGE=192.168.1.0/24       │
│                                                             │
│  2. Build app with Central Server URL baked in              │
│     └── Or: App config file set by IT during deployment     │
│                                                             │
│  3. User launches app                                       │
│     └── App tries to connect to Central Server              │
│                                                             │
│  4. Central Server checks client IP                         │
│     └── If in allowed range → Accept connection             │
│     └── If not in range → Reject (401/403)                  │
│                                                             │
│  5. Connection established                                  │
│     └── Show green status indicator                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**What's Needed:**

| Component | Location | Task |
|-----------|----------|------|
| **Server URL config** | App build or config file | Admin sets once |
| **IP whitelist** | Server `.env` | `ALLOWED_IP_RANGE=192.168.x.x/24` |
| **IP check middleware** | `server/middleware/` | Already exists! |
| **Connection status UI** | `locaNext/` | Show green/orange/red |

**GOLDEN RULE: Users Never Do Admin Work**
```
END USERS should NEVER:
├── Configure server URLs
├── Set up connections
├── Manage IP whitelists
└── Touch any technical settings

ADMIN/IT handles ALL of this:
├── Server URL (baked into build or deployed config)
├── IP whitelist (server .env)
└── User account creation

USER experience:
├── Launch app → It just works
├── See green/orange/red status indicator
└── Do their translation work
```

---

### Phase 0.5: Connection Status Panel (NEW!)

**Purpose:** Let users see server health at a glance in Settings menu.

**UI Mockup:**
```
┌─ Server Connection Status ─────────────────────────────────┐
│                                                            │
│  Central Server: https://central.company.com               │
│                                                            │
│  ● Connected                              [Change Server]  │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Status        ● GREEN - All systems operational   │   │
│  │  Latency       45ms                                │   │
│  │  Server Load   ● ORANGE - Moderate (65%)           │   │
│  │  Active Users  12                                  │   │
│  │  Last Sync     2 seconds ago                       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  [Test Connection]                        [Reconnect]      │
└────────────────────────────────────────────────────────────┘
```

**Status Indicators:**
| Color | Meaning |
|-------|---------|
| 🟢 GREEN | Connected, server healthy, low load |
| 🟠 ORANGE | Connected but busy (high load) or slow |
| 🔴 RED | Not connected / server unreachable |

**Backend Endpoint Needed:**
```python
GET /api/health/status
{
    "status": "healthy",
    "load_percent": 65,
    "active_connections": 12,
    "db_status": "connected",
    "uptime_seconds": 86400
}
```

**Tasks:**
- [ ] Create `GET /api/health/status` endpoint
- [ ] Create `ConnectionStatus.svelte` component
- [ ] Add to Settings menu
- [ ] Polling every 30s or on-demand refresh
- [ ] Visual indicators (green/orange/red)

**Files that need changes:**
```
locaNext/src/lib/stores/app.js:15  → serverUrl = writable('http://localhost:8888')
locaNext/src/lib/components/TaskManager.svelte:197  → hardcoded localhost
locaNext/src/lib/components/apps/KRSimilar.svelte:26  → API_BASE hardcoded
locaNext/src/lib/components/apps/LDM.svelte:14  → API_BASE hardcoded
locaNext/src/lib/components/ldm/*.svelte  → Multiple files with API_BASE
```

**Solution Architecture:**
```javascript
// config.js or electron store
const SERVER_URL = getSavedServerUrl() || 'http://localhost:8888';

// All API calls use this
fetch(`${SERVER_URL}/api/...`)
```

---

### Phase 1: File Upload → Central DB

**What EXISTS:**
- ✅ PostgreSQL connection works
- ✅ API endpoints exist
- ⚠️ Parsers exist but need verification

**What's MISSING:**
- ❌ Custom column picker for Excel (only A/B hardcoded)
- ❌ Custom attribute picker for XML
- ❌ Multi-file batch upload
- ❌ Upload progress for large files over network

**File Types:**

| Type | Parser | Custom Selection | Status |
|------|--------|-----------------|--------|
| TXT (tab) | Predefined | N/A | ⚠️ Verify works |
| XML | Predefined | Need attribute picker | ❌ TODO |
| Excel | openpyxl | Need column picker | ❌ TODO |
| TMX | Standard | Predefined | ⚠️ Verify works |

---

### Phase 2: TM Upload & Search

**What EXISTS:**
- ✅ `server/tools/ldm/tm_manager.py` - Backend API
- ✅ `server/tools/ldm/tm_indexer.py` - Index builder
- ✅ Database tables exist

**What's MISSING:**
- ❌ **TM Upload UI** (ISSUE-011) - No frontend at all!
- ❌ **TM Search API** (Phase 7.4) - `tm_search.py` not built
- ❌ **TM Manager UI** - List, delete, activate TMs

---

### Phase 3: Real-time Sync (WebSocket)

**What EXISTS:**
- ✅ WebSocket connection works
- ✅ Row edit sync works
- ✅ Row locking works

**What's MISSING for Central Server:**
- ⚠️ WebSocket reconnection on network drop
- ⚠️ Offline mode / queue changes
- ⚠️ Conflict resolution if same row edited offline

---

## Architecture: Development vs Production

### Development (Current - Works)
```
┌─────────────────────────────────────────┐
│         User's PC (localhost)           │
├─────────────────────────────────────────┤
│  LocaNext Desktop                       │
│       ↓                                 │
│  FastAPI Backend (localhost:8888)       │
│       ↓                                 │
│  PostgreSQL (localhost:5432)            │
│       ↓                                 │
│  Local Indexes (FAISS, embeddings)      │
└─────────────────────────────────────────┘
```

### Production (Target - NOT READY)
```
┌─────────────────────────┐         ┌─────────────────────────┐
│     User's PC (Local)   │         │   Central Server        │
├─────────────────────────┤         ├─────────────────────────┤
│  LocaNext Desktop       │   ───►  │  FastAPI Backend        │
│       │                 │  HTTPS  │       ↓                 │
│  Local Indexes          │   ◄───  │  PostgreSQL + PgBouncer │
│  (FAISS, embeddings)    │  WebSocket                        │
└─────────────────────────┘         └─────────────────────────┘

User PC does:                       Central Server does:
- ML inference                      - Store all text data
- FAISS search                      - User auth
- Embeddings                        - Multi-user coordination
- UI rendering                      - Backup/restore
```

---

## Priority Order

### CRITICAL (Do First)

1. **Server URL Configuration** (SIMPLIFIED)
   - Bake URL into app build OR use config file
   - Admin/IT sets once during deployment
   - IP whitelist on server side (already exists!)
   - No per-user configuration needed

2. **Connection Status Panel**
   - Visual status in Settings menu
   - Green/Orange/Red indicators
   - Server load, latency, active users
   - Reconnect button

### HIGH Priority

3. **TM Upload UI** (ISSUE-011)
   - TMUploadModal.svelte
   - TMManager.svelte
   - Wire to existing backend

3. **Custom File Parsers**
   - Excel column picker
   - XML attribute picker
   - Preview before import

### MEDIUM Priority

4. **TM Search API** (Phase 7.4)
   - 5-Tier cascade search
   - tm_search.py

5. **Multi-file Upload**
   - Batch processing
   - Progress tracking

### LOW Priority

6. **Offline Mode**
   - Queue changes when offline
   - Sync when reconnected

---

## Estimated Work

| Phase | Task | Effort |
|-------|------|--------|
| **Phase 0** | Server URL Config | Medium |
| **Phase 0.5** | Connection Status Panel | Medium |
| Phase 1 | File parsers + pickers | Large |
| Phase 2 | TM Upload UI | Medium |
| Phase 2 | TM Search API | Medium-Large |
| Phase 3 | WebSocket improvements | Medium |

---

## Files That Need Server URL Fix

```
# Hardcoded localhost:8888 - MUST CHANGE

locaNext/src/lib/stores/app.js
locaNext/src/lib/components/TaskManager.svelte
locaNext/src/lib/components/UpdateModal.svelte
locaNext/src/lib/components/apps/KRSimilar.svelte
locaNext/src/lib/components/apps/LDM.svelte
locaNext/src/lib/components/ldm/FileExplorer.svelte
locaNext/src/lib/components/ldm/DataGrid.svelte
locaNext/src/lib/components/ldm/VirtualGrid.svelte
locaNext/src/lib/utils/remote-logger.js
```

---

## Summary

**For Central Server deployment:**

| Item | Status | Notes |
|------|--------|-------|
| Server URL config | ⚠️ Simple | Admin bakes into build or config file |
| IP whitelist | ✅ EXISTS | `server/middleware/` already has this |
| Connection status UI | ❌ TODO | Green/orange/red panel |
| TM upload UI | ❌ TODO | ISSUE-011 |
| Custom file parsers | ❌ TODO | Excel/XML column pickers |
| TM Search | ❌ TODO | Phase 7.4 |

**Connection Flow:**
```
User launches app → App connects to Central Server URL (baked in)
                  → Server checks IP whitelist
                  → If authorized: Connect + show green status
                  → If not: Reject 403
```

**What's EASY:** URL config (admin sets once), IP auth (already built)
**What's LEFT:** Connection status UI, TM features, file parsers

---

*Created: 2025-12-11*
*This doc replaces the previous version with CRITICAL findings*
