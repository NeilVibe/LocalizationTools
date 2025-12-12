#!/bin/bash
# ============================================================================
# LocaNext Server Startup Script
# ============================================================================
# Starts all servers as background processes that persist after logout.
# Servers run independently - no tmux session required.
#
# Usage: ./scripts/start_all_servers.sh
# Stop:  ./scripts/stop_all_servers.sh
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/home/neil1988/LocalizationTools"
GITEA_DIR="/home/neil1988/gitea"
LOG_DIR="/tmp/locanext"

echo "=============================================="
echo "  LocaNext Server Startup"
echo "=============================================="
echo ""

# Create log directory
mkdir -p $LOG_DIR

# ----------------------------------------------------------------------------
# 1. PostgreSQL (system service)
# ----------------------------------------------------------------------------
echo -n "PostgreSQL (5432)... "
if pg_isready -q 2>/dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}Starting...${NC}"
    sudo service postgresql start
    sleep 2
    if pg_isready -q 2>/dev/null; then
        echo -e "${GREEN}✓ Started${NC}"
    else
        echo -e "${RED}✗ FAILED${NC}"
        exit 1
    fi
fi

# ----------------------------------------------------------------------------
# 2. Backend API (8888)
# ----------------------------------------------------------------------------
echo -n "Backend API (8888)... "
if curl -s --connect-timeout 1 http://localhost:8888/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Already running${NC}"
else
    # Kill any orphan process on port
    PID=$(lsof -t -i:8888 2>/dev/null || true)
    [ -n "$PID" ] && kill -9 $PID 2>/dev/null || true

    # Start backend
    cd $PROJECT_DIR
    nohup python3 server/main.py > $LOG_DIR/backend.log 2>&1 &
    disown

    # Wait for ready
    for i in {1..30}; do
        if curl -s --connect-timeout 1 http://localhost:8888/health >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Started${NC}"
            break
        fi
        sleep 1
        [ $i -eq 30 ] && echo -e "${RED}✗ TIMEOUT${NC}"
    done
fi

# ----------------------------------------------------------------------------
# 3. Gitea (3000)
# ----------------------------------------------------------------------------
echo -n "Gitea (3000)... "
if curl -s --connect-timeout 1 http://localhost:3000 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Already running${NC}"
else
    cd $GITEA_DIR
    GITEA_WORK_DIR=$GITEA_DIR nohup ./gitea web > $LOG_DIR/gitea.log 2>&1 &
    disown

    for i in {1..15}; do
        if curl -s --connect-timeout 1 http://localhost:3000 >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Started${NC}"
            break
        fi
        sleep 1
        [ $i -eq 15 ] && echo -e "${YELLOW}~ Starting (slow)${NC}"
    done
fi

# ----------------------------------------------------------------------------
# 4. Admin Dashboard (5175)
# ----------------------------------------------------------------------------
echo -n "Admin Dashboard (5175)... "
if curl -s --connect-timeout 1 http://localhost:5175 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Already running${NC}"
else
    cd $PROJECT_DIR/adminDashboard
    nohup npm run dev -- --port 5175 > $LOG_DIR/admin.log 2>&1 &
    disown

    for i in {1..15}; do
        if curl -s --connect-timeout 1 http://localhost:5175 >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Started${NC}"
            break
        fi
        sleep 1
        [ $i -eq 15 ] && echo -e "${YELLOW}~ Starting (slow)${NC}"
    done
fi

# ----------------------------------------------------------------------------
# 5. Summary
# ----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo -e "  ${GREEN}ALL SERVERS STARTED${NC}"
echo "=============================================="
echo ""
echo "Services:"
echo "  • PostgreSQL:      localhost:5432"
echo "  • Backend API:     localhost:8888"
echo "  • API Docs:        localhost:8888/docs"
echo "  • Gitea:           localhost:3000"
echo "  • Admin Dashboard: localhost:5175"
echo ""
echo "Logs: $LOG_DIR/"
echo "  • tail -f $LOG_DIR/backend.log"
echo "  • tail -f $LOG_DIR/gitea.log"
echo "  • tail -f $LOG_DIR/admin.log"
echo ""
echo "Commands:"
echo "  • Check: ./scripts/check_servers.sh"
echo "  • Stop:  ./scripts/stop_all_servers.sh"
echo ""
