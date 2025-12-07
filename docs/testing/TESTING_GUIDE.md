# LocalizationTools - User Testing Guide

**How to test the complete system and see your usage stats!**

---

## 🚀 Quick Start - Test the Complete Workflow

### Step 1: Start the Server

The server receives logs and stores them in the database.

```bash
# Start the logging server (runs on port 8888)
python3 server/main.py
```

**Expected output:**
```
2025-11-08 15:01:56 | INFO     | Starting LocalizationTools Server v1.0.0
2025-11-08 15:01:56 | SUCCESS  | Database initialized successfully
INFO:     Uvicorn running on http://0.0.0.0:8888
```

**✅ Server is now running!** Keep this terminal open.

---

### Step 2: Launch the Admin Dashboard

The admin dashboard shows all your beautiful stats!

**Open a NEW terminal** and run:

```bash
# Start the admin dashboard (runs on port 8885)
python3 run_admin_dashboard.py
```

**Expected output:**
```
INFO     | Starting LocalizationTools Admin Dashboard...
INFO     | Launching Admin Dashboard on http://127.0.0.1:8885
Running on local URL:  http://0.0.0.0:8885
```

**✅ Admin dashboard will auto-open in your browser!**

**Admin Dashboard URL:** http://localhost:8885

---

### Step 3: Use the XLSTransfer Tool

Now let's use a tool and generate some logs!

**Open a THIRD terminal** and run:

```bash
# Start XLSTransfer tool (runs on port 7860)
python3 run_xlstransfer.py
```

**Expected output:**
```
Running on local URL:  http://0.0.0.0:7860
```

**✅ XLSTransfer tool will auto-open in your browser!**

**Tool URL:** http://localhost:7860

---

### Step 4: Generate Some Activity

