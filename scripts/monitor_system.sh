#!/bin/bash

# System Monitoring Script for LocalizationTools
# Tests backend, frontend, database, and WebSocket connectivity

echo "========================================="
echo "LocalizationTools System Monitor"
echo "$(date)"
echo "========================================="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if processes are running
echo "1. PROCESS STATUS"
echo "-----------------"

if pgrep -f "python.*uvicorn" > /dev/null; then
    echo -e "${GREEN}✓${NC} Backend (Python/FastAPI) is running"
    BACKEND_PID=$(pgrep -f "python.*uvicorn")
    echo "  PID: $BACKEND_PID"
else
    echo -e "${RED}✗${NC} Backend is NOT running"
fi

if pgrep -f "vite.*dev.*5173" > /dev/null; then
    echo -e "${GREEN}✓${NC} Frontend (Vite) is running on port 5173"
else
    echo -e "${RED}✗${NC} Frontend is NOT running"
fi
echo

# 2. Check port bindings
echo "2. PORT STATUS"
echo "--------------"
BACKEND_PORT=$(ss -tlnp 2>/dev/null | grep python | grep -oP ':\K\d+' | head -1)
if [ ! -z "$BACKEND_PORT" ]; then
    echo -e "${GREEN}✓${NC} Backend listening on port: $BACKEND_PORT"
else
    echo -e "${RED}✗${NC} Backend not listening on any port"
fi

if ss -tlnp 2>/dev/null | grep 5173 > /dev/null; then
    echo -e "${GREEN}✓${NC} Frontend listening on port: 5173"
else
    echo -e "${RED}✗${NC} Frontend not listening on port 5173"
fi
echo

# 3. Test Backend API Health
echo "3. BACKEND API TESTS"
echo "--------------------"

# Health check
HEALTH=$(curl -s http://localhost:8888/health 2>/dev/null)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Health endpoint: OK"
    echo "  $(echo $HEALTH | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f\"Database: {d.get(\"database\")}, Version: {d.get(\"version\")}\")')"
else
    echo -e "${RED}✗${NC} Health endpoint: FAILED"
fi

# Root endpoint
ROOT=$(curl -s http://localhost:8888/ 2>/dev/null)
if echo "$ROOT" | grep -q "LocalizationTools"; then
    echo -e "${GREEN}✓${NC} Root endpoint: OK"
else
    echo -e "${RED}✗${NC} Root endpoint: FAILED"
fi

# API docs
DOCS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/docs 2>/dev/null)
if [ "$DOCS" = "200" ]; then
    echo -e "${GREEN}✓${NC} API documentation: Available at http://localhost:8888/docs"
else
    echo -e "${RED}✗${NC} API documentation: Not available"
fi
echo

# 4. Test Frontend
echo "4. FRONTEND TESTS"
echo "-----------------"
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>/dev/null)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}✓${NC} Frontend homepage: OK (HTTP $FRONTEND_STATUS)"
else
    echo -e "${RED}✗${NC} Frontend homepage: FAILED (HTTP $FRONTEND_STATUS)"
fi
echo

# 5. Test WebSocket/Socket.IO
echo "5. WEBSOCKET/SOCKET.IO TESTS"
echo "-----------------------------"

# Socket.IO polling endpoint
SOCKETIO=$(curl -s "http://localhost:8888/ws/socket.io/?EIO=4&transport=polling" 2>/dev/null | head -c 50)
if echo "$SOCKETIO" | grep -q "sid"; then
    echo -e "${GREEN}✓${NC} Socket.IO polling: OK"
    echo "  $(echo $SOCKETIO | grep -oP 'sid":"[^"]+' | head -1)"
else
    echo -e "${RED}✗${NC} Socket.IO polling: FAILED"
fi
echo

# 6. Database Status
echo "6. DATABASE STATUS"
echo "------------------"
python3 << 'PYEOF'
import sqlite3
import sys

try:
    db_path = '/home/neil1988/LocalizationTools/server/data/localizationtools.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\033[0;32m✓\033[0m Database connected: {len(tables)} tables")

    # Check active operations
    cursor.execute("SELECT COUNT(*) FROM active_operations")
    ops_count = cursor.fetchone()[0]
    print(f"  Active operations: {ops_count}")

    # Check users
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    print(f"  Users: {users_count}")

    # Check sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    sessions_count = cursor.fetchone()[0]
    print(f"  Sessions: {sessions_count}")

    # Recent activity
    cursor.execute("SELECT MAX(updated_at) FROM active_operations")
    last_op = cursor.fetchone()[0]
    if last_op:
        print(f"  Last operation: {last_op}")

    conn.close()
except Exception as e:
    print(f"\033[0;31m✗\033[0m Database error: {e}")
    sys.exit(1)
PYEOF
echo

# 7. Check for errors in logs
echo "7. RECENT LOG ERRORS"
echo "--------------------"
ERROR_COUNT=$(tail -100 /home/neil1988/LocalizationTools/server_output.log 2>/dev/null | grep -i "ERROR" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No recent errors in server log"
else
    echo -e "${YELLOW}⚠${NC} Found $ERROR_COUNT error(s) in last 100 log lines"
    echo "  Last 3 errors:"
    tail -100 /home/neil1988/LocalizationTools/server_output.log 2>/dev/null | grep -i "ERROR" | tail -3 | sed 's/^/  /'
fi
echo

# 8. Summary
echo "========================================="
echo "SUMMARY"
echo "========================================="
echo
echo "Backend API: http://localhost:8888"
echo "Frontend:    http://localhost:5173"
echo "API Docs:    http://localhost:8888/docs"
echo
echo "Run this script anytime to check system status"
echo
