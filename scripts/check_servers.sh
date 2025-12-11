#!/bin/bash
# ============================================================================
# LocaNext Server Health Check
# ============================================================================
# Quick check if all servers are running. Use before testing/development.
#
# Usage: ./scripts/check_servers.sh
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "  LocaNext Server Health Check"
echo "=============================================="
echo ""

ALL_OK=true

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
    echo -e "${GREEN}✓ OK${NC}"
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

echo ""
echo "=============================================="
if [ "$ALL_OK" = true ]; then
    echo -e "  ${GREEN}ALL SERVERS OK${NC}"
else
    echo -e "  ${RED}SERVERS NOT READY${NC}"
    echo ""
    echo "  Run: ./scripts/start_all_servers.sh"
fi
echo "=============================================="
