# Demo Recording Guide

**Purpose:** Create screenshots and videos to demonstrate LocaNext features
**Author:** Claude (Autonomous)
**Updated:** 2025-12-08

---

## Quick Start (Claude Autonomous)

```bash
# 1. Start X Server (if not running)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"

# 2. Set display
export DISPLAY=:0

# 3. Verify X Server works
xdpyinfo | head -3

# 4. Take screenshot
scrot /tmp/demo_$(date +%Y%m%d_%H%M%S).png
```

---

## Step 1: Start X Server (VcXsrv)

### Check if Running
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Get-Process vcxsrv -ErrorAction SilentlyContinue"
```

### Start VcXsrv
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"
sleep 2
```

### Set Display
```bash
export DISPLAY=:0
```

### Verify Connection
```bash
xdpyinfo | head -3
# Should show: name of display: :0
```

---

## Step 2: Screenshots

### Method A: scrot (Quick Screenshots)

```bash
# Full screen
DISPLAY=:0 scrot /tmp/screenshot.png

# Delayed 3 seconds (time to switch window)
DISPLAY=:0 scrot -d 3 /tmp/screenshot.png

# Active window only
DISPLAY=:0 scrot -u /tmp/window.png

# Timestamped
DISPLAY=:0 scrot /tmp/demo_$(date +%Y%m%d_%H%M%S).png
```

### Method B: Playwright (Web/Electron)

```bash
# Screenshot web page
DISPLAY=:0 npx playwright screenshot \
  --wait-for-timeout=3000 \
  http://localhost:5176/ \
  /tmp/locanext.png

# With viewport size
DISPLAY=:0 npx playwright screenshot \
  --viewport-size=1920,1080 \
  --wait-for-timeout=3000 \
  http://localhost:5176/ \
  /tmp/locanext_hd.png
```

### Method C: CDP Screenshot (Electron App)

```javascript
// Via CDP - in testing_toolkit
// Add to run_test.js or use directly
const screenshot = await Runtime.evaluate({
  expression: `
    (async () => {
      const canvas = document.querySelector('canvas') || document.body;
      return await html2canvas(canvas).then(c => c.toDataURL());
    })()
  `,
  awaitPromise: true
});
```

---

## Step 3: Video Recording

### ffmpeg Screen Recording

```bash
# Record 60 seconds at 30fps
DISPLAY=:0 ffmpeg -f x11grab \
  -video_size 1920x1080 \
  -framerate 30 \
  -i :0 \
  -c:v libx264 \
  -preset ultrafast \
  -t 60 \
  /tmp/demo.mp4

# Record 30 seconds with audio (if available)
DISPLAY=:0 ffmpeg -f x11grab \
  -video_size 1920x1080 \
  -framerate 30 \
  -i :0 \
  -t 30 \
  /tmp/demo_30s.mp4

# Stop recording: Ctrl+C
```

### Record Specific Window

```bash
# Get window geometry
xdotool getactivewindow getwindowgeometry

# Record specific area (x,y offset + size)
DISPLAY=:0 ffmpeg -f x11grab \
  -video_size 1280x720 \
  -framerate 30 \
  -i :0+100,100 \
  -t 30 \
  /tmp/window_demo.mp4
```

---

## Step 4: Automation (xdotool)

### Mouse Control
```bash
# Move mouse to position
xdotool mousemove 500 300

# Left click
xdotool click 1

# Right click
xdotool click 3

# Double click
xdotool click --repeat 2 1
```

### Keyboard Control
```bash
# Type text
xdotool type "Hello World"

# Press Enter
xdotool key Return

# Press Tab
xdotool key Tab

# Keyboard shortcuts
xdotool key ctrl+s    # Save
xdotool key ctrl+Enter  # Save and next
xdotool key Escape    # Cancel
```

### Window Control
```bash
# Focus window by name
wmctrl -a "LocaNext"

# List all windows
wmctrl -l

# Resize window
wmctrl -r "LocaNext" -e 0,0,0,1920,1080
```

---

## LDM Demo Script

### Automated Demo Recording

