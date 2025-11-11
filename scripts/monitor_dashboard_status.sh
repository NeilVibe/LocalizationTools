#!/bin/bash
# Dashboard Status Monitor - Quick Health Check

cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║              DASHBOARD STATUS MONITOR                        ║
╚══════════════════════════════════════════════════════════════╝

🖥️  SERVERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# Check Backend
BACKEND_STATUS=$(curl -s http://localhost:8888/health 2>/dev/null | jq -r '.status' 2>/dev/null || echo "down")
if [ "$BACKEND_STATUS" = "healthy" ]; then
    echo "✅ Backend Server:      http://localhost:8888 ($BACKEND_STATUS)"
else
    echo "❌ Backend Server:      http://localhost:8888 (NOT RESPONDING)"
fi

# Check Admin Dashboard
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5175 2>/dev/null)
if [ "$DASHBOARD_STATUS" = "200" ]; then
    echo "✅ Admin Dashboard:     http://localhost:5175 (HTTP $DASHBOARD_STATUS)"
else
    echo "❌ Admin Dashboard:     http://localhost:5175 (HTTP $DASHBOARD_STATUS)"
fi

# Check LocaNext
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>/dev/null)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ LocaNext Frontend:   http://localhost:5173 (HTTP $FRONTEND_STATUS)"
else
    echo "❌ LocaNext Frontend:   http://localhost:5173 (HTTP $FRONTEND_STATUS)"
fi

cat << 'EOF'

📊 QUICK API TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# Test a few key endpoints
OVERVIEW=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/api/v2/admin/stats/overview 2>/dev/null)
DAILY=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/api/v2/admin/stats/daily?days=7 2>/dev/null)
RANKINGS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8888/api/v2/admin/rankings/users?period=monthly&limit=5" 2>/dev/null)

[ "$OVERVIEW" = "200" ] && echo "✅ Overview Stats:      HTTP $OVERVIEW" || echo "❌ Overview Stats:      HTTP $OVERVIEW"
[ "$DAILY" = "200" ] && echo "✅ Daily Stats:         HTTP $DAILY" || echo "❌ Daily Stats:         HTTP $DAILY"
[ "$RANKINGS" = "200" ] && echo "✅ User Rankings:       HTTP $RANKINGS" || echo "❌ User Rankings:       HTTP $RANKINGS"

cat << 'EOF'

🎨 FRONTEND PAGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# Test dashboard pages
for page in "" "stats" "rankings"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5175/${page}" 2>/dev/null)
  name=$([ -z "$page" ] && echo "Home" || echo "${page^}")
  [ "$status" = "200" ] && echo "✅ $name:               HTTP $status" || echo "❌ $name:               HTTP $status"
done

cat << 'EOF'

📋 RECENT ACTIVITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

# Show recent API requests
if [ -f "/tmp/server_test.log" ]; then
    echo "Last 3 API requests:"
    tail -50 /tmp/server_test.log 2>/dev/null | grep "→" | tail -3 | sed 's/^/  /'
else
    echo "  No recent activity logs found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Run 'bash scripts/test_dashboard_full.sh' for comprehensive testing"
echo ""
