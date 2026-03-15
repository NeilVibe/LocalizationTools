#!/bin/bash
# =============================================================================
# LocaNext API Endpoint Health Check
# =============================================================================
# Quick health-check script for all LocaNext backend API endpoints.
# Tests that endpoints exist and return non-5xx responses.
# 4xx responses for auth-protected endpoints are acceptable (endpoint exists).
#
# Usage:
#   ./scripts/api_test.sh                           # Default localhost:8888
#   ./scripts/api_test.sh --base-url http://host:port
#   ./scripts/api_test.sh --auth-token <token>
#   LOCANEXT_TOKEN=<token> ./scripts/api_test.sh
# =============================================================================

set -euo pipefail

# --- Configuration ---
BASE_URL="http://localhost:8888"
AUTH_TOKEN="${LOCANEXT_TOKEN:-}"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        --auth-token)
            AUTH_TOKEN="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--base-url URL] [--auth-token TOKEN]"
            echo ""
            echo "Options:"
            echo "  --base-url URL      Backend URL (default: http://localhost:8888)"
            echo "  --auth-token TOKEN  Auth token (or set LOCANEXT_TOKEN env var)"
            echo "  -h, --help          Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# --- Counters ---
PASS=0
FAIL=0
WARN=0
TOTAL=0

# --- Helper: test endpoint ---
# Usage: test_endpoint METHOD PATH [BODY]
# Returns: prints table row, updates counters
test_endpoint() {
    local method="$1"
    local path="$2"
    local body="${3:-}"
    local url="${BASE_URL}${path}"
    local status

    TOTAL=$((TOTAL + 1))

    # Build curl command
    local curl_args=(-s -o /dev/null -w "%{http_code}" -X "$method" --max-time 10)

    if [[ -n "$AUTH_TOKEN" ]]; then
        curl_args+=(-H "Authorization: Bearer ${AUTH_TOKEN}")
    fi

    curl_args+=(-H "Content-Type: application/json")

    if [[ -n "$body" ]]; then
        curl_args+=(-d "$body")
    fi

    # Execute request
    status=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo "000")

    # Evaluate result
    local result
    local color
    if [[ "$status" =~ ^[23] ]]; then
        result="PASS"
        color="$GREEN"
        PASS=$((PASS + 1))
    elif [[ "$status" =~ ^4 ]]; then
        # 4xx = endpoint exists but auth/validation issue (acceptable for health check)
        result="WARN"
        color="$YELLOW"
        WARN=$((WARN + 1))
    else
        result="FAIL"
        color="$RED"
        FAIL=$((FAIL + 1))
    fi

    printf "  %-6s %-45s %s ${color}%-6s${NC}\n" "$method" "$path" "$status" "$result"
}

# --- Header ---
echo ""
echo -e "${BOLD}${CYAN}LocaNext API Health Check${NC}"
echo -e "${CYAN}Base URL: ${BASE_URL}${NC}"
echo -e "${CYAN}Token:    ${AUTH_TOKEN:+set}${AUTH_TOKEN:-not set}${NC}"
echo ""
printf "  ${BOLD}%-6s %-45s %-4s %-6s${NC}\n" "METHOD" "ENDPOINT" "CODE" "STATUS"
echo "  --------------------------------------------------------------------------"

# --- Health / Status ---
echo -e "\n  ${BOLD}[ Core ]${NC}"
test_endpoint GET  "/api/health"
test_endpoint GET  "/api/status"
test_endpoint GET  "/api/version/latest"

# --- Auth ---
echo -e "\n  ${BOLD}[ Auth ]${NC}"
test_endpoint POST "/api/auth/login" '{"username":"test","password":"test"}'
test_endpoint GET  "/api/auth/me"

# --- Files ---
echo -e "\n  ${BOLD}[ Files ]${NC}"
test_endpoint GET  "/api/ldm/files"

# --- Rows ---
echo -e "\n  ${BOLD}[ Rows ]${NC}"
test_endpoint GET  "/api/ldm/rows/1"

# --- Search ---
echo -e "\n  ${BOLD}[ Search ]${NC}"
test_endpoint GET  "/api/ldm/search?q=test"

# --- Translation Memory ---
echo -e "\n  ${BOLD}[ Translation Memory ]${NC}"
test_endpoint GET  "/api/ldm/tm/search?q=test"

# --- QA ---
echo -e "\n  ${BOLD}[ QA ]${NC}"
test_endpoint GET  "/api/ldm/qa/run/1"

# --- AI Suggestions ---
echo -e "\n  ${BOLD}[ AI Suggestions ]${NC}"
test_endpoint GET  "/api/ldm/ai-suggestions/test_key"

# --- Gamedata ---
echo -e "\n  ${BOLD}[ Gamedata ]${NC}"
test_endpoint POST "/api/ldm/gamedata/browse" '{"path":"."}'

# --- Codex ---
echo -e "\n  ${BOLD}[ Codex ]${NC}"
test_endpoint GET  "/api/ldm/codex/types"

# --- World Map ---
echo -e "\n  ${BOLD}[ World Map ]${NC}"
test_endpoint GET  "/api/ldm/worldmap/data"

# --- Naming ---
echo -e "\n  ${BOLD}[ Naming ]${NC}"
test_endpoint GET  "/api/ldm/naming/suggest/character?name=test"

# --- Summary ---
echo ""
echo "  --------------------------------------------------------------------------"
echo -e "  ${BOLD}Summary:${NC} ${TOTAL} endpoints tested"
echo -e "    ${GREEN}PASS: ${PASS}${NC}  ${YELLOW}WARN (4xx): ${WARN}${NC}  ${RED}FAIL (5xx/timeout): ${FAIL}${NC}"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
    echo -e "  ${RED}${BOLD}RESULT: FAILED${NC} -- ${FAIL} endpoint(s) returned 5xx or timed out"
    exit 1
else
    echo -e "  ${GREEN}${BOLD}RESULT: PASSED${NC} -- All endpoints responding (${WARN} auth-gated)"
    exit 0
fi
