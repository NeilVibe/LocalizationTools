# Quick Debug Reference

> Fast access to logs and debug commands for LocaNext

---

## Log Locations

| Log | Location | Command |
|-----|----------|---------|
| **Backend** | `/tmp/locanext/backend.log` | `tail -50 /tmp/locanext/backend.log` |
| **Vite** | `/tmp/locanext/vite.log` | `tail -50 /tmp/locanext/vite.log` |
| **Frontend (Electron)** | `~/.local/share/locanext/logs/` | Check app data folder |
| **Gitea CI** | Gitea web UI or SQLite | See CI section below |

---

## Quick Log Commands

```bash
# Backend logs - last 50 lines
tail -50 /tmp/locanext/backend.log

# Backend logs - live follow
tail -f /tmp/locanext/backend.log

# Backend ERRORS only
grep -i "error\|exception\|traceback" /tmp/locanext/backend.log | tail -30

# Frontend remote logs (sent to backend)
grep "FRONTEND" /tmp/locanext/backend.log | tail -20

# Clear logs for fresh capture
> /tmp/locanext/backend.log && > /tmp/locanext/vite.log
```

---

## Frontend Debug (Browser Console)

The remote logger (`remote-logger.js`) sends frontend errors to backend automatically.

**In DEV mode (localhost:5173):**
1. Open browser DevTools: `F12`
2. Go to Console tab
3. All `logger.*` calls appear here with colors

**Frontend log levels:**
- `logger.debug()` - Verbose
- `logger.info()` - Normal
- `logger.success()` - Green
- `logger.warning()` - Yellow
- `logger.error()` - Red
- `logger.file(op, filename, data)` - File operations
- `logger.apiCall(endpoint, method, data)` - API calls

---

## Debug Subagents Matrix

| Subagent | When to Use | Tools |
|----------|-------------|-------|
| `gdp-debugger` | ANY bug needing microscopic analysis | Read, Grep, Glob, Bash |
| `python-debugger` | Backend API, database, async/await issues | Read, Grep, Glob, Bash |
| `vite-debugger` | Frontend UI bugs, Svelte reactivity, API calls from browser | Read, Grep, Glob, Bash |
| `nodejs-debugger` | Electron main process, IPC issues | Read, Grep, Glob, Bash |
| `windows-debugger` | Bugs ONLY in packaged Windows app | Read, Grep, Glob, Bash |
| `code-reviewer` | After writing code - check for bugs | Read, Grep, Glob |
| `dev-tester` | Run Playwright tests, verify fixes | Read, Grep, Glob, Bash |

### Usage Examples

```
# Backend 500 error
Task(subagent_type="python-debugger", prompt="Debug 500 error on POST /api/ldm/files/upload")

# Frontend button not working
Task(subagent_type="vite-debugger", prompt="Debug why upload button does nothing")

# Any bug - full GDP analysis
Task(subagent_type="gdp-debugger", prompt="Find exact line causing 'coroutine not awaited'")
```

---

## Common Error Patterns

### 1. `'coroutine' object is not subscriptable/iterable`
**Cause:** Missing `await` on async function call
**Fix:** Add `await` before the call
```python
# Wrong
result = db.get_data()

# Right
result = await db.get_data()
```

### 2. `database is locked` (SQLite)
**Cause:** Concurrent writes or zombie processes
**Fix:**
```bash
pkill -f "python.*server/main"
./scripts/db_manager.sh sqlite-reinit
```

### 3. Frontend action does nothing (silent failure)
**Cause:** Early return without logging, or backend not running
**Check:**
```bash
# Is backend running?
curl http://localhost:8888/health

# Check frontend remote logs
grep "FRONTEND" /tmp/locanext/backend.log | tail -10
```

### 4. Build status unknown
**Check:** Use SQLite query, never guess
```bash
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status FROM action_run ORDER BY id DESC LIMIT 1')
STATUS = {1:'SUCCESS', 2:'FAILURE', 6:'RUNNING'}
r = c.fetchone()
print(f'Build {r[0]}: {STATUS.get(r[1], r[1])}')"
```

---

## Code Paths to Check

### File Upload (2 paths!)
| Path | Code Location | Triggered When |
|------|---------------|----------------|
| PostgreSQL | `files.py:upload_file()` | User logged in with project |
| Offline Storage | `files.py:_upload_to_local_storage()` | User in OFFLINE_MODE |

**LESSON:** Always test BOTH paths when debugging file operations!

### TM Operations (2 modes!)
| Mode | Database | When |
|------|----------|------|
| PostgreSQL | `tm_repo.py` (PostgreSQL) | Server connected |
| SQLite | `sqlite/tm_repo.py` | Offline mode |

---

## Full Debug Workflow

1. **Reproduce** - Get exact steps to trigger bug
2. **Clear logs** - `> /tmp/locanext/backend.log`
3. **Trigger bug** - Perform the action
4. **Check backend** - `tail -50 /tmp/locanext/backend.log`
5. **Check frontend** - `grep FRONTEND /tmp/locanext/backend.log`
6. **Find error line** - Look for ERROR/Exception/Traceback
7. **Read code** - Go to exact file:line mentioned
8. **Fix** - Apply the fix
9. **Test** - Verify fix works
10. **Document** - Add to this file if new pattern

---

*Created: Session 60 - After discovering missing `await` in Offline Storage upload path*
