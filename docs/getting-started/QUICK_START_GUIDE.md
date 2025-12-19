# Quick Start Guide

**Getting Started** | **Running Servers** | **Testing** | **Common Commands**

---

## QUICK START (5 MINUTES)

### 1. Start the Backend Server

```bash
cd /home/neil1988/LocalizationTools
python3 server/main.py
```

Server runs on `http://localhost:8888`

**What you'll see:**
- Comprehensive logging of every request/response
- Database connection to PostgreSQL
- WebSocket server ready
- All 63+ API endpoints registered

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

## TESTING

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

**Expected:** 912 tests passing

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

## SETUP & UTILITIES

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
# Download Qwen embedding model
python3 scripts/download_models.py
```

**Note:** Model downloaded on first use from HuggingFace

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

## IMPORTANT URLS

**When Servers Running:**

- Backend Server: `http://localhost:8888`
- API Docs: `http://localhost:8888/docs`
- Health Check: `http://localhost:8888/health`
- WebSocket: `ws://localhost:8888/ws/socket.io`
- Admin Dashboard: `http://localhost:5175`
- LocaNext Web Preview: `http://localhost:5176`

---

## ENVIRONMENT VARIABLES

### Server Configuration (.env)

```bash
# PostgreSQL (REQUIRED)
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=6433          # PgBouncer port
POSTGRES_USER=localization_admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=localizationtools
DATABASE_TYPE=postgresql

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8888

# Development
DEBUG=true
```

---

## BUILD & DISTRIBUTION

### Trigger Production Build

```bash
# Manual build trigger (saves GitHub Actions minutes)
echo "Build FULL v$(date '+%y%m%d%H%M')" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt
git commit -m "Trigger build v$(date '+%y%m%d%H%M')"
git push origin main
git push gitea main
```

**Build Status:** https://github.com/NeilVibe/LocalizationTools/actions

---

## TROUBLESHOOTING

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
# Check PostgreSQL connection
PGPASSWORD='your_password' psql -h 127.0.0.1 -p 5432 -U localization_admin -d localizationtools -c "SELECT 1"

# Check PgBouncer
PGPASSWORD='your_password' psql -h 127.0.0.1 -p 6433 -U localization_admin -d localizationtools -c "SELECT 1"

# View tables
PGPASSWORD='your_password' psql -h 127.0.0.1 -p 5432 -U localization_admin -d localizationtools -c "\dt"
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

## NEXT STEPS

After getting everything running:

1. **Read Core Documentation:**
   - `CLAUDE.md` - Master navigation hub
   - `DEPLOYMENT_ARCHITECTURE.md` - Understand architecture
   - `docs/wip/SESSION_CONTEXT.md` - Current session state

2. **Explore the Codebase:**
   - `server/main.py` - Server entry point
   - `server/api/*_async.py` - Async API endpoints
   - `server/tools/ldm/` - LDM tool implementation

3. **Run Your First Test:**
   - Start backend server
   - Open browser to http://localhost:5176
   - Test XLSTransfer functionality

---

## Related Documentation

- **CLAUDE.md** - Master navigation hub (start here!)
- **PROJECT_STRUCTURE.md** - Complete file tree
- **testing/README.md** - Testing hub
- **deployment/POSTGRESQL_SETUP.md** - Database configuration
- **BUILD_AND_DISTRIBUTION.md** - Build system