```bash
#!/bin/bash
# demo_ldm.sh - Record LDM demo

# Setup
export DISPLAY=:0
DEMO_DIR="/tmp/ldm_demo_$(date +%Y%m%d)"
mkdir -p $DEMO_DIR

# Start recording
echo "Starting recording..."
ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :0 \
  -c:v libx264 -preset ultrafast \
  $DEMO_DIR/ldm_demo.mp4 &
FFMPEG_PID=$!

# Wait for setup
sleep 2

# Run LDM test sequence via CDP
cd ~/LocalizationTools/testing_toolkit
node scripts/run_test.js ldm.fullSequence

# Take screenshots at key moments
sleep 2
scrot $DEMO_DIR/01_project_created.png
sleep 2
scrot $DEMO_DIR/02_file_uploaded.png
sleep 2
scrot $DEMO_DIR/03_row_edited.png

# Stop recording
kill $FFMPEG_PID

echo "Demo saved to $DEMO_DIR"
```

### Manual Demo Steps

```bash
# 1. Screenshot: Empty LDM
DISPLAY=:0 scrot -d 2 /tmp/ldm_01_empty.png

# 2. Create project (via CDP)
node scripts/run_test.js ldm.createProject
sleep 2
DISPLAY=:0 scrot /tmp/ldm_02_project.png

# 3. Upload file
node scripts/run_test.js ldm.uploadTxt
sleep 2
DISPLAY=:0 scrot /tmp/ldm_03_uploaded.png

# 4. Edit row
node scripts/run_test.js ldm.editRow
sleep 2
DISPLAY=:0 scrot /tmp/ldm_04_edited.png
```

---

## Output Locations

| Type | Location | Format |
|------|----------|--------|
| Screenshots | `/tmp/*.png` | PNG |
| Videos | `/tmp/*.mp4` | MP4 |
| Demo folder | `/tmp/ldm_demo_YYYYMMDD/` | Mixed |

---

## Troubleshooting

### X Server Issues

```bash
# Error: "unable to open display"
export DISPLAY=:0

# Error: VcXsrv not running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"
```

### Blank Screenshots

```bash
# Always use DISPLAY=:0 prefix
DISPLAY=:0 scrot /tmp/test.png

# Check display connection
DISPLAY=:0 xdpyinfo | head -3
```

### Recording Issues

```bash
# Check ffmpeg installed
ffmpeg -version

# Use simpler encoding if slow
ffmpeg -f x11grab -video_size 1280x720 -framerate 15 -i :0 \
  -c:v libx264 -preset ultrafast -t 30 /tmp/demo.mp4
```

---

## Tool Installation

```bash
# Install all demo tools
sudo apt update
sudo apt install -y scrot ffmpeg xdotool wmctrl imagemagick

# Verify
scrot --version
ffmpeg -version
xdotool --version
wmctrl --version
```

---

## Summary: Claude Autonomous Demo Flow

```bash
# === FULL AUTONOMOUS DEMO ===

# 1. Start X Server
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command \
  "Start-Process 'C:\Program Files\VcXsrv\vcxsrv.exe' -ArgumentList ':0 -multiwindow -clipboard -wgl -ac'"
sleep 2
export DISPLAY=:0

# 2. Start backend server
cd ~/LocalizationTools
python3 server/main.py &
sleep 5

# 3. Start LocaNext (Windows) with CDP
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/LocaNext.exe \
  --remote-debugging-port=9222 &
sleep 5

# 4. Run demo with screenshots
cd ~/LocalizationTools/testing_toolkit
node scripts/run_test.js ldm.fullSequence

# 5. Take final screenshot
DISPLAY=:0 scrot /tmp/ldm_demo_complete.png

# 6. (Optional) Record video of another run
DISPLAY=:0 ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :0 \
  -c:v libx264 -preset ultrafast -t 60 /tmp/ldm_demo.mp4 &
sleep 2
node scripts/run_test.js ldm.fullSequence
pkill ffmpeg

echo "Demo complete! Check /tmp/ for outputs"
```

---

*Last updated: 2025-12-08*
