#!/bin/bash
# Real-time TaskManager Monitoring
# Shows when TaskManager makes API calls and what happens

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         TASKMANAGER REAL-TIME MONITORING                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Watching for:"
echo "  • /api/progress/operations - TaskManager fetching operations"
echo "  • auth_token usage - Token authentication"  
echo "  • WebSocket 'progress' events - Real-time updates"
echo "  • TaskManager component loads"
echo ""
echo "Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

tail -f /home/neil1988/LocalizationTools/server_output.log | while read line; do
    # TaskManager API calls
    if echo "$line" | grep -q "/api/progress/operations"; then
        if echo "$line" | grep -q "GET"; then
            echo -e "${GREEN}[TASKMANAGER FETCH]${NC} $line"
        elif echo "$line" | grep -q "DELETE"; then
            echo -e "${YELLOW}[TASKMANAGER CLEAR]${NC} $line"
        fi
    # Auth with Bearer token
    elif echo "$line" | grep -q "Bearer\|Authorization"; then
        echo -e "${BLUE}[AUTH TOKEN]${NC} $line"
    # WebSocket progress events
    elif echo "$line" | grep -qi "operation_start\|progress_update\|operation_complete"; then
        echo -e "${GREEN}[WEBSOCKET EVENT]${NC} $line"
    # Frontend logs mentioning TaskManager
    elif echo "$line" | grep -qi "taskmanager\|task.*manager"; then
        echo -e "${BLUE}[TASKMANAGER]${NC} $line"
    # Errors
    elif echo "$line" | grep -qi "ERROR.*progress\|ERROR.*task"; then
        echo -e "${RED}[ERROR]${NC} $line"
    fi
done
