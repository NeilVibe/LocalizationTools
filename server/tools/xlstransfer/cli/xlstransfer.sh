#!/bin/bash
# XLSTransfer CLI wrapper script
# Automatically sets PYTHONPATH and calls the Python CLI

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Set PYTHONPATH to project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Call the Python CLI with all arguments
exec python3 "$SCRIPT_DIR/xlstransfer_cli.py" "$@"
