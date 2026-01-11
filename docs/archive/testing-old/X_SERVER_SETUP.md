# X Server Setup (VcXsrv)

For visual testing and debugging in WSL.

**Note**: X Server is OPTIONAL. Playwright tests work headless without it.

---

## ⚠️ CRITICAL: WSL DISPLAY Fix

**Problem**: WSL sets `DISPLAY` to wrong IP like `10.255.255.254:0`
**Solution**: VcXsrv listens on `:0` (localhost display 0)

```
┌─────────────────────────────────────────────────────────────┐
│  ALWAYS USE:  DISPLAY=:0  prefix for visual operations!    │
│                                                             │
│  ❌ WRONG:  npx playwright screenshot ...                   │
│  ✅ RIGHT:  DISPLAY=:0 npx playwright screenshot ...        │
│                                                             │
│  ❌ WRONG:  chromium-browser http://localhost:5175          │
│  ✅ RIGHT:  DISPLAY=:0 chromium-browser http://localhost:5175│
└─────────────────────────────────────────────────────────────┘
```

**Symptoms of wrong DISPLAY:**
- Blank/white screenshots
- "unable to open display" errors
- Browser doesn't appear visually

**Quick fix:**
```bash
# Check current DISPLAY
echo $DISPLAY
# If it shows 10.255.255.254:0 or similar IP, it's WRONG!

# Fix: Always prefix commands with DISPLAY=:0
DISPLAY=:0 npx playwright screenshot --wait-for-timeout=3000 http://localhost:5175/ /tmp/test.png
```

---

## Starting VcXsrv

Claude can start this autonomously:

```bash
# Check if already running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Get-Process vcxsrv -ErrorAction SilentlyContinue"

# Start VcXsrv
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"

# Wait and verify
sleep 2
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Get-Process vcxsrv"
```

---

## Configure Display

```bash
export DISPLAY=:0

# Test connection
xdpyinfo | head -3
```

---

## Open Browser Visually

```bash
# Open LocaNext
chromium-browser http://localhost:5173 &

# Open Admin Dashboard
chromium-browser http://localhost:5175 &

# Specific window size
chromium-browser --window-size=1920,1080 http://localhost:5173 &
```

---

## Run Playwright with Visible Browser

```bash
cd locaNext && npm run test:headed
```

---

## When to Use X Server

| Task | Need X Server? |
|------|----------------|
| Run tests | No (headless) |
| Debug failing test | Maybe (headed mode) |
| Take screenshots | **Yes** (needs DISPLAY) |
| Record demo video | Yes |
| Visual inspection | Yes |

---

## Visual UI Testing with Playwright Screenshots

**CRITICAL: Use `DISPLAY=:0` prefix for screenshots in WSL!**

### Quick Screenshot Command

```bash
# Single page screenshot
DISPLAY=:0 npx playwright screenshot --wait-for-timeout=3000 http://localhost:5175/ /tmp/screenshot.png

# With specific viewport
DISPLAY=:0 npx playwright screenshot --viewport-size=1280,720 --wait-for-timeout=3000 http://localhost:5175/ /tmp/screenshot.png
```

### Capture All Admin Dashboard Pages

```bash
# Overview
DISPLAY=:0 npx playwright screenshot --wait-for-timeout=3000 http://localhost:5175/ /tmp/admin_overview.png

# Users
DISPLAY=:0 npx playwright screenshot --wait-for-timeout=3000 http://localhost:5175/users /tmp/admin_users.png

# Stats
DISPLAY=:0 npx playwright screenshot --wait-for-timeout=3000 http://localhost:5175/stats /tmp/admin_stats.png

# Logs
DISPLAY=:0 npx playwright screenshot --wait-for-timeout=3000 http://localhost:5175/logs /tmp/admin_logs.png
```

### Troubleshooting Screenshots

**Problem: Blank/white screenshots**

```bash
# Check DISPLAY is correct
echo $DISPLAY
# If it shows something like 10.255.255.254:0, override it:
export DISPLAY=:0

# Or use inline override:
DISPLAY=:0 npx playwright screenshot ...
```

**Problem: X display connection error**

```bash
# Verify VcXsrv is running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Get-Process vcxsrv"

# Test X connection
DISPLAY=:0 xdpyinfo | head -3
```

### Why DISPLAY=:0?

WSL sometimes sets DISPLAY to the wrong IP (like `10.255.255.254:0`).
VcXsrv listens on `:0` (display 0 on localhost).
Always use `DISPLAY=:0` prefix for visual operations.
