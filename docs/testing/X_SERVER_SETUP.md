# X Server Setup (VcXsrv)

For visual testing and debugging in WSL.

**Note**: X Server is OPTIONAL. Playwright tests work headless without it.

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
| Take screenshots | No (Playwright does it) |
| Record demo video | Yes |
| Visual inspection | Yes |
