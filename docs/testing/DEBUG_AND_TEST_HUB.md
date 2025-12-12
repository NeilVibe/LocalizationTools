# Debug & Test Hub - Complete Remote Access Guide

**Priority:** Central Documentation | **Updated:** 2025-12-06

This is the **MASTER GUIDE** for all testing, debugging, and remote access methods.

---

## 🎯 AUTONOMOUS TESTING PHILOSOPHY

**Claude works ALONE on testing. User provides direction only.**

```
TESTING PROTOCOL:
═══════════════════════════════════════════════════════════════

User Role:
├── Overall design decisions
├── Direction and priorities
└── Final approval

Claude Role (FULLY AUTONOMOUS):
├── Build the app
├── Deploy to test folder
├── Run ALL tests independently
├── Fix issues found
├── Rebuild and retest
├── Report results
└── NO USER INTERVENTION NEEDED
```

### 📂 Windows Testing Playground

```
D:\LocaNext\              ← OFFICIAL WINDOWS TEST FOLDER
├── LocaNext.exe          ← Built app
├── server/               ← Backend
├── logs/                 ← Test logs
└── *.js                  ← CDP test scripts

WSL Access: /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext
```

### 📁 Test Data Files (D:\TestFilesForLocaNext)

```
D:\TestFilesForLocaNext\          ← TEST DATA FOR ALL TOOLS
│
├── QuickSearch Test Files:
│   ├── sampleofLanguageData.txt  ← RECOMMENDED (16MB, 9 cols, KR+FR)
│   └── SMALLTESTFILEFORQUICKSEARCH.txt ← ⚠️ BAD (inconsistent columns)
│
├── XLSTransfer Test Files:
│   ├── 150linetransaltiontest.xlsx
│   ├── translationTEST.xlsx
│   ├── TESTSMALL.xlsx
│   └── versysmallSMALLDB1.xlsx
│
├── KR Similar Test Files:
│   ├── lineembeddingtest.xlsx
│   └── 검은별test.xlsx
│
├── Glossary Test Files:
│   ├── GlossaryUploadTestFile.xlsx
│   ├── fileusedfordynamicglossary.xlsx
│   └── fileusedfornormalglossary.xlsx
│
└── Close Files:
    ├── closetotest.txt
    └── closetotest_translated.txt

WSL Access: /mnt/d/TestFilesForLocaNext
```

**⚠️ IMPORTANT: QuickSearch requires 7+ column TSV files (cols 0-6):**
- Column 5 = Korean text
- Column 6 = Translation text
- Use `sampleofLanguageData.txt` NOT `SMALLTESTFILEFORQUICKSEARCH.txt`

**Claude has FULL authority to:**
- ✅ Erase everything and rebuild fresh
- ✅ Push new builds anytime
- ✅ Run CDP tests via remote debugging
- ✅ Auto-login (credentials in config)
- ✅ Modify code, test, iterate independently
- ✅ Install/uninstall as needed

**Claude does NOT need user for:**
- ❌ Running tests
- ❌ Starting/stopping app
- ❌ Reading logs
- ❌ Building new versions
- ❌ Deploying to test folder

---

## 🔑 DEV_MODE: Localhost Auto-Authentication

**For autonomous testing without manual login:**

```bash
# Start server with DEV_MODE
DEV_MODE=true python3 server/main.py
```

**What DEV_MODE does:**
- Auto-authenticates API calls from localhost (127.0.0.1, ::1)
- Returns `dev_admin` user with admin privileges
- No JWT token required for API testing
- Warning logged on startup: "DEV_MODE enabled"

**Security constraints:**
- ONLY works on localhost - remote requests still require auth
- Blocked if `PRODUCTION=true` is set
- If token provided, uses normal auth flow

**Use cases:**
- Claude autonomous API testing
- curl commands without auth header
- CDP tests without login flow
- Admin dashboard testing

**Files:**
- `server/config.py` - DEV_MODE flag
- `server/utils/dependencies.py` - auto-auth logic

---

## 🌍 MULTI-ENVIRONMENT TESTING (CRITICAL!)

### 📊 FULL MULTI-DIMENSIONAL TEST TREE

