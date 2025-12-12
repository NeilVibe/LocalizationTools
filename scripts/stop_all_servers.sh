#!/bin/bash
# ============================================================================
# LocaNext Server Stop Script
# ============================================================================
# Stops all servers by killing processes on their ports.
#
# Usage: ./scripts/stop_all_servers.sh
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "  LocaNext Server Shutdown"
echo "=============================================="
echo ""

# Kill servers by port
declare -A SERVERS=(
    [8888]="Backend API"
    [3000]="Gitea"
    [5175]="Admin Dashboard"
)

for PORT in "${!SERVERS[@]}"; do
    NAME="${SERVERS[$PORT]}"
    echo -n "$NAME ($PORT)... "
    PID=$(lsof -t -i:$PORT 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        echo -e "${GREEN}✓ Stopped${NC}"
    else
        echo -e "${YELLOW}Not running${NC}"
    fi
done

echo ""
echo "=============================================="
echo -e "  ${GREEN}ALL SERVERS STOPPED${NC}"
echo "=============================================="
echo ""
echo "PostgreSQL is still running (system service)."
echo "To stop it: sudo service postgresql stop"
echo ""
