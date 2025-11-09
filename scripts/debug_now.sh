#!/bin/bash
# ONE COMMAND - See EVERYTHING

clear
echo "========================================"
echo "🔍 COMPLETE SYSTEM STATUS - RIGHT NOW"
echo "========================================"
echo ""

# 1. Server Status
echo "📊 SERVERS:"
curl -s http://localhost:8888/health > /dev/null && echo "  ✅ Backend (8888): UP" || echo "  ❌ Backend (8888): DOWN"
curl -s http://localhost:5173/ > /dev/null && echo "  ✅ LocaNext (5173): UP" || echo "  ❌ LocaNext (5173): DOWN"
echo ""

# 2. Recent Backend Activity (last 2 minutes)
echo "📦 BACKEND ACTIVITY (last 2 min):"
tail -100 server/data/logs/server.log | grep "$(date +%Y-%m-%d)" | tail -15
echo ""

# 3. ALL Errors (last 30 min)
echo "🔴 ALL ERRORS (last 30 min):"
grep "ERROR\|CRITICAL" server/data/logs/server.log | tail -5 || echo "  ✅ No errors"
echo ""

# 4. Frontend Logs (if any)
echo "🖥️  FRONTEND LOGS (if captured):"
grep "FRONTEND" server/data/logs/server.log | tail -5 || echo "  ⚠️  No frontend logs captured"
echo ""

echo "========================================"
