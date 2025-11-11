#!/bin/bash
# Monitor FRONTEND errors from browser console
# These are sent to backend via remote-logger.js

echo "=========================================="
echo "📱 FRONTEND ERROR MONITOR"
echo "=========================================="
echo "Monitoring browser console errors sent to backend..."
echo "Press Ctrl+C to stop"
echo ""

# Get initial line count
LOGFILE="server/data/logs/server.log"
LAST_LINE=$(wc -l < "$LOGFILE")

echo "Watching for frontend errors..."
echo ""

while true; do
    CURRENT_LINE=$(wc -l < "$LOGFILE")

    if [ "$CURRENT_LINE" -gt "$LAST_LINE" ]; then
        # New lines added
        NEW_LINES=$((CURRENT_LINE - LAST_LINE))

        # Check for frontend errors in new lines
        tail -n "$NEW_LINES" "$LOGFILE" | grep "\[FRONTEND\]" | while read -r line; do
            TIMESTAMP=$(date '+%H:%M:%S')

            # Color code by type
            if echo "$line" | grep -q "ERROR"; then
                echo -e "\033[0;31m[$TIMESTAMP] FRONTEND ERROR:\033[0m"
                echo "$line" | grep -oP "DATA: \K.*"
            elif echo "$line" | grep -q "WARNING"; then
                echo -e "\033[1;33m[$TIMESTAMP] FRONTEND WARNING:\033[0m"
                echo "$line" | grep -oP "DATA: \K.*"
            else
                echo -e "\033[0;36m[$TIMESTAMP] FRONTEND INFO:\033[0m"
                echo "$line" | grep -oP "DATA: \K.*"
            fi
            echo ""
        done

        LAST_LINE=$CURRENT_LINE
    fi

    sleep 0.5
done
