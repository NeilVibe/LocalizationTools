# Quick Start Guide

**Getting Started** | **Running Servers** | **Testing** | **Common Commands**

---

## 🚀 QUICK START (5 MINUTES)

### 1. Start the Backend Server

```bash
cd /home/neil1988/LocalizationTools
python3 server/main.py
```

Server runs on `http://localhost:8888`

**What you'll see:**
- Comprehensive logging of every request/response
- Database initialization (PostgreSQL or SQLite)
- WebSocket server ready
- All 38 API endpoints registered

**Test it:**
- Health check: `http://localhost:8888/health`
- API docs: `http://localhost:8888/docs`

---

### 2. Run LocaNext Desktop App

```bash
cd /home/neil1988/LocalizationTools/locaNext

# Development mode (with hot reload)
npm run dev

# Electron mode (desktop app)
npm run electron:dev

# Web preview (browser testing)
npm run dev:svelte -- --port 5176
```

**Login:** admin / admin123

**Note:** XLSTransfer requires Electron app (not web browser) due to file dialogs

---

### 3. Run Admin Dashboard

```bash
cd /home/neil1988/LocalizationTools/adminDashboard
npm run dev -- --port 5175
```

Dashboard runs on `http://localhost:5175`

---

## 🧪 TESTING

### Run All Tests

```bash
cd /home/neil1988/LocalizationTools

# All tests
python3 -m pytest

# Async tests only
python3 -m pytest tests/test_async_*.py -v

# Unit tests only
python3 -m pytest tests/unit/ -v

# With coverage
python3 -m pytest --cov=server --cov=client
```

**Expected:** 160 tests passing (49% coverage) ✅

---

### Test Backend Endpoints

```bash
# Health check
curl http://localhost:8888/health

# Login (get JWT token)
curl -X POST http://localhost:8888/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Test authenticated endpoint
curl -X GET http://localhost:8888/api/v2/auth/me \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

---

## 🛠️ SETUP & UTILITIES

### Create Admin User

```bash
python3 scripts/create_admin.py
```

Creates default admin user (username: admin, password: admin123)

---

### Version Management

```bash
# Check version consistency across all files
python3 scripts/check_version_unified.py

# Update version (datetime-based)
NEW_VERSION=$(date '+%y%m%d%H%M')
echo "New version: $NEW_VERSION"
# Edit version.py, then run check
```

---

### Download AI Models

```bash
# Download Korean BERT model (447MB)
python3 scripts/download_models.py
```

**Note:** Model already installed locally in `client/models/`

---

### System Monitoring

```bash
# Full system health check
./scripts/monitor_system.sh

# Live status dashboard
./scripts/monitor_backend_live.sh

# Clean & archive old logs
./scripts/clean_logs.sh
```

---

## 🌐 IMPORTANT URLS

**When Servers Running:**

- Backend Server: `http://localhost:8888`
- API Docs: `http://localhost:8888/docs`
- Health Check: `http://localhost:8888/health`
- WebSocket: `ws://localhost:8888/ws/socket.io`
- Admin Dashboard: `http://localhost:5175`
- LocaNext Web Preview: `http://localhost:5176`

---

## ⚙️ ENVIRONMENT VARIABLES

### Server Configuration

```bash
# Database (default: PostgreSQL)
DATABASE_TYPE=postgresql  # or sqlite

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8888

# Optional Services
REDIS_ENABLED=false  # true to enable
CELERY_ENABLED=false  # true to enable

# Development
DEBUG=true
```

---

## 📦 BUILD & DISTRIBUTION

### Trigger Production Build

```bash
# Manual build trigger (saves GitHub Actions minutes)
echo "Build FULL v$(date '+%y%m%d%H%M')" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt
git commit -m "Trigger build v$(date '+%y%m%d%H%M')"
git push origin main
```

**Build Status:** https://github.com/NeilVibe/LocalizationTools/actions

---

## 🔍 TROUBLESHOOTING

### Server Won't Start

```bash
# Check if port 8888 is in use
lsof -i :8888

# Kill process if needed
kill -9 <PID>

# Check logs
tail -f server/data/logs/server.log
```

---

### Database Issues

```bash
# Reset database (SQLite)
rm server/data/app.db
python3 server/main.py  # Will recreate

# Check database
sqlite3 server/data/app.db ".tables"
```

---

### Tests Failing

```bash
# Run tests with verbose output
python3 -m pytest -vv

# Run specific test file
python3 -m pytest tests/test_async_auth.py -v

# Show print statements
python3 -m pytest -s
```

---

## 🎓 NEXT STEPS

After getting everything running:

1. **Read Core Documentation:**
   - `CLAUDE.md` - Master navigation hub
   - `DEPLOYMENT_ARCHITECTURE.md` - Understand hybrid model
   - `XLSTRANSFER_GUIDE.md` - XLSTransfer deep dive

2. **Explore the Codebase:**
   - `server/main.py` - Server entry point
   - `server/api/*_async.py` - Async API endpoints
   - `server/tools/xlstransfer/` - Tool template

3. **Run Your First Test:**
   - Start backend server
   - Open browser to http://localhost:5176
   - Test XLSTransfer functionality

---

## 📚 Related Documentation

- **CLAUDE.md** - Master navigation hub (start here!)
- **PROJECT_STRUCTURE.md** - Complete file tree
- **TESTING_GUIDE.md** - Comprehensive testing procedures
- **MONITORING_COMPLETE_GUIDE.md** - Monitoring & logging
- **BUILD_AND_DISTRIBUTION.md** - Build system
