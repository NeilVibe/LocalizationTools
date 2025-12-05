#!/bin/bash
# Push updates to Windows installation
# Usage: ./scripts/push_to_windows.sh

WINDOWS_PATH="/mnt/c/Users/MYCOM/Desktop/LocaNext"

echo "=== Pushing updates to Windows ==="

# 1. Copy Python server files
echo "1. Copying server files..."
cp -r server/utils/client/progress.py "$WINDOWS_PATH/server/utils/client/progress.py"
rm -rf "$WINDOWS_PATH/server/utils/client/__pycache__"

# 2. Rebuild and copy frontend
echo "2. Building frontend..."
cd locaNext
npm run build 2>/dev/null
cd ..

echo "3. Copying frontend build..."
cp -r locaNext/build/* "$WINDOWS_PATH/resources/app/build/"

# 4. Copy electron files
echo "4. Copying electron files..."
cp locaNext/electron/main.js "$WINDOWS_PATH/resources/app/electron/main.js"
cp locaNext/electron/preload.js "$WINDOWS_PATH/resources/app/electron/preload.js"

# 5. Clear logs
echo "5. Clearing logs..."
rm -f "$WINDOWS_PATH/logs/"*.log

# 6. Ensure first_run_complete exists
echo "First run completed on $(date)" > "$WINDOWS_PATH/first_run_complete.flag"

echo ""
echo "=== Done! ==="
echo "Windows installation updated. Run LocaNext.exe to test."
