#!/bin/bash
# ============================================================================
# LocaNext Testing Toolkit - Launch and Test
# ============================================================================
# Complete autonomous test workflow:
# 1. Kill existing processes
# 2. Launch LocaNext with CDP
# 3. Run all tests
# 4. Report results
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLKIT_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$TOOLKIT_DIR/scripts"

# Configuration
CDP_PORT="${CDP_PORT:-9222}"
LOCANEXT_PATH="${LOCANEXT_PATH:-C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\LocaNext\\LocaNext.exe}"
WAIT_AFTER_LAUNCH="${WAIT_AFTER_LAUNCH:-25}"

echo "============================================================"
echo "LOCANEXT AUTONOMOUS TEST SUITE"
echo "============================================================"
echo "CDP Port: $CDP_PORT"
echo "LocaNext: $LOCANEXT_PATH"
echo "Scripts:  $SCRIPTS_DIR"
echo "============================================================"
echo ""

# ─────────────────────────────────────────────────────────────────
# PHASE 1: CLEANUP
# ─────────────────────────────────────────────────────────────────
echo "[PHASE 1] Cleaning up existing processes..."

# Kill LocaNext processes
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>&1 || true
sleep 2

# Kill orphan python (optional - backend may conflict)
# /mnt/c/Windows/System32/taskkill.exe /F /IM python.exe 2>&1 || true

# Verify no processes
PROC_COUNT=$(/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "(Get-Process LocaNext -ErrorAction SilentlyContinue).Count" 2>/dev/null || echo "0")
echo "  Remaining LocaNext processes: $PROC_COUNT"

if [ "$PROC_COUNT" != "0" ]; then
    echo "  WARNING: Could not kill all processes. Waiting..."
    sleep 5
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# PHASE 2: LAUNCH
# ─────────────────────────────────────────────────────────────────
echo "[PHASE 2] Launching LocaNext with CDP on port $CDP_PORT..."

# Clear logs
rm -f /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/logs/*.log 2>/dev/null || true

# Launch via PowerShell (synchronous start, app runs async)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
    -Command "Start-Process -FilePath '$LOCANEXT_PATH' -ArgumentList '--remote-debugging-port=$CDP_PORT'"

echo "  Waiting ${WAIT_AFTER_LAUNCH}s for app to initialize..."
sleep "$WAIT_AFTER_LAUNCH"

# ─────────────────────────────────────────────────────────────────
# PHASE 3: VERIFY
# ─────────────────────────────────────────────────────────────────
echo ""
echo "[PHASE 3] Verifying launch..."

# Check process count
PROC_COUNT=$(/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "(Get-Process LocaNext -ErrorAction SilentlyContinue).Count" 2>/dev/null || echo "0")
echo "  LocaNext processes: $PROC_COUNT"

if [ "$PROC_COUNT" = "0" ]; then
    echo "  ERROR: LocaNext did not start"
    exit 1
fi

# Check CDP
echo -n "  CDP available: "
CDP_CHECK=$(/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "(Invoke-WebRequest -Uri 'http://localhost:$CDP_PORT/json' -UseBasicParsing -TimeoutSec 5).StatusCode" 2>/dev/null || echo "FAIL")

if [ "$CDP_CHECK" = "200" ]; then
    echo "YES"
else
    echo "NO (code: $CDP_CHECK)"
    echo "  ERROR: CDP not accessible on port $CDP_PORT"
    exit 1
fi

# Check backend
echo -n "  Backend health: "
HEALTH=$(/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "(Invoke-WebRequest -Uri 'http://localhost:8888/health' -UseBasicParsing -TimeoutSec 5).Content" 2>/dev/null || echo "FAIL")

if [[ "$HEALTH" == *"healthy"* ]]; then
    echo "OK"
else
    echo "ERROR ($HEALTH)"
    echo "  WARNING: Backend may not be running properly"
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# PHASE 4: RUN TESTS
# ─────────────────────────────────────────────────────────────────
echo "[PHASE 4] Running test suite..."
echo ""

# Install dependencies if needed
cd "$SCRIPTS_DIR"
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install --silent
fi

# Run all tests
node run_all_tests.js "$@"
TEST_EXIT_CODE=$?

echo ""

# ─────────────────────────────────────────────────────────────────
# PHASE 5: CLEANUP
# ─────────────────────────────────────────────────────────────────
echo "[PHASE 5] Cleaning up..."

/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>&1 || true

echo ""
echo "============================================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "ALL TESTS PASSED"
else
    echo "SOME TESTS FAILED"
fi
echo "============================================================"

exit $TEST_EXIT_CODE
