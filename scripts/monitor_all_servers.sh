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

echo "📝 Recent Activity (Last 20 log entries):"
echo "========================================="
if [ -f "/home/neil1988/LocalizationTools/server/logs/localizationtools.log" ]; then
  tail -20 /home/neil1988/LocalizationTools/server/logs/localizationtools.log | grep -E "(INFO|WARNING|ERROR|SUCCESS)" | while read line; do
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
  echo "  No log file found yet"
fi
echo ""

echo "========================================="
echo "🔄 Live Monitoring Commands:"
echo "========================================="
echo "Watch Backend:    tail -f server/logs/localizationtools.log"
echo "Watch Errors:     tail -f server/logs/error.log"
echo "Watch API Calls:  tail -f server/logs/localizationtools.log | grep 'API'"
echo "Watch User:       tail -f server/logs/localizationtools.log | grep 'username'"
echo ""
echo "Run this script again: bash scripts/monitor_all_servers.sh"
echo "========================================="
