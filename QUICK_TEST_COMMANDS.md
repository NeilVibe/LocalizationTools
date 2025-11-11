# Quick Test Commands for LocalizationTools

## One-Line Health Check
```bash
curl -s http://localhost:8888/health && echo " ✓ Backend OK"
```

## Full System Monitor
```bash
./scripts/monitor_system.sh
```

## Test All APIs
```bash
# Backend health
curl -s http://localhost:8888/health | python3 -m json.tool

# XLSTransfer module
curl -s http://localhost:8888/api/v2/xlstransfer/health | python3 -m json.tool

# Frontend
curl -I http://localhost:5173/

# WebSocket
curl -s "http://localhost:8888/ws/socket.io/?EIO=4&transport=polling" | head -c 100
```

## Check Database Operations
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/home/neil1988/LocalizationTools/server/data/localizationtools.db')
cursor = conn.cursor()

# Active operations count
cursor.execute("SELECT COUNT(*) FROM active_operations")
print(f"Total operations: {cursor.fetchone()[0]}")

# Recent operations
cursor.execute("""
SELECT operation_id, tool_name, status, progress_percentage, started_at
FROM active_operations
ORDER BY started_at DESC LIMIT 5
""")
print("\nRecent operations:")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} - {row[2]} ({row[3]}%) - {row[4]}")

conn.close()
EOF
```

## Test WebSocket with Python
```bash
timeout 5 python3 << 'EOF'
import socketio
import time

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print("✓ WebSocket connected!")

try:
    sio.connect('http://localhost:8888', socketio_path='/ws/socket.io')
    print(f"Status: {'Connected' if sio.connected else 'Disconnected'}")
    time.sleep(2)
    sio.disconnect()
except Exception as e:
    print(f"✗ Error: {e}")
EOF
```

## Check Processes
```bash
# Backend
pgrep -f "python.*uvicorn" && echo "✓ Backend running" || echo "✗ Backend not running"

# Frontend
pgrep -f "vite.*5173" && echo "✓ Frontend running" || echo "✗ Frontend not running"
```

## Check Ports
```bash
ss -tlnp | grep -E ":(8888|5173|8000)"
```

## View Recent Logs
```bash
# Backend logs
tail -50 /home/neil1988/LocalizationTools/server_output.log

# Backend errors only
tail -100 /home/neil1988/LocalizationTools/server_output.log | grep -i error

# Frontend errors
tail -50 /home/neil1988/LocalizationTools/logs/locanext_error.log
```

## Database Quick Stats
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/neil1988/LocalizationTools/server/data/localizationtools.db')
c = conn.cursor()
for table in ['users', 'sessions', 'active_operations', 'log_entries']:
    c.execute(f'SELECT COUNT(*) FROM {table}')
    print(f'{table}: {c.fetchone()[0]}')
conn.close()
"
```

## Test Specific API Endpoints
```bash
# List all available routes (from Swagger)
curl -s http://localhost:8888/openapi.json | python3 -m json.tool | grep '"path"'

# Test progress operations (requires auth)
curl -s http://localhost:8888/api/progress/operations

# Test file upload status
curl -s http://localhost:8888/api/v2/xlstransfer/test/status
```

## Monitor in Real-Time
```bash
# Watch backend logs
tail -f /home/neil1988/LocalizationTools/server_output.log

# Watch database operations
watch -n 2 'python3 -c "import sqlite3; c=sqlite3.connect(\"/home/neil1988/LocalizationTools/server/data/localizationtools.db\").cursor(); c.execute(\"SELECT COUNT(*) FROM active_operations\"); print(f\"Operations: {c.fetchone()[0]}\")"'
```

## Quick Troubleshooting
```bash
# If backend not responding
ps aux | grep uvicorn

# Check backend port
netstat -tlnp 2>/dev/null | grep python || ss -tlnp | grep python

# Restart backend (if needed)
# pkill -f "python.*uvicorn" && cd /home/neil1988/LocalizationTools && python3 server/main.py &

# Check frontend issues
curl -v http://localhost:5173/ 2>&1 | grep -E "HTTP|Connection"
```

## Full API Documentation
Open in browser:
```
http://localhost:8888/docs
```

## URLs
- **Backend:** http://localhost:8888
- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8888/docs
- **Auth Server:** http://localhost:8000
