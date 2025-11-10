# Monitoring Guide - Best Practices

**Last Updated**: 2025-11-10
**Purpose**: Proper monitoring approach for live troubleshooting

---

## ❌ WHAT NOT TO DO

### 1. Don't Check Old Logs
```bash
# ❌ WRONG - Shows yesterday's errors
tail -100 server/data/logs/error.log

# ❌ WRONG - Grep entire log file (includes old data)
grep "ERROR" server/data/logs/server.log
```

**Why wrong**: You're looking at historical data, not current issues.

### 2. Don't Create Test Scripts for Every Issue
**Problem**: We had script bloat - diagnostic scripts, test scripts, live monitors, etc.
**Solution**: Use ONLY the monitoring scripts we maintain.

---

## ✅ CORRECT MONITORING APPROACH

### Method 1: Live Monitoring (BEST for Development)

**Watch for NEW errors as they happen:**
```bash
# In one terminal, run this and LEAVE IT RUNNING
bash scripts/monitor_logs_realtime.sh --errors-only

# Now reproduce the issue in another terminal/browser
# You'll see errors appear in REAL-TIME with color coding
```

**What you see:**
- 🔥 CRITICAL errors (red)
- ❌ ERROR messages (red)
- ⚠️ WARNING messages (yellow)
- ✅ SUCCESS messages (green)

**When to use**: Active development, debugging, reproducing issues.

---

### Method 2: Recent Errors (Quick Check)

**Check ONLY the last 10 NEW errors:**
```bash
# Show only errors from current hour
tail -50 server/data/logs/server.log | grep "$(date '+%Y-%m-%d %H:')" | grep ERROR

# Or simpler - last 10 lines with ERROR
tail -100 server/data/logs/server.log | grep ERROR | tail -10
```

**When to use**: Quick sanity check, CI/CD pipelines.

---

### Method 3: Test Specific Feature Right Now

**Test an API endpoint LIVE:**
```bash
python3 - <<'EOF'
import requests
import json

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
print(f"Data: {response.json()}")
EOF
```

**When to use**: Testing specific functionality, validating fixes.

---

## 🛠️ MONITORING TOOLS WE USE

### Primary Tools (Use These)

1. **`scripts/monitor_logs_realtime.sh`** - Live error monitoring
   ```bash
   # All logs
   bash scripts/monitor_logs_realtime.sh

   # Errors only (recommended)
   bash scripts/monitor_logs_realtime.sh --errors-only

   # Backend only
   bash scripts/monitor_logs_realtime.sh --backend-only
   ```

2. **`scripts/monitor_frontend_errors.sh`** - Frontend browser console errors
   ```bash
   # Watch frontend errors from browser console
   bash scripts/monitor_frontend_errors.sh

   # NOTE: Frontend errors are sent to backend via remote-logger.js
   # They appear in backend logs with [FRONTEND] tag
   # This includes: console.error(), ReferenceError, TypeError, etc.
   ```

3. **`tail` for Recent Logs**
   ```bash
   # Last 20 lines
   tail -20 server/data/logs/server.log

   # Follow mode (live)
   tail -f server/data/logs/server.log
   ```

4. **`grep` with Time Filter**
   ```bash
   # Errors from current hour only
   grep "$(date '+%Y-%m-%d %H:')" server/data/logs/server.log | grep ERROR

   # Frontend errors specifically
   grep "\[FRONTEND\]" server/data/logs/server.log | grep ERROR
   ```

### DO NOT CREATE NEW MONITORING SCRIPTS
If you need to check something, use the tools above. Don't create:
- ❌ `diagnose_xyz.sh`
- ❌ `test_abc.sh`
- ❌ `check_123.sh`

---

## 📊 LOG FILE LOCATIONS

```
server/data/logs/
├── server.log       ← All backend activity
└── error.log        ← Backend errors only

logs/
├── locanext_app.log      ← Frontend (Electron)
├── locanext_error.log    ← Frontend errors
├── dashboard_app.log     ← Dashboard
└── dashboard_error.log   ← Dashboard errors
```

---

## 🧹 LOG MAINTENANCE

### When to Clean Logs

**Clean logs when:**
- Starting a new development session (avoid confusion from old errors)
- After fixing major bugs (clear error history)
- Logs exceed 1000+ lines (performance)
- Before demonstrating to stakeholders (show clean slate)

### How to Clean Logs

```bash
# Archive old logs and start fresh
./scripts/clean_logs.sh
```

**What this does:**
- Archives all logs to `logs/archive/TIMESTAMP/`
- Resets current logs with clean markers
- Preserves historical data (never deletes)
- Adds timestamp marker to new logs

**Example output:**
```
✓ Archived error.log (1187 lines) → archive/20251110_125239/
✓ Reset error.log (added clean marker)
✓ Archived server.log (5771 lines) → archive/20251110_125239/
✓ Reset server.log (added clean marker)
```

**After cleaning:**
```bash
# Verify logs are clean
wc -l server/data/logs/*.log
# Should show ~3 lines each (just the markers)

# Check archive was created
ls -lh logs/archive/
```

### Why This Matters

**Problem**: Old error logs confuse future troubleshooting
- Claude sees 1000+ old errors and thinks system is broken
- Hard to distinguish current issues from historical ones
- Log files grow large and slow down searches

**Solution**: Clean logs regularly
- Fresh start for each session
- Historical data preserved in archive
- Clear markers show when logs were reset
- Future Claude sessions see clean slate

