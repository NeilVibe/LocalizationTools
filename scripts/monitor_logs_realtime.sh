#!/bin/bash
# Real-Time Log Monitoring - All Servers
# Usage: ./scripts/monitor_logs_realtime.sh [OPTIONS]
# Options:
#   --errors-only    Show only ERROR and CRITICAL messages
#   --no-color       Disable color output
#   --backend-only   Monitor backend server only

set -e

PROJECT_ROOT="/home/neil1988/LocalizationTools"
SESSION_ID=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Parse options
ERRORS_ONLY=false
NO_COLOR=false
BACKEND_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --errors-only) ERRORS_ONLY=true; shift ;;
        --no-color) NO_COLOR=true; shift ;;
        --backend-only) BACKEND_ONLY=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ "$NO_COLOR" = true ]; then
    RED=''; YELLOW=''; GREEN=''; BLUE=''; CYAN=''; GRAY=''; NC=''
fi

echo "=========================================="
echo "📡 REAL-TIME LOG MONITORING"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo "Started: $(date)"
echo ""

if [ "$ERRORS_ONLY" = true ]; then
    echo "🔍 Mode: ERRORS ONLY (ERROR, CRITICAL)"
elif [ "$BACKEND_ONLY" = true ]; then
    echo "🔍 Mode: Backend Server Only"
else
    echo "🔍 Mode: ALL LOGS (INFO, WARNING, ERROR)"
fi

echo ""
echo "📊 Monitoring:"
echo "  - Backend Server: $PROJECT_ROOT/server/data/logs/server.log"
echo "  - Backend Errors: $PROJECT_ROOT/server/data/logs/error.log"
if [ "$BACKEND_ONLY" != true ]; then
    echo "  - LocaNext App:   $PROJECT_ROOT/logs/locanext_app.log"
    echo "  - LocaNext Errors: $PROJECT_ROOT/logs/locanext_error.log"
    echo "  - Dashboard App:  $PROJECT_ROOT/logs/dashboard_app.log"
    echo "  - Dashboard Errors: $PROJECT_ROOT/logs/dashboard_error.log"
fi
echo ""
echo "💡 Tips:"
echo "  - Press Ctrl+C to stop monitoring"
echo "  - Errors are shown in ${RED}RED${NC}"
echo "  - Warnings are shown in ${YELLOW}YELLOW${NC}"
echo "  - Success is shown in ${GREEN}GREEN${NC}"
echo ""
echo "=========================================="
echo ""

# Create session log file
SESSION_LOG="$PROJECT_ROOT/logs/sessions/session_${SESSION_ID}.log"
echo "Monitoring Session Started: $(date)" > "$SESSION_LOG"

# Function to colorize log lines
colorize_log() {
    while IFS= read -r line; do
        # Add to session log
        echo "$line" >> "$SESSION_LOG"

        # Skip if errors-only mode and not an error
        if [ "$ERRORS_ONLY" = true ]; then
            if ! echo "$line" | grep -qiE "ERROR|CRITICAL|EXCEPTION|FAIL"; then
                continue
            fi
        fi

        # Colorize output
        if echo "$line" | grep -qi "CRITICAL"; then
            echo -e "${RED}🔥 $line${NC}"
        elif echo "$line" | grep -qi "ERROR"; then
            echo -e "${RED}❌ $line${NC}"
        elif echo "$line" | grep -qi "EXCEPTION"; then
            echo -e "${RED}💥 $line${NC}"
        elif echo "$line" | grep -qi "WARNING"; then
            echo -e "${YELLOW}⚠️  $line${NC}"
        elif echo "$line" | grep -qi "SUCCESS"; then
            echo -e "${GREEN}✅ $line${NC}"
        elif echo "$line" | grep -qi "INFO"; then
            echo -e "${BLUE}ℹ️  $line${NC}"
        elif echo "$line" | grep -qi "DEBUG"; then
            echo -e "${GRAY}🔍 $line${NC}"
        else
            echo "$line"
        fi
    done
}

# Ensure log files exist
touch "$PROJECT_ROOT/server/data/logs/server.log"
touch "$PROJECT_ROOT/server/data/logs/error.log"
touch "$PROJECT_ROOT/logs/locanext_app.log"
touch "$PROJECT_ROOT/logs/locanext_error.log"
touch "$PROJECT_ROOT/logs/dashboard_app.log"
touch "$PROJECT_ROOT/logs/dashboard_error.log"

# Monitor all log files
echo "🚀 Monitoring started... (watching for new log entries)"
echo ""

if [ "$BACKEND_ONLY" = true ]; then
    # Backend only mode
    tail -f -n 0 \
        "$PROJECT_ROOT/server/data/logs/server.log" \
        "$PROJECT_ROOT/server/data/logs/error.log" \
        2>/dev/null | colorize_log
else
    # All servers mode
    tail -f -n 0 \
        "$PROJECT_ROOT/server/data/logs/server.log" \
        "$PROJECT_ROOT/server/data/logs/error.log" \
        "$PROJECT_ROOT/logs/locanext_app.log" \
        "$PROJECT_ROOT/logs/locanext_error.log" \
        "$PROJECT_ROOT/logs/dashboard_app.log" \
        "$PROJECT_ROOT/logs/dashboard_error.log" \
        2>/dev/null | colorize_log
fi
