# 10 - Troubleshooting

**Purpose:** Common issues and their solutions

---

## Quick Diagnostics

### Server-Side Checks

```bash
# Check all services
sudo systemctl status postgresql gitea

# Check ports
sudo netstat -tlnp | grep -E '5432|3000'

# Check disk space
df -h

# Check memory
free -h

# Check PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

### Client-Side Checks (Windows)

```powershell
# Check if backend running
Invoke-RestMethod -Uri "http://localhost:8888/health"

# Check network to server
Test-NetConnection -ComputerName 10.10.30.50 -Port 5432

# Check LocaNext processes
Get-Process -Name "*LocaNext*"
```

---

## Connection Issues

### Problem: App Shows "Offline Mode" When Should Be Online

**Symptoms:**
- App starts but shows "Offline" indicator
- Database type shows "sqlite" instead of "postgresql"

**Causes & Solutions:**

1. **Server unreachable**
   ```powershell
   # Test connectivity
   Test-NetConnection -ComputerName 10.10.30.50 -Port 5432

   # If fails: Check firewall, VPN, network
   ```

2. **Wrong server config**
   ```
   - Open LDM > Server Status > Configure
   - Verify: Host, Port, User, Password, Database
   - Click "Test Connection"
   - If fails, check credentials with admin
   ```

3. **Server config not saved**
   ```
   - Check file exists: %APPDATA%\LocaNext\server-config.json
   - If missing, reconfigure and save
   - Restart app after saving
   ```

4. **PostgreSQL not accepting connections**
   ```bash
   # On server, check pg_hba.conf allows client IP
   sudo grep "10.10" /etc/postgresql/16/main/pg_hba.conf

   # If missing, add client's network and reload
   sudo systemctl reload postgresql
   ```

---

### Problem: "Connection Refused" Error

**Symptoms:**
- Cannot connect to server
- Error: "Connection refused" or timeout

**Solutions:**

1. **PostgreSQL not running**
   ```bash
   sudo systemctl start postgresql
   sudo systemctl status postgresql
   ```

2. **PostgreSQL not listening on network**
   ```bash
   # Check postgresql.conf
   grep listen_addresses /etc/postgresql/16/main/postgresql.conf
   # Should be: listen_addresses = '*'

   # Restart after change
   sudo systemctl restart postgresql
   ```

3. **Firewall blocking**
   ```bash
   # Check UFW
   sudo ufw status | grep 5432

   # If not listed, add rule
   sudo ufw allow from 10.10.0.0/16 to any port 5432
   ```

---

### Problem: "Authentication Failed"

**Symptoms:**
- Connection reaches server but login fails
- Error: "password authentication failed"

**Solutions:**

1. **Wrong password**
   ```
   - Verify password with admin
   - Check for typos (case-sensitive)
   - Try password in psql directly:
     psql -h 10.10.30.50 -U locanext_app -d locanext
   ```

2. **User doesn't exist**
   ```sql
   -- On server, check user exists
   sudo -u postgres psql -c "SELECT usename FROM pg_user;"

   -- If missing, create
   sudo -u postgres psql -c "CREATE USER locanext_app WITH PASSWORD 'password';"
   ```

3. **Wrong auth method in pg_hba.conf**
   ```bash
   # Check auth method
   sudo grep locanext /etc/postgresql/16/main/pg_hba.conf

   # Should use scram-sha-256, not md5 or trust
   ```

---

## Installation Issues

### Problem: First-Run Setup Hangs

**Symptoms:**
- "Installing Python dependencies" stuck
- "Downloading Embedding Model" stuck
- Progress bar not moving

**Solutions:**

1. **No internet access**
   ```
   - Model download requires internet
   - Check proxy settings if behind corporate proxy
   - For air-gapped: Pre-install model (see 09_MAINTENANCE.md)
   ```

2. **Firewall blocking HuggingFace**
   ```powershell
   # Test connectivity
   Test-NetConnection -ComputerName huggingface.co -Port 443

   # If blocked, ask IT to whitelist:
   # - huggingface.co
   # - cdn-lfs.huggingface.co
   ```

3. **Disk full**
   ```powershell
   # Model needs ~3GB
   Get-PSDrive C | Select-Object Free
   ```

4. **Antivirus blocking**
   ```
   - Temporarily disable antivirus
   - Run setup
   - Re-enable antivirus
   - Add LocaNext to exclusions
   ```

---

### Problem: "Python Not Found" During Setup

**Symptoms:**
- Backend fails to start
- Error mentions Python not found

**Solutions:**

1. **Bundled Python missing**
   ```
   - Reinstall LocaNext
   - Check: C:\Program Files\LocaNext\resources\python\
   - Should contain python.exe
   ```

2. **Path too long**
   ```
   - Windows has 260 char path limit
   - Install to shorter path: C:\LocaNext
   ```

---

## Login Issues

### Problem: "Invalid Credentials"

**Solutions:**

1. **Username/password wrong**
   - Check with admin for correct credentials
   - Usernames are case-sensitive

2. **User account disabled**
   ```sql
   -- Admin checks:
   SELECT username, is_active FROM users WHERE username = 'john.doe';

   -- Re-enable:
   UPDATE users SET is_active = true WHERE username = 'john.doe';
   ```

3. **Session expired**
   - Close app completely
   - Reopen and login again

---

### Problem: User Forgot Password

**Admin Action:**
```bash
# Reset via API
TOKEN=$(curl -s -X POST http://10.10.30.50:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "ADMIN_PASS"}' | jq -r '.access_token')

curl -X POST http://10.10.30.50:8888/api/users/john.doe/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "TempPassword123!"}'
```

Or via CLI:
```bash
python3 -c "
from server.auth.user_manager import UserManager
UserManager().reset_password('john.doe', 'TempPassword123!')
"
```

---

## Performance Issues

### Problem: App Slow / Unresponsive

**Solutions:**

1. **Too many database connections**
   ```sql
   -- Check connections
   SELECT count(*) FROM pg_stat_activity WHERE datname = 'locanext';

   -- Kill idle connections
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE datname = 'locanext'
     AND state = 'idle'
     AND state_change < NOW() - INTERVAL '1 hour';
   ```

2. **Database needs vacuum**
   ```bash
   sudo -u postgres psql -d locanext -c "VACUUM ANALYZE;"
   ```

3. **Large file loaded**
   - Files with 100k+ rows may be slow
   - Consider splitting large files
   - Use search/filter instead of scrolling

4. **Low memory on client**
   ```powershell
   # Check memory
   Get-Process LocaNext | Select-Object WorkingSet64

   # If using >2GB, restart app
   ```

---

### Problem: Database Queries Slow

**Solutions:**

1. **Missing indexes**
   ```sql
   -- Check for missing indexes
   EXPLAIN ANALYZE SELECT * FROM ldm_rows WHERE file_id = 123;

   -- If "Seq Scan", add index:
   CREATE INDEX idx_ldm_rows_file_id ON ldm_rows(file_id);
   ```

2. **Bloated tables**
   ```sql
   -- Check bloat
   SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(tablename::text))
   FROM pg_tables WHERE schemaname = 'public';

   -- Vacuum
   VACUUM FULL ldm_rows;
   ```

3. **Connection pool exhausted**
   - Increase pool size in config
   - Or use PgBouncer

---

## Build Issues

### Problem: CI Build Fails

**Check:**

1. **View build logs**
   ```
   http://10.10.30.50:3000/locanext/LocaNext/actions
   Click on failed build > View logs
   ```

2. **Common failures:**
   - Tests fail: Fix failing tests
   - Dependencies: Run `npm install` locally first
   - Out of disk: Clean old builds

3. **Re-trigger build**
   ```bash
   echo "Retry $(date)" >> GITEA_TRIGGER.txt
   git add -A && git commit -m "Retry build" && git push company main
   ```

---

### Problem: Installer Won't Build

**Solutions:**

1. **Missing Wine (for Windows builds on Linux)**
   ```bash
   sudo apt install wine64 wine32
   ```

2. **Node modules corrupted**
   ```bash
   cd locaNext
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **electron-builder error**
   ```bash
   # Clear cache
   rm -rf ~/.cache/electron
   rm -rf ~/.cache/electron-builder

   # Retry
   npm run electron:build
   ```

