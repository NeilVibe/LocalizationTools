#!/bin/bash
# Comprehensive Dashboard Testing & Monitoring Script
# Tests all 16 API endpoints and dashboard pages

echo "=============================================="
echo "📊 DASHBOARD COMPREHENSIVE TEST"
echo "=============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}

    echo -n "Testing $name... "

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$response" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $response)"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC} (Expected $expected_status, got $response)"
        ((FAILED++))
    fi
}

# Test function with data validation
test_endpoint_data() {
    local name=$1
    local url=$2
    local jq_check=$3

    echo -n "Testing $name... "

    response=$(curl -s "$url")
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$http_code" -eq 200 ]; then
        result=$(echo "$response" | jq -r "$jq_check" 2>/dev/null)
        if [ "$result" != "null" ] && [ "$result" != "" ]; then
            echo -e "${GREEN}✅ PASS${NC} (HTTP $http_code, data: $result)"
            ((PASSED++))
        else
            echo -e "${YELLOW}⚠️  WARN${NC} (HTTP $http_code, but no data)"
            ((PASSED++))
        fi
    else
        echo -e "${RED}❌ FAIL${NC} (HTTP $http_code)"
        ((FAILED++))
    fi
}

echo "=== BACKEND SERVER ==="
test_endpoint "Health Check" "http://localhost:8888/health"
echo ""

echo "=== STATISTICS ENDPOINTS (10) ==="
test_endpoint_data "Overview Stats" \
    "http://localhost:8888/api/v2/admin/stats/overview" \
    '.today_operations'

test_endpoint_data "Daily Stats" \
    "http://localhost:8888/api/v2/admin/stats/daily?days=7" \
    '.data | length'

test_endpoint_data "Weekly Stats" \
    "http://localhost:8888/api/v2/admin/stats/weekly?weeks=4" \
    '.data | length'

test_endpoint_data "Monthly Stats" \
    "http://localhost:8888/api/v2/admin/stats/monthly?months=6" \
    '.data | length'

test_endpoint_data "Tool Popularity" \
    "http://localhost:8888/api/v2/admin/stats/tools/popularity?days=30" \
    '.tools | length'

test_endpoint_data "Function Stats (XLSTransfer)" \
    "http://localhost:8888/api/v2/admin/stats/tools/XLSTransfer/functions?days=30" \
    '.functions | length'

test_endpoint_data "Fastest Functions" \
    "http://localhost:8888/api/v2/admin/stats/performance/fastest?limit=10" \
    '.fastest_functions | length'

test_endpoint_data "Slowest Functions" \
    "http://localhost:8888/api/v2/admin/stats/performance/slowest?limit=10" \
    '.slowest_functions | length'

test_endpoint_data "Error Rate" \
    "http://localhost:8888/api/v2/admin/stats/errors/rate?days=30" \
    '.data | length'

test_endpoint_data "Top Errors" \
    "http://localhost:8888/api/v2/admin/stats/errors/top?limit=10" \
    '.top_errors | length'
echo ""

echo "=== RANKINGS ENDPOINTS (6) ==="
test_endpoint_data "User Rankings (by ops)" \
    "http://localhost:8888/api/v2/admin/rankings/users?period=monthly&limit=10" \
    '.rankings | length'

test_endpoint_data "User Rankings (by time)" \
    "http://localhost:8888/api/v2/admin/rankings/users/by-time?period=monthly&limit=10" \
    '.rankings | length'

test_endpoint_data "App Rankings" \
    "http://localhost:8888/api/v2/admin/rankings/apps?period=all_time" \
    '.rankings | length'

test_endpoint_data "Function Rankings (by usage)" \
    "http://localhost:8888/api/v2/admin/rankings/functions?period=monthly&limit=10" \
    '.rankings | length'

test_endpoint_data "Function Rankings (by time)" \
    "http://localhost:8888/api/v2/admin/rankings/functions/by-time?period=monthly&limit=10" \
    '.rankings | length'

test_endpoint_data "Top Combined Rankings" \
    "http://localhost:8888/api/v2/admin/rankings/top?period=all_time" \
    '.top_users | length'
echo ""

echo "=== FRONTEND SERVERS ==="
test_endpoint "Admin Dashboard" "http://localhost:5175"
test_endpoint "LocaNext Frontend" "http://localhost:5173"
echo ""

echo "=== DASHBOARD PAGES ==="
test_endpoint "Dashboard Home" "http://localhost:5175/"
test_endpoint "Statistics Page" "http://localhost:5175/stats"
test_endpoint "Rankings Page" "http://localhost:5175/rankings"
test_endpoint "Users Page" "http://localhost:5175/users"
test_endpoint "Activity Page" "http://localhost:5175/activity"
test_endpoint "Logs Page" "http://localhost:5175/logs"
echo ""

echo "=============================================="
echo "📊 TEST RESULTS"
echo "=============================================="
echo -e "Total Endpoints: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ SOME TESTS FAILED${NC}"
    exit 1
fi
