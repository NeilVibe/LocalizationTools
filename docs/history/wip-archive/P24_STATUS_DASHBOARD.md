# P24: Server Status Dashboard

**Priority:** P24 | **Status:** IN PROGRESS | **Created:** 2025-12-12

---

## Goal

Real-time health monitoring for Central Server - simple view in LocaNext app, detailed view in Admin Dashboard.

---

## Two Interfaces

### 1. LocaNext App (Simple - for users)

```
┌─ Server Status ────────────────────────────┐
│                                            │
│  Central Server: localhost:8888            │
│                                            │
│  ● API Server    🟢 Connected              │
│  ● Database      🟢 Connected              │
│  ● WebSocket     🟢 Connected              │
│                                            │
└────────────────────────────────────────────┘
```

**Location:** Settings menu in LocaNext
**Purpose:** User sees green = good, red = call IT

---

### 2. Admin Dashboard (Detailed - for admins)

```
┌─ System Health ─────────────────────────────────────────────────┐
│                                                                 │
│  ┌─ API Server ──────────┐  ┌─ Database ──────────────────────┐│
│  │ Status: 🟢 Healthy    │  │ Status: 🟢 Connected            ││
│  │ Response: 45ms        │  │ Pool: 12/100 connections        ││
│  │ Uptime: 3d 14h        │  │ Avg Query: 2.3ms                ││
│  │ Requests/min: 847     │  │ Active Queries: 3               ││
│  └───────────────────────┘  │ Size: 2.4 GB                    ││
│                             └─────────────────────────────────┘│
│  ┌─ WebSocket ───────────┐  ┌─ System Resources ──────────────┐│
│  │ Status: 🟢 Active     │  │ CPU: 23% ████░░░░░░             ││
│  │ Connections: 8        │  │ Memory: 4.2/16 GB ██░░░░░░░░    ││
│  │ Messages/min: 156     │  │ Disk: 45% █████░░░░░            ││
│  └───────────────────────┘  └─────────────────────────────────┘│
│                                                                 │
│  ┌─ Active Users ────────────────────────────────────────────┐ │
│  │ Total Online: 8                                           │ │
│  │ user1@company.com - LDM (2 min ago)                      │ │
│  │ user2@company.com - XLSTransfer (5 min ago)              │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Location:** Admin Dashboard → new "Status" menu/page
**Purpose:** IT/Admin sees everything - diagnose issues, monitor load

---

## Implementation Plan

### Phase 1: Health API Endpoint

**Backend:** `GET /api/health/status`

```python
# Response
{
    "api": {
        "status": "healthy",
        "uptime_seconds": 302400,
        "requests_per_minute": 847
    },
    "database": {
        "status": "connected",
        "pool_size": 100,
        "pool_used": 12,
        "avg_query_ms": 2.3,
        "active_queries": 3,
        "size_bytes": 2576980377
    },
    "websocket": {
        "status": "active",
        "connections": 8,
        "messages_per_minute": 156
    },
    "system": {
        "cpu_percent": 23,
        "memory_used_gb": 4.2,
        "memory_total_gb": 16,
        "disk_percent": 45
    },
    "users": {
        "online_count": 8,
        "active_sessions": [...]
    }
}
```

**Files:**
- [ ] `server/api/health.py` - New health API endpoint

---

### Phase 2: LocaNext Status Panel (Simple)

**Frontend:** `ServerStatus.svelte`

- Green/orange/red indicators
- Shows in Settings menu
- Polls every 30 seconds
- Simple endpoint: `GET /api/health/simple`

**Files:**
- [ ] `locaNext/src/lib/components/ServerStatus.svelte`
- [ ] Add to Settings menu

---

### Phase 3: Admin Dashboard Status Page (Detailed)

**Frontend:** Full status page in Admin Dashboard

- All metrics from `/api/health/status`
- Real-time updates (WebSocket or polling)
- Graphs/charts for load over time (optional)
- Active users list

**Files:**
- [ ] `adminDashboard/src/routes/status/+page.svelte`
- [ ] `adminDashboard/src/lib/components/StatusCard.svelte`

---

## Status Indicators

| Color | Condition |
|-------|-----------|
| 🟢 GREEN | All good - connected, low load (<70%) |
| 🟠 ORANGE | Warning - high load (70-90%) or slow response |
| 🔴 RED | Critical - disconnected, overloaded (>90%), or error |

---

## Tasks

### Backend
- [ ] Create `GET /api/health/status` (detailed)
- [ ] Create `GET /api/health/simple` (for LocaNext app)
- [ ] Add DB pool stats
- [ ] Add system resource stats (psutil)
- [ ] Add WebSocket connection count
- [ ] Add active users list

### LocaNext App
- [ ] Create `ServerStatus.svelte`
- [ ] Add to Settings menu
- [ ] Green/orange/red indicators
- [ ] Poll every 30s

### Admin Dashboard
- [ ] Create Status page
- [ ] API Server card
- [ ] Database card
- [ ] WebSocket card
- [ ] System Resources card
- [ ] Active Users list

---

## Dependencies

```
psutil  # For CPU, memory, disk stats (may already be installed)
```

---

*Created: 2025-12-12*
