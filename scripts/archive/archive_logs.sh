#!/bin/bash
# Archive Old Logs - Clean Slate for New Monitoring Session
# Usage: ./scripts/archive_logs.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROJECT_ROOT="/home/neil1988/LocalizationTools"
ARCHIVE_DIR="$PROJECT_ROOT/logs/archive/$TIMESTAMP"

echo "=========================================="
echo "🗄️  ARCHIVING OLD LOGS"
echo "=========================================="
echo "Timestamp: $TIMESTAMP"
echo "Archive Location: $ARCHIVE_DIR"
echo ""

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Archive backend server logs
if [ -f "$PROJECT_ROOT/server/data/logs/server.log" ]; then
    SIZE=$(du -h "$PROJECT_ROOT/server/data/logs/server.log" | cut -f1)
    LINES=$(wc -l < "$PROJECT_ROOT/server/data/logs/server.log")
    echo "📄 Backend server.log: $SIZE ($LINES lines)"
    mv "$PROJECT_ROOT/server/data/logs/server.log" "$ARCHIVE_DIR/backend_server.log"
else
    echo "⚠️  No server.log found"
fi

if [ -f "$PROJECT_ROOT/server/data/logs/error.log" ]; then
    SIZE=$(du -h "$PROJECT_ROOT/server/data/logs/error.log" | cut -f1)
    LINES=$(wc -l < "$PROJECT_ROOT/server/data/logs/error.log")
    echo "📄 Backend error.log: $SIZE ($LINES lines)"
    mv "$PROJECT_ROOT/server/data/logs/error.log" "$ARCHIVE_DIR/backend_error.log"
else
    echo "⚠️  No error.log found"
fi

# Archive session logs if any
if [ -d "$PROJECT_ROOT/logs/sessions" ] && [ "$(ls -A $PROJECT_ROOT/logs/sessions)" ]; then
    echo "📄 Archiving session logs..."
    mv "$PROJECT_ROOT/logs/sessions"/* "$ARCHIVE_DIR/" 2>/dev/null || true
fi

# Create fresh log files
touch "$PROJECT_ROOT/server/data/logs/server.log"
touch "$PROJECT_ROOT/server/data/logs/error.log"

echo ""
echo "✅ Logs archived to: $ARCHIVE_DIR"
echo "✅ Fresh log files created"
echo ""
echo "🎯 You can now start monitoring with CLEAN logs!"
echo "   All future logs will be from THIS session only."
echo ""
echo "To view archived logs:"
echo "   cat $ARCHIVE_DIR/backend_server.log"
echo "   cat $ARCHIVE_DIR/backend_error.log"
echo "=========================================="
