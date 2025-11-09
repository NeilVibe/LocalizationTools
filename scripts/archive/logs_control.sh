#!/bin/bash
# Log Monitoring Control Center
# Master script for Claude to manage all log monitoring operations
# Usage: ./scripts/logs_control.sh <command>

set -e

PROJECT_ROOT="/home/neil1988/LocalizationTools"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

show_help() {
    echo "=========================================="
    echo "📡 LOG MONITORING CONTROL CENTER"
    echo "=========================================="
    echo ""
    echo "🎯 This is Claude's tool for monitoring the ecosystem"
    echo ""
    echo "Commands:"
    echo ""
    echo "  ${GREEN}fresh${NC}        - Archive old logs and start fresh"
    echo "               (Use before starting new testing session)"
    echo ""
    echo "  ${BLUE}watch${NC}        - Watch logs in real-time (all messages)"
    echo "  ${RED}errors${NC}       - Watch logs in real-time (errors only)"
    echo ""
    echo "  ${YELLOW}analyze${NC}      - Analyze current logs and generate report"
    echo "  ${CYAN}quick${NC}        - Quick error count (no full report)"
    echo ""
    echo "  ${GREEN}status${NC}       - Show current log status"
    echo "  ${BLUE}sessions${NC}     - List all monitoring sessions"
    echo ""
    echo "Examples:"
    echo "  ./scripts/logs_control.sh fresh      # Start clean before testing"
    echo "  ./scripts/logs_control.sh errors     # Monitor errors in real-time"
    echo "  ./scripts/logs_control.sh analyze    # Generate error report"
    echo "  ./scripts/logs_control.sh quick      # Quick error check"
    echo ""
    echo "=========================================="
}

cmd_fresh() {
    echo -e "${CYAN}🧹 Starting fresh monitoring session...${NC}"
    "$SCRIPTS_DIR/archive_logs.sh"
    echo ""
    echo -e "${GREEN}✅ Ready for clean monitoring!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start servers"
    echo "  2. Run: ./scripts/logs_control.sh watch"
    echo "  3. Perform testing"
    echo "  4. Run: ./scripts/logs_control.sh analyze"
}

cmd_watch() {
    echo -e "${BLUE}👀 Starting real-time log monitoring...${NC}"
    echo ""
    "$SCRIPTS_DIR/monitor_logs_realtime.sh"
}

cmd_errors() {
    echo -e "${RED}🔥 Monitoring ERRORS ONLY...${NC}"
    echo ""
    "$SCRIPTS_DIR/monitor_logs_realtime.sh" --errors-only
}

cmd_analyze() {
    echo -e "${YELLOW}📊 Analyzing logs...${NC}"
    echo ""
    "$SCRIPTS_DIR/analyze_logs.sh"
}

