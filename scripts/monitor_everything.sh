#!/bin/bash
# UNIFIED MONITORING - See EVERYTHING at once

echo "========================================"
echo "🔍 UNIFIED ERROR MONITOR"
echo "========================================"
echo ""

# Check all servers
echo "📊 SERVERS STATUS:"
ps aux | grep -E "(python3 server/main.py|npm run dev)" | grep -v grep | while read line; do
  echo "  ✅ $(echo $line | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')"
done
echo ""

# Show ALL recent errors from ALL sources
echo "🔴 ALL ERRORS (Last 30 minutes):"
echo "----------------------------------------"

# Backend errors
if [ -f "server/data/logs/error.log" ]; then
  echo ""
  echo "📦 BACKEND ERRORS:"
  grep "ERROR\|CRITICAL" server/data/logs/error.log | tail -10 | while read line; do
    echo "  ❌ $line"
  done
fi

# Backend server log errors
if [ -f "server/data/logs/server.log" ]; then
  echo ""
  echo "📦 BACKEND SERVER ERRORS:"
  grep "ERROR\|CRITICAL" server/data/logs/server.log | tail -10 | while read line; do
    echo "  ❌ $line"
  done
fi

# LocaNext errors
if [ -f "logs/locanext_error.log" ]; then
  echo ""
  echo "🖥️  LOCANEXT ERRORS:"
  cat logs/locanext_error.log | tail -10 | while read line; do
    [ -n "$line" ] && echo "  ❌ $line"
  done
fi

# Dashboard errors  
if [ -f "logs/dashboard_error.log" ]; then
  echo ""
  echo "📊 DASHBOARD ERRORS:"
  cat logs/dashboard_error.log | tail -10 | while read line; do
    [ -n "$line" ] && echo "  ❌ $line"
  done
fi

echo ""
echo "========================================"
echo "✅ Monitoring complete"
echo "========================================"