---

## 🔍 TROUBLESHOOTING WORKFLOWS

### Issue: API Returns 401 Unauthorized

**Step 1 - Check if server is running:**
```bash
curl -s http://localhost:8888/health
```

**Step 2 - Test login:**
```bash
curl -X POST http://localhost:8888/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Step 3 - Check LIVE logs:**
```bash
bash scripts/monitor_logs_realtime.sh --errors-only
# Then reproduce the 401 error
```

**Step 4 - Check for auth errors in last 5 minutes:**
```bash
tail -100 server/data/logs/server.log | grep "401\|Unauthorized"
```

---

### Issue: WebSocket Connection Fails

**Step 1 - Check server has WebSocket:**
```bash
grep "Socket.IO" server/data/logs/server.log | tail -5
```

**Step 2 - Test Socket.IO endpoint:**
```bash
curl -s http://localhost:8888/socket.io/?EIO=4&transport=polling
```

**Step 3 - Check WebSocket path in frontend:**
```bash
grep "path.*socket" locaNext/src/lib/api/websocket.js
# Should show: path: '/ws/socket.io'
```

**Step 4 - Monitor WebSocket errors LIVE:**
```bash
bash scripts/monitor_logs_realtime.sh --errors-only
# Open browser, trigger WebSocket connection
```

---

### Issue: Progress Tracking Not Working

**Step 1 - Check database has operations:**
```bash
python3 - <<'EOF'
from sqlalchemy import create_engine, select
from server.database.models import ActiveOperation
from server.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(select(ActiveOperation))
    ops = result.fetchall()
    print(f"Operations in DB: {len(ops)}")
    for op in ops[:5]:
        print(f"  - {op.operation_name} ({op.status})")
EOF
```

**Step 2 - Test progress API:**
```bash
# Get token and test
python3 -c "
import requests
r = requests.post('http://localhost:8888/api/v2/auth/login', json={'username':'admin','password':'admin123'})
token = r.json()['access_token']
r = requests.get('http://localhost:8888/api/progress/operations?status=running', headers={'Authorization': f'Bearer {token}'})
print(f'Status: {r.status_code}')
print(f'Data: {r.json()}')
"
```

**Step 3 - Monitor progress updates LIVE:**
```bash
bash scripts/monitor_logs_realtime.sh | grep -E "progress|operation"
```

---

## 🎯 QUICK REFERENCE COMMANDS

```bash
# Live monitoring (leave running)
bash scripts/monitor_logs_realtime.sh --errors-only

# Check server health
curl -s http://localhost:8888/health

# Recent errors (last 10)
tail -100 server/data/logs/server.log | grep ERROR | tail -10

# Test login works
curl -X POST http://localhost:8888/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Check servers running
ps aux | grep -E "python3 server/main.py|npm.*dev" | grep -v grep

# Restart backend server
pkill -f "python3 server/main.py" && sleep 2 && nohup python3 server/main.py > /dev/null 2>&1 &
```

---

## 📝 INTERPRETING ERRORS

### Expected Errors (Not Real Issues)

```
WARNING | Cannot fetch tasks: User not logged in
→ Expected when TaskManager opens before login
→ Not an error, just informational
→ Will stop once user logs in

ERROR | HTTP 401: Unauthorized
→ Expected when token expired or not logged in
→ Solution: Login again
→ Tokens expire after 1 hour

WebSocket connection error (first try)
→ Expected on initial connection
→ Socket.IO tries multiple transports
→ Should succeed after 1-2 retries
```

### Real Errors (Need Fixing)

```
ERROR | 500 Internal Server Error
→ Backend crashed or validation error
→ Check server logs immediately
→ Usually includes stack trace

CRITICAL | Database connection failed
→ PostgreSQL/SQLite not accessible
→ Check database service running
→ Check DATABASE_URL in config

ERROR | Module not found
→ Missing Python dependency
→ Run: pip install -r requirements.txt
→ Or check virtual environment active
```

---

## 🚀 MONITORING DURING DEVELOPMENT

**Best Practice Workflow:**

1. **Terminal 1** - Backend server:
   ```bash
   python3 server/main.py
   ```

2. **Terminal 2** - Live monitoring:
   ```bash
   bash scripts/monitor_logs_realtime.sh --errors-only
   ```

3. **Terminal 3** - Frontend:
   ```bash
   cd locaNext && npm run dev:svelte -- --port 5173
   ```

4. **Browser** - Application:
   ```
   http://localhost:5173
   ```

Now when you interact with the app:
- Terminal 2 shows errors in REAL-TIME
- You see exactly when and why errors occur
- No need to check historical logs

---

## 📚 SUMMARY

**DO**:
- ✅ Use `monitor_logs_realtime.sh --errors-only` for live monitoring
- ✅ Check last 10 lines: `tail -100 ... | grep ERROR | tail -10`
- ✅ Test features with Python scripts (immediately, not async)
- ✅ Filter by current hour: `grep "$(date '+%Y-%m-%d %H:')"`

**DON'T**:
- ❌ Check entire log files (too much historical data)
- ❌ Create new monitoring scripts for every issue
- ❌ Look at yesterday's errors when debugging today
- ❌ Use `head -100` on large log files (shows oldest data)

**Remember**: Live monitoring beats historical analysis every time!

---

*Last Updated: 2025-11-10*
