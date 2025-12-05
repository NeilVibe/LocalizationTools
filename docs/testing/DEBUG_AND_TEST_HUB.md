# Debug & Test Hub - Complete Remote Access Guide

**Priority:** Central Documentation | **Updated:** 2025-12-05

This is the **MASTER GUIDE** for all testing, debugging, and remote access methods.

---

## 🗺️ CAPABILITIES TREE (What Claude Can Do)

```
REMOTE ACCESS & TESTING CAPABILITIES
═══════════════════════════════════════════════════════════════════════════════
│
├── 🖥️ WINDOWS EXE DEBUGGING (from WSL)
│   │
│   ├── 📡 CDP (Chrome DevTools Protocol) ──── MOST POWERFUL
│   │   ├── Launch: LocaNext.exe --remote-debugging-port=9222
│   │   ├── Connect: http://localhost:9222/json
│   │   ├── Capabilities:
│   │   │   ├── ✅ Read DOM state
│   │   │   ├── ✅ Execute JavaScript
│   │   │   ├── ✅ Click buttons programmatically
│   │   │   ├── ✅ Fill forms
│   │   │   ├── ✅ Navigate pages
│   │   │   ├── ✅ Take screenshots
│   │   │   ├── ✅ Monitor console logs
│   │   │   └── ✅ Intercept network requests
│   │   ├── Test Scripts: locaNext/scripts/master_test.js
│   │   └── Doc: WINDOWS_TROUBLESHOOTING.md
│   │
│   ├── 📁 Log File Access
│   │   ├── Path: /mnt/c/Users/.../AppData/Local/LocaNext/logs/
│   │   ├── Read: cat /mnt/c/.../main.log
│   │   ├── Watch: tail -f /mnt/c/.../main.log
│   │   └── All Electron logs written here
│   │
│   └── 🔌 Process Control
│       ├── Launch: /mnt/c/.../LocaNext.exe &
│       ├── Kill: taskkill.exe /IM LocaNext.exe /F
│       └── Check: tasklist.exe | grep LocaNext
│
├── 🐍 BACKEND TESTING (Python)
│   │
│   ├── pytest ──────────────────────────── PRIMARY TEST RUNNER
│   │   ├── Quick: python3 -m pytest -v
│   │   ├── With Server: RUN_API_TESTS=1 python3 -m pytest -v
│   │   ├── Single file: python3 -m pytest tests/api/test_remote_logging.py -v
│   │   ├── Coverage: python3 -m pytest --cov=server
│   │   └── Doc: PYTEST_GUIDE.md
│   │
│   ├── Direct API Testing
│   │   ├── curl: curl -X GET http://localhost:8888/health
│   │   ├── Python requests: In test files
│   │   └── httpie: http GET localhost:8888/health
│   │
│   └── Database Inspection
│       ├── SQLite: sqlite3 server/data/localizationtools.db
│       ├── Tables: .tables
│       └── Query: SELECT * FROM users;
│
├── 🌐 FRONTEND TESTING
│   │
│   ├── Playwright ──────────────────────── E2E BROWSER AUTOMATION
│   │   ├── Run: cd locaNext && npm test
│   │   ├── Headed: npm test -- --headed
│   │   ├── Debug: npm test -- --debug
│   │   ├── Single: npm test -- tests/login.spec.ts
│   │   └── Doc: PLAYWRIGHT_GUIDE.md
│   │
│   ├── Visual Testing (X Server)
│   │   ├── Setup: Start VcXsrv on Windows
│   │   ├── Export: export DISPLAY=:0
│   │   ├── Test: xeyes (should show eyes window)
│   │   └── Doc: X_SERVER_SETUP.md
│   │
│   └── Browser DevTools
│       ├── Electron: Ctrl+Shift+I or DEBUG_MODE=true
│       ├── Console: View JS errors
│       └── Network: Monitor API calls
│
├── 🔄 REAL-TIME MONITORING
│   │
│   ├── WebSocket
│   │   ├── Connect: ws://localhost:8888/ws/socket.io
│   │   ├── Events: progress, logs, task updates
│   │   └── Test: wscat -c ws://localhost:8888/ws/socket.io
│   │
│   ├── Server Logs
│   │   ├── Watch: tail -f /tmp/server.log
│   │   ├── Errors: grep ERROR /tmp/server.log
│   │   └── Script: bash scripts/monitor_logs_realtime.sh
│   │
│   └── Health Endpoints
│       ├── Main: http://localhost:8888/health
│       ├── Telemetry: http://localhost:8888/api/v1/remote-logs/health
│       └── DB: Included in /health response
│
├── 📊 TELEMETRY TESTING (P12.5)
│   │
│   ├── Two-Port Simulation
│   │   ├── Desktop: python3 server/main.py (port 8888)
│   │   ├── Central: SERVER_PORT=9999 python3 server/main.py
│   │   └── Test: RUN_API_TESTS=1 python3 -m pytest tests/api/test_remote_logging.py -v
│   │
│   └── Telemetry API Endpoints
│       ├── POST /api/v1/remote-logs/register
│       ├── POST /api/v1/remote-logs/sessions/start
│       ├── POST /api/v1/remote-logs/submit
│       └── POST /api/v1/remote-logs/sessions/end
│
└── 🛠️ UTILITY TOOLS
    │
    ├── Screenshots/Recording
    │   ├── scrot: scrot screenshot.png (X Server needed)
    │   ├── ffmpeg: Record video
    │   └── Doc: TOOLS_REFERENCE.md
    │
    ├── UI Automation (Linux)
    │   ├── xdotool: xdotool search --name "LocaNext"
    │   ├── Click: xdotool click 1
    │   └── Type: xdotool type "hello"
    │
    └── Network Tools
        ├── netstat: netstat -tlnp | grep 8888
        ├── curl: API testing
        └── wget: Download files

═══════════════════════════════════════════════════════════════════════════════
```

