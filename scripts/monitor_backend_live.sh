#!/bin/bash

# Live Backend Monitor
# Continuously monitors backend health and logs

BACKEND_URL="http://localhost:8888"
CHECK_INTERVAL=5  # seconds

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear
echo "========================================="
echo "Backend Live Monitor"
echo "Monitoring: $BACKEND_URL"
echo "Refresh: Every ${CHECK_INTERVAL}s (Press Ctrl+C to stop)"
echo "========================================="
echo

while true; do
    clear
    echo "========================================="
    echo "Backend Live Monitor - $(date '+%H:%M:%S')"
    echo "========================================="
    echo

    # Health check
    HEALTH=$(curl -s $BACKEND_URL/health 2>/dev/null)
    if echo "$HEALTH" | grep -q "healthy"; then
        echo -e "${GREEN}✓ Backend: HEALTHY${NC}"
        echo "  Status: $(echo $HEALTH | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status"))' 2>/dev/null)"
        echo "  Database: $(echo $HEALTH | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("database"))' 2>/dev/null)"
    else
        echo -e "${RED}✗ Backend: OFFLINE${NC}"
    fi
    echo

    # Check processes
    if pgrep -f "python.*uvicorn" > /dev/null; then
        PID=$(pgrep -f "python.*uvicorn")
        CPU=$(ps -p $PID -o %cpu= 2>/dev/null | tr -d ' ')
        MEM=$(ps -p $PID -o %mem= 2>/dev/null | tr -d ' ')
        echo -e "${GREEN}✓ Process: Running${NC}"
        echo "  PID: $PID"
        echo "  CPU: ${CPU}%"
        echo "  Memory: ${MEM}%"
    else
        echo -e "${RED}✗ Process: NOT RUNNING${NC}"
    fi
    echo

    # Database stats
    python3 << 'PYEOF' 2>/dev/null
import sqlite3
try:
    conn = sqlite3.connect('/home/neil1988/LocalizationTools/server/data/localizationtools.db')
    c = conn.cursor()

    # Active operations
    c.execute("SELECT COUNT(*) FROM active_operations WHERE status='running'")
    running = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM active_operations WHERE status='completed'")
    completed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM active_operations WHERE status='failed'")
    failed = c.fetchone()[0]

    # Active users
    c.execute("SELECT COUNT(*) FROM sessions WHERE ended_at IS NULL")
    active_sessions = c.fetchone()[0]

    print("\033[0;32m✓ Database:\033[0m Connected")
    print(f"  Running operations: {running}")
    print(f"  Completed operations: {completed}")
    if failed > 0:
        print(f"  Failed operations: \033[1;33m{failed}\033[0m")
    else:
        print(f"  Failed operations: {failed}")
    print(f"  Active sessions: {active_sessions}")

    conn.close()
except Exception as e:
    print(f"\033[0;31m✗ Database: Error - {e}\033[0m")
PYEOF
    echo

    # Recent log errors
    ERROR_COUNT=$(tail -50 /home/neil1988/LocalizationTools/server_output.log 2>/dev/null | grep -i "ERROR" | wc -l)
    if [ "$ERROR_COUNT" -eq 0 ]; then
        echo -e "${GREEN}✓ Logs: No recent errors${NC}"
    else
        echo -e "${YELLOW}⚠ Logs: $ERROR_COUNT error(s) in last 50 lines${NC}"
        echo "  Last error:"
        tail -50 /home/neil1988/LocalizationTools/server_output.log 2>/dev/null | grep -i "ERROR" | tail -1 | sed 's/^/  /' | cut -c1-80
    fi
    echo

    # WebSocket status
    WS_TEST=$(curl -s "http://localhost:8888/ws/socket.io/?EIO=4&transport=polling" 2>/dev/null | head -c 20)
    if echo "$WS_TEST" | grep -q "sid"; then
        echo -e "${GREEN}✓ WebSocket: Active${NC}"
    else
        echo -e "${RED}✗ WebSocket: Inactive${NC}"
    fi
    echo

    echo "========================================="
    echo "Next refresh in ${CHECK_INTERVAL}s..."

    sleep $CHECK_INTERVAL
done
