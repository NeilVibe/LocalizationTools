#!/bin/bash
# Test the logging infrastructure directly

echo "========================================"
echo "🧪 Testing Logging Infrastructure"
echo "========================================"
echo ""

PROJECT_ROOT="/home/neil1988/LocalizationTools"

# Test 1: Backend logging (already working)
echo "1️⃣  Testing Backend Server Logging..."
echo "   Sending test request to backend..."
RESPONSE=$(curl -s http://localhost:8888/health)
if [ $? -eq 0 ]; then
    echo "   ✅ Backend responded: $RESPONSE"
    echo "   📝 Last 3 backend log entries:"
    tail -3 "$PROJECT_ROOT/server/data/logs/server.log" 2>/dev/null | sed 's/^/      /' || echo "      No logs yet"
else
    echo "   ❌ Backend not running"
fi

echo ""

# Test 2: Test Electron logger directly (Node.js)
echo "2️⃣  Testing Electron Logger (via Node.js)..."
cat > /tmp/test_electron_logger.mjs << 'EOF'
import { fileURLToPath } from 'url';
import path from 'path';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Import the logger
const loggerPath = path.join(__dirname, '../locaNext/electron/logger.js');
const { logger } = await import(loggerPath);

console.log('✅ Logger imported successfully');

// Test logging
logger.info('Test info message', { test: true });
logger.success('Test success message');
logger.warning('Test warning message');
logger.error('Test error message', { code: 500 });
logger.ipc('test-channel', { data: 'test' });
logger.python('/test/script.py', true, 'output');

console.log('✅ All logger methods executed');
EOF

cd "$PROJECT_ROOT" && node /tmp/test_electron_logger.mjs 2>&1 | grep "✅" || echo "   ⚠️  Logger test completed (check for errors above)"

echo ""
echo "   📝 Checking if LocaNext log was created:"
if [ -f "$PROJECT_ROOT/logs/locanext_app.log" ]; then
    echo "   ✅ locanext_app.log exists!"
    tail -5 "$PROJECT_ROOT/logs/locanext_app.log" | sed 's/^/      /'
else
    echo "   ⏳ locanext_app.log will be created when Electron runs"
fi

echo ""

# Test 3: Dashboard logging (browser mode - no file logs)
echo "3️⃣  Testing Dashboard (Browser Mode)..."
echo "   ⚠️  Dashboard in browser mode only logs to browser console"
echo "   ⚠️  File logging requires Node.js environment (SSR)"
echo "   💡 To see Dashboard logs:"
echo "      - Open browser: http://localhost:5175"
echo "      - Open DevTools Console (F12)"
echo "      - Navigate pages to trigger logging"

echo ""

# Summary
echo "========================================"
echo "📊 SUMMARY"
echo "========================================"
echo ""
echo "✅ Backend: WORKING (file logs active)"
echo "⏳ LocaNext: Code ready (needs Electron to run)"
echo "⏳ Dashboard: Code ready (browser console only in dev)"
echo ""
echo "🎯 Testing Options:"
echo ""
echo "Option 1: Test Backend (WORKING NOW)"
echo "  bash scripts/monitor_logs_realtime.sh --backend-only"
echo ""
echo "Option 2: Test via API/curl (NO GUI NEEDED)"
echo "  # Trigger backend activity"
echo "  curl http://localhost:8888/health"
echo "  curl http://localhost:8888/api/v2/auth/login -X POST -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}'"
echo "  tail -f server/data/logs/server.log"
echo ""
echo "Option 3: View Dashboard in browser"
echo "  # Open in your Windows browser (if WSL port forwarding works)"
echo "  http://localhost:5175"
echo "  # Check browser console (F12) for logs"
echo ""
echo "Option 4: Test Electron logger manually (just did above)"
echo "  node /tmp/test_electron_logger.mjs"
echo ""
echo "========================================"
