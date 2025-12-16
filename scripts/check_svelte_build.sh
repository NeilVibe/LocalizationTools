#!/bin/bash
# P35: Svelte 5 Build Health Check
# Checks for critical warnings that indicate broken reactivity
#
# Usage: ./scripts/check_svelte_build.sh
#
# Exit codes:
#   0 = Build passed, no critical warnings
#   1 = Critical warnings found (build will likely have bugs)

set -e

echo "=== P35: Svelte 5 Build Health Check ==="
echo ""

cd "$(dirname "$0")/../locaNext"

# Run build and capture output
echo "Building frontend..."
BUILD_OUTPUT=$(npm run build 2>&1)
BUILD_EXIT=$?

# Check for critical warnings that cause reactivity bugs
# These are the warnings that caused BUG-011
CRITICAL_WARNINGS=(
    "non_reactive_update"
    "Changing its value will not correctly trigger updates"
)

FOUND_CRITICAL=0
for pattern in "${CRITICAL_WARNINGS[@]}"; do
    if echo "$BUILD_OUTPUT" | grep -q "$pattern"; then
        echo "[CRITICAL] Found: $pattern"
        echo "$BUILD_OUTPUT" | grep -B2 -A2 "$pattern" | head -20
        FOUND_CRITICAL=1
    fi
done

# Report results
echo ""
echo "=== Build Health Summary ==="
if [ $BUILD_EXIT -ne 0 ]; then
    echo "[FAIL] Build failed with exit code $BUILD_EXIT"
    exit 1
fi

if [ $FOUND_CRITICAL -eq 1 ]; then
    echo "[FAIL] Critical Svelte 5 reactivity warnings found!"
    echo ""
    echo "These warnings indicate state variables that won't trigger UI updates."
    echo "See P35_SVELTE5_MIGRATION.md for fix instructions."
    echo ""
    echo "Fix: Convert 'let x = value;' to 'let x = \$state(value);'"
    exit 1
fi

# Check for deprecation warnings (non-critical but worth noting)
DEPRECATED_COUNT=$(echo "$BUILD_OUTPUT" | grep -c "event_directive_deprecated" || true)
UNUSED_CSS_COUNT=$(echo "$BUILD_OUTPUT" | grep -c "css_unused_selector" || true)
A11Y_COUNT=$(echo "$BUILD_OUTPUT" | grep -c "a11y_" || true)

echo "[PASS] No critical reactivity warnings found"
echo ""
echo "Non-critical warnings (for future cleanup):"
echo "  - Event syntax deprecations: $DEPRECATED_COUNT"
echo "  - Unused CSS selectors: $UNUSED_CSS_COUNT"
echo "  - Accessibility hints: $A11Y_COUNT"
echo ""
echo "[OK] Svelte 5 build health check passed"
exit 0
