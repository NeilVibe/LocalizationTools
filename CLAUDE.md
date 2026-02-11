# CLAUDE.md - LocaNext Navigation Hub

> **KEEP THIS FILE COMPACT.** Details in linked docs. Fast-moving info lives in SESSION_CONTEXT.md.

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Docs hub** | [docs/INDEX.md](docs/INDEX.md) ← START HERE |
| **Session context?** | [docs/current/SESSION_CONTEXT.md](docs/current/SESSION_CONTEXT.md) |
| **Open bugs?** | [docs/current/ISSUES_TO_FIX.md](docs/current/ISSUES_TO_FIX.md) |
| **Current task?** | [Roadmap.md](Roadmap.md) |
| **Architecture?** | [docs/architecture/ARCHITECTURE_SUMMARY.md](docs/architecture/ARCHITECTURE_SUMMARY.md) |
| **Offline/Online?** | [docs/architecture/OFFLINE_ONLINE_MODE.md](docs/architecture/OFFLINE_ONLINE_MODE.md) |
| **Bug hunting?** | [docs/protocols/GRANULAR_DEBUG_PROTOCOL.md](docs/protocols/GRANULAR_DEBUG_PROTOCOL.md) ← GDP |
| **DEV Testing** | [testing_toolkit/DEV_MODE_PROTOCOL.md](testing_toolkit/DEV_MODE_PROTOCOL.md) |
| **Build → Test** | [testing_toolkit/MASTER_TEST_PROTOCOL.md](testing_toolkit/MASTER_TEST_PROTOCOL.md) |
| **CI/CD debug?** | [docs/reference/cicd/TROUBLESHOOTING.md](docs/reference/cicd/TROUBLESHOOTING.md) |
| **Enterprise?** | [docs/reference/enterprise/HUB.md](docs/reference/enterprise/HUB.md) |
| **DB Management?** | `./scripts/db_manager.sh help` |
| **Dev Paradigms?** | [PARADIGMS.md](PARADIGMS.md) ← Libraries, patterns, lessons |

---

## Glossary

