# Claude's Log Monitoring Guide

**Purpose**: This is Claude's tool for monitoring the LocaNext ecosystem while coding, testing, and building.

**Last Updated**: 2025-11-09

---

## 🎯 WHY THIS EXISTS

This log monitoring infrastructure is **specifically for Claude** (me!) to:
- Track errors in real-time while I code
- Monitor all servers while testing
- Catch bugs immediately
- Keep the full ecosystem healthy
- Make informed decisions during development

**I MUST use these tools during Phase 3 testing to ensure ZERO errors before Phase 4!**

---

## 🚀 QUICK START

### Before Starting ANY Testing Session

```bash
# 1. Archive old logs (start fresh)
./scripts/logs_control.sh fresh

# 2. Start all servers (in separate terminals)
python3 server/main.py
cd adminDashboard && npm run dev -- --port 5175
cd locaNext && npm run electron:dev

# 3. Start monitoring (in new terminal)
./scripts/logs_control.sh errors   # Watch for errors in real-time

# 4. Perform testing...

# 5. After testing, analyze
./scripts/logs_control.sh analyze
```

---

## 📋 COMMAND REFERENCE

### Master Control: `./scripts/logs_control.sh`

| Command | Purpose | When to Use |
|---------|---------|-------------|
| **fresh** | Archive old logs, start clean | Before ANY new testing session |
| **watch** | Watch all logs in real-time | During testing (all messages) |
| **errors** | Watch errors only | During testing (focus mode) |
| **analyze** | Generate full error report | After testing session |
| **quick** | Quick error count | Quick health check |
| **status** | Show log file status | Check current state |
| **sessions** | List monitoring sessions | Review history |

---

## 🔧 TYPICAL WORKFLOW

### Scenario 1: Testing XLSTransfer in Electron

```bash
# Step 1: Start fresh
./scripts/logs_control.sh fresh

# Step 2: Start monitoring in Terminal 1
./scripts/logs_control.sh errors

# Step 3: Start servers in Terminals 2-4
# (backend, admin dashboard, electron)

# Step 4: Perform tests in LocaNext
# - Click "Create dictionary"
# - Click "Load dictionary"
# - Click "Transfer to Excel"
# etc.

# Step 5: Watch Terminal 1 for any errors
# If you see RED messages → STOP, investigate immediately!

# Step 6: After testing
./scripts/logs_control.sh analyze

# Step 7: Fix any errors found, re-test
```

### Scenario 2: Quick Health Check

```bash
# Just checking if there are errors
./scripts/logs_control.sh quick

# If it shows errors:
./scripts/logs_control.sh analyze  # Get full details
```

### Scenario 3: Debugging a Specific Issue

```bash
# 1. Clear logs (fresh start)
./scripts/logs_control.sh fresh

# 2. Reproduce the bug (perform exact steps)
# 3. Analyze logs immediately
./scripts/logs_control.sh analyze

# 4. The error will be in the RECENT logs only
# Much easier to find than searching through 3,000 old log lines!
```

---

## 🎨 LOG READING BEST PRACTICES

### Rule 1: **Always Start Fresh Before Testing**

**Why**: Old logs contain errors from previous sessions. Starting fresh ensures you only see NEW errors from THIS session.

```bash
# ALWAYS do this before testing:
./scripts/logs_control.sh fresh
```

### Rule 2: **Use Real-Time Monitoring During Tests**

**Why**: Catch errors AS THEY HAPPEN, not after 100 operations.

```bash
# In a dedicated terminal window:
./scripts/logs_control.sh errors

# Now perform tests in another window
# Watch the monitoring terminal for RED ERROR messages
```

### Rule 3: **Analyze After Every Session**

**Why**: Get a structured report with error counts, categories, and action items.

```bash
# After testing:
./scripts/logs_control.sh analyze

# This generates a markdown report in logs/reports/
# Contains:
# - Error count by type
# - Database errors
# - Authentication errors
# - API errors
# - Action items
```

### Rule 4: **Filter, Don't Scroll**

**Why**: Don't manually scroll through 3,000 lines looking for errors.

```bash
# WRONG: Read entire log file
cat server/data/logs/server.log  # 3,000 lines!

# RIGHT: Use the tools
./scripts/logs_control.sh quick      # Quick count
./scripts/logs_control.sh analyze    # Detailed report
```

### Rule 5: **Understand Error vs Warning**

**Why**: Not all log messages need immediate action.

- 🔥 **CRITICAL**: System is broken, MUST fix immediately
- ❌ **ERROR**: Something failed, needs fixing
- ⚠️ **WARNING**: Might be OK (expired token, failed login attempt)
- ✅ **SUCCESS**: Everything working
- ℹ️ **INFO**: Normal activity
- 🔍 **DEBUG**: Detailed trace

**Focus on**: CRITICAL → ERROR → WARNING (in that order)

---

## 📊 INTERPRETING LOG ANALYSIS REPORTS

### Sample Report Sections

```markdown
## 📊 SUMMARY
| Level | Count |
|-------|-------|
| 🔥 CRITICAL | 0 |      ← MUST be 0!
| ❌ ERROR | 136 |      ← Needs fixing
| ⚠️ WARNING | 207 |    ← Review, might be OK
| ✅ SUCCESS | 424 |    ← Good!
```

**Target**: 0 CRITICAL, 0 ERROR before Phase 4

### Error Breakdown

