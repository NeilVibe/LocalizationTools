#!/bin/bash

# Complete Server Monitoring Script
# Shows real-time logs for ALL servers

echo "========================================"
echo "🔍 LocaNext - Complete Server Monitor"
echo "========================================"
echo ""

# Check what's running
echo "📊 Running Servers:"
ps aux | grep -E "(python3 server/main.py|npm run dev)" | grep -v grep | while read line; do
  PID=$(echo $line | awk '{print $2}')
  CMD=$(echo $line | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
  echo "  PID $PID: $CMD"
done
echo ""

# Check ports
echo "🌐 Active Ports:"
netstat -tlnp 2>/dev/null | grep -E "(8888|5175|5173)" | awk '{print "  " $4 " -> " $7}'
echo ""

# Server status
echo "✅ Server Health Checks:"
curl -s http://localhost:8888/health > /dev/null && echo "  Backend (8888): ✅ HEALTHY" || echo "  Backend (8888): ❌ DOWN"
curl -s http://localhost:5175/ > /dev/null && echo "  Dashboard (5175): ✅ HEALTHY" || echo "  Dashboard (5175): ❌ DOWN"
curl -s http://localhost:5173/ > /dev/null && echo "  LocaNext (5173): ✅ HEALTHY" || echo "  LocaNext (5173): ❌ DOWN"
echo ""

echo "📝 Recent Activity (Last 20 log entries from each server):"
echo "========================================="

# Backend Server Logs
echo ""
echo "🖥️  BACKEND SERVER:"
if [ -f "/home/neil1988/LocalizationTools/server/data/logs/server.log" ]; then
  tail -10 /home/neil1988/LocalizationTools/server/data/logs/server.log | grep -E "(INFO|WARNING|ERROR|SUCCESS)" | while read line; do
    if echo "$line" | grep -q "ERROR"; then
      echo "  ❌ $line"
    elif echo "$line" | grep -q "WARNING"; then
      echo "  ⚠️  $line"
    elif echo "$line" | grep -q "SUCCESS"; then
      echo "  ✅ $line"
    else
      echo "  ℹ️  $line"
    fi
  done
else
  echo "  No backend log file found"
fi

# LocaNext App Logs
echo ""
echo "💻 LOCANEXT APP:"
if [ -f "/home/neil1988/LocalizationTools/logs/locanext_app.log" ]; then
  tail -10 /home/neil1988/LocalizationTools/logs/locanext_app.log | grep -E "(INFO|WARNING|ERROR|SUCCESS)" | while read line; do
    if echo "$line" | grep -q "ERROR"; then
      echo "  ❌ $line"
    elif echo "$line" | grep -q "WARNING"; then
      echo "  ⚠️  $line"
    elif echo "$line" | grep -q "SUCCESS"; then
      echo "  ✅ $line"
    else
      echo "  ℹ️  $line"
    fi
  done
else
  echo "  No LocaNext log file found (app not run yet)"
fi

# Dashboard Logs
echo ""
echo "📊 ADMIN DASHBOARD:"
if [ -f "/home/neil1988/LocalizationTools/logs/dashboard_app.log" ]; then
  tail -10 /home/neil1988/LocalizationTools/logs/dashboard_app.log | grep -E "(INFO|WARNING|ERROR|SUCCESS)" | while read line; do
    if echo "$line" | grep -q "ERROR"; then
      echo "  ❌ $line"
    elif echo "$line" | grep -q "WARNING"; then
      echo "  ⚠️  $line"
    elif echo "$line" | grep -q "SUCCESS"; then
      echo "  ✅ $line"
    else
      echo "  ℹ️  $line"
    fi
  done
else
  echo "  No Dashboard log file found (app not run yet)"
fi
echo ""

echo "========================================="
echo "🔄 Live Monitoring Commands:"
echo "========================================="
echo "Monitor ALL servers (recommended):"
echo "  bash scripts/monitor_logs_realtime.sh"
echo ""
echo "Monitor specific logs:"
echo "  Backend:    tail -f server/data/logs/server.log"
echo "  LocaNext:   tail -f logs/locanext_app.log"
echo "  Dashboard:  tail -f logs/dashboard_app.log"
echo "  All Errors: tail -f server/data/logs/error.log logs/*_error.log"
echo ""
echo "Monitor with filters:"
echo "  bash scripts/monitor_logs_realtime.sh --errors-only"
echo "  bash scripts/monitor_logs_realtime.sh --backend-only"
echo ""
echo "Run this script again: bash scripts/monitor_all_servers.sh"
echo "========================================="