In the **XLSTransfer tool** (http://localhost:7860):

1. Go to any tab (e.g., "Create Dictionary")
2. Upload some Excel files or use any function
3. Process them!

**Each operation will:**
- ✅ Execute on your local CPU
- ✅ Send usage logs to the server (port 8888)
- ✅ Store in the database
- ✅ Appear in the admin dashboard!

---

### Step 5: View Your Beautiful Stats! 🎉

Switch to the **Admin Dashboard** browser tab (http://localhost:8885)

You'll see **5 tabs** with comprehensive statistics:

#### 📊 **Overview Tab**
- **Real-time KPIs:**
  - Total users
  - Active users
  - Total operations today
  - Recent activity count
- **Tool usage breakdown**
- **Recent operations log**

#### 📝 **Logs Tab**
- All recent activity logs
- Filterable by date, user, tool, status
- Shows: timestamp, user, tool, function, duration, status

#### 👥 **Users Tab**
- All registered users
- User statistics (operations count, last activity)
- User management (activate/deactivate)

#### ❌ **Errors Tab**
- Error log monitoring
- Failed operations tracking
- Error messages and details

#### ⚙️ **Settings Tab**
- Server configuration display
- Database information
- System status

---

## 🎨 What You'll See in the Admin Dashboard

### Example Overview Display:

```
╔══════════════════════════════════════════════════════════╗
║           LOCALIZATIONTOOLS ADMIN DASHBOARD              ║
╚══════════════════════════════════════════════════════════╝

📊 QUICK STATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Users:          5
Active Users:         3
Operations Today:    27
Recent Activity:     12

🔧 TOOL USAGE BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

XLSTransfer:         18 operations (67%)
  └─ create_dictionary:     8 ops (avg 10.5s)
  └─ transfer_to_excel:     6 ops (avg 15.2s)
  └─ check_newlines:        4 ops (avg 3.1s)

📈 RECENT OPERATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2025-11-08 15:30:22 | testuser | XLSTransfer | create_dictionary | ✅ 12.5s
2025-11-08 15:28:15 | testuser | XLSTransfer | transfer_to_excel | ✅ 18.3s
2025-11-08 15:25:03 | admin    | XLSTransfer | check_newlines    | ✅ 2.8s
```

**Click "Refresh Data" button to see updates in real-time!**

---

## 🎯 Testing Scenarios

### Scenario 1: Basic Usage Test

**Goal:** Generate logs and see them in the dashboard

1. ✅ Start server
2. ✅ Open admin dashboard
3. ✅ Run XLSTransfer tool
4. ✅ Use "Create Dictionary" function
5. ✅ Go to admin dashboard → Overview tab
6. ✅ Click "Refresh Data"
7. ✅ See your operation logged!

**Expected Result:**
- Operation appears in "Recent Operations"
- Tool usage stats updated
- User activity tracked

---

### Scenario 2: Multi-Function Test

**Goal:** Test different functions and see statistics

1. ✅ Use "Create Dictionary" 3 times
2. ✅ Use "Transfer to Excel" 2 times
3. ✅ Use "Check Newlines" 1 time
4. ✅ Refresh admin dashboard
5. ✅ See breakdown:
   - XLSTransfer: 6 total operations
   - create_dictionary: 3 ops
   - transfer_to_excel: 2 ops
   - check_newlines: 1 op

**Expected Result:**
- Accurate operation counts
- Average duration per function
- Success rate tracking

---

### Scenario 3: Error Tracking Test

**Goal:** Cause an error and see it tracked

1. ✅ In XLSTransfer, try to upload invalid file
2. ✅ Operation fails
3. ✅ Go to admin dashboard → Errors tab
4. ✅ See error logged with message

**Expected Result:**
- Error appears in Errors tab
- Error message captured
- Failed operation count incremented

---

## 📍 Port Reference

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Server** | 8888 | http://localhost:8888 | Logging server & API |
| **Admin Dashboard** | 8885 | http://localhost:8885 | Stats & management |
| **XLSTransfer** | 7860 | http://localhost:7860 | Tool interface |

**All services run locally on your machine.**

---

## 🔐 Default Credentials

**Admin Login:**
- Username: `admin`
- Password: `admin123`

**Note:** Change these in production! See `ADMIN_SETUP.md` for details.

---

## 🐛 Troubleshooting

### Problem: "Server not running"

**Solution:**
```bash
# Check if server is running
curl http://localhost:8888/health

# Expected response:
{"status":"healthy","database":"connected","version":"1.0.0"}
```

If not running, start it:
```bash
python3 server/main.py
```

---

### Problem: "Admin dashboard shows no data"

**Checklist:**
1. ✅ Is the server running? (port 8888)
2. ✅ Did you use any tool functions?
3. ✅ Did you click "Refresh Data" button?
4. ✅ Check server terminal for errors

---

### Problem: "Port already in use"

**Solution:**
```bash
# Kill processes on specific port
lsof -ti:8888 | xargs kill -9  # Kill server
lsof -ti:8885 | xargs kill -9  # Kill admin dashboard
lsof -ti:7860 | xargs kill -9  # Kill XLSTransfer
```

---

## 🎓 Understanding the Flow

```
┌─────────────────┐
│  XLSTransfer    │  (Your local CPU does the work)
│  (Port 7860)    │
└────────┬────────┘
         │
         │ Sends logs via HTTP
         │
         ▼
┌─────────────────┐
│  Logging Server │  (Stores logs in database)
│  (Port 8888)    │
└────────┬────────┘
         │
         │ Queries database
         │
         ▼
┌─────────────────┐
│ Admin Dashboard │  (Shows beautiful stats!)
│  (Port 8885)    │
└─────────────────┘
```

**Key Points:**
- ✅ Tools run on YOUR CPU (local processing)
- ✅ Server only receives logs (lightweight)
- ✅ Dashboard queries database for stats
- ✅ Everything is local (no cloud needed)

---

## 🎨 Expected Admin Dashboard Features

### Current Features (MVP):
- ✅ Real-time operation logs
- ✅ Tool usage statistics
- ✅ User activity tracking
- ✅ Error monitoring
- ✅ Server status display

### Future Features (Coming Soon):
- 📊 Interactive charts (daily/weekly/monthly)
- 📈 Performance trends over time
- 👥 User leaderboards
- 📊 Export reports (PDF/Excel)
- 🔔 Real-time notifications

---

## ✅ Success Criteria

**You'll know it's working when:**

1. ✅ Server starts without errors
2. ✅ Admin dashboard opens in browser
3. ✅ XLSTransfer tool opens in browser
4. ✅ Using any function logs operation
5. ✅ Dashboard shows your operations
6. ✅ Statistics update correctly
7. ✅ Refresh button works

**If all above work → System is working perfectly!** 🎉

---

## 🚀 Next Steps

Once you've tested the system:

1. **Add more users** (see ADMIN_SETUP.md)
2. **Test with real files** (use actual Excel files)
3. **Monitor performance** (check PERFORMANCE.md)
4. **Deploy to production** (coming in next phase)

---

## 📞 Need Help?

- **Documentation:** See README.md, Claude.md, ADMIN_SETUP.md
- **Testing:** See TESTING.md for unit/integration tests
- **Performance:** See PERFORMANCE.md for benchmarks
- **Database:** See database_schema.sql for schema

---

## 📝 Summary

**To test the complete system:**

```bash
# Terminal 1: Start server
python3 server/main.py

# Terminal 2: Start admin dashboard
python3 run_admin_dashboard.py

# Terminal 3: Start XLSTransfer tool
python3 run_xlstransfer.py
```

**Then:**
1. Use the tool (http://localhost:7860)
2. View stats (http://localhost:8885)
3. See beautiful, well-organized statistics! 🎉

**Everything works locally. No internet required. Your CPU does the processing.**

---

**Ready to test? Start with Terminal 1 and work your way down! 🚀**
