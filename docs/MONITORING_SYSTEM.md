# Complete Monitoring System Documentation

**Last Updated**: 2025-11-09
**Status**: ✅ COMPLETE - All three servers now have comprehensive logging

## Overview

This document describes the complete monitoring infrastructure for all three LocaNext servers:
1. **Backend Server** (FastAPI)
2. **LocaNext Desktop App** (Electron)
3. **Admin Dashboard** (SvelteKit)

## Architecture

### 1. Backend Server Logging ✅

**Location**: `server/data/logs/`
- `server.log` - All backend activity (INFO, SUCCESS, WARNING, ERROR)
- `error.log` - Only ERROR and CRITICAL messages

**Implementation**:
- Uses Python `loguru` library
- Middleware logs every HTTP request/response
- WebSocket events logged
- Database operations logged
- Performance tracking (slow requests flagged)

**File**: `server/middleware/logging_middleware.py`

### 2. LocaNext Electron App Logging ✅ NEW

**Location**: `logs/`
- `locanext_app.log` - All LocaNext activity
- `locanext_error.log` - Only ERROR and CRITICAL messages

**Implementation**:
- Custom logger utility: `locaNext/electron/logger.js`
- Logs to file AND console (in development)
- Captures:
  - App lifecycle events (startup, shutdown, window events)
  - IPC calls (file dialogs, Python execution, etc.)
  - Python script execution (success/failure)
  - Uncaught exceptions and promise rejections
  - All electron main process events

**Key Features**:
- Automatic log rotation (archives logs older than 7 days)
- Structured logging with timestamps
- JSON data support for rich context
- Separate error log for quick filtering

**File**: `locaNext/electron/logger.js`
**Integration**: `locaNext/electron/main.js`

### 3. Admin Dashboard Logging ✅ NEW

**Location**: `logs/`
- `dashboard_app.log` - All dashboard activity
- `dashboard_error.log` - Only ERROR and CRITICAL messages

**Implementation**:
- Custom logger utility: `adminDashboard/src/lib/utils/logger.js`
- Logs to:
  1. Browser console (always)
  2. File (when running in Node.js/dev server)
  3. Backend server (for ERROR/CRITICAL only)
- Captures:
  - Component lifecycle events
  - API calls
  - User actions
  - WebSocket events
  - Data loading/errors

**File**: `adminDashboard/src/lib/utils/logger.js`
**Integration**: `adminDashboard/src/routes/+page.svelte` (and other pages)

## Log Format

All logs use a consistent format:

```
YYYY-MM-DD HH:MM:SS | LEVEL    | message | optional_data_json
```

**Example**:
```
2025-11-09 13:23:48 | INFO     | Electron app ready | {"version":"1.0.0","platform":"linux"}
2025-11-09 13:24:12 | SUCCESS  | Main window ready and visible
2025-11-09 13:25:30 | ERROR    | Python execution error | {"scriptPath":"/path/to/script.py","error":"File not found"}
```

## Monitoring Tools

### 1. Real-Time Monitor (All Servers)

**Command**:
```bash
bash scripts/monitor_logs_realtime.sh
```

**Features**:
- Monitors all 6 log files simultaneously
- Color-coded output (errors in red, warnings in yellow, success in green)
- Saves session to `logs/sessions/session_YYYYMMDD_HHMMSS.log`
- Press Ctrl+C to stop

**Options**:
```bash
# Show only errors
bash scripts/monitor_logs_realtime.sh --errors-only

# Monitor backend only
bash scripts/monitor_logs_realtime.sh --backend-only

# No colors
bash scripts/monitor_logs_realtime.sh --no-color
```

### 2. Server Status Monitor

**Command**:
```bash
bash scripts/monitor_all_servers.sh
```

**Shows**:
- Running servers (PIDs and commands)
- Active ports (8888, 5175, 5173)
- Health checks for all 3 servers
- Last 10 log entries from each server
- Available monitoring commands

## Log Files Reference

| Server | Application Log | Error Log | Notes |
|--------|----------------|-----------|-------|
| Backend | `server/data/logs/server.log` | `server/data/logs/error.log` | Production-ready |
| LocaNext | `logs/locanext_app.log` | `logs/locanext_error.log` | Electron main process |
| Dashboard | `logs/dashboard_app.log` | `logs/dashboard_error.log` | SvelteKit dev + browser |

## Usage Examples

### Monitor Everything in Real-Time

```bash
# Terminal 1: Start all servers
python3 server/main.py &
cd adminDashboard && npm run dev -- --port 5175 &
cd locaNext && npm run dev &

# Terminal 2: Monitor all logs
bash scripts/monitor_logs_realtime.sh
```

### Check Server Status

