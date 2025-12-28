# Claude Confusion History

**Purpose:** Track mistakes to prevent repeating them.

---

## Key Patterns

| Pattern | Description |
|---------|-------------|
| **DOCS FIRST** | Read docs before guessing |
| **CHECK STATE** | Verify versions/configs before acting |
| **ACTIVE TEST** | Use CDP, don't just launch and wait |
| **GOAL MATCH** | Verify command achieves stated goal |
| **VERIFY CONFIG** | Check actual values, don't assume |

---

## Common Mistakes

| ID | Mistake | Fix |
|----|---------|-----|
| 1 | WSL env vars don't pass to Windows | Use different credential mechanism |
| 2 | Marking fixed before visual verify | Extract app.asar and check |
| 3 | Tried reinstall for auto-update test | Launch existing app instead |
| 4 | Rate limiting blocked tests | Use `DEV_MODE=true` |
| 5 | Auto-update pointed to GitHub | Changed default to Gitea |
| 6 | Passive testing (launch and wait) | Use CDP for active interaction |
| 7 | Background tasks left running | Clean up stale processes |
| 8 | Wrong bash syntax | Test commands before running |
| 9 | Checking runner status wrong way | Use SQL, not curl |
| 10 | **Wrong DB table name** (`files` vs `ldm_files`) | Check schema first with `pg_tables` query |
| 11 | **Wrong DB column name** (`source_text` vs `source`) | Check columns with `information_schema.columns` |
| 12 | **Running commands from wrong directory** | Always `cd` to correct dir OR use absolute paths |
| 13 | **Playwright test from root instead of locaNext** | Run from `/home/neil1988/LocalizationTools/locaNext` |
| 14 | **Hardcoded wrong DB credentials** | Use `from config import DATABASE_URL` |
| 15 | **ModuleNotFoundError for config** | Must run from LocalizationTools dir with `sys.path.insert` |
| 16 | **INSTALL vs UPDATE confusion** | INSTALL = fresh from .exe, UPDATE = auto-updater. See DOC-001 |
| 17 | **Pushed to Gitea without checking state** | Check `ps aux | grep gitea` + `free -h` BEFORE pushing |
| 18 | **Started Gitea manually (./gitea web)** | ALWAYS use `sudo systemctl start/stop gitea` |
| 19 | **Didn't stop Gitea after push** | ALWAYS `sudo systemctl stop gitea` after pushing |
| 20 | **Triggered CI without resource check** | Check `free -h` + `uptime` before triggering builds |

---

## 2025-12-28 Session Confusions

### Confusion 10-15: Database & Terminal Commands

**What went wrong:**
```bash
# WRONG: Ran from root, config module not found
python3 << 'EOF'
from config import DATABASE_URL  # ModuleNotFoundError!
EOF

# WRONG: Used wrong table name
SELECT * FROM files  # UndefinedTable error - it's ldm_files!

# WRONG: Used wrong column names
SELECT source_text FROM ldm_rows  # UndefinedColumn - it's 'source'!

# WRONG: Ran Playwright from wrong directory
npx playwright test tests/xxx.spec.ts  # No tests found
```

**Correct commands:**
```bash
# RIGHT: Run from LocalizationTools with sys.path
cd /home/neil1988/LocalizationTools && python3 << 'EOF'
import sys
sys.path.insert(0, 'server')
from config import DATABASE_URL
# ... rest of code
EOF

# RIGHT: Use correct table names (ldm_ prefix)
SELECT * FROM ldm_files
SELECT * FROM ldm_rows
SELECT * FROM ldm_projects

# RIGHT: Use correct column names
SELECT id, row_num, source, target FROM ldm_rows

# RIGHT: Run Playwright from locaNext directory
cd /home/neil1988/LocalizationTools/locaNext && npx playwright test tests/xxx.spec.ts
```

---

### Confusion 16: INSTALL vs UPDATE (CRITICAL)

**What went wrong:**
```bash
# WRONG: Told user to run install when app was already installed
./scripts/playground_install.sh --launch --auto-login  # Wasted 5 minutes!

# User asked: "install? we don't use the update feature?"
# This revealed GRAVE documentation confusion
```

**The difference:**

| INSTALL | UPDATE |
|---------|--------|
| Fresh installation from .exe | Auto-updater downloads new version |
| First time, clean slate, testing first-run | App already installed, just need new code |
| 2-5 min (includes Python setup) | 30 sec - 2 min |
| `./scripts/playground_install.sh` | Just open the app, it auto-updates |

