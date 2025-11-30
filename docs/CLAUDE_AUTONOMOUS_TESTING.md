# Claude Autonomous Testing Guide

**Created**: 2025-11-11
**Purpose**: Enable Claude to test and verify everything independently without user intervention

---

## Philosophy

**"Claude-esque" Testing**: Claude should NEVER ask the user to check something that can be verified programmatically.

### ❌ BAD (Barbaric):
```
Claude: "Can you open the browser and tell me what time is showing in TaskManager?"
```

### ✅ GOOD (Claude-esque):
```python
# Claude tests it himself via API
import requests
response = requests.get('http://localhost:8888/api/progress/operations', ...)
print(f"Timestamp in API: {response.json()[0]['started_at']}")
```

---

## Rule: Test Everything Via API/Logs

You have access to:
1. ✅ **API endpoints** - Test via curl/Python
2. ✅ **Logs** - Monitor via tail/grep
3. ✅ **Database** - Query if needed
4. ✅ **Monitoring scripts** - Run and parse output
5. ✅ **Graphical browser** - X server available, can open Chromium directly!
6. ✅ **Headless browser** - For automated testing without GUI

**IMPORTANT**: This environment HAS X server configured (DISPLAY=10.255.255.254:0)
- You CAN open graphical browsers directly: `chromium-browser http://localhost:5173 &`
- You CAN take screenshots: `chromium-browser --screenshot=screenshot.png http://localhost:5173`
- You DON'T need Selenium for basic visual testing

**NEVER ask the user to check something you can verify yourself!**

---

## Starting X Server (VcXsrv) - DO THIS FIRST!

**Claude CAN start VcXsrv by himself** via PowerShell from WSL:

```bash
# Check if VcXsrv is already running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Get-Process vcxsrv -ErrorAction SilentlyContinue"

# If not running, START IT:
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"

# Wait 2 seconds, then verify it's running
sleep 2
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Get-Process vcxsrv"

# Test X connection (use DISPLAY=:0, not the old IP)
export DISPLAY=:0
xdpyinfo | head -3
```

**Key Points:**
- VcXsrv is installed at `C:\Program Files\VcXsrv\vcxsrv.exe`
- Use `-ac` flag to disable access control (allows WSL connections)
- Set `DISPLAY=:0` (not the old `10.255.255.254:0`)
- Claude can do this autonomously - NO user intervention needed!

---

## Using Graphical Browser (X Server Available!)

**Environment**: X server on DISPLAY=:0 (start VcXsrv first - see above)
**Browser**: Chromium 142 installed

### Opening Browser for Visual Testing

```bash
# FIRST: Make sure X Server is running (see section above)
export DISPLAY=:0

# Open LocaNext frontend
chromium-browser http://localhost:5173 &

# Open Admin Dashboard
chromium-browser http://localhost:5175 &

# Open with specific window size
chromium-browser --window-size=1920,1080 http://localhost:5173 &

# Take screenshot without showing window
chromium-browser --headless --screenshot=screenshot.png http://localhost:5173
```

### When to Use Graphical Browser

Use graphical browser when:
- Need to verify visual layout/styling
- Need to test UI interactions (clicks, forms)
- API testing isn't sufficient
- Need to debug frontend rendering issues

**Still prefer API testing first** - it's faster and more reliable.

---

## Common Testing Scenarios

### 1. Check What Frontend Is Displaying

**❌ DON'T ASK:**
> "What do you see in the TaskManager Started column?"

**✅ DO THIS:**
```python
# Test the API endpoint that frontend uses
python3 <<'EOF'
import requests
import json

# Login
r = requests.post("http://localhost:8888/api/v2/auth/login",
                  json={"username":"admin","password":"admin123"})
token = r.json()["access_token"]

# Get operations (same endpoint frontend uses)
r = requests.get("http://localhost:8888/api/progress/operations",
                 headers={"Authorization": f"Bearer {token}"})

# Analyze the response
operations = r.json()
if operations:
    op = operations[0]
    print(f"API returns started_at: {op['started_at']}")
    print(f"This is what frontend receives and displays")

    # Check for timezone info
    if 'Z' in op['started_at'] or '+' in op['started_at']:
        print("✅ Has timezone info")
    else:
        print("❌ Missing timezone info (bug!)")
EOF
```

### 2. Check If Operation Completed

**❌ DON'T ASK:**
> "Did the operation finish? What status do you see?"

