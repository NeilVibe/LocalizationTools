#!/bin/bash
# ============================================================================
# LocaNext DEV Server Health Check
# ============================================================================
# Quick check if DEV servers are running. Use before testing/development.
#
# Usage: ./scripts/check_servers.sh
#
# NOTE: For Gitea CI/CD, use: ./scripts/gitea_control.sh status
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "  LocaNext DEV Server Health Check"
echo "=============================================="
echo ""

ALL_OK=true
AUDIT_LOG="/home/neil1988/LocalizationTools/server/data/logs/security_audit.log"

# Check PostgreSQL
echo -n "PostgreSQL (5432)... "
if pg_isready -q 2>/dev/null; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ NOT RUNNING${NC}"
    ALL_OK=false
fi

# Check Backend API
echo -n "Backend API (8888)... "
HEALTH=$(curl -s --connect-timeout 2 http://localhost:8888/health 2>/dev/null)
if [[ "$HEALTH" == *"healthy"* ]]; then
    # Check if DEV_MODE is enabled
    DEV_MODE_HINT=""
    if pgrep -af "python.*server/main" | grep -q "DEV_MODE"; then
        DEV_MODE_HINT=" [DEV_MODE]"
    fi
    echo -e "${GREEN}✓ OK${NC}${DEV_MODE_HINT}"
else
    echo -e "${RED}✗ NOT RUNNING${NC}"
    ALL_OK=false
fi

# Check WebSocket (same port as API)
echo -n "WebSocket (8888/ws)... "
if [[ "$HEALTH" == *"healthy"* ]]; then
    echo -e "${GREEN}✓ OK${NC} (via API)"
else
    echo -e "${RED}✗ NOT RUNNING${NC}"
    ALL_OK=false
fi

# Check Vite Dev Server (PRIMARY for UI dev)
echo -n "Vite Dev (5173)... "
if curl -s --connect-timeout 2 http://localhost:5173 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${YELLOW}~ NOT RUNNING${NC} (optional for DEV)"
fi

# Check Admin Dashboard (optional)
echo -n "Admin Dashboard (5175)... "
if curl -s --connect-timeout 2 http://localhost:5175 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${YELLOW}~ NOT RUNNING${NC} (optional)"
fi

# Check rate limit status
echo ""
echo -n "Rate Limit Status... "
if [ -f "$AUDIT_LOG" ]; then
    FAILED_COUNT=$(grep -c "LOGIN_FAILURE.*127.0.0.1" "$AUDIT_LOG" 2>/dev/null || echo "0")
    # Count only recent (last 15 min)
    RECENT_FAILS=$(grep "LOGIN_FAILURE.*127.0.0.1" "$AUDIT_LOG" 2>/dev/null | tail -5 | wc -l)
    if [ "$RECENT_FAILS" -ge 5 ]; then
        echo -e "${RED}⚠ LOCKED${NC} ($RECENT_FAILS recent fails)"
        echo -e "         Fix: ${YELLOW}./scripts/check_servers.sh --clear-ratelimit${NC}"
    else
        echo -e "${GREEN}✓ OK${NC} ($RECENT_FAILS/5 attempts)"
    fi
else
    echo -e "${GREEN}✓ OK${NC} (no log)"
fi

echo ""
echo "=============================================="
if [ "$ALL_OK" = true ]; then
    echo -e "  ${GREEN}CORE SERVERS OK${NC}"
else
    echo -e "  ${RED}SERVERS NOT READY${NC}"
    echo ""
    echo "  Run: ./scripts/start_all_servers.sh"
fi
echo "=============================================="
echo ""
echo "Quick Commands:"
echo "  Start DEV:     DEV_MODE=true python3 server/main.py"
echo "  Start Vite:    cd locaNext && npm run dev"
echo "  Clear rate:    ./scripts/check_servers.sh --clear-ratelimit"
echo "  Gitea CI/CD:   ./scripts/gitea_control.sh status"
echo ""

# Handle --clear-ratelimit flag
if [ "$1" == "--clear-ratelimit" ]; then
    echo "Clearing rate limit..."
    if [ -f "$AUDIT_LOG" ]; then
        grep -v "LOGIN_FAILURE.*127.0.0.1" "$AUDIT_LOG" > /tmp/audit_clean.log 2>/dev/null
        mv /tmp/audit_clean.log "$AUDIT_LOG"
        echo -e "${GREEN}✓ Rate limit cleared${NC}"
    else
        echo "No audit log found"
    fi
fi
