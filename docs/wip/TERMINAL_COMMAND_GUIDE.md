# Terminal Command Guide

**Purpose:** Correct commands to avoid common mistakes.

---

## Quick Reference

| Task | Correct Command |
|------|-----------------|
| Playwright test | `cd /home/neil1988/LocalizationTools/locaNext && npx playwright test tests/xxx.spec.ts` |
| Database query | `cd /home/neil1988/LocalizationTools && python3 << 'EOF' ... EOF` |
| Backend health | `curl -s http://localhost:8888/health \| jq` |
| Frontend check | `curl -s http://localhost:5173` |

---

## Database Commands

### ALWAYS use this pattern:
```bash
cd /home/neil1988/LocalizationTools && python3 << 'EOF'
import sys
sys.path.insert(0, 'server')
from sqlalchemy import create_engine, text
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("YOUR QUERY HERE"))
    for r in result.fetchall():
        print(r)
EOF
```

### Table Names (use ldm_ prefix!)
| Wrong | Correct |
|-------|---------|
| `files` | `ldm_files` |
| `rows` | `ldm_rows` |
| `projects` | `ldm_projects` |
| `folders` | `ldm_folders` |
| `tm_entries` | `ldm_tm_entries` |

### Column Names (ldm_rows)
| Wrong | Correct |
|-------|---------|
| `source_text` | `source` |
| `target_text` | `target` |
| `filename` | `name` (in ldm_files) |

### Check Schema First
```bash
cd /home/neil1988/LocalizationTools && python3 << 'EOF'
import sys
sys.path.insert(0, 'server')
from sqlalchemy import create_engine, text
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    # List all tables
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    print("Tables:", [r[0] for r in result.fetchall()])

    # Check columns for a table
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'ldm_rows' ORDER BY ordinal_position
    """))
    print("ldm_rows columns:", [r[0] for r in result.fetchall()])
EOF
```

---

## Playwright Commands

### ALWAYS run from locaNext directory:
```bash
cd /home/neil1988/LocalizationTools/locaNext && npx playwright test tests/xxx.spec.ts --reporter=list
```

### Common test commands:
```bash
# Run specific test
cd /home/neil1988/LocalizationTools/locaNext && npx playwright test tests/search-proue.spec.ts --reporter=list

# Run all tests
cd /home/neil1988/LocalizationTools/locaNext && npx playwright test --reporter=list

# Run with UI
cd /home/neil1988/LocalizationTools/locaNext && npx playwright test --ui
```

### WRONG (will fail):
```bash
# From root - NO!
npx playwright test tests/xxx.spec.ts

# Without cd - NO!
npx playwright test /home/neil1988/LocalizationTools/locaNext/tests/xxx.spec.ts
```

---

## Server Commands

### Check if servers running:
```bash
# Backend
curl -s http://localhost:8888/health | jq

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
```

### Start servers:
```bash
# Backend (with DEV_MODE)
cd /home/neil1988/LocalizationTools && DEV_MODE=true python3 server/main.py

# Frontend
cd /home/neil1988/LocalizationTools/locaNext && npm run dev
```

### Kill servers:
```bash
pkill -f "python3 server/main"
pkill -f "vite dev"
```

---

## Git Commands

### Push to both remotes:
```bash
git add -A && git commit -m "message" && git push origin main && git push gitea main
```

---

## GITEA PROTOCOL (Activation/Push/Deactivation)

### Why This Protocol?
Gitea uses CPU resources. Only activate when needed for git push/CI builds.

### Step 1: ACTIVATE Gitea
```bash
sudo systemctl start gitea
sleep 5  # Wait for service to be ready

# Verify Gitea is running
systemctl is-active gitea  # Should show "active"
```

### Step 2: COMMIT and PUSH
```bash
# Stage all changes
git add -A

# Commit with descriptive message
git commit -m "$(cat <<'EOF'
Build XXX: Description of changes

- Fix 1: UI-076 search bar
- Fix 2: UI-077 duplicate names
- Fix 3: UI-080 search indexing

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"

# Push to BOTH remotes
git push origin main      # GitHub
git push gitea main       # Gitea (triggers CI build)
```

### Step 3: DEACTIVATE Gitea (Optional - saves resources)
```bash
# Only after push is complete
sudo systemctl stop gitea

# Verify stopped
systemctl is-active gitea  # Should show "inactive"
```

### Quick One-Liner (Full Protocol)
```bash
sudo systemctl start gitea && sleep 5 && git add -A && git commit -m "message" && git push origin main && git push gitea main && sudo systemctl stop gitea
```

### Check Gitea Status
```bash
systemctl is-active gitea
# "active" = running
# "inactive" = stopped
```

### Check Build Status (via DB - PRIMARY METHOD)
```bash
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 5')
STATUS = {0:'UNKNOWN', 1:'SUCCESS', 2:'FAILURE', 3:'CANCELLED', 4:'SKIPPED', 5:'WAITING', 6:'RUNNING', 7:'BLOCKED'}
for r in c.fetchall():
    print(f'Run {r[0]}: {STATUS.get(r[1], r[1]):8} - {r[2]}')"
```
**Status codes:** 0=UNKNOWN, 1=SUCCESS, 2=FAILURE, 5=WAITING, **6=RUNNING**, 7=BLOCKED

---

## Directory Reference

| Purpose | Path |
|---------|------|
| Project root | `/home/neil1988/LocalizationTools` |
| Frontend | `/home/neil1988/LocalizationTools/locaNext` |
| Backend | `/home/neil1988/LocalizationTools/server` |
| Tests | `/home/neil1988/LocalizationTools/locaNext/tests` |
| Docs | `/home/neil1988/LocalizationTools/docs` |
| WIP docs | `/home/neil1988/LocalizationTools/docs/wip` |

---

## API Commands

### Login and get token:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8888/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')
echo $TOKEN
```

### Use token in API call:
```bash
curl -s "http://localhost:8888/api/ldm/projects" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

*Keep this guide handy to avoid command mistakes!*
