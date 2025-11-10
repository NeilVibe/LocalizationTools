#!/bin/bash
# Clean and Archive Logs
# Archives old logs with timestamp and starts fresh
# Run this before starting new Claude sessions to avoid confusion

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_DIR="/home/neil1988/LocalizationTools/logs/archive/${TIMESTAMP}"
LOG_DIR="/home/neil1988/LocalizationTools/server/data/logs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              LOG CLEANING & ARCHIVAL TOOL                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Create archive directory
mkdir -p "$ARCHIVE_DIR"
echo -e "${BLUE}[ARCHIVE]${NC} Created archive directory: $ARCHIVE_DIR"
echo ""

# Function to archive and clean a log file
archive_log() {
    local log_file=$1
    local log_name=$(basename "$log_file")

    if [ -f "$log_file" ]; then
        local size=$(wc -l < "$log_file" 2>/dev/null || echo "0")

        if [ "$size" -gt 0 ]; then
            # Archive the old log
            cp "$log_file" "$ARCHIVE_DIR/$log_name"
            echo -e "${GREEN}✓${NC} Archived $log_name (${size} lines) → archive/${TIMESTAMP}/"

            # Clear and add marker
            echo "# Log cleaned and reset: $(date '+%Y-%m-%d %H:%M:%S')" > "$log_file"
            echo "# Previous logs archived to: logs/archive/${TIMESTAMP}/" >> "$log_file"
            echo "# " >> "$log_file"

            echo -e "${YELLOW}✓${NC} Reset $log_name (added clean marker)"
        else
            echo -e "${BLUE}○${NC} Skipped $log_name (empty)"
        fi
    else
        echo -e "${YELLOW}○${NC} Not found: $log_file"
    fi
}

echo "Archiving backend logs..."
echo "─────────────────────────────────────────────────────────────"
archive_log "$LOG_DIR/error.log"
archive_log "$LOG_DIR/server.log"
archive_log "/home/neil1988/LocalizationTools/server_output.log"

echo ""
echo "Archiving frontend logs..."
echo "─────────────────────────────────────────────────────────────"
archive_log "/home/neil1988/LocalizationTools/logs/locanext_error.log"
archive_log "/home/neil1988/LocalizationTools/logs/locanext_app.log"

echo ""
echo "Archiving other logs..."
echo "─────────────────────────────────────────────────────────────"
archive_log "/home/neil1988/LocalizationTools/logs/dashboard_app.log"
archive_log "/home/neil1988/LocalizationTools/logs/dashboard_error.log"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   CLEANUP COMPLETE                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Archive location:${NC} $ARCHIVE_DIR"
echo ""
echo "Next steps:"
echo "  1. Old logs are safely archived"
echo "  2. Current logs now have clean slate"
echo "  3. Each log has a marker showing when it was cleaned"
echo "  4. Future Claude sessions won't be confused by old errors"
echo ""

# Show archive summary
echo "Archive summary:"
ls -lh "$ARCHIVE_DIR" 2>/dev/null | tail -n +2 | awk '{printf "  • %-30s %8s\n", $9, $5}'
echo ""
