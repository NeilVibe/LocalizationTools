#!/bin/bash
# Analyze Logs - Generate Error Report
# Usage: ./scripts/analyze_logs.sh [--session SESSION_ID]

set -e

PROJECT_ROOT="/home/neil1988/LocalizationTools"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Parse options
SESSION_ID=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --session) SESSION_ID="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "=========================================="
echo "📊 LOG ANALYSIS"
echo "=========================================="
echo "Timestamp: $TIMESTAMP"
echo ""

# Determine which logs to analyze
if [ -n "$SESSION_ID" ]; then
    echo "🔍 Analyzing session: $SESSION_ID"
    SERVER_LOG="$PROJECT_ROOT/logs/sessions/session_${SESSION_ID}.log"
    if [ ! -f "$SERVER_LOG" ]; then
        echo "❌ Session log not found: $SERVER_LOG"
        exit 1
    fi
    ERROR_LOG="$SERVER_LOG"
else
    echo "🔍 Analyzing current logs"
    SERVER_LOG="$PROJECT_ROOT/server/data/logs/server.log"
    ERROR_LOG="$PROJECT_ROOT/server/data/logs/error.log"
fi

# Check if log files exist
if [ ! -f "$SERVER_LOG" ]; then
    echo "❌ Server log not found: $SERVER_LOG"
    exit 1
fi

REPORT_FILE="$PROJECT_ROOT/logs/reports/error_report_${TIMESTAMP}.md"

echo "📝 Generating report: $REPORT_FILE"
echo ""

# Generate report
cat > "$REPORT_FILE" << EOF
# Log Analysis Report
**Generated**: $(date)
**Analyzed Files**:
- Server Log: $SERVER_LOG
- Error Log: $ERROR_LOG

---

## 📊 SUMMARY

EOF

# Count log levels
CRITICAL_COUNT=$(grep -ci "CRITICAL" "$SERVER_LOG" 2>/dev/null || echo "0")
ERROR_COUNT=$(grep -ci "ERROR" "$SERVER_LOG" 2>/dev/null || echo "0")
WARNING_COUNT=$(grep -ci "WARNING" "$SERVER_LOG" 2>/dev/null || echo "0")
SUCCESS_COUNT=$(grep -ci "SUCCESS" "$SERVER_LOG" 2>/dev/null || echo "0")
TOTAL_LINES=$(wc -l < "$SERVER_LOG")

cat >> "$REPORT_FILE" << EOF
| Level | Count |
|-------|-------|
| 🔥 CRITICAL | $CRITICAL_COUNT |
| ❌ ERROR | $ERROR_COUNT |
| ⚠️ WARNING | $WARNING_COUNT |
| ✅ SUCCESS | $SUCCESS_COUNT |
| 📝 Total Lines | $TOTAL_LINES |

**Error Rate**: $(awk "BEGIN {printf \"%.2f\", ($ERROR_COUNT + $CRITICAL_COUNT) / $TOTAL_LINES * 100}")%

---

## 🚨 CRITICAL ERRORS

EOF

# Extract unique critical errors
if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "### Found $CRITICAL_COUNT CRITICAL errors" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -i "CRITICAL" "$SERVER_LOG" | grep -v "^  " | head -20 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"
else
    echo "✅ No critical errors found!" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## ❌ ERRORS

EOF

# Extract unique errors (excluding stack traces)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "### Found $ERROR_COUNT errors" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -i "ERROR" "$SERVER_LOG" | grep -v "^  " | grep -v "CRITICAL" | head -30 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"

    # Group errors by type
    echo "" >> "$REPORT_FILE"
    echo "### Error Breakdown by Type" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -i "ERROR" "$SERVER_LOG" | grep -v "^  " | cut -d'|' -f4- | sort | uniq -c | sort -rn | head -10 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"
else
    echo "✅ No errors found!" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## ⚠️ WARNINGS

EOF

# Extract warnings
if [ "$WARNING_COUNT" -gt 0 ]; then
    echo "### Found $WARNING_COUNT warnings" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -i "WARNING" "$SERVER_LOG" | grep -v "^  " | head -20 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"

    # Group warnings by type
    echo "" >> "$REPORT_FILE"
    echo "### Warning Breakdown by Type" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -i "WARNING" "$SERVER_LOG" | grep -v "^  " | cut -d'|' -f4- | sort | uniq -c | sort -rn | head -10 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"
else
    echo "✅ No warnings found!" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## 🔍 SPECIFIC ERROR ANALYSIS

EOF

