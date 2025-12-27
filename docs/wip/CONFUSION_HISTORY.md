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
