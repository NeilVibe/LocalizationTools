# Server Management

**Purpose:** How to start, stop, and check LocaNext servers.
**Last Updated:** 2025-12-12

---

## Quick Commands

```bash
# Check if servers are running
./scripts/check_servers.sh

# Start ALL servers (PostgreSQL + Backend)
./scripts/start_all_servers.sh

# Just check health
curl http://localhost:8888/health
```

---

## Required Services

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| Backend API | 8888 | FastAPI + WebSocket |

---

## Startup Script

The `start_all_servers.sh` script:

1. **Checks PostgreSQL** - Starts if not running
2. **Clears port 8888** - Kills any process using the port
3. **Starts Backend** - Runs `python3 server/main.py` in background
4. **Health Check** - Verifies everything is running
5. **Shows Summary** - Green = ready, Red = problem

---

## Health Check Script

The `check_servers.sh` script:
- Quick status check (no changes)
- Shows green/red for each service
- Use before development/testing

---

## Manual Commands

```bash
# PostgreSQL
sudo service postgresql start
sudo service postgresql stop
sudo service postgresql status

# Backend (manual)
python3 server/main.py

# Backend (background)
nohup python3 server/main.py > /tmp/locatools_server.log 2>&1 &

# Check logs
tail -f /tmp/locatools_server.log

# Kill backend
kill $(lsof -t -i:8888)
```

---

## Troubleshooting

### Port 8888 in use
```bash
lsof -i :8888
kill -9 <PID>
```

### PostgreSQL won't start
```bash
sudo service postgresql status
sudo tail -50 /var/log/postgresql/postgresql-14-main.log
```

### Backend crashes immediately
```bash
# Check if PostgreSQL is running first
pg_isready

# Check backend logs
cat /tmp/locatools_server.log
```

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Connection refused" on 8888 | Backend not running | `./scripts/start_all_servers.sh` |
| "Database connection failed" | PostgreSQL not running | `sudo service postgresql start` |
| Port 8888 already in use | Old process lingering | `kill $(lsof -t -i:8888)` |
| Lock requests timeout | WebSocket not connected | Restart backend |

---

## Session Startup Checklist

**ALWAYS run at start of development session:**

```bash
cd /home/neil1988/LocalizationTools
./scripts/check_servers.sh
# If not OK:
./scripts/start_all_servers.sh
```

---

*Created: 2025-12-12*
