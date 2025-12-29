# Server Management

**Purpose:** How to start, stop, and check LocaNext servers.
**Last Updated:** 2025-12-29

---

## Quick Commands

```bash
# Check server status + rate limit
./scripts/check_servers.sh

# Start DEV servers (auto-clears rate limit, uses DEV_MODE)
./scripts/start_all_servers.sh

# Start with Vite dev server
./scripts/start_all_servers.sh --with-vite

# Stop DEV servers
./scripts/stop_all_servers.sh

# Clear rate limit lockout
./scripts/check_servers.sh --clear-ratelimit

# Gitea CI/CD (separate!)
./scripts/gitea_control.sh status
./scripts/gitea_control.sh start
./scripts/gitea_control.sh stop
```

---

## Server Architecture

### DEV Servers (start_all_servers.sh)

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| Backend API | 8888 | FastAPI + WebSocket (DEV_MODE) |
| Vite Dev | 5173 | Frontend HMR (optional) |
| Admin Dashboard | 5175 | Admin UI (optional) |

### CI/CD Servers (gitea_control.sh)

| Service | Port | Purpose |
|---------|------|---------|
| Gitea | 3000 | Git server + Actions |
| Linux Runner | - | WSL build runner |
| Windows Runner | - | Windows build runner |

**Why separate?** Gitea uses ~60% CPU when idle. Only start it when pushing/building.

---

## Startup Script

The `start_all_servers.sh` script:

1. **Clears rate limit** - Auto-clears failed login attempts
2. **Checks PostgreSQL** - Starts if not running
3. **Clears port 8888** - Kills any process using the port
4. **Starts Backend** - With `DEV_MODE=true` (no rate limiting!)
5. **Optionally starts Vite** - With `--with-vite` flag
6. **Starts Admin Dashboard** - On port 5175
7. **Shows Summary** - Green = ready, Red = problem

---

## Health Check Script

The `check_servers.sh` script:
- Quick status check for DEV servers
- Shows rate limit status (locked/OK)
- Use `--clear-ratelimit` to fix lockouts
- Points to `gitea_control.sh` for CI/CD

---

## Rate Limiting

**Problem:** 5+ failed logins locks the IP for 15 minutes.

**Solutions:**

| Method | When to Use |
|--------|-------------|
| `DEV_MODE=true` | Disables rate limiting entirely |
| `start_all_servers.sh` | Auto-clears on startup |
| `--clear-ratelimit` | Manual clear when needed |

```bash
# Check if locked
./scripts/check_servers.sh
# Rate Limit Status... ⚠ LOCKED (5 recent fails)

# Fix it
./scripts/check_servers.sh --clear-ratelimit
# ✓ Rate limit cleared
```

---

## Manual Commands

```bash
# PostgreSQL
sudo service postgresql start
sudo service postgresql stop
sudo service postgresql status

# Backend (DEV_MODE recommended)
DEV_MODE=true python3 server/main.py

# Backend (background with DEV_MODE)
DEV_MODE=true nohup python3 server/main.py > /tmp/locanext/backend.log 2>&1 &

# Vite dev server
cd locaNext && npm run dev

# Check logs
tail -f /tmp/locanext/backend.log

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

### Rate limit locked (429 error)
```bash
./scripts/check_servers.sh --clear-ratelimit
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
cat /tmp/locanext/backend.log
```

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Connection refused" on 8888 | Backend not running | `./scripts/start_all_servers.sh` |
| "Database connection failed" | PostgreSQL not running | `sudo service postgresql start` |
| Port 8888 already in use | Old process lingering | `kill $(lsof -t -i:8888)` |
| "Too many failed login attempts" | Rate limit triggered | `./scripts/check_servers.sh --clear-ratelimit` |
| Lock requests timeout | WebSocket not connected | Restart backend |
| Gitea not in check_servers | By design | Use `./scripts/gitea_control.sh status` |

---

## Session Startup Checklist

**ALWAYS run at start of development session:**

```bash
cd /home/neil1988/LocalizationTools
./scripts/check_servers.sh
# If not OK:
./scripts/start_all_servers.sh --with-vite
```

---

*Updated: 2025-12-29 - Separated DEV vs CI/CD, added rate limit handling*