| Term | Meaning |
|------|---------|
| **CCAD** | **Check Claude.md And Docs** - When confused, ALWAYS check docs first! |
| **GDP** | **Granular Debug Protocol** - Microscopic logging for autonomous bug hunting. See `docs/protocols/` |
| **SW** | Shell Wrapper - `./scripts/gitea_control.sh` for Gitea management |
| **DBM** | DB Manager - `./scripts/db_manager.sh` for database operations |
| **RM** | Roadmap.md - global priorities |
| **WIP** | `docs/current/` - active work (issues, session) |
| **IL** | Issue List (ISSUES_TO_FIX.md) |
| **TDL** | To Do List (TodoWrite tool tracking) |
| **LDM** | Language Data Manager (CAT tool, App #4) |
| **TM** | Translation Memory |
| **FAISS** | Vector index for semantic search |
| **CDP** | Chrome DevTools Protocol - browser automation via DevTools |
| **PG** | Playground - Windows test environment |
| **PW** | Playwright - browser automation framework for testing |
| **Playground** | Windows test: `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground` |
| **RFC** | `RessourcesForCodingTheProject/` - Monolith reference scripts |
| **NewScripts** | `RFC/NewScripts/` - Mini-projects (personal tools, potential LocaNext apps) |
| **PM** | Plan Mode - Claude's structured planning workflow with ExitPlanMode tool |
| **Optimistic UI** | **MANDATORY!** UI updates INSTANTLY on user action, server syncs in background. If server fails, revert. Never make user wait for server response on UI changes. |
| **Svelte 5** | **WE USE SVELTE 5 RUNES!** Use `$state`, `$derived`, `$effect`. Always use keys in `{#each}`. See Svelte 5 section below. |

---

## Svelte 5 Runes (CRITICAL!)

**LocaNext uses Svelte 5 with Runes.** Not Svelte 4. Follow these patterns:

```svelte
// ✅ State
let count = $state(0);
let items = $state([]);

// ✅ Derived (computed values)
let doubled = $derived(count * 2);
let filtered = $derived(items.filter(x => x.active));

// ✅ Effects (side effects)
$effect(() => {
  console.log('Count changed:', count);
});

// ✅ Array mutations (Svelte 5 proxies them)
items.push(newItem);      // Works!
items.splice(index, 1);   // Works!
items = items.filter(...); // Also works

// ✅ ALWAYS use keys in {#each}
{#each items as item (item.id)}  // Good
{#each items as item}            // Bad - no key!

// ✅ Async + State: Use tracking sets for optimistic UI
let deletingIds = $state(new Set());
let visible = $derived(items.filter(i => !deletingIds.has(i.id)));
```

**Common Mistakes:**
- Using `export let` instead of `$state` for local state
- Forgetting keys in `{#each}` loops → flicker on updates
- Using `$:` reactive statements (Svelte 4) → use `$derived`/`$effect`

---

## XML Language Data: Newline = `<br/>` (CRITICAL!)

**Newlines in XML language data are represented as `<br/>` tags. This is the ONLY correct format.**

```xml
<!-- ✅ CORRECT — This is how our entire system works -->
KR="첫 번째 줄<br/>두 번째 줄"
EN="First line<br/>Second line"

<!-- ❌ WRONG — Will break the entire pipeline -->
KR="첫 번째 줄&#10;두 번째 줄"
KR="첫 번째 줄\n두 번째 줄"
```

**ALL tools** (QuickTranslate, QuickSearch, QACompiler, LanguageDataExporter, LDM, etc.) MUST preserve `<br/>` tags when reading, processing, and writing XML language data. Getting this wrong breaks the entire enterprise architecture.

---

## Architecture

```
LocaNext.exe (User PC)          Central PostgreSQL
├─ Embedded Python Backend  ──→  ├─ ALL text data
├─ FAISS indexes (local)         ├─ Users, sessions
├─ Qwen model (local, 2.3GB)     └─ TM entries, logs
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback)
```

---

## Development Protocol (CRITICAL!)

### DEV TESTING = PRIMARY WORKFLOW

```
┌─────────────────────────────────────────────────────────────┐
│  DEV TESTING FIRST - BUILD ONLY WHEN TIME IS RIGHT         │
├─────────────────────────────────────────────────────────────┤
│  1. Code changes in locaNext/                               │
│  2. Test via localhost:5173 (Vite dev server)               │
│  3. Run Playwright tests: npx playwright test               │
│  4. Fix issues, repeat until VERIFIED working               │
│  5. Push to Git (GitHub + Gitea)                            │
│  6. Only BUILD when significant milestone reached           │
└─────────────────────────────────────────────────────────────┘
```

**DEV Testing Location:** `testing_toolkit/DEV_MODE_PROTOCOL.md`

**Helpers Location:** `testing_toolkit/dev_tests/helpers/`

**Test Data:** `tests/fixtures/sample_language_data.txt` (63 rows, real Korean data with PAColor tags)

### Why DEV Testing First?

| DEV Testing | Windows Build |
|-------------|---------------|
| Instant feedback (<1s) | 15+ min build cycle |
| HMR updates | Must rebuild |
| Easy debugging | Hard to debug |
| Playwright works | CDP needed |
| Use for: All UI work | Use for: Final validation |

### Testing Matrix (MEMORIZE THIS)

| What | Where | Login | How |
|------|-------|-------|-----|
| **DEV** | localhost:5173 | admin/admin123 | Playwright |
| **Windows App** | Playground | admin/admin123 | `node testing_toolkit/cdp/login.js` |

### WSL = FULL WINDOWS POWER

```bash
# USER SCREENSHOTS (Win+Shift+S) - CHECK HERE FIRST!
ls -lt /mnt/c/Users/MYCOM/Pictures/Screenshots/*.png | head -3

# Read user's latest screenshot
cat "/mnt/c/Users/MYCOM/Pictures/Screenshots/$(ls -t /mnt/c/Users/MYCOM/Pictures/Screenshots/ | head -1)"

# Node.js on Windows
/mnt/c/Program\ Files/nodejs/node.exe script.js

# PowerShell
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "..."

# CDP login to Windows app
/mnt/c/Program\ Files/nodejs/node.exe testing_toolkit/cdp/login.js
```

**USER SCREENSHOT LOCATION:** `/mnt/c/Users/MYCOM/Pictures/Screenshots/`

**NOTHING IS IMPOSSIBLE FROM WSL.**

---

## Critical Rules

1. **DOCS FIRST (MANDATORY!)** - Before ANY protocol task: **STOP → READ THE DOC → THEN ACT**.

   ```
   ⚠️ EVERY TIME you do something that "feels like a protocol":
      1. STOP - Don't start doing it
      2. FIND the relevant doc (Quick Navigation table above)
      3. READ the exact commands/steps
      4. THEN execute exactly as documented
   ```

   **Skipping docs = wrong approach = wasted time = user frustration**
2. **ALWAYS CHOOSE HARD** - Between EASY/MEDIUM/HARD, ALWAYS choose HARD. No shortcuts. No workarounds. No quick fixes.
   - EASY WAY = Technical debt, breaks later, embarrassing
   - HARD WAY = Proper fix, survives forever, professional
   - Example: `overflow: visible` (easy) broke 480,000px scroll → `overflow: hidden` + flexbox constraints (hard) = perfect
3. **Sacred Scripts** - XLSTransfer, KR Similar, QuickSearch are battle-tested perfection (never change a byte). Rest of `RessourcesForCodingTheProject/` = monolith reference scripts to copy patterns from
4. **No Backend Mods** - Only wrapper layers (API, GUI)
5. **Logger Only** - Never `print()`, always `logger`
6. **Dual Push Protocol** - Push to both GitHub and Gitea:
   ```
   git push origin main                           # GitHub (always on)
   ./scripts/gitea_control.sh start               # Start Gitea
   git push gitea main                            # Push to Gitea
   ./scripts/gitea_control.sh stop                # Stop Gitea (save resources)
   ```

---

## CI PARADIGMS (TWO DIFFERENT SYSTEMS!)

| Project | Push To | CI System | Trigger |
|---------|---------|-----------|---------|
| **LocaNext** (main app) | GitHub + Gitea | **Gitea CI** (Windows runner) | `git push gitea main` |
| **NewScripts** (personal tools) | GitHub only | **GitHub Actions** | `git push origin main` |

**STOP CONFUSING THESE:**
- LocaNext = Electron app, needs Windows build → Gitea CI with Windows runner
- NewScripts (MapDataGenerator, QACompiler, etc.) = Python tools → GitHub Actions only

**NewScripts CI trigger:** Just push to GitHub. If workflow exists in `.github/workflows/`, it runs automatically.

---

7. **WSL ↔ Windows** - CDP tests can run from WSL via `/mnt/c/Program\ Files/nodejs/node.exe`
8. **Fix Everything** - No defer, no excuses, fix all issues
9. **NEVER RESTART** - Restarting does NOT solve issues. ALWAYS follow this workflow:
   1. STOP everything
   2. CLEAN resources (kill zombie processes)
   3. INVESTIGATE root cause
   4. FIX the actual issue
   5. Only THEN start fresh
10. **VERIFY WITH TESTS** - Never assume fixes work. Run headless Playwright tests. Take screenshots. Get HARD EVIDENCE.
11. **GITEA: STOP/START > RESTART** - Never use restart. Always CLEAN STOP → CLEAN START when needed → CLEAN STOP when done. Gitea uses ~60% CPU idle - don't leave running!
12. **BUILD STATUS = SQLite** - ALWAYS use SQLite query for build status, NEVER guess:
    ```bash
    python3 -c "
    import sqlite3
    c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
    c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 3')
    STATUS = {0:'UNKNOWN', 1:'SUCCESS', 2:'FAILURE', 5:'WAITING', 6:'RUNNING', 7:'BLOCKED'}
    for r in c.fetchall(): print(f'Run {r[0]}: {STATUS.get(r[1], r[1]):8} - {r[2]}')"
    ```
    **CRITICAL: STATUS 6 = RUNNING - just WAIT, don't investigate!**
13. **SW FIRST** - When checking Gitea, use Shell Wrapper first: `./scripts/gitea_control.sh status`
14. **STUPID vs ELEGANT** - Before writing code, ask: Is this STUPID or ELEGANT? STUPID = unnecessary, fragile, solves problems that don't exist. ELEGANT = right solution, robust, survives changes. Don't fix stupid code - DELETE it and find the elegant way.
15. **NO GREP FOR DEBUG** - Never use `grep` or keyword filtering when debugging logs. Read FULL logs with `cat` or `tail`. Grep hides context and masks the real problem. See FULL picture, not filtered slices.

---

## Quick Commands

```bash
# Check DEV servers + rate limit status
./scripts/check_servers.sh

# Start DEV servers (with DEV_MODE, auto-clears rate limit)
./scripts/start_all_servers.sh

# Start with Vite dev server
./scripts/start_all_servers.sh --with-vite

# Clear rate limit lockout
./scripts/check_servers.sh --clear-ratelimit

# Backend only (DEV_MODE recommended)
DEV_MODE=true python3 server/main.py

# Desktop app
cd locaNext && npm run electron:dev

# Gitea CI/CD (separate from DEV servers)
./scripts/gitea_control.sh start

# Trigger build
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Playground install (FRESH install only!)
./scripts/playground_install.sh --launch --auto-login

# === DB Manager ===
./scripts/db_manager.sh status -v      # Full DB status (SQLite + PostgreSQL)
./scripts/db_manager.sh sqlite-reinit  # Fresh SQLite reset
./scripts/db_manager.sh sqlite-analyze # Analyze SQLite contents
./scripts/db_manager.sh pg-analyze     # Analyze PostgreSQL contents
./scripts/db_manager.sh backup         # Backup all databases
```

---

## INSTALL vs UPDATE (CRITICAL DISTINCTION!)

| | INSTALL | UPDATE |
|--|---------|--------|
| **What** | Fresh installation from .exe | Auto-updater downloads new version |
| **When** | First time, clean slate, testing first-run | App already installed, just need new code |
| **Time** | 2-5 min (includes Python setup) | 30 sec - 2 min |
| **Command** | `./scripts/playground_install.sh` | Just open the app, it auto-updates |

### Decision: Which To Use?

```
App NOT installed yet?          → INSTALL
App installed, testing new fix? → UPDATE (just open the app!)
Testing first-run experience?   → INSTALL (after uninstall)
Testing auto-updater itself?    → UPDATE
Quick verification of fix?      → UPDATE
```

### UPDATE Flow (Most Common!)
1. Push code to Gitea → Build completes
2. Open LocaNext on Windows (already installed)
3. App auto-checks for updates on startup
4. Notification appears → Download → Restart
5. Verify fix in new version

### INSTALL Flow (Rare!)
1. Uninstall existing app (if any)
2. Run `./scripts/playground_install.sh --launch --auto-login`
3. Wait for first-run setup (Python deps, model)
4. App launches fresh

**DOC-001:** See [docs/history/DOC-001_INSTALL_VS_UPDATE_CONFUSION.md](docs/history/DOC-001_INSTALL_VS_UPDATE_CONFUSION.md)

---

## URLs

| Service | URL |
|---------|-----|
| Backend | http://localhost:8888 |
| API Docs | http://localhost:8888/docs |
| Gitea | http://172.28.150.120:3000 |

---

## Documentation

```
testing_toolkit/          # ← PRIMARY TESTING DOCS
├── MASTER_TEST_PROTOCOL.md  ← FULL WORKFLOW: Push→CI→Build→Install→Test
├── cdp/                     # Node.js CDP tests
│   ├── README.md               ← CDP test guide
│   └── *.js                    ← Test scripts
└── README.md                ← Testing overview

docs/
├── INDEX.md              # Docs navigation hub
├── architecture/         # System design docs
├── protocols/            # Claude protocols (GDP, etc.)
├── current/              # Active work
│   ├── SESSION_CONTEXT.md
│   └── ISSUES_TO_FIX.md
├── reference/            # Stable reference
│   ├── enterprise/       # Enterprise deployment
│   ├── cicd/             # CI/CD docs
│   └── security/         # Security docs
├── guides/               # User guides
└── archive/              # Old docs
```

---

## New Session Checklist

1. `./scripts/check_servers.sh`
2. Read [Roadmap.md](Roadmap.md)
3. Read [SESSION_CONTEXT.md](docs/current/SESSION_CONTEXT.md)
4. Check [ISSUES_TO_FIX.md](docs/current/ISSUES_TO_FIX.md)
5. Ask user what to do

---

## Claude Work Protocol (CRITICAL)

### I DO THE WORK - NO ACTION VERBS TO USER

```
⚠️ ABSOLUTE RULE: NEVER use action verbs directed at the user.

   ❌ FORBIDDEN phrases (cause RAGE):
      - "You need to..."
      - "You should..."
      - "Open the app..."
      - "Click..."
      - "Run this command..."
      - "Try..."

   ✅ CORRECT approach:
      - I do it myself
      - I run the command
      - I launch the app
      - I verify the fix
```

**NEVER say "You" + "Verb" to the user.** I am the one who:
- **I code** - Write the fixes
- **I test** - Run Playwright headless tests BEFORE pushing
- **I build** - Trigger builds and wait for completion
- **I install** - Run `./scripts/playground_install.sh --launch --auto-login`
- **I login** - Handle auto-login, debug if it fails
- **I verify** - Take screenshots, run CDP tests, get HARD EVIDENCE
- **I fix** - If something breaks, I investigate and fix it

### The Workflow I Must Follow

```
1. CODE THE FIX
   └─ Make changes to fix the issue

2. TEST BEFORE PUSH (CRITICAL!)
   └─ Run Playwright headless: node verify_ui_fixes.js
   └─ Take screenshots
   └─ VERIFY the fix works BEFORE pushing

3. PUSH AND BUILD
   └─ git add -A && git commit -m "Fix: description"
   └─ echo "Build NNN" >> GITEA_TRIGGER.txt
   └─ git push origin main && git push gitea main

4. WAIT FOR BUILD
   └─ Check: python3 -c "import sqlite3; ..." (database query)
   └─ DO NOT proceed until build SUCCESS

5. INSTALL TO PLAYGROUND
   └─ ./scripts/playground_install.sh --launch --auto-login
   └─ This downloads, installs, launches, and auto-logins

6. VERIFY IN PLAYGROUND
   └─ If auto-login fails, I debug it
   └─ Run CDP tests from Windows PowerShell
   └─ Take screenshots as proof
```

### What NOT to Do

| WRONG (Easy Way) | RIGHT (Hard Way) |
|------------------|------------------|
| "You should run..." | I run the command myself |
| Push code without testing | Test with Playwright BEFORE push |
| Assume fixes work | Take screenshots, get PROOF |
| "Try restarting" | STOP → CLEAN → INVESTIGATE → FIX → START |
| Skip documentation | Update docs THE HARD WAY |

### Background Tasks

- Check running tasks: `ls /tmp/claude/.../tasks/`
- DO NOT cancel tasks while build is running
- Clean up zombie processes AFTER investigating

---

## Claude Behavior

1. **Be frank** - Bad idea? Say so
2. **Independent** - Give honest opinions
3. **Optimal first** - Best approach first
4. **I do the work** - Never tell user to do things I should do myself

---

## Stats

- **Tests:** 1100+ total (737 unit, 170 integration, 86 security)
- **Coverage:** 47% overall → 70% target
- **LDM Routes:** projects 98%, folders 90%, tm_entries 74%
- **Endpoints:** 65+
- **Tools:** 4 (XLSTransfer, QuickSearch, KR Similar, LDM)
- **Languages:** 100+ (full Unicode support)

---

*Hub file - details in linked docs*

*Last updated: 2026-02-01*