```
MULTI-DIMENSIONAL TESTING PROTOCOL
═══════════════════════════════════════════════════════════════════════════════
│
├── 📍 DIMENSION 1: Server Binding Check (FIRST!)
│   │
│   ├── Command: netstat -tlnp 2>/dev/null | grep 8888
│   │
│   ├── If 127.0.0.1:8888 → ONLY WSL can access ❌
│   │   └── FIX: SERVER_HOST=0.0.0.0 python3 server/main.py
│   │
│   └── If 0.0.0.0:8888 → All platforms can access ✅
│
├── 📍 DIMENSION 2: WSL Testing
│   │
│   ├── curl tests
│   │   ├── curl -s http://localhost:8888/health
│   │   └── curl -s http://localhost:5175/
│   │
│   └── API endpoints
│       ├── curl http://localhost:8888/api/v2/admin/stats/database
│       └── curl http://localhost:8888/api/v2/admin/stats/server
│
├── 📍 DIMENSION 3: Playwright Browser Simulation
│   │
│   ├── Command: node scripts/visual-test.cjs --verbose
│   │
│   ├── Checks:
│   │   ├── ALL console output (log, info, warn, error, debug)
│   │   ├── Screenshots to /tmp/dashboard_*.png
│   │   ├── API response codes
│   │   ├── DOM elements present
│   │   └── "undefined" text detection
│   │
│   └── Output: 0 errors required, warnings should be fixed
│
├── 📍 DIMENSION 4: Windows Browser Access
│   │
│   ├── User opens: http://localhost:5175/database
│   │   └── Should work if server bound to 0.0.0.0
│   │
│   └── Windows PowerShell test:
│       └── curl http://localhost:8888/health
│
├── 📍 DIMENSION 5: LocaNext.exe (Electron)
│   │
│   ├── Launch: ./LocaNext.exe --remote-debugging-port=9222
│   ├── CDP endpoint: http://localhost:9222/json
│   └── Tests: node scripts/master_test.js
│
└── 📍 DIMENSION 6: Cross-Platform Validation
    │
    ├── Compare timestamps: When did user test vs when did you test?
    ├── Compare environments: Was server running for both?
    └── Compare bindings: 127.0.0.1 vs 0.0.0.0?

═══════════════════════════════════════════════════════════════════════════════
```

### Quick Multi-Dimensional Test Command

```bash
# Run ALL dimensions in sequence:

# D1: Check binding
netstat -tlnp 2>/dev/null | grep 8888

# D2: WSL curl
curl -s http://localhost:8888/health

# D3: Playwright
cd adminDashboard && node scripts/visual-test.cjs --verbose

# D4: Windows - user must verify (or check via PowerShell)
# D5: LocaNext - CDP tests if app running
# D6: Compare with user's environment
```

### ⚠️ THE BIGGEST MISTAKE: Testing in ONE Environment Only

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  YOUR CURL FROM WSL ≠ USER'S WINDOWS BROWSER                                 ║
║                                                                               ║
║  If curl works in WSL but user sees ERR_CONNECTION_REFUSED:                  ║
║  → Server is bound to 127.0.0.1 (WSL only)                                   ║
║  → Windows browser can't reach WSL localhost                                 ║
║                                                                               ║
║  FIX: Start server with SERVER_HOST=0.0.0.0                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### The Environment Matrix

| Environment | What It Tests | How to Test |
|-------------|---------------|-------------|
| **WSL curl** | WSL localhost only | `curl http://localhost:8888/health` |
| **WSL Playwright** | WSL browser (headless) | `node scripts/visual-test.cjs` |
| **Windows Browser** | Windows → WSL network | User opens `http://localhost:5175` |
| **LocaNext.exe** | Electron → Backend | CDP tests via port 9222 |

### Server Binding Check (DO THIS FIRST!)

```bash
# Check what the server is bound to
netstat -tlnp 2>/dev/null | grep 8888

# If you see:
# 127.0.0.1:8888  → ONLY WSL can access (Windows browser will FAIL!)
# 0.0.0.0:8888    → ALL can access (Windows browser will work)
```

### Starting Server for Windows Access

```bash
# WRONG - Only WSL can access:
python3 server/main.py

# CORRECT - Windows browser can access:
SERVER_HOST=0.0.0.0 python3 server/main.py
```

### Full Multi-Environment Test Protocol