**✅ DO THIS:**
```bash
# Method 1: Check API
python3 -c "
import requests
r = requests.post('http://localhost:8888/api/v2/auth/login',
                  json={'username':'admin','password':'admin123'})
token = r.json()['access_token']
r = requests.get('http://localhost:8888/api/progress/operations/1',
                 headers={'Authorization': f'Bearer {token}'})
print(f\"Status: {r.json()['status']}\")
print(f\"Progress: {r.json()['progress_percentage']}%\")
"

# Method 2: Check logs
tail -50 server/data/logs/server.log | grep "operation 1" | grep -E "complete|failed"
```

### 3. Check If Error Occurred

**❌ DON'T ASK:**
> "Did you see any errors in the UI?"

**✅ DO THIS:**
```bash
# Check error logs
tail -100 server/data/logs/server.log | grep ERROR

# Check frontend remote logs
tail -100 server/data/logs/server.log | grep "\[FRONTEND\]" | grep ERROR

# Use monitoring script
bash scripts/monitor_system.sh | grep -A5 "RECENT LOG ERRORS"
```

### 4. Check Timezone Display

**❌ DON'T ASK:**
> "What time does it show in the UI?"

**✅ DO THIS:**
```python
# Check API response format
python3 <<'EOF'
import requests
from datetime import datetime

r = requests.post("http://localhost:8888/api/v2/auth/login",
                  json={"username":"admin","password":"admin123"})
token = r.json()["access_token"]

r = requests.get("http://localhost:8888/api/progress/operations",
                 headers={"Authorization": f"Bearer {token}"})

op = r.json()[0]
raw_time = op['started_at']
print(f"Raw API response: {raw_time}")

# Parse and analyze
dt = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
print(f"Timezone info: {dt.tzinfo}")

if dt.tzinfo is None:
    print("❌ BUG: No timezone info (browser won't know it's UTC)")
else:
    print("✅ Has timezone info")

# Show what browser would display
print(f"\nCurrent server time (KST): {datetime.now()}")
print(f"Operation time from API: {dt}")
print(f"Difference: {(datetime.now() - dt.replace(tzinfo=None)).total_seconds() / 3600:.1f} hours")
EOF
```

### 5. Check WebSocket Events

**❌ DON'T ASK:**
> "Are you getting real-time updates?"

**✅ DO THIS:**
```bash
# Check WebSocket logs
tail -100 server/data/logs/server.log | grep -E "WebSocket|Socket.IO|emit_"

# Test Socket.IO connection
curl -s "http://localhost:8888/socket.io/?EIO=4&transport=polling" | head -20

# Monitor WebSocket events live
bash scripts/monitor_taskmanager.sh &
# Then trigger an operation and watch
```

### 6. Check File Download

**❌ DON'T ASK:**
> "Did the file download correctly?"

**✅ DO THIS:**
```bash
# Test download endpoint
python3 <<'EOF'
import requests

r = requests.post("http://localhost:8888/api/v2/auth/login",
                  json={"username":"admin","password":"admin123"})
token = r.json()["access_token"]

# Test download
r = requests.get("http://localhost:8888/api/download/operation/1",
                 headers={"Authorization": f"Bearer {token}"})

print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('Content-Type')}")
print(f"Content-Disposition: {r.headers.get('Content-Disposition')}")
print(f"File size: {len(r.content)} bytes")

if r.status_code == 200:
    print("✅ Download works")
else:
    print("❌ Download failed")
EOF
```

### 7. Simulate User Workflow

**❌ DON'T ASK:**
> "Can you test Create Dictionary for me?"

**✅ DO THIS:**
```python
# Complete workflow via API
python3 <<'EOF'
import requests
import time

# Login
r = requests.post("http://localhost:8888/api/v2/auth/login",
                  json={"username":"admin","password":"admin123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Load dictionary
r = requests.post("http://localhost:8888/api/v2/xlstransfer/test/load-dictionary",
                  headers=headers)
print(f"Load dictionary: {r.status_code}")

# Upload file and get sheets
files = {'file': open('test_data/TEST.xlsx', 'rb')}
r = requests.post("http://localhost:8888/api/v2/xlstransfer/test/get-sheets",
                  headers=headers, files=files)
print(f"Get sheets: {r.status_code}")
print(f"Sheets: {r.json()}")

# Translate Excel
selections = {"TEST.xlsx": {"Sheet1": {"kr_column": "A", "trans_column": "B"}}}
files = {'file': open('test_data/TEST.xlsx', 'rb')}
data = {'selections': str(selections)}
r = requests.post("http://localhost:8888/api/v2/xlstransfer/test/translate-excel",
                  headers=headers, files=files, data=data)
print(f"Translate: {r.status_code}")

# Monitor progress
operation_id = r.json().get('operation_id')
while True:
    r = requests.get(f"http://localhost:8888/api/progress/operations/{operation_id}",
                     headers=headers)
    status = r.json()['status']
    progress = r.json()['progress_percentage']
    print(f"Status: {status}, Progress: {progress}%")
    if status in ['completed', 'failed']:
        break
    time.sleep(2)
EOF
```