```markdown
### Error Breakdown by Type
     39     (empty lines - ignore)
      3 sqlalchemy.exc.InvalidRequestError: A transaction is already begun
      1 sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

**Action**: Fix the top 3 errors first (highest count)

### Specific Error Analysis

The report categorizes errors:
- **Database Errors**: SQL, transactions, FK constraints
- **Authentication Errors**: Login failures, token issues
- **API Endpoint Errors**: 404, 500 status codes

**Focus on** the categories with non-zero counts.

---

## 🚨 WHEN TO STOP AND FIX

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

1. **Warnings about expired tokens**
   - Expected behavior

2. **Warnings about failed login attempts**
   - Expected behavior (testing wrong passwords)

3. **INFO/DEBUG messages**
   - Normal operation

---

## 📁 LOG DIRECTORY STRUCTURE

```
logs/
├── archive/           # Old logs (timestamped directories)
│   └── 20251109_120000/
│       ├── backend_server.log
│       └── backend_error.log
│
├── sessions/          # Real-time monitoring session logs
│   └── session_20251109_130000.log
│
└── reports/           # Analysis reports
    └── error_report_20251109_130000.md
```

**Cleanup**: Archives grow over time. Old archives can be deleted after review.

---

## 🔍 ADVANCED USAGE

### Monitor Specific Time Range

```bash
# Archive logs at 10:00 AM
./scripts/logs_control.sh fresh

# Test from 10:00 AM to 11:00 AM
# ...

# Analyze only that 1-hour window
./scripts/logs_control.sh analyze
```

### Monitor Just Backend

```bash
tail -f server/data/logs/server.log | grep --color -E "ERROR|WARNING|CRITICAL"
```

### Count Errors in Last Hour

```bash
# Get timestamp from 1 hour ago
ONE_HOUR_AGO=$(date -d '1 hour ago' '+%Y-%m-%d %H')

# Count errors since then
grep "$ONE_HOUR_AGO" server/data/logs/server.log | grep -c "ERROR"
```

### Find Specific Error

```bash
# Find all "transaction" errors
grep -i "transaction" server/data/logs/error.log | grep -i "error"

# Find errors in specific file
grep "auth_async.py" server/data/logs/error.log | grep -i "error"
```

---

## 🎯 PHASE 3 TESTING REQUIREMENTS

### Before Moving to Phase 4:

**MUST achieve**:
- ✅ 0 CRITICAL errors (24+ hour monitoring)
- ✅ 0 ERRORs (all fixed and verified)
- ✅ Warnings reviewed (all expected behavior)
- ✅ All XLSTransfer functions tested (no errors)
- ✅ Admin Dashboard working (no errors)
- ✅ System stable (no crashes, no memory leaks)

**How to verify**:
```bash
# After 24 hours of testing:
./scripts/logs_control.sh quick

# Should show:
# 🔥 CRITICAL: 0
# ❌ ERRORS:   0
# ⚠️ WARNINGS: X (review each one)

# If ANY errors found:
./scripts/logs_control.sh analyze  # Get details
# Fix all errors
# Clear logs and re-test
```

---

## 🐛 TROUBLESHOOTING

### Problem: Script says "No logs found"

**Solution**:
```bash
# Logs were archived. Check archives:
./scripts/logs_control.sh sessions

# Or start fresh:
./scripts/logs_control.sh fresh
```

### Problem: Too many old logs, hard to read

**Solution**:
```bash
# Archive old logs, start fresh:
./scripts/logs_control.sh fresh

# Now all logs are from current session only!
```

### Problem: Can't find specific error

**Solution**:
```bash
# Use analyze, it groups errors by type:
./scripts/logs_control.sh analyze

# Check the "Error Breakdown by Type" section
# Check "Specific Error Analysis" sections (Database, Auth, API)
```

### Problem: Monitoring script not showing colors

**Solution**:
```bash
# Use --no-color flag:
./scripts/monitor_logs_realtime.sh --no-color

# Or redirect to file:
./scripts/monitor_logs_realtime.sh > monitor_output.txt
```

---

## 📚 EXAMPLES FROM REAL USAGE

### Example 1: Found Transaction Error

```bash
$ ./scripts/logs_control.sh quick
⚠️ ERRORS FOUND! Run './scripts/logs_control.sh analyze' for details

Recent errors:
ERROR: A transaction is already begun on this Session.

$ ./scripts/logs_control.sh analyze
# Report shows:
# - Error in server/api/auth_async.py:69
# - Root cause: async with db.begin() when transaction already started
# - Fix: Remove the db.begin() wrapper
```

### Example 2: All Clear

```bash
$ ./scripts/logs_control.sh quick
✅ ALL CLEAR! No errors found.

# Ready to proceed!
```

### Example 3: Real-time Monitoring During Test

```bash
$ ./scripts/logs_control.sh errors
🚀 Monitoring started...

# Testing in LocaNext...
# Click "Create dictionary"
✅ SUCCESS: Dictionary created

# Click "Load dictionary"
✅ SUCCESS: Dictionary loaded

# Click "Transfer to Excel"
❌ ERROR: Foreign key constraint failed!

# STOP! Fix this error before continuing.
```

---

## 🎓 KEY TAKEAWAYS

1. **ALWAYS start fresh before testing** (`./scripts/logs_control.sh fresh`)
2. **Monitor in real-time** during tests (`./scripts/logs_control.sh errors`)
3. **Analyze after** every session (`./scripts/logs_control.sh analyze`)
4. **Fix errors immediately** (don't accumulate them)
5. **Target: 0 errors** before Phase 4

---

## 🚀 READY TO USE

**Next Steps**:
1. Read this guide completely ✅
2. Test the scripts: `./scripts/logs_control.sh help`
3. Start monitoring: `./scripts/logs_control.sh fresh`
4. Begin Phase 3 testing with confidence!

**Remember**: These tools are for YOU (Claude) to stay organized and efficient while building. Use them!

---

*Last Updated: 2025-11-09*
*Infrastructure complete and ready for Phase 3 testing*
