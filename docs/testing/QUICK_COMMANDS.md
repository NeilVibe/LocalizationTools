# Quick Test Commands

Copy-paste ready. No explanations.

---

## Backend (pytest)

```bash
# All tests (no server)
python3 -m pytest tests/ -v

# With server (TRUE simulation)
python3 server/main.py &
sleep 3
RUN_API_TESTS=1 python3 -m pytest -v

# Specific test file
python3 -m pytest tests/unit/test_auth_module.py -v

# Security tests only
python3 -m pytest tests/security/ -v

# With coverage
python3 -m pytest --cov=server --cov-report=html
```

---

## Frontend (Playwright)

```bash
# LocaNext (56 tests)
cd locaNext && npm test

# Admin Dashboard (30 tests)
cd adminDashboard && npm test

# With visible browser
npm run test:headed

# Interactive UI
npm run test:ui

# Single test file
npx playwright test login.spec.ts

# Generate report
npm run test:report
```

---

## X Server (Visual Testing)

```bash
# Start VcXsrv
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"

# Set display
export DISPLAY=:0

# Test connection
xdpyinfo | head -3
```

---

## Screenshots & Recording

```bash
# Playwright screenshot
cd locaNext && npx playwright test screenshot.spec.ts

# Screen recording (60s)
ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :0 \
  -c:v libx264 -preset ultrafast -t 60 demo.mp4
```