```bash
# === STEP 1: Check Server Binding ===
netstat -tlnp 2>/dev/null | grep 8888
# If 127.0.0.1, restart with SERVER_HOST=0.0.0.0

# === STEP 2: Test from WSL ===
curl -s http://localhost:8888/health
# Should return {"status":"healthy"...}

# === STEP 3: Test from WSL Playwright (simulates browser) ===
cd /home/neil1988/LocalizationTools/adminDashboard
node scripts/visual-test.cjs --verbose --page=/database

# === STEP 4: Check if Windows can reach it ===
# Windows PowerShell:
# curl http://localhost:8888/health
# OR user opens http://localhost:5175/database in browser
```

### Common Multi-Environment Issues

| Symptom | Environment Issue | Fix |
|---------|-------------------|-----|
| WSL curl works, Windows browser fails | Server bound to 127.0.0.1 | `SERVER_HOST=0.0.0.0` |
| Playwright works, user sees error | Different timing/state | Check when user tested vs when you tested |
| LocaNext.exe connects, browser fails | Different port/binding | Check all ports (8888, 5175, 5176) |
| Everything works locally, fails remotely | Firewall/network | Check Windows firewall |

### When User Reports Error

```
1. ASK: What environment? (Windows browser? LocaNext.exe? WSL?)
2. CHECK: Server binding (127.0.0.1 vs 0.0.0.0)
3. TEST: From SAME environment as user
4. NEVER: Assume your WSL curl represents their Windows browser
```

---

## 🚨 CRITICAL: CLEANUP PROTOCOL (BEFORE EACH TEST RUN)

**ALWAYS kill test processes BEFORE launching new ones. Port conflicts = failures.**

### Kill LocaNext (Windows) - REQUIRED before each test:
```bash
# USE FULL PATH - tasklist.exe alone may fail silently!
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T

# Verify CLEAN
/mnt/c/Windows/System32/tasklist.exe | grep -i "loca" || echo "CLEAN"
```

### DO NOT KILL:
```
❌ Gitea - needed for git push/commit
❌ Other user processes
```

### Kill Backend (WSL):
```bash
fuser -k 8888/tcp 2>/dev/null || true
```

### Verification:
```bash
# Check all clear
/mnt/c/Windows/System32/tasklist.exe | grep -i loca   # Should be empty
curl -s http://localhost:8888/health                   # Should fail (no server)
curl -s http://localhost:3000/                         # Gitea should respond 200
```

### Known Hallucination Traps:
1. **`tasklist.exe` without full path may return empty** - ALWAYS use `/mnt/c/Windows/System32/tasklist.exe`
2. **"No process found" doesn't mean clean** - verify with full path
3. **Multiple LocaNext instances accumulate** - each test run adds more if not killed

---

## 🎯 SINGLE-INSTANCE TESTING PROTOCOL (CRITICAL!)

**ROOT CAUSE OF MULTIPLE WINDOWS**: Each bash command with `./LocaNext.exe &` spawns a NEW window.

```
⚠️ NEVER DO THIS:
═══════════════════════════════════════════════════════════════
# Each of these spawns a NEW instance!
./LocaNext.exe &          # Instance 1
sleep 5
./LocaNext.exe &          # Instance 2 (BAD!)
curl ...
./LocaNext.exe &          # Instance 3 (WORSE!)
```

```
✅ CORRECT APPROACH:
═══════════════════════════════════════════════════════════════
STEP 1: Clean slate
├── Kill ALL existing instances
├── /mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T
└── Verify: /mnt/c/Windows/System32/tasklist.exe | grep -i loca

STEP 2: Launch ONE instance
├── cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext && ./LocaNext.exe --remote-debugging-port=9222 &
├── Wait 40 seconds for full startup
└── NEVER launch again until code changes!

STEP 3: Run ALL tests against that ONE instance
├── Use curl/CDP/API tests - they don't spawn new windows
├── Use pytest - runs against server, no new windows
├── Use Node.js scripts - connects to existing CDP
└── Reuse same instance for hours if needed

STEP 4: Only restart when:
├── Code changes need testing
├── App crashes or freezes
├── Configuration changes
└── NOT for each new test!
```

### Commands That SPAWN New Windows (AVOID!):
```bash
./LocaNext.exe &              # ❌ Spawns new window
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/LocaNext.exe  # ❌ Spawns new window
```

