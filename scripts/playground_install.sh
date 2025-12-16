#!/bin/bash
# ============================================================================
# AUTONOMOUS PLAYGROUND INSTALL - WSL Wrapper
# ============================================================================
# Purpose: Run Playground installation from WSL
# Usage: ./scripts/playground_install.sh [options]
#
# Options:
#   --launch       Launch app after install with CDP
#   --skip-clean   Don't clean Playground first
#   --cdp-port PORT  CDP port (default: 9222)
#   --auto-login   Auto-login as neil/neil after First Time Setup
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Convert WSL path to Windows path
SCRIPT_WIN_PATH=$(wslpath -w "$SCRIPT_DIR/playground_install.ps1")

echo "============================================"
echo "  AUTONOMOUS PLAYGROUND INSTALL (WSL)"
echo "============================================"
echo ""

# Parse arguments
LAUNCH_FLAG=""
SKIP_CLEAN_FLAG=""
AUTO_LOGIN_FLAG=""
CDP_PORT="9222"

while [[ $# -gt 0 ]]; do
    case $1 in
        --launch)
            LAUNCH_FLAG="-LaunchAfterInstall -EnableCDP"
            shift
            ;;
        --skip-clean)
            SKIP_CLEAN_FLAG="-SkipClean"
            shift
            ;;
        --cdp-port)
            CDP_PORT="$2"
            shift 2
            ;;
        --auto-login)
            AUTO_LOGIN_FLAG="-AutoLogin"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Running PowerShell script..."
echo ""

# Run PowerShell script via powershell.exe
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -ExecutionPolicy Bypass -File "$SCRIPT_WIN_PATH" $LAUNCH_FLAG $SKIP_CLEAN_FLAG $AUTO_LOGIN_FLAG -CDPPort $CDP_PORT

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "  WSL: Installation completed successfully"
    echo "============================================"

    # Show Playground contents
    PLAYGROUND="/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground"
    if [ -d "$PLAYGROUND/LocaNext" ]; then
        echo ""
        echo "Playground contents:"
        ls -la "$PLAYGROUND/LocaNext/" | head -10
        echo ""
        echo "App size: $(du -sh "$PLAYGROUND/LocaNext" | cut -f1)"
    fi
else
    echo ""
    echo "============================================"
    echo "  WSL: Installation FAILED (exit code: $EXIT_CODE)"
    echo "============================================"
fi

exit $EXIT_CODE