```bash
bash scripts/monitor_all_servers.sh
```

Output:
```
========================================
🔍 LocaNext - Complete Server Monitor
========================================

📊 Running Servers:
  Backend (8888): ✅ HEALTHY
  Dashboard (5175): ✅ HEALTHY
  LocaNext (5173): ✅ HEALTHY

📝 Recent Activity (Last 10 log entries from each server):
...
```

### Monitor Only Errors

```bash
bash scripts/monitor_logs_realtime.sh --errors-only
```

### Monitor Specific Server

```bash
# Backend only
tail -f server/data/logs/server.log

# LocaNext only
tail -f logs/locanext_app.log

# Dashboard only
tail -f logs/dashboard_app.log

# All errors only
tail -f server/data/logs/error.log logs/*_error.log
```

### Search Logs

```bash
# Find all errors in the last hour
grep "ERROR" logs/*.log server/data/logs/*.log

# Find specific user activity
grep "user_id: 123" logs/*.log

# Find Python execution logs
grep "Python:" logs/locanext_app.log
```

## Logger API Reference

### LocaNext Electron Logger

```javascript
import { logger } from './logger.js';

// Basic logging
logger.info('Message', { optional: 'data' });
logger.success('Operation completed');
logger.warning('Potential issue');
logger.error('Error occurred', { error: err.message });
logger.critical('Critical failure', { stack: err.stack });
logger.debug('Debug info'); // Only in development

// Specialized logging
logger.ipc('channel-name', { data });
logger.python('/path/to/script.py', success, output);
logger.cleanup(); // Archive old logs
```

### Admin Dashboard Logger

```javascript
import { logger } from '$lib/utils/logger.js';

// Basic logging
logger.info('Message', { optional: 'data' });
logger.success('Data loaded');
logger.warning('Slow response');
logger.error('API failed', { error: err.message });
logger.debug('Debug info'); // Only in dev mode

// Specialized logging
logger.apiCall('/api/users', 'GET', { params });
logger.userAction('delete-user', { userId: 123 });
logger.component('Dashboard', 'mounted', { data });
```

## Maintenance

### Log Rotation

**LocaNext**: Automatic (logs older than 7 days archived to `logs/archive/`)

**Backend**: Manual (implement if needed)

**Dashboard**: Manual (implement if needed)

### Cleanup Old Logs

```bash
# Archive logs older than 30 days
find logs/ -name "*.log" -mtime +30 -exec gzip {} \;

# Delete archived logs older than 90 days
find logs/archive/ -name "*.gz" -mtime +90 -delete
```

## Troubleshooting

### Log files not created

**Solution**: The log files are created automatically when:
1. LocaNext app starts (creates `locanext_app.log`)
2. Dashboard starts (creates `dashboard_app.log`)
3. Backend starts (creates `server.log`)

If files don't exist, the apps haven't been run yet with the new logging.

### Monitoring script shows "No log file found"

This is normal if the app hasn't been run yet. Start the app and logs will appear.

### Logs not appearing in real-time

Make sure the apps are actually running and generating activity. Try:
```bash
# Trigger some backend activity
curl http://localhost:8888/health

# Trigger LocaNext activity (if running)
# Use the app UI to perform actions

# Trigger Dashboard activity (if running)
# Load the dashboard in browser
```

## Benefits for Claude AI

This comprehensive logging system allows Claude to:

1. **Debug Issues**: See exact error messages and stack traces
2. **Track Operations**: Monitor Python script execution, IPC calls, API requests
3. **Performance Analysis**: Identify slow requests and bottlenecks
4. **User Behavior**: Understand how users interact with the apps
5. **Real-Time Monitoring**: Watch all three servers simultaneously
6. **Historical Analysis**: Review past sessions and errors
7. **Testing Verification**: Confirm features work correctly by checking logs

## Next Steps

1. ✅ Logging implemented for all 3 servers
2. ✅ Monitoring scripts updated
3. 🔜 Test with actual app usage
4. 🔜 Add metrics dashboard (optional)
5. 🔜 Add alerting for critical errors (optional)

## Files Modified/Created

**Created**:
- `locaNext/electron/logger.js` - LocaNext logger utility
- `adminDashboard/src/lib/utils/logger.js` - Dashboard logger utility
- `docs/MONITORING_SYSTEM.md` - This documentation

**Modified**:
- `locaNext/electron/main.js` - Integrated logger
- `adminDashboard/src/routes/+page.svelte` - Integrated logger
- `scripts/monitor_logs_realtime.sh` - Added all 6 log files
- `scripts/monitor_all_servers.sh` - Shows all 3 servers

---

**Status**: ✅ Complete - Ready for testing and deployment