### Commands That DON'T Spawn Windows (SAFE):
```bash
curl http://localhost:8888/health           # ✅ API call only
curl http://localhost:9222/json             # ✅ CDP check only
node test_script.js                         # ✅ Connects to existing CDP
python3 -m pytest -v                        # ✅ Runs tests against server
/mnt/c/Windows/System32/tasklist.exe        # ✅ Just checks processes
```

### Testing Flow:
```
[INIT] Kill all → Launch ONE → Wait 40s
                      ↓
              [TEST LOOP]
              ↓        ↓
         curl tests   CDP tests   pytest
              ↓        ↓           ↓
              └────────┴───────────┘
                      ↓
              [REPEAT TESTS]
              (same instance)
                      ↓
         [ONLY RESTART IF CODE CHANGED]
```

---

## 🧹 SESSION START: BLOAT CHECK PROTOCOL (MANDATORY!)

**FIRST THING every new Claude session: Check for parasites from previous sessions.**

```bash
# === SESSION START BLOAT CHECK ===
# Run these BEFORE doing any work:

# 1. Check for Windows parasites (LocaNext.exe)
echo "=== WINDOWS PROCESSES ==="
/mnt/c/Windows/System32/tasklist.exe 2>/dev/null | grep -i "loca" || echo "CLEAN - No LocaNext"

# 2. Check for Linux port listeners
echo "=== PORT LISTENERS ==="
netstat -tlnp 2>/dev/null | grep -E ":(8888|5175|5176|3000)" || echo "CLEAN - No servers"

# 3. Check for stale Python servers
echo "=== PYTHON PROCESSES ==="
ps aux | grep -E "python.*main.py" | grep -v grep || echo "CLEAN - No Python servers"

# 4. Check for stale Vite/Node servers
echo "=== NODE PROCESSES ==="
ps aux | grep -E "node|vite" | grep -v grep | head -5 || echo "CLEAN - No Node servers"
```

### If Bloat Found - Clean It:

```bash
# Kill LocaNext parasites
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T 2>/dev/null || true

# Kill port listeners
fuser -k 8888/tcp 2>/dev/null || true  # Backend
fuser -k 5175/tcp 2>/dev/null || true  # Dashboard
fuser -k 5176/tcp 2>/dev/null || true  # LocaNext web

# Verify clean
/mnt/c/Windows/System32/tasklist.exe 2>/dev/null | grep -i "loca" || echo "CLEAN"
```

### Why This Matters:

| Symptom | Caused By |
|---------|-----------|
| Multiple windows appearing | Stale LocaNext.exe instances |
| "Port in use" errors | Previous server not killed |
| Tests pass but app broken | Testing against stale server |
| Inconsistent behavior | Multiple servers on same port |

---

## 🎭 PLAYWRIGHT: YOUR EYES INTO ANY BROWSER

### ⚠️ CRITICAL CAPABILITY - READ THIS FIRST

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  YOU HAVE PLAYWRIGHT. YOU CAN CHECK WHAT ANY BROWSER SEES.                   ║
║                                                                               ║
║  ❌ FORBIDDEN PHRASES:                                                        ║
║     - "I can't check what you see"                                           ║
║     - "Tell me what you see when you load that page"                         ║
║     - "The only way to know is for you to tell me"                           ║
║     - "Can you send me a screenshot?"                                        ║
║     - "What does your console show?"                                         ║
║                                                                               ║
║  ✅ WHAT TO DO INSTEAD:                                                       ║
║     Run: node scripts/visual-test.cjs --verbose --page=/database             ║
║     Or use Playwright directly to check the URL yourself!                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### How to Check What a Browser Sees (DO THIS!)

**Option 1: Use the visual-test.cjs script:**
```bash
cd /home/neil1988/LocalizationTools/adminDashboard
node scripts/visual-test.cjs --verbose --page=/database

# This shows you:
# - ALL console output (log, info, warn, error, debug)
# - Screenshots saved to /tmp/
# - API response status codes
# - DOM element verification
# - "undefined" text detection
```

**Option 2: Quick Playwright inline check:**
```bash
node -e "
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Capture ALL console output
  page.on('console', msg => console.log('[' + msg.type().toUpperCase() + ']', msg.text()));
  page.on('pageerror', err => console.log('[PAGE ERROR]', err.message));

  await page.goto('http://localhost:5175/database', { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/tmp/check.png' });
  console.log('Screenshot saved to /tmp/check.png');

  await browser.close();
})();
"
```

