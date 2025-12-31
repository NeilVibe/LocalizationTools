# CLAUDE.md - LocaNext Navigation Hub

> **KEEP THIS FILE COMPACT.** Details in linked docs. Fast-moving info lives in SESSION_CONTEXT.md.

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **DEV Testing (PRIMARY!)** | [testing_toolkit/DEV_MODE_PROTOCOL.md](testing_toolkit/DEV_MODE_PROTOCOL.md) ← USE THIS |
| **Current task?** | [Roadmap.md](Roadmap.md) |
| **Session context?** | [docs/wip/SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md) |
| **Open bugs?** | [docs/wip/ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md) |
| **WIP docs?** | [docs/wip/README.md](docs/wip/README.md) |
| **Build → Test (Windows)** | [testing_toolkit/MASTER_TEST_PROTOCOL.md](testing_toolkit/MASTER_TEST_PROTOCOL.md) |
| **CI/CD debug?** | [docs/cicd/TROUBLESHOOTING.md](docs/cicd/TROUBLESHOOTING.md) |
| **Enterprise deploy?** | [docs/enterprise/HUB.md](docs/enterprise/HUB.md) |

---

## Glossary

| Term | Meaning |
|------|---------|
| **RM** | Roadmap.md - global priorities |
| **WIP** | docs/wip/*.md - active task files |
| **IL** | Issue List (ISSUES_TO_FIX.md) |
| **TDL** | To Do List (TodoWrite tool tracking) |
| **LDM** | Language Data Manager (CAT tool, App #4) |
| **TM** | Translation Memory |
| **FAISS** | Vector index for semantic search |
| **CDP** | Chrome DevTools Protocol - browser automation via DevTools |
| **PG** | Playground - Windows test environment |
| **PW** | Playwright - browser automation framework for testing |
| **Playground** | Windows test: `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground` |

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
3. **Monolith is Sacred** - Copy `RessourcesForCodingTheProject/` logic exactly
4. **No Backend Mods** - Only wrapper layers (API, GUI)
5. **Logger Only** - Never `print()`, always `logger`
6. **Dual Push Protocol** - Push to both GitHub and Gitea:
   ```
   git push origin main                           # GitHub (always on)
   ./scripts/gitea_control.sh start               # Start Gitea
   git push gitea main                            # Push to Gitea
   ./scripts/gitea_control.sh stop                # Stop Gitea (save resources)
   ```
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
├── wip/                  # Active work
│   ├── SESSION_CONTEXT.md      ← Current state + next steps
│   ├── ISSUES_TO_FIX.md        ← Bug tracker (7 open, 0 critical)
│   └── P36_COVERAGE_GAPS.md    ← Coverage analysis + test plan
├── cicd/                 # CI/CD documentation (ALL CI/CD HERE)
│   ├── CI_CD_HUB.md            ← Pipeline overview
│   ├── TROUBLESHOOTING.md      ← ⭐ EFFECTIVE DEBUGGING (use this!)
│   ├── GITEA_SAFETY_PROTOCOL.md ← CPU issues, runner safety
│   ├── HOW_TO_BUILD.md         ← Trigger builds
│   └── RUNNER_SERVICE_SETUP.md ← Runner config
├── enterprise/           # Company deployment
│   └── HUB.md
└── history/              # Archives
```

---

## New Session Checklist

1. `./scripts/check_servers.sh`
2. Read [Roadmap.md](Roadmap.md)
3. Read [SESSION_CONTEXT.md](docs/wip/SESSION_CONTEXT.md)
4. Check [ISSUES_TO_FIX.md](docs/wip/ISSUES_TO_FIX.md)
5. Ask user what to do

---

## Claude Work Protocol (CRITICAL)

### I DO THE WORK

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