---

## Advanced: Headless Browser Testing

**When to use**: ONLY when you need to test actual DOM rendering/JavaScript that can't be tested via API.

```python
# Example: Test TaskManager UI rendering
python3 <<'EOF'
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)

# Login
driver.get('http://localhost:5173')
driver.find_element_by_name('username').send_keys('admin')
driver.find_element_by_name('password').send_keys('admin123')
driver.find_element_by_css_selector('button[type="submit"]').click()

# Navigate to TaskManager
driver.get('http://localhost:5173/taskmanager')

# Check what's displayed
time_element = driver.find_element_by_css_selector('.task-timestamp')
displayed_time = time_element.text
print(f"TaskManager shows: {displayed_time}")

driver.quit()
EOF
```

**Note**: Prefer API testing over headless browser (faster, simpler, more reliable).

---

## Complete Testing Workflow

### Before Testing

```bash
# 1. Clean logs
bash scripts/clean_logs.sh

# 2. Verify servers running
bash scripts/monitor_system.sh

# 3. Start monitoring
bash scripts/monitor_logs_realtime.sh --errors-only &
MONITOR_PID=$!
```

### During Testing

```python
# Test via API (no user interaction needed)
import requests
import time

# All your tests here...
```

### After Testing

```bash
# 1. Check for errors
tail -100 server/data/logs/server.log | grep ERROR

# 2. Verify operations completed
bash scripts/monitor_system.sh | grep -A5 "DATABASE STATUS"

# 3. Stop monitoring
kill $MONITOR_PID

# 4. Generate report
echo "✅ Tested X operations"
echo "✅ 0 errors found"
echo "✅ All operations completed successfully"
```

---

## Testing Checklist

Before asking user to verify something, ask yourself:

- [ ] Can I test this via API? (99% yes)
- [ ] Can I check logs? (99% yes)
- [ ] Can I query database? (if needed)
- [ ] Can I use monitoring scripts? (yes)
- [ ] Do I REALLY need the user? (almost never)

**If all answers are no** (very rare): Then and ONLY then ask the user.

---

## Examples from Real Failures

### Failure #1: Monitoring Incident (2025-11-11)

**What Claude did:**
> "Can you tell me what operations you ran?"

**What Claude SHOULD have done:**
```bash
tail -2000 server/data/logs/server.log | \
  grep -E "POST.*xlstransfer|ActiveOperation|operation_start"
```

### Failure #2: Timezone Question (2025-11-11)

**What Claude did:**
> "What time do you see in TaskManager?"

**What Claude SHOULD have done:**
```python
# Check API response
python3 -c "
import requests
r = requests.post('http://localhost:8888/api/v2/auth/login', ...)
r = requests.get('http://localhost:8888/api/progress/operations', ...)
print(f'API returns: {r.json()[0][\"started_at\"]}')"
```

---

## Summary

**The Golden Rule:**

> If it goes through the server, Claude can test it.
> If it's in the logs, Claude can verify it.
> If it's in the API, Claude can check it.

**NEVER** ask the user to be your eyes when you have:
- ✅ API endpoints
- ✅ Logs
- ✅ Monitoring scripts
- ✅ Database access
- ✅ Headless browser (if needed)
- ✅ **VcXsrv** (can start via PowerShell!)
- ✅ **PowerShell access** (can run Windows commands from WSL)

**Be autonomous. Be Claude-esque.**

---

## PowerShell Tricks from WSL

Claude has full PowerShell access from WSL. Use it!

```bash
# Run any PowerShell command
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "YOUR_COMMAND"

# Examples:
# List Windows processes
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Get-Process | Select -First 5"

# Start a Windows application
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process notepad"

# Check if an app is running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Get-Process vcxsrv -ErrorAction SilentlyContinue"

# Start VcXsrv (X Server)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"
```

**This means Claude can:**
- Start Windows applications (VcXsrv, etc.)
- Check Windows processes
- Access Windows filesystem via `/mnt/c/`
- Run Windows commands when Linux tools aren't enough

---

**Last Updated**: 2025-11-30
**Status**: Mandatory reading before testing