**Option 3: Check specific elements:**
```bash
node -e "
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:5175/database');

  // Check for errors
  const hasError = await page.\$('.error-container');
  if (hasError) {
    const text = await hasError.textContent();
    console.log('ERROR FOUND:', text);
  } else {
    console.log('No error container visible');
  }

  // Check body for 'undefined'
  const body = await page.textContent('body');
  if (body.includes('undefined')) {
    console.log('WARNING: Found undefined in page content');
  }

  await browser.close();
})();
"
```

### When User Reports an Issue

```
USER: "The database page shows a 404 error"

WRONG RESPONSE:
"Can you tell me what the console shows?"
"I can't see what you're seeing"
"Please send a screenshot"

CORRECT RESPONSE:
*Runs Playwright to check http://localhost:5175/database*
"I checked the page with Playwright. Here's what I see: [results]"
```

---

## 🔍 USER-VS-CLAUDE DISCREPANCY RESOLUTION PROTOCOL

**CRITICAL: When user reports issue X but your tests show Y, YOU ARE PROBABLY WRONG.**

```
⚠️ NEVER SAY: "It works for me" or "This is a caching issue"
⚠️ NEVER SAY: "Tell me what you see" - YOU HAVE PLAYWRIGHT, CHECK YOURSELF!
⚠️ NEVER: Start servers silently then claim "it works"
⚠️ NEVER: Test in YOUR environment while user is in THEIR environment
✅ ALWAYS: Use Playwright to check URLs before asking user anything
✅ ALWAYS: Trust user observation, investigate the difference
✅ ALWAYS: Check what's running BEFORE starting anything new
✅ ALWAYS: If you start a server, acknowledge it changes the environment
```

### The "I Started It" Trap

**WRONG:**
```
1. User reports: "Dashboard shows 404 error"
2. Claude runs: python3 server/main.py & (silently starts server)
3. Claude tests: curl http://localhost:8888 -> 200 OK
4. Claude says: "It works! No errors!"
5. User still sees 404 because THEIR browser loaded before Claude's server started
```

**RIGHT:**
```
1. User reports: "Dashboard shows 404 error"
2. Claude uses Playwright to check http://localhost:5175/database
3. Claude sees: "Error loading database stats - Not Found"
4. Claude checks: Is server running? NO
5. Claude acknowledges: "Playwright confirms the error. Server is NOT running."
```

### Step 1: Use Playwright FIRST

When user says "I see error X":
1. **USE PLAYWRIGHT** to check the exact URL they mentioned
2. See what Playwright shows - does it match user's report?
3. If it matches: You now see the issue, fix it
4. If it differs: Compare environments (server running? ports?)

```bash
# FIRST ACTION when user reports an issue:
node scripts/visual-test.cjs --verbose --page=/database
```

### Step 2: Compare Environments (only if needed)

| Check | User Environment | Claude Environment |
|-------|------------------|-------------------|
| Server running? | May have old server | May have just restarted |
| Time of test | When they reported | When you tested (could be later) |
| Browser cache | May have cached errors | Fresh Playwright session |
| Console output | ALL types (log, warn, error) | You may only capture errors |

### Step 3: Capture EVERYTHING

```javascript
// WRONG - Only captures errors:
page.on('console', msg => {
    if (msg.type() === 'error') { /* ... */ }  // Misses log, warn, info!
});

// CORRECT - Captures ALL console types:
page.on('console', msg => {
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
});
```

### Common Discrepancy Causes:

| User Sees | Claude Tests Show | Root Cause |
|-----------|-------------------|------------|
| 404 error | 200 OK | Claude restarted server after user's test |
| Console errors | No errors | Claude only captures 'error' type, not all |
| "undefined" in UI | Data looks fine | Frontend/backend field mismatch |
| Broken page | Tests pass | Testing different URL or stale environment |

### Resolution Checklist:

- [ ] **Used Playwright to check the exact URL user mentioned**
- [ ] Captured ALL console types (log, info, warn, error, debug)
- [ ] Did NOT restart any servers between user report and my test
- [ ] Tested exact same URL user reported
- [ ] Screenshot saved and reviewed

---

## 🖼️ ADMIN DASHBOARD VISUAL TESTING

**IMPORTANT**: Always run visual tests to catch display issues that automated tests miss.

### Prerequisites (CRITICAL!)

