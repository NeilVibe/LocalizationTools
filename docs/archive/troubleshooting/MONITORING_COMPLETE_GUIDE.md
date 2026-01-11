# LocalizationTools - Complete Monitoring Guide

**Last Updated**: 2025-11-11
**Status**: ✅ COMPLETE - All monitoring infrastructure operational
**Purpose**: Comprehensive guide for monitoring all LocalizationTools servers

---

## 📚 Table of Contents

1. [Monitoring Failure Analysis](#monitoring-failure-analysis)
2. [System Architecture](#system-architecture)
3. [Available Monitoring Scripts](#available-monitoring-scripts)
4. [Best Practices](#best-practices)
5. [Claude AI Workflow](#claude-ai-workflow)
6. [Log File Reference](#log-file-reference)
7. [Quick Reference Commands](#quick-reference-commands)
8. [Troubleshooting](#troubleshooting)

---

## Monitoring Failure Analysis

### The Incident (2025-11-11)

Claude AI incorrectly told the user **"NO operations were run in the last 30 minutes"** when actually **3 operations HAD been run**. This was a critical monitoring failure that must never happen again.

### What Went Wrong:

1. **Used ad-hoc `tail` commands** instead of proper monitoring scripts
2. **Looked at wrong time window** (checked 23:47-23:58, but ops were at 23:39, 23:42, 00:01)
3. **Saw "0 operations"** after user cleared history and stopped investigating
4. **Didn't grep for POST requests** to find historical operations
5. **Confused UTC vs KST** timestamps (frontend showed 14:40, server showed 23:40)

### Lessons Learned:

✅ **ALWAYS** use existing monitoring scripts
✅ **ALWAYS** search logs with `tail -2000` or more
✅ **ALWAYS** grep for POST requests to find operations
✅ **NEVER** trust "0 operations" without checking logs
✅ **ALWAYS** account for timezone differences (KST = UTC+9)

---

## System Architecture

### Overview

LocalizationTools has 3 servers with comprehensive logging:

1. **Backend Server** (FastAPI) - Port 8888
2. **LocaNext Desktop App** (Electron + Svelte) - Port 5173
3. **Admin Dashboard** (SvelteKit) - Port 5175

### 1. Backend Server Logging ✅

**Location**: `server/data/logs/`
- `server.log` - All backend activity (INFO, SUCCESS, WARNING, ERROR)
- `error.log` - Only ERROR and CRITICAL messages

**Implementation**:
- Uses Python `loguru` library
- Middleware logs every HTTP request/response
- WebSocket events logged
- Database operations logged
- Performance tracking (slow requests >1s flagged)

**File**: `server/middleware/logging_middleware.py`

### 2. LocaNext Electron App Logging ✅

**Location**: `logs/`
- `locanext_app.log` - All LocaNext activity
- `locanext_error.log` - Only ERROR and CRITICAL messages

**Implementation**:
- Custom logger utility: `locaNext/electron/logger.js`
- Logs to file AND console (in development)
- Captures:
  - App lifecycle events (startup, shutdown, window events)
  - IPC calls (file dialogs, Python execution)
  - Python script execution (success/failure)
  - Uncaught exceptions and promise rejections

**Key Features**:
- Automatic log rotation (archives logs older than 7 days)
- Structured logging with timestamps
- JSON data support for rich context

### 3. Admin Dashboard Logging ✅

**Location**: `logs/`
- `dashboard_app.log` - All dashboard activity
- `dashboard_error.log` - Only ERROR and CRITICAL messages

**Implementation**:
- Custom logger utility: `adminDashboard/src/lib/utils/logger.js`
- Logs to:
  1. Browser console (always)
  2. File (when running in Node.js/dev server)
  3. Backend server (for ERROR/CRITICAL only via remote logging)
- Captures:
  - Component lifecycle events
  - API calls
  - User actions
  - WebSocket events

### Log Format

All logs use a consistent format:

```
YYYY-MM-DD HH:MM:SS | LEVEL    | message | optional_data_json
```

**Example**:
```
2025-11-11 00:01:02 | INFO     | Excel translation requested by user: admin
2025-11-11 00:01:02 | SUCCESS  | Created ActiveOperation record: ID=1
2025-11-11 00:01:02 | INFO     | Background task started for operation 1
```

---

## Available Monitoring Scripts

### Rule #1: ALWAYS Use Monitoring Scripts

We have 6 monitoring scripts in `scripts/` directory. **USE THEM**, don't reinvent the wheel!

### 1. Comprehensive System Check

```bash
bash scripts/monitor_system.sh
```

**Shows**:
- Process status (backend, frontend running?)
- Port status (8888, 5173, 5175 listening?)
- Backend API tests (health, root, docs endpoints)
- Frontend tests (homepage responding?)
- WebSocket/Socket.IO tests
- Database status (tables, active operations, users)
- Recent log errors

**When to use**: First thing to check system health

### 2. Live Backend Monitoring

```bash
bash scripts/monitor_backend_live.sh
```

**Shows**:
- Real-time backend logs (updates every 5s)
- API calls, operations, errors, performance
- Color-coded output

**When to use**: During active development/testing

### 3. TaskManager Monitoring

```bash
bash scripts/monitor_taskmanager.sh
```

**Shows**:
- TaskManager API calls (`/api/progress/operations`)
- WebSocket events (progress, operation_start, etc.)
- Auth token usage

**When to use**: Debugging TaskManager or progress tracking issues

### 4. Real-time Log Monitoring (All 6 Logs)

```bash
# All logs
bash scripts/monitor_logs_realtime.sh

# Errors only (recommended)
bash scripts/monitor_logs_realtime.sh --errors-only

# Backend only
bash scripts/monitor_logs_realtime.sh --backend-only

# No colors
bash scripts/monitor_logs_realtime.sh --no-color
```

**Shows**:
- Live tail of all 6 log files
- Color-coded: 🔥 CRITICAL, ❌ ERROR, ⚠️ WARNING, ✅ SUCCESS
- Saves session to `logs/sessions/session_TIMESTAMP.log`

**When to use**: Active monitoring during testing

### 5. Frontend Error Monitoring

```bash
bash scripts/monitor_frontend_errors.sh
```

**Shows**:
- Browser console errors
- Frontend errors sent to backend via remote logger

**When to use**: Debugging frontend issues

### 6. All Servers Status

```bash
bash scripts/monitor_all_servers.sh
```

**Shows**:
- Quick snapshot of all server status
- Recent log entries from each server

**When to use**: Quick health check

---

## Best Practices

### ❌ WHAT NOT TO DO

#### 1. Don't Check Old Logs

```bash
# ❌ WRONG - Shows historical errors, not current issues
tail -100 server/data/logs/error.log
grep "ERROR" server/data/logs/server.log  # All errors ever!
```

**Why wrong**: You're looking at historical data, not current issues.

#### 2. Don't Use Small Tail

```bash
# ❌ WRONG - Too small, misses operations
tail -100 server/data/logs/server.log
```

**Why wrong**: Operations might be 200-500 lines back in the logs.

#### 3. Don't Only Check GET Requests

```bash
# ❌ WRONG - GET requests are just polling
grep "GET.*operations" server/data/logs/server.log
```

**Why wrong**: Actual operations are POST requests, not GET.

#### 4. Don't Trust "0 operations" Without Verification

**Why wrong**: User might have cleared history. Check logs for POST requests!

#### 5. Don't Create New Monitoring Scripts

**Why wrong**: We already have 6 monitoring scripts. Use them!

---

### ✅ CORRECT MONITORING APPROACH

#### Method 1: Live Monitoring (BEST for Development)

```bash
# In one terminal, run this and LEAVE IT RUNNING
bash scripts/monitor_logs_realtime.sh --errors-only

# Now reproduce the issue in another terminal/browser
# You'll see errors appear in REAL-TIME with color coding
```

**What you see**:
- 🔥 CRITICAL errors (red)
- ❌ ERROR messages (red)
- ⚠️ WARNING messages (yellow)
- ✅ SUCCESS messages (green)

**When to use**: Active development, debugging, reproducing issues.

#### Method 2: Historical Operation Search

**Find ALL XLSTransfer operations in last 30 minutes:**

```bash
tail -2000 /home/neil1988/LocalizationTools/server/data/logs/server.log | \
  grep -E "POST.*xlstransfer|ActiveOperation|operation_start|Background task" | \
  grep -E "23:[3-5][0-9]|00:0[0-2]"  # Adjust time range as needed
```

**Example Output**:
```
2025-11-10 23:39:13 | SUCCESS | Created ActiveOperation record: ID=10
2025-11-10 23:39:13 | INFO | Background task started for operation 10
2025-11-10 23:42:33 | SUCCESS | Created ActiveOperation record: ID=11
```

#### Method 3: Check Database for Active Operations

```bash
# Use the monitoring script
bash scripts/monitor_system.sh | grep -A5 "DATABASE STATUS"
```

#### Method 4: Test Specific Feature Right Now

```bash
# Test an API endpoint LIVE
python3 - <<'EOF'
import requests

# Test login
response = requests.post(
    "http://localhost:8888/api/v2/auth/login",
    json={"username": "admin", "password": "admin123"}
)
print(f"Login: {response.status_code}")

# Test progress API
token = response.json()["access_token"]
response = requests.get(
    "http://localhost:8888/api/progress/operations?status=running",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Progress API: {response.status_code}")
print(f"Operations: {len(response.json())}")
EOF
```

---

## Claude AI Workflow

### Before Starting ANY Testing Session

```bash
# 1. Archive old logs (start fresh)
bash scripts/clean_logs.sh

# 2. Start all servers (in separate terminals)
python3 server/main.py
cd adminDashboard && npm run dev -- --port 5175
cd locaNext && npm run dev:svelte -- --port 5173

# 3. Start monitoring (in new terminal)
bash scripts/monitor_logs_realtime.sh --errors-only

# 4. Perform testing...

# 5. After testing, check for errors
bash scripts/monitor_system.sh
```

### STOP TESTING IF:

1. **CRITICAL errors appear**
   - System is broken
   - Fix immediately before continuing

2. **Same ERROR repeats 10+ times**
   - Don't generate more of the same error
   - Fix root cause first

3. **Server crashes**
   - Check logs for cause
   - Fix before restarting

### CONTINUE TESTING IF:

1. **Warnings about expired tokens** - Expected behavior
2. **Warnings about failed login attempts** - Expected behavior (testing wrong passwords)
3. **INFO/DEBUG messages** - Normal operation

### Phase 3 Testing Requirements

**MUST achieve before Phase 4**:
- ✅ 0 CRITICAL errors (24+ hour monitoring)
- ✅ 0 ERRORs (all fixed and verified)
- ✅ Warnings reviewed (all expected behavior)
- ✅ All XLSTransfer functions tested (no errors)
- ✅ Admin Dashboard working (no errors)
- ✅ System stable (no crashes, no memory leaks)

---

## Log File Reference

### Directory Structure

```
server/data/logs/
├── server.log       ← All backend activity
└── error.log        ← Backend errors only

logs/
├── locanext_app.log      ← Frontend (Electron)
├── locanext_error.log    ← Frontend errors
├── dashboard_app.log     ← Dashboard
├── dashboard_error.log   ← Dashboard errors
├── archive/              ← Old logs (timestamped directories)
│   └── 20251111_000000/
├── sessions/             ← Real-time monitoring session logs
│   └── session_20251111_000000.log
└── reports/              ← Analysis reports (if using log analysis tools)
```

### Timezone Reference

**CRITICAL**: Understand timezone conversion to avoid confusion!

| Source | Timezone | Example Time | Notes |
|--------|----------|--------------|-------|
| **Server Logs** | KST (UTC+9) | `23:40:26` | Backend writes in KST |
| **Frontend Console Logs** | UTC | `14:40:26` | 9 hours behind KST |
| **Frontend UI** | User's Local | Should auto-convert | Currently may show UTC (bug) |

**To convert manually:**
```bash
# Server log time: 23:40:26 KST
# Frontend log time: 14:40:26 UTC
# Calculation: 23:40 - 9 hours = 14:40 ✓ (same moment)
```

---

## Quick Reference Commands

### System Health

```bash
# Quick health check
bash scripts/monitor_system.sh

# Check if servers running
ps aux | grep -E "python3 server/main.py|npm.*dev" | grep -v grep

# Test backend health
curl -s http://localhost:8888/health

# Test frontend
curl -s http://localhost:5173 > /dev/null && echo "Frontend OK" || echo "Frontend DOWN"
```

### Find Operations

```bash
# Find operations in last 30 minutes (adjust time range)
tail -2000 server/data/logs/server.log | \
  grep -E "POST.*xlstransfer|ActiveOperation|operation_start"

# Find specific operation by ID
grep "operation 12" server/data/logs/server.log

# Count operations today
grep "ActiveOperation record" server/data/logs/server.log | \
  grep "$(date +%Y-%m-%d)" | wc -l

# Find operation completions
tail -2000 server/data/logs/server.log | \
  grep -E "operation_complete|operation_failed"
```

### Error Checking

```bash
# Recent errors (last 10)
tail -100 server/data/logs/server.log | grep ERROR | tail -10

# Errors from current hour only
grep "$(date '+%Y-%m-%d %H:')" server/data/logs/server.log | grep ERROR

# Frontend errors specifically
grep "\[FRONTEND\]" server/data/logs/server.log | grep ERROR

# Live error monitoring
tail -f server/data/logs/server.log | grep --color -E "ERROR|WARNING|CRITICAL"
```

### Log Maintenance

```bash
# Archive old logs and start fresh
bash scripts/clean_logs.sh

# Verify logs are clean
wc -l server/data/logs/*.log

# Check archive was created
ls -lh logs/archive/
```

### Time Verification

```bash
# Check current time
date  # Shows: Tue Nov 11 12:04:15 AM KST 2025

# Calculate "10 minutes ago"
# Current: 00:04 KST
# 10 mins ago: 23:54 KST
# Search: grep -E "23:5[4-9]|00:0[0-4]"
```

---

## Troubleshooting

### "User ran a process, I can't see it"

```bash
# Step 1: What time is it now?
date

# Step 2: Check system health
bash scripts/monitor_system.sh

# Step 3: Search logs for POST requests in last 30 mins
tail -2000 server/data/logs/server.log | \
  grep -E "POST.*xlstransfer" | \
  grep -E "23:[3-5][0-9]|00:0[0-2]"  # Adjust time range

# Step 4: Find ActiveOperation creations
tail -2000 server/data/logs/server.log | grep "ActiveOperation record"

# Step 5: Check background tasks
tail -2000 server/data/logs/server.log | grep "Background task started"
```

### API Returns 401 Unauthorized

```bash
# Step 1: Check if server is running
curl -s http://localhost:8888/health

# Step 2: Test login
curl -X POST http://localhost:8888/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Step 3: Check auth errors in last 5 minutes
tail -100 server/data/logs/server.log | grep "401\|Unauthorized"

# Step 4: Monitor live
bash scripts/monitor_logs_realtime.sh --errors-only
```

### WebSocket Connection Fails

```bash
# Step 1: Check server has WebSocket
grep "Socket.IO" server/data/logs/server.log | tail -5

# Step 2: Test Socket.IO endpoint
curl -s http://localhost:8888/socket.io/?EIO=4&transport=polling

# Step 3: Monitor WebSocket errors live
bash scripts/monitor_logs_realtime.sh --errors-only
# Then trigger WebSocket connection in browser
```

### Progress Tracking Not Working

```bash
# Step 1: Check database has operations
bash scripts/monitor_system.sh | grep -A5 "DATABASE STATUS"

# Step 2: Test progress API
python3 -c "
import requests
r = requests.post('http://localhost:8888/api/v2/auth/login',
                  json={'username':'admin','password':'admin123'})
token = r.json()['access_token']
r = requests.get('http://localhost:8888/api/progress/operations',
                 headers={'Authorization': f'Bearer {token}'})
print(f'Status: {r.status_code}')
print(f'Operations: {len(r.json())}')
"

# Step 3: Monitor progress updates live
bash scripts/monitor_logs_realtime.sh | grep -E "progress|operation"
```

---

## Summary

### DO:
- ✅ Use `bash scripts/monitor_system.sh` first
- ✅ Use `monitor_logs_realtime.sh --errors-only` for live monitoring
- ✅ Search with `tail -2000` for historical operations
- ✅ Grep for POST requests to find operations
- ✅ Check timezone (KST = UTC+9)
- ✅ Test features with Python scripts (immediately)
- ✅ Archive logs before new testing sessions

### DON'T:
- ❌ Use `tail -100` (too small)
- ❌ Only check GET requests (those are polling)
- ❌ Trust "0 operations" without checking logs
- ❌ Forget timezone differences
- ❌ Create new monitoring scripts
- ❌ Look at entire log files without filtering
- ❌ Check yesterday's errors when debugging today

### Remember:
**Live monitoring beats historical analysis every time!**

---

**Last Updated**: 2025-11-11
**Status**: Complete and ready for use
**Reviewed**: After monitoring failure incident
