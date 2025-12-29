#!/bin/bash
# ============================================================================
# LocaNext DEV Server Startup Script
# ============================================================================
# Starts DEV servers with DEV_MODE=true (no rate limiting).
# Servers run independently - no tmux session required.
#
# Usage: ./scripts/start_all_servers.sh [--with-vite]
# Stop:  ./scripts/stop_all_servers.sh
#
# NOTE: For Gitea CI/CD, use: ./scripts/gitea_control.sh start
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/home/neil1988/LocalizationTools"
LOG_DIR="/tmp/locanext"
AUDIT_LOG="$PROJECT_DIR/server/data/logs/security_audit.log"

echo "=============================================="
echo "  LocaNext DEV Server Startup"
echo "=============================================="
echo ""

# Create log directory
mkdir -p $LOG_DIR

# Clear rate limit on startup (for DEV convenience)
if [ -f "$AUDIT_LOG" ]; then
    grep -v "LOGIN_FAILURE.*127.0.0.1" "$AUDIT_LOG" > /tmp/audit_clean.log 2>/dev/null || true
    mv /tmp/audit_clean.log "$AUDIT_LOG" 2>/dev/null || true
    echo -e "${GREEN}✓ Rate limit cleared${NC}"
fi

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
# 2. Backend API (8888) - DEV_MODE=true (no rate limiting!)
# ----------------------------------------------------------------------------
echo -n "Backend API (8888)... "
if curl -s --connect-timeout 1 http://localhost:8888/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Already running${NC}"
else
    # Kill any orphan process on port
    PID=$(lsof -t -i:8888 2>/dev/null || true)
    [ -n "$PID" ] && kill -9 $PID 2>/dev/null || true

    # Start backend with DEV_MODE=true (disables rate limiting)
    cd $PROJECT_DIR
    DEV_MODE=true nohup python3 server/main.py > $LOG_DIR/backend.log 2>&1 &
    disown

    # Wait for ready
    for i in {1..30}; do
        if curl -s --connect-timeout 1 http://localhost:8888/health >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Started${NC} [DEV_MODE]"
            break
        fi
        sleep 1
        [ $i -eq 30 ] && echo -e "${RED}✗ TIMEOUT${NC}"
    done
fi

# ----------------------------------------------------------------------------
# 3. Vite Dev Server (5173) - Optional with --with-vite
# ----------------------------------------------------------------------------
if [ "$1" == "--with-vite" ]; then
    echo -n "Vite Dev (5173)... "
    if curl -s --connect-timeout 1 http://localhost:5173 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Already running${NC}"
    else
        cd $PROJECT_DIR/locaNext
        nohup npm run dev > $LOG_DIR/vite.log 2>&1 &
        disown

        for i in {1..15}; do
            if curl -s --connect-timeout 1 http://localhost:5173 >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Started${NC}"
                break
            fi
            sleep 1
            [ $i -eq 15 ] && echo -e "${YELLOW}~ Starting (slow)${NC}"
        done
    fi
fi

# ----------------------------------------------------------------------------
# 4. Admin Dashboard (5175) - Optional
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
echo -e "  ${GREEN}DEV SERVERS STARTED${NC}"
echo "=============================================="
echo ""
echo "Services:"
echo "  • PostgreSQL:      localhost:5432"
echo "  • Backend API:     localhost:8888 [DEV_MODE - no rate limit]"
echo "  • API Docs:        localhost:8888/docs"
if [ "$1" == "--with-vite" ]; then
echo "  • Vite Dev:        localhost:5173"
fi
echo "  • Admin Dashboard: localhost:5175"
echo ""
echo "Logs: $LOG_DIR/"
echo "  • tail -f $LOG_DIR/backend.log"
if [ "$1" == "--with-vite" ]; then
echo "  • tail -f $LOG_DIR/vite.log"
fi
echo "  • tail -f $LOG_DIR/admin.log"
echo ""
echo "Commands:"
echo "  • Check:     ./scripts/check_servers.sh"
echo "  • Stop:      ./scripts/stop_all_servers.sh"
echo "  • Gitea:     ./scripts/gitea_control.sh start"
echo "  • With Vite: ./scripts/start_all_servers.sh --with-vite"
echo ""
