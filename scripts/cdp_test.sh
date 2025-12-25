#!/bin/bash
# ============================================================================
# CDP TEST RUNNER - Secure Local Testing
# ============================================================================
# Purpose: Run CDP tests with local credentials
# Usage: ./scripts/cdp_test.sh [test_name]
#
# Examples:
#   ./scripts/cdp_test.sh login        # Run login.js
#   ./scripts/cdp_test.sh quick_check  # Run quick_check.js
#   ./scripts/cdp_test.sh              # Run all tests
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CDP_DIR="$PROJECT_ROOT/testing_toolkit/cdp"

# Load local credentials (REQUIRED)
if [ -f "$PROJECT_ROOT/.env.local" ]; then
    set -a
    source "$PROJECT_ROOT/.env.local"
    set +a
else
    echo "ERROR: .env.local not found!"
    echo "Create it with:"
    echo "  CDP_TEST_USER=your_username"
    echo "  CDP_TEST_PASS=your_password"
    exit 1
fi

# Verify credentials are set
if [ -z "$CDP_TEST_USER" ] || [ -z "$CDP_TEST_PASS" ]; then
    echo "ERROR: CDP_TEST_USER and CDP_TEST_PASS must be set in .env.local"
    exit 1
fi

echo "============================================"
echo "  CDP TEST RUNNER (Local)"
echo "============================================"
echo "User: $CDP_TEST_USER"
echo "CDP Dir: $CDP_DIR"
echo ""

# Get Windows node.exe path
NODE_WIN="/mnt/c/Program Files/nodejs/node.exe"

if [ ! -f "$NODE_WIN" ]; then
    echo "ERROR: Node.js not found at $NODE_WIN"
    exit 1
fi

# Run specified test or all tests
TEST_NAME="${1:-all}"

cd "$CDP_DIR"

case "$TEST_NAME" in
    login)
        echo "Running login.js..."
        "$NODE_WIN" login.js
        ;;
    quick_check)
        echo "Running quick_check.js..."
        "$NODE_WIN" quick_check.js
        ;;
    server_status)
        echo "Running test_server_status.js..."
        "$NODE_WIN" test_server_status.js
        ;;
    all)
        echo "Running all tests..."
        echo ""
        echo "=== LOGIN ==="
        "$NODE_WIN" login.js
        echo ""
        echo "=== QUICK CHECK ==="
        "$NODE_WIN" quick_check.js
        echo ""
        echo "=== SERVER STATUS ==="
        "$NODE_WIN" test_server_status.js
        ;;
    *)
        # Run custom test file
        if [ -f "${TEST_NAME}.js" ]; then
            echo "Running ${TEST_NAME}.js..."
            "$NODE_WIN" "${TEST_NAME}.js"
        elif [ -f "$TEST_NAME" ]; then
            echo "Running $TEST_NAME..."
            "$NODE_WIN" "$TEST_NAME"
        else
            echo "ERROR: Test not found: $TEST_NAME"
            echo "Available: login, quick_check, server_status, all"
            exit 1
        fi
        ;;
esac

echo ""
echo "============================================"
echo "  CDP TEST COMPLETE"
echo "============================================"