# Analyze specific error types
echo "### Database Errors" >> "$REPORT_FILE"
DB_ERRORS=$(grep -i "database\|sql\|transaction\|foreign key" "$SERVER_LOG" | grep -i "error\|exception" | wc -l)
if [ "$DB_ERRORS" -gt 0 ]; then
    echo "Found $DB_ERRORS database-related errors:" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -i "database\|sql\|transaction\|foreign key" "$SERVER_LOG" | grep -i "error\|exception" | grep -v "^  " | head -10 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"
else
    echo "✅ No database errors" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "### Authentication Errors" >> "$REPORT_FILE"
AUTH_ERRORS=$(grep -i "auth\|login\|token" "$SERVER_LOG" | grep -i "error\|fail" | wc -l)
if [ "$AUTH_ERRORS" -gt 0 ]; then
    echo "Found $AUTH_ERRORS authentication-related errors:" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -i "auth\|login\|token" "$SERVER_LOG" | grep -i "error\|fail" | grep -v "^  " | head -10 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"
else
    echo "✅ No authentication errors" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "### API Endpoint Errors" >> "$REPORT_FILE"
API_ERRORS=$(grep -E "4[0-9]{2}|5[0-9]{2}" "$SERVER_LOG" | wc -l)
if [ "$API_ERRORS" -gt 0 ]; then
    echo "Found $API_ERRORS API errors (4xx/5xx status codes):" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    grep -E "← (4[0-9]{2}|5[0-9]{2})" "$SERVER_LOG" | head -20 >> "$REPORT_FILE" 2>/dev/null || true
    echo '```' >> "$REPORT_FILE"
else
    echo "✅ No API errors" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## 🎯 ACTION ITEMS

EOF

# Generate action items based on findings
if [ "$CRITICAL_COUNT" -gt 0 ] || [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️ **IMMEDIATE ACTION REQUIRED**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    if [ "$CRITICAL_COUNT" -gt 0 ]; then
        echo "- [ ] Fix $CRITICAL_COUNT CRITICAL errors (highest priority)" >> "$REPORT_FILE"
    fi

    if [ "$DB_ERRORS" -gt 0 ]; then
        echo "- [ ] Fix $DB_ERRORS database errors" >> "$REPORT_FILE"
    fi

    if [ "$AUTH_ERRORS" -gt 0 ]; then
        echo "- [ ] Fix $AUTH_ERRORS authentication errors" >> "$REPORT_FILE"
    fi

    if [ "$API_ERRORS" -gt 0 ]; then
        echo "- [ ] Fix $API_ERRORS API endpoint errors" >> "$REPORT_FILE"
    fi

    echo "" >> "$REPORT_FILE"
    echo "**Cannot proceed to Phase 4 until all errors are resolved!**" >> "$REPORT_FILE"
else
    echo "✅ **ALL CLEAR!**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "No critical errors or errors found. System is ready for Phase 4." >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## 📈 RECOMMENDATIONS

EOF

# Performance recommendations
AVG_DURATION=$(grep "Duration:" "$SERVER_LOG" | grep -oP "Duration: \K[0-9.]+" | awk '{sum+=$1; count+=1} END {if(count>0) print sum/count; else print 0}')
SLOW_REQUESTS=$(grep "Duration:" "$SERVER_LOG" | grep -oP "Duration: \K[0-9.]+" | awk '$1 > 1000 {count+=1} END {print count+0}')

echo "- Average request duration: ${AVG_DURATION}ms" >> "$REPORT_FILE"
echo "- Slow requests (>1000ms): $SLOW_REQUESTS" >> "$REPORT_FILE"

if [ "${AVG_DURATION%.*}" -gt 100 ]; then
    echo "- ⚠️ Average response time is high (>${AVG_DURATION}ms). Consider optimization." >> "$REPORT_FILE"
else
    echo "- ✅ Response times are acceptable (<100ms average)" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "*Report generated by: scripts/analyze_logs.sh*" >> "$REPORT_FILE"

# Display summary
echo "=========================================="
echo "✅ ANALYSIS COMPLETE"
echo "=========================================="
echo ""
echo "📊 Summary:"
echo "  🔥 CRITICAL: $CRITICAL_COUNT"
echo "  ❌ ERROR:    $ERROR_COUNT"
echo "  ⚠️  WARNING:  $WARNING_COUNT"
echo "  ✅ SUCCESS:  $SUCCESS_COUNT"
echo ""
echo "📝 Full report saved to:"
echo "   $REPORT_FILE"
echo ""
echo "To view report:"
echo "   cat $REPORT_FILE"
echo "=========================================="

# Also display the report
cat "$REPORT_FILE"
