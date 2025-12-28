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