**The dashboard REQUIRES the backend server to be running:**

```bash
# STEP 1: Start backend server (port 8888)
cd /home/neil1988/LocalizationTools
python3 server/main.py &

# STEP 2: Start dashboard (port 5175)
cd adminDashboard
npm run dev -- --port 5175 &

# STEP 3: THEN run visual tests
node scripts/visual-test.cjs
```

**If backend is NOT running, you will see:**
```
GET http://localhost:8888/api/v2/admin/stats/database net::ERR_CONNECTION_REFUSED
API Request failed: TypeError: Failed to fetch
```

The visual-test.cjs script now checks for this and will exit with a clear error message if the backend is not running.

### Quick Visual Test Command

```bash
# Run from adminDashboard directory
cd /home/neil1988/LocalizationTools/adminDashboard
node scripts/visual-test.cjs
```

### What Visual Test Checks

| Page | Path | Key Checks |
|------|------|------------|
| Overview | `/` | Stats values, app rankings visible |
| Users | `/users` | User list loads |
| Stats | `/stats` | App/function rankings, no "undefined" |
| Telemetry | `/telemetry` | Page loads (data may be empty) |
| Logs | `/logs` | Log entries visible |
| Database | `/database` | DB stats, table list |
| Server | `/server` | CPU/Memory/Disk stats, system info |

### Screenshots Location

```
/tmp/dashboard_overview.png
/tmp/dashboard_users.png
/tmp/dashboard_stats.png
/tmp/dashboard_telemetry.png
/tmp/dashboard_logs.png
/tmp/dashboard_database.png
/tmp/dashboard_server.png
```

### Common Issues Detected

| Issue | Cause | Solution |
|-------|-------|----------|
| "undefined" in content | API field name mismatch | Check API returns vs frontend expects |
| 404 errors | Server needs restart | Restart `python3 server/main.py` |
| N/A values | Empty API response | Check API endpoint returns data |
| Error loading stats | Backend endpoint missing | Add endpoint to server |

### Manual Visual Verification

If visual test passes but you want to verify manually:

```bash
# 1. Start backend server
python3 server/main.py &

# 2. Start dashboard
cd adminDashboard && npm run dev -- --port 5175 &

# 3. Open in browser: http://localhost:5175
# 4. Navigate each page and check for errors
```

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
│   └── Database Inspection (PostgreSQL)
│       ├── Connect: psql -h 127.0.0.1 -p 5432 -U localization_admin -d localizationtools
│       ├── Tables: \dt
│       └── Query: SELECT * FROM users;
│
├── 🎭 PLAYWRIGHT - YOUR EYES INTO ANY BROWSER (USE THIS!)
│   │
│   ├── Playwright ──────────────────────── SEE WHAT ANY URL SHOWS
│   │   │
│   │   ├── ⚠️ FORBIDDEN: Saying "I can't check what you see"
│   │   ├── ⚠️ FORBIDDEN: Saying "Tell me what the console shows"
│   │   ├── ✅ DO THIS: Use Playwright to check URLs yourself!
│   │   │
│   │   ├── Quick Check Any URL:
│   │   │   └── node scripts/visual-test.cjs --verbose --page=/database
│   │   │
│   │   ├── Admin Dashboard Visual Test:
│   │   │   ├── cd adminDashboard && node scripts/visual-test.cjs
│   │   │   ├── Screenshots: /tmp/dashboard_*.png
│   │   │   └── Shows ALL console output (log, info, warn, error)
│   │   │
│   │   ├── Inline Playwright Check:
│   │   │   └── node -e "require('playwright').chromium.launch()..."
│   │   │
│   │   ├── E2E Tests:
│   │   │   ├── Run: cd locaNext && npm test
│   │   │   ├── Headed: npm test -- --headed
│   │   │   └── Debug: npm test -- --debug
│   │   │
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
├── 📊 Admin Dashboard
│   └── scripts/visual-test.cjs ── Visual testing script (7 pages)
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
| **Dashboard Visual** | **7 pages** | **Node.js/Playwright** | **scripts/visual-test.cjs** |
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

*Last updated: 2025-12-06 - MULTI-ENVIRONMENT TESTING: WSL curl ≠ Windows browser! Check server binding (127.0.0.1 vs 0.0.0.0). PLAYWRIGHT: Never say "tell me what you see" - check yourself!*