**Correct approach:**

```
1. Is app already installed in Playground?
   ├── NO → Use INSTALL (./scripts/playground_install.sh)
   └── YES → Use UPDATE (just open the app)

2. Do you need to test first-run experience?
   ├── YES → Use INSTALL
   └── NO → Use UPDATE

3. Do you need a clean slate?
   ├── YES → Use INSTALL
   └── NO → Use UPDATE
```

**See [DOC-001_INSTALL_VS_UPDATE_CONFUSION.md](DOC-001_INSTALL_VS_UPDATE_CONFUSION.md) for full details.**

---

### Confusion 17-20: GITEA RESOURCE CRISIS (CRITICAL)

**Date:** 2025-12-28 13:02 KST

**What went wrong:**
```
1. Started Gitea manually (./gitea web) on Dec 27
2. Never killed it - zombie held port 3000
3. Pushed to Gitea without checking state
4. CI Run 410 started - pytest consumed 36.5GB RAM
5. System froze - only 280MB free of 39GB
6. Gitea in crash loop (72 restarts!)
```

**Evidence:**
```
PID 859420: Zombie from Dec 27, holding port 3000
PID 913123: pytest using 93% memory (36.5GB!)
Run 410: status=3 (stuck), started 12:36, never finished
```

**Correct workflow:**
```bash
# BEFORE pushing to Gitea:
free -h                           # Check memory (need >2GB free)
uptime                            # Check load (should be <3)
ps aux | grep gitea | grep -v grep  # Check for zombies
sudo systemctl status gitea       # Check service state

# Push workflow:
sudo systemctl start gitea
git push origin main && git push gitea main
sudo systemctl stop gitea         # ALWAYS STOP AFTER!

# If zombies found:
kill -9 <zombie_pid>
sudo systemctl start gitea
```

**See [ALERT-001_GITEA_RESOURCE_CRISIS.md](ALERT-001_GITEA_RESOURCE_CRISIS.md) for full details.**

---

### Confusion 21: INFINITE BUILD WAIT (CRITICAL)

**Date:** 2025-12-28 13:30 KST

**What went wrong:**
```
1. Build 411 started - knew it would fail (had unfixed tests)
2. Instead of pushing fixes immediately, waited for it to complete
3. Tests ran for 25+ MINUTES consuming 11GB+ RAM
4. Kept polling "is it done?" every 60-90 seconds
5. Build was STUCK, not failing - infinite resource consumption
6. Wasted 25+ minutes waiting for a guaranteed failure
```

**Evidence:**
```
pytest PID 920886: 92% CPU, 28% MEM (11GB), time: 15:44+
Build 411 status: RUN (never changed to FAIL)
Infinite wait loop instead of action
```

**Correct workflow:**
```bash
# BUILD TIMEOUT PROTOCOL
# Normal build times:
#   - Trigger job: <1 min
#   - Safety checks (tests): 5-10 min
#   - Windows build: 5-15 min
# TOTAL: ~15-20 min MAX

# CHECK #1: After 5 min of tests running
if [ tests_running_time > 5 min ]; then
    check_progress  # Should be >30%
fi

# CHECK #2: After 10 min of tests running
if [ tests_running_time > 10 min ]; then
    check_memory    # Should be <5GB for tests
    if [ memory > 8GB ]; then
        ALERT: "Tests consuming too much memory!"
        pkill -f pytest
    fi
fi

# CHECK #3: After 15 min TOTAL
if [ build_time > 15 min ]; then
    ALERT: "Build exceeded normal time!"
    investigate_immediately
    DO NOT keep waiting
fi
```

**Key lesson:**
- **NEVER wait indefinitely** - builds have known timeframes
- **If build will fail, push fixes NOW** - don't wait for failure
- **Monitor resources** during builds (RAM, CPU)
- **Kill stuck processes** - don't let them consume resources

---

## Prevention Rules

1. **Verify paths exist** before running scripts
2. **Start backend with `DEV_MODE=true`** for testing
3. **Use known credentials:** admin/admin123
4. **THINK before acting** - Does command match goal?
5. **CHECK STATE** - What version is installed?
6. **Check runner status via SQL:**
   ```bash
   python3 -c "import sqlite3; c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor(); c.execute('SELECT id, status FROM action_run ORDER BY id DESC LIMIT 3'); print(c.fetchall())"
   ```

---

*Confusion tracker | Keep this SHORT*
