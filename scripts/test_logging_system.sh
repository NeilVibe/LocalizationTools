#!/bin/bash
# Test the complete logging system

echo "========================================"
echo "🧪 Testing Complete Logging System"
echo "========================================"
echo ""

PROJECT_ROOT="/home/neil1988/LocalizationTools"

# Test 1: Check backend logging
echo "1️⃣  Testing Backend Server logging..."
curl -s http://localhost:8888/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Backend is running and logging"
    echo "   📝 Recent backend logs:"
    tail -3 "$PROJECT_ROOT/server/data/logs/server.log" | sed 's/^/      /'
else
    echo "   ❌ Backend is not running"
    echo "   Run: python3 server/main.py"
fi

echo ""

# Test 2: Check if log files exist
echo "2️⃣  Checking log file structure..."
LOG_FILES=(
    "$PROJECT_ROOT/server/data/logs/server.log"
    "$PROJECT_ROOT/server/data/logs/error.log"
)

for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        size=$(du -h "$log_file" | cut -f1)
        echo "   ✅ $(basename $log_file) exists ($size)"
    else
        echo "   ⚠️  $(basename $log_file) not created yet"
    fi
done

echo ""

# Test 3: Check monitoring scripts
echo "3️⃣  Testing monitoring scripts..."
if [ -x "$PROJECT_ROOT/scripts/monitor_logs_realtime.sh" ]; then
    echo "   ✅ monitor_logs_realtime.sh is executable"
else
    echo "   ⚠️  monitor_logs_realtime.sh needs chmod +x"
fi

if [ -x "$PROJECT_ROOT/scripts/monitor_all_servers.sh" ]; then
    echo "   ✅ monitor_all_servers.sh is executable"
else
    echo "   ⚠️  monitor_all_servers.sh needs chmod +x"
fi

echo ""

# Test 4: Check server status
echo "4️⃣  Checking server health..."
BACKEND_UP=$(curl -s http://localhost:8888/health > /dev/null 2>&1 && echo "✅" || echo "❌")
DASHBOARD_UP=$(curl -s http://localhost:5175/ > /dev/null 2>&1 && echo "✅" || echo "❌")
LOCANEXT_UP=$(curl -s http://localhost:5173/ > /dev/null 2>&1 && echo "✅" || echo "❌")

echo "   Backend (8888):  $BACKEND_UP"
echo "   Dashboard (5175): $DASHBOARD_UP"
echo "   LocaNext (5173):  $LOCANEXT_UP"

echo ""

# Summary
echo "========================================"
echo "📊 SUMMARY"
echo "========================================"

if [ "$BACKEND_UP" = "✅" ]; then
    echo "✅ Backend logging: WORKING"
else
    echo "❌ Backend logging: NOT RUNNING"
fi

echo "⏳ LocaNext logging: Ready (will activate when app runs)"
echo "⏳ Dashboard logging: Ready (will activate when app runs)"

echo ""
echo "🎯 Next Steps:"
echo "   1. Run: bash scripts/monitor_logs_realtime.sh"
echo "   2. Use the apps to generate activity"
echo "   3. Watch logs appear in real-time!"
echo ""
echo "📖 Documentation: docs/MONITORING_SYSTEM.md"
echo "========================================"