cmd_quick() {
    echo "=========================================="
    echo "⚡ QUICK ERROR CHECK"
    echo "=========================================="
    echo ""

    SERVER_LOG="$PROJECT_ROOT/server/data/logs/server.log"
    ERROR_LOG="$PROJECT_ROOT/server/data/logs/error.log"

    if [ ! -f "$SERVER_LOG" ]; then
        echo -e "${RED}❌ No server logs found${NC}"
        exit 1
    fi

    CRITICAL=$(grep -ci "CRITICAL" "$SERVER_LOG" 2>/dev/null || echo "0")
    ERRORS=$(grep -ci "ERROR" "$SERVER_LOG" 2>/dev/null || echo "0")
    WARNINGS=$(grep -ci "WARNING" "$SERVER_LOG" 2>/dev/null || echo "0")
    TOTAL=$(wc -l < "$SERVER_LOG")

    echo "📊 Current Log Status:"
    echo ""

    if [ "$CRITICAL" -gt 0 ]; then
        echo -e "  ${RED}🔥 CRITICAL: $CRITICAL${NC}"
    else
        echo -e "  ${GREEN}🔥 CRITICAL: 0${NC}"
    fi

    if [ "$ERRORS" -gt 0 ]; then
        echo -e "  ${RED}❌ ERRORS:   $ERRORS${NC}"
    else
        echo -e "  ${GREEN}❌ ERRORS:   0${NC}"
    fi

    if [ "$WARNINGS" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️  WARNINGS: $WARNINGS${NC}"
    else
        echo -e "  ${GREEN}⚠️  WARNINGS: 0${NC}"
    fi

    echo "  📝 Total lines: $TOTAL"
    echo ""

    if [ "$CRITICAL" -gt 0 ] || [ "$ERRORS" -gt 0 ]; then
        echo -e "${RED}⚠️  ERRORS FOUND! Run './scripts/logs_control.sh analyze' for details${NC}"
        echo ""
        echo "Recent errors:"
        grep -i "ERROR\|CRITICAL" "$SERVER_LOG" | grep -v "^  " | tail -5
        exit 1
    else
        echo -e "${GREEN}✅ ALL CLEAR! No errors found.${NC}"
        exit 0
    fi
}

cmd_status() {
    echo "=========================================="
    echo "📊 LOG STATUS"
    echo "=========================================="
    echo ""

    SERVER_LOG="$PROJECT_ROOT/server/data/logs/server.log"
    ERROR_LOG="$PROJECT_ROOT/server/data/logs/error.log"

    if [ -f "$SERVER_LOG" ]; then
        SIZE=$(du -h "$SERVER_LOG" | cut -f1)
        LINES=$(wc -l < "$SERVER_LOG")
        MODIFIED=$(stat -c %y "$SERVER_LOG" | cut -d'.' -f1)
        echo "📄 Server Log:"
        echo "   File: $SERVER_LOG"
        echo "   Size: $SIZE ($LINES lines)"
        echo "   Modified: $MODIFIED"
    else
        echo "❌ No server.log found"
    fi

    echo ""

    if [ -f "$ERROR_LOG" ]; then
        SIZE=$(du -h "$ERROR_LOG" | cut -f1)
        LINES=$(wc -l < "$ERROR_LOG")
        MODIFIED=$(stat -c %y "$ERROR_LOG" | cut -d'.' -f1)
        echo "📄 Error Log:"
        echo "   File: $ERROR_LOG"
        echo "   Size: $SIZE ($LINES lines)"
        echo "   Modified: $MODIFIED"
    else
        echo "❌ No error.log found"
    fi

    echo ""
    echo "📁 Archives: $(ls -1 $PROJECT_ROOT/logs/archive 2>/dev/null | wc -l) sessions"
    echo "📁 Session Logs: $(ls -1 $PROJECT_ROOT/logs/sessions 2>/dev/null | wc -l) files"
    echo "📁 Reports: $(ls -1 $PROJECT_ROOT/logs/reports 2>/dev/null | wc -l) files"
    echo ""
}

cmd_sessions() {
    echo "=========================================="
    echo "📋 MONITORING SESSIONS"
    echo "=========================================="
    echo ""

    ARCHIVE_DIR="$PROJECT_ROOT/logs/archive"

    if [ -d "$ARCHIVE_DIR" ] && [ "$(ls -A $ARCHIVE_DIR)" ]; then
        echo "Archived sessions:"
        ls -lt "$ARCHIVE_DIR" | grep '^d' | awk '{print "  📦", $9, "("$6, $7, $8")"}'
    else
        echo "No archived sessions found"
    fi

    echo ""

    SESSION_DIR="$PROJECT_ROOT/logs/sessions"

    if [ -d "$SESSION_DIR" ] && [ "$(ls -A $SESSION_DIR)" ]; then
        echo "Active session logs:"
        ls -lt "$SESSION_DIR" | grep '^-' | awk '{print "  📝", $9, "("$5" bytes)"}'
    else
        echo "No active session logs"
    fi

    echo ""
}

# Main command dispatcher
case "${1:-help}" in
    fresh)    cmd_fresh ;;
    watch)    cmd_watch ;;
    errors)   cmd_errors ;;
    analyze)  cmd_analyze ;;
    quick)    cmd_quick ;;
    status)   cmd_status ;;
    sessions) cmd_sessions ;;
    help|--help|-h) show_help ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
