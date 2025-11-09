#!/bin/bash
# INSTANT ERROR CHECK - See everything NOW

clear
echo "========================================"
echo "🔴 ALL SYSTEM ERRORS - INSTANT VIEW"
echo "========================================"
echo ""

# 1. Backend Errors (since server restart at 18:01)
echo "📦 BACKEND (since 18:01):"
grep "ERROR\|CRITICAL" server/data/logs/server.log | grep "2025-11-09 18:" | tail -20 || echo "  ✅ No errors"
echo ""

# 2. Frontend LocaNext  
echo "🖥️  LOCANEXT FRONTEND:"
if [ -f "logs/locanext_error.log" ] && [ -s "logs/locanext_error.log" ]; then
  tail -10 logs/locanext_error.log
else
  echo "  ✅ No errors (or not logging to file)"
fi
echo ""

# 3. Dashboard
echo "📊 DASHBOARD:"
if [ -f "logs/dashboard_error.log" ] && [ -s "logs/dashboard_error.log" ]; then
  tail -10 logs/dashboard_error.log  
else
  echo "  ✅ No errors (or not logging to file)"
fi
echo ""

# 4. Check if servers are running
echo "🔄 SERVER STATUS:"
curl -s http://localhost:8888/health > /dev/null && echo "  ✅ Backend: HEALTHY" || echo "  ❌ Backend: DOWN"
curl -s http://localhost:5173/ > /dev/null && echo "  ✅ LocaNext: HEALTHY" || echo "  ❌ LocaNext: DOWN"  
curl -s http://localhost:5175/ > /dev/null && echo "  ✅ Dashboard: HEALTHY" || echo "  ❌ Dashboard: DOWN"
echo ""

echo "========================================"
echo "Run this anytime: bash scripts/check_all_errors.sh"
echo "========================================"