---

## WebSocket Issues

### Problem: Real-time Sync Not Working

**Symptoms:**
- Changes not appearing for other users
- Lock indicators not updating

**Solutions:**

1. **WebSocket blocked by proxy**
   ```
   - Corporate proxies may block WebSocket
   - Ask IT to allow WebSocket to server
   ```

2. **Backend WebSocket not running**
   ```bash
   # Check backend logs for socket.io messages
   journalctl -u locanext | grep socket
   ```

3. **Different file versions**
   - Both users must be on same file
   - Refresh file list

---

## Log Locations

| Component | Log Location |
|-----------|--------------|
| PostgreSQL | `/var/log/postgresql/postgresql-16-main.log` |
| Gitea | `journalctl -u gitea` |
| LocaNext Backend (server) | `/var/log/locanext/` or stdout |
| LocaNext Client (Windows) | `%APPDATA%\LocaNext\logs\` |

---

## Getting Help

### Information to Collect

When reporting issues, include:

1. **Version:** LocaNext version (Settings > About)
2. **Mode:** Online or Offline
3. **Error message:** Exact text
4. **Steps to reproduce:** What you did
5. **Logs:** Relevant log entries
6. **Screenshots:** If UI issue

### Contact

- IT Support: [your-it-email]
- LocaNext Admin: [admin-email]
- Documentation: This folder

---

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "Connection refused" | Server not running/reachable | Check server, firewall |
| "Authentication failed" | Wrong credentials | Verify username/password |
| "Database not found" | Wrong database name | Check config |
| "Permission denied" | User lacks privileges | Contact admin |
| "Timeout" | Network slow or blocked | Check network, firewall |
| "Row locked" | Another user editing | Wait or ask them to finish |
| "File too large" | File exceeds limit | Split file or increase limit |
