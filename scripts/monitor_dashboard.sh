#!/bin/bash
# Real-time Dashboard Monitoring Script
# Shows all server statuses and recent activity

echo "========================================="
echo "📊 DASHBOARD MONITORING - REAL-TIME"
echo "========================================="
echo ""

# Check Backend Server
echo "🔧 BACKEND SERVER (port 8888)"
if ps aux | grep -v grep | grep "python3 server/main.py" > /dev/null; then
    echo "  Status: ✅ RUNNING"
    BACKEND_PID=$(ps aux | grep -v grep | grep "python3 server/main.py" | awk '{print $2}')
    echo "  PID: $BACKEND_PID"

    # Test health endpoint
    HEALTH=$(curl -s http://localhost:8888/health 2>/dev/null | jq -r '.status' 2>/dev/null || echo "error")
    echo "  Health: $HEALTH"

    # Count API endpoints
    echo "  Latest log:"
    tail -1 server/data/logs/server.log 2>/dev/null | sed 's/^/    /'
else
    echo "  Status: ❌ NOT RUNNING"
fi
echo ""

# Check Admin Dashboard
echo "📈 ADMIN DASHBOARD (port 5175)"
if ps aux | grep -v grep | grep "npm run dev.*5175" > /dev/null; then
    echo "  Status: ✅ RUNNING"
    DASH_PID=$(ps aux | grep -v grep | grep "npm run dev.*5175" | awk '{print $2}')
    echo "  PID: $DASH_PID"

    # Test if responding
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5175 2>/dev/null || echo "000")
    echo "  HTTP Response: $HTTP_CODE"
else
    echo "  Status: ❌ NOT RUNNING"
fi
echo ""

# Check LocaNext
echo "🌐 LOCANEXT (port 5173)"
if ps aux | grep -v grep | grep "npm run dev.*5173" > /dev/null; then
    echo "  Status: ✅ RUNNING"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>/dev/null || echo "000")
    echo "  HTTP Response: $HTTP_CODE"
else
    echo "  Status: ❌ NOT RUNNING"
fi
echo ""

# Recent API Activity
echo "📊 RECENT API ACTIVITY (Last 5 requests)"
echo "----------------------------------------"
tail -5 server/data/logs/server.log 2>/dev/null | \
    grep "→\|←" | \
    sed 's/^/  /' || echo "  No recent activity"
echo ""

# Database Stats
echo "💾 DATABASE STATS"
echo "----------------------------------------"
if [ -f "server/data/localizationtools.db" ]; then
    DB_SIZE=$(du -h server/data/localizationtools.db | cut -f1)
    echo "  Size: $DB_SIZE"

    # Count records (requires sqlite3)
    if command -v sqlite3 &> /dev/null; then
        LOG_COUNT=$(sqlite3 server/data/localizationtools.db "SELECT COUNT(*) FROM log_entries;" 2>/dev/null || echo "N/A")
        USER_COUNT=$(sqlite3 server/data/localizationtools.db "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "N/A")
        echo "  Log Entries: $LOG_COUNT"
        echo "  Users: $USER_COUNT"
    fi
else
    echo "  ❌ Database file not found"
fi
echo ""

# Test Dashboard API
echo "🧪 DASHBOARD API TEST"
echo "----------------------------------------"
if curl -s http://localhost:8888/health > /dev/null 2>&1; then
    # Try to get overview stats (requires auth)
    echo "  Backend health: ✅ OK"
    echo "  Dashboard endpoints: Available at /api/v2/admin/stats/*"
else
    echo "  ❌ Backend not responding"
fi
echo ""

echo "========================================="
echo "Press Ctrl+C to exit, or run with 'watch' for continuous monitoring:"
echo "  watch -n 2 bash $0"
echo "========================================="
