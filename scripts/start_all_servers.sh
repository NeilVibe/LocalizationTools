#!/bin/bash
# ============================================================================
# LocaNext Server Startup Script
# ============================================================================
# This script ensures ALL servers are running before development/testing.
# Run this at the start of every session.
#
# Usage: ./scripts/start_all_servers.sh
# ============================================================================

set -e  # Exit on error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "  LocaNext Server Startup Script"
echo "=============================================="
echo ""

# ----------------------------------------------------------------------------
# 1. Check PostgreSQL
# ----------------------------------------------------------------------------
echo -n "Checking PostgreSQL... "
if pg_isready -q 2>/dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}Starting PostgreSQL...${NC}"
    sudo service postgresql start
    sleep 2
    if pg_isready -q 2>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL started${NC}"
    else
        echo -e "${RED}✗ FAILED to start PostgreSQL!${NC}"
        exit 1
    fi
fi

# ----------------------------------------------------------------------------
# 2. Check/Kill existing backend on port 8888
# ----------------------------------------------------------------------------
echo -n "Checking port 8888... "
PID=$(lsof -t -i:8888 2>/dev/null || true)
if [ -n "$PID" ]; then
    echo -e "${YELLOW}Port in use by PID $PID - killing...${NC}"
    kill -9 $PID 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✓ Port 8888 freed${NC}"
else
    echo -e "${GREEN}✓ Port available${NC}"
fi

# ----------------------------------------------------------------------------
# 3. Start Backend Server
# ----------------------------------------------------------------------------
echo "Starting FastAPI backend..."
cd /home/neil1988/LocalizationTools

# Start in background with nohup
nohup python3 server/main.py > /tmp/locatools_server.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for server to be ready
echo -n "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8888/health > /dev/null 2>&1; then
        echo -e " ${GREEN}✓ Ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e " ${RED}✗ TIMEOUT - Backend failed to start!${NC}"
        echo "Check logs: cat /tmp/locatools_server.log"
        exit 1
    fi
done

# ----------------------------------------------------------------------------
# 4. Health Check
# ----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  Health Check"
echo "=============================================="
HEALTH=$(curl -s http://localhost:8888/health)
echo "Backend: $HEALTH"

# Check DB connection
DB_CHECK=$(curl -s http://localhost:8888/api/stats/db-health 2>/dev/null || echo '{"status":"unknown"}')
echo "Database: $DB_CHECK"

# ----------------------------------------------------------------------------
# 5. Summary
# ----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo -e "  ${GREEN}ALL SERVERS READY${NC}"
echo "=============================================="
echo ""
echo "Services:"
echo "  • PostgreSQL:  localhost:5432"
echo "  • Backend API: localhost:8888"
echo "  • API Docs:    localhost:8888/docs"
echo ""
echo "Logs: tail -f /tmp/locatools_server.log"
echo ""