---

## 📚 DOCUMENTATION TREE

```
docs/testing/
│
├── DEBUG_AND_TEST_HUB.md ──── THIS FILE (Master Guide)
│
├── 🚀 Quick Start
│   └── QUICK_COMMANDS.md ──── Copy-paste commands
│
├── 🐍 Backend Testing
│   └── PYTEST_GUIDE.md ────── pytest patterns, fixtures
│
├── 🌐 Frontend Testing
│   ├── PLAYWRIGHT_GUIDE.md ── E2E browser tests
│   └── X_SERVER_SETUP.md ──── Visual testing from WSL
│
├── 🖥️ Windows/Electron
│   └── ../WINDOWS_TROUBLESHOOTING.md ── CDP, logs, debugging
│
└── 🛠️ Tools
    └── TOOLS_REFERENCE.md ──── xdotool, ffmpeg, scrot
```

**Related Docs (outside testing/):**
- `docs/ELECTRON_TROUBLESHOOTING.md` - Black screen, preload issues
- `docs/MONITORING_COMPLETE_GUIDE.md` - Log monitoring
- `docs/LOGGING_PROTOCOL.md` - How to log properly

---

## ⚡ QUICK REFERENCE

### Start Everything for Full Testing

```bash
# Terminal 1: Backend
python3 server/main.py > /tmp/server.log 2>&1 &

# Terminal 2: Watch logs
tail -f /tmp/server.log

# Terminal 3: Run tests
RUN_API_TESTS=1 python3 -m pytest -v
```

### Test Windows EXE via CDP

```bash
# 1. Launch with debugging (from WSL)
/mnt/c/Users/.../LocaNext/LocaNext.exe --remote-debugging-port=9222 &

# 2. Wait for startup
sleep 30

# 3. Check pages available
curl -s http://localhost:9222/json | jq '.[].url'

# 4. Run CDP tests
node /mnt/c/.../locaNext/scripts/master_test.js
```

### Test Telemetry API

```bash
# Register
curl -X POST http://localhost:8888/api/v1/remote-logs/register \
  -H "Content-Type: application/json" \
  -d '{"installation_name": "Test", "version": "1.0.0"}'

# Submit logs (use api_key from register response)
curl -X POST http://localhost:8888/api/v1/remote-logs/submit \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"installation_id": "YOUR_ID", "logs": [{"timestamp": "2025-12-05T12:00:00Z", "level": "INFO", "message": "test", "source": "test", "installation_id": "YOUR_ID"}]}'
```

---

## 🧪 TEST COUNTS

| Category | Tests | Tool | Doc |
|----------|-------|------|-----|
| Backend Unit | 350+ | pytest | PYTEST_GUIDE.md |
| Backend E2E | 115 | pytest | PYTEST_GUIDE.md |
| API Simulation | 168 | pytest | PYTEST_GUIDE.md |
| Security | 86 | pytest | SECURITY_HARDENING.md |
| Telemetry | 10 | pytest | test_remote_logging.py |
| Frontend LocaNext | 134 | Playwright | PLAYWRIGHT_GUIDE.md |
| Frontend Dashboard | 30 | Playwright | PLAYWRIGHT_GUIDE.md |
| CDP (Windows EXE) | 15 | Node.js | WINDOWS_TROUBLESHOOTING.md |
| **Total** | **~1000+** | | |

---

## 🔑 KEY PATTERNS

### CDP: Finding the App Page (Not DevTools)

```javascript
// CDP returns multiple pages - find the actual app
const pages = await fetch('http://localhost:9222/json').then(r => r.json());
const appPage = pages.find(p =>
    p.type === 'page' &&
    p.url.includes('file:') &&
    !p.url.includes('devtools')
);
```

### pytest: TRUE Simulation (No Mocks)

```python
# Skip if server not running
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_API_TESTS"),
    reason="RUN_API_TESTS not set"
)

# Use real API client
class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8888"):
        self.session = requests.Session()
```

### Playwright: Headless by Default

```typescript
// In playwright.config.ts
use: {
    headless: true,  // Set false for visual debugging
    screenshot: 'only-on-failure',
}
```

---

## 📋 TROUBLESHOOTING QUICK FIXES

| Problem | Solution |
|---------|----------|
| Port 8888 in use | `fuser -k 8888/tcp` |
| CDP can't connect | Check if app started, wait longer |
| X Server not working | `export DISPLAY=:0` |
| pytest skipping tests | Set `RUN_API_TESTS=1` |
| Electron black screen | Check preload.js errors |
| WebSocket not connecting | Verify server started |

---

*Last updated: 2025-12-05*
