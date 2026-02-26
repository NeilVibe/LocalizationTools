# CLAUDE.md - LocaNext Navigation Hub

> **KEEP THIS FILE COMPACT.** Details in linked docs. Fast-moving info lives in SESSION_CONTEXT.md.

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Docs hub** | [docs/INDEX.md](docs/INDEX.md) |
| **Session context?** | [docs/current/SESSION_CONTEXT.md](docs/current/SESSION_CONTEXT.md) |
| **Open bugs?** | [docs/current/ISSUES_TO_FIX.md](docs/current/ISSUES_TO_FIX.md) |
| **Current task?** | [Roadmap.md](Roadmap.md) |
| **Architecture?** | [docs/architecture/ARCHITECTURE_SUMMARY.md](docs/architecture/ARCHITECTURE_SUMMARY.md) |
| **Offline/Online?** | [docs/architecture/OFFLINE_ONLINE_MODE.md](docs/architecture/OFFLINE_ONLINE_MODE.md) |
| **Bug hunting?** | [docs/protocols/GRANULAR_DEBUG_PROTOCOL.md](docs/protocols/GRANULAR_DEBUG_PROTOCOL.md) (GDP) |
| **PRXR Protocol?** | [docs/protocols/PRXR.md](docs/protocols/PRXR.md) |
| **DEV Testing** | [testing_toolkit/DEV_MODE_PROTOCOL.md](testing_toolkit/DEV_MODE_PROTOCOL.md) |
| **Build → Test** | [testing_toolkit/MASTER_TEST_PROTOCOL.md](testing_toolkit/MASTER_TEST_PROTOCOL.md) |
| **Install vs Update?** | [docs/history/DOC-001_INSTALL_VS_UPDATE_CONFUSION.md](docs/history/DOC-001_INSTALL_VS_UPDATE_CONFUSION.md) |
| **CI/CD debug?** | [docs/reference/cicd/TROUBLESHOOTING.md](docs/reference/cicd/TROUBLESHOOTING.md) |
| **Enterprise?** | [docs/reference/enterprise/HUB.md](docs/reference/enterprise/HUB.md) |
| **DB Management?** | `./scripts/db_manager.sh help` |
| **Dev Paradigms?** | [PARADIGMS.md](PARADIGMS.md) |

---

## Glossary

| Term | Meaning |
|------|---------|
| **CCAD** | Check Claude.md And Docs — when confused, ALWAYS check docs first |
| **GDP** | Granular Debug Protocol — microscopic logging for bug hunting. See `docs/protocols/` |
| **PRXR** | Plan-Review-Execute-Review — protocol for non-trivial changes. See `docs/protocols/PRXR.md` |
| **PM** | Plan Mode — Claude's structured planning workflow with ExitPlanMode tool |
| **SW** | Shell Wrapper — `./scripts/gitea_control.sh` |
| **DBM** | DB Manager — `./scripts/db_manager.sh` |
| **RFC** | `RessourcesForCodingTheProject/` — monolith reference scripts |
| **NewScripts** | `RFC/NewScripts/` — mini-projects (personal tools, potential LocaNext apps) |
| **QSS** | Quick Standalone Scripts — single-file Python+tkinter tools in `RFC/NewScripts/QuickStandaloneScripts/` |
| **LDM** | Language Data Manager (CAT tool, App #4) |
| **TM** | Translation Memory |
| **FAISS** | Vector index for semantic search |
| **PG** | Playground — `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground` |
| **CDP** | Chrome DevTools Protocol — browser automation via DevTools |
| **PW** | Playwright — browser automation for testing |
| **Optimistic UI** | **MANDATORY!** UI updates INSTANTLY, server syncs in background. If server fails, revert. |
| **Svelte 5** | **RUNES ONLY!** `$state`, `$derived`, `$effect`. Always use keys in `{#each}`. See below. |

---

## Svelte 5 Runes (CRITICAL!)

**LocaNext uses Svelte 5 with Runes.** Not Svelte 4. Follow these patterns:

```svelte
let count = $state(0);                                    // State
let doubled = $derived(count * 2);                        // Derived
$effect(() => { console.log(count); });                   // Effect
items.push(newItem);                                      // Array mutation (proxied)
{#each items as item (item.id)}                           // ALWAYS use keys
let deletingIds = $state(new Set());                      // Optimistic UI tracking
let visible = $derived(items.filter(i => !deletingIds.has(i.id)));
```

**Common Mistakes:** `export let` instead of `$state` | Missing keys in `{#each}` | Using `$:` (Svelte 4)

---

## XML Language Data: Newline = `<br/>` (CRITICAL!)

**Newlines in XML = `<br/>` tags. The ONLY correct format.**

```xml
KR="첫 번째 줄<br/>두 번째 줄"    <!-- ✅ CORRECT -->
KR="첫 번째 줄&#10;두 번째 줄"    <!-- ❌ WRONG — breaks everything -->
```

ALL tools MUST preserve `<br/>` tags when reading, processing, and writing XML language data.

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

## Development Protocol

**DEV testing first, build only at milestones.**

| DEV Testing | Windows Build |
|-------------|---------------|
| Instant feedback (<1s) | 15+ min build cycle |
| HMR + Playwright | CDP needed |
| Use for: All UI work | Use for: Final validation |

| What | Where | Login | How |
|------|-------|-------|-----|
| **DEV** | localhost:5173 | admin/admin123 | Playwright |
| **Windows App** | Playground | admin/admin123 | CDP (`node testing_toolkit/cdp/login.js`) |

**WSL paths:**
- Screenshots: `/mnt/c/Users/MYCOM/Pictures/Screenshots/`
- Node.js: `/mnt/c/Program\ Files/nodejs/node.exe`
- PowerShell: `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe`

---

## Critical Rules

1. **DOCS FIRST** — Before any protocol task: STOP → READ THE DOC → THEN ACT. Skipping docs = wrong approach = wasted time.
2. **ALWAYS CHOOSE HARD** — No shortcuts. EASY = tech debt. HARD = survives forever.
3. **Sacred Scripts** — XLSTransfer, KR Similar, QuickSearch: never change a byte. Rest of RFC = reference to copy patterns from.
4. **No Backend Mods** — Only wrapper layers (API, GUI)
5. **Logger Only** — Never `print()`, always `logger`
6. **Dual Push** — Always push to both GitHub and Gitea:
   ```
   git push origin main && ./scripts/gitea_control.sh start && git push gitea main && ./scripts/gitea_control.sh stop
   ```
7. **CI: Two Systems** — LocaNext → Gitea CI (Windows runner, `git push gitea main`). NewScripts → GitHub Actions (`git push origin main`). Don't confuse them.
8. **WSL ↔ Windows** — CDP tests run from WSL via `/mnt/c/Program\ Files/nodejs/node.exe`
9. **Fix Everything** — No defer, no excuses
10. **NEVER RESTART** — STOP → CLEAN → INVESTIGATE → FIX → START
11. **VERIFY WITH TESTS** — Never assume. Playwright headless. Screenshots. HARD EVIDENCE.
12. **GITEA: STOP/START > RESTART** — Never use restart. Gitea uses ~60% CPU idle — don't leave running.
13. **BUILD STATUS = SQLite** — Always query, never guess:
    ```bash
    python3 -c "
    import sqlite3
    c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
    c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 3')
    STATUS = {0:'UNKNOWN', 1:'SUCCESS', 2:'FAILURE', 5:'WAITING', 6:'RUNNING', 7:'BLOCKED'}
    for r in c.fetchall(): print(f'Run {r[0]}: {STATUS.get(r[1], r[1]):8} - {r[2]}')"
    ```
    STATUS 6 = RUNNING — just WAIT, don't investigate.
14. **SW FIRST** — Check Gitea via Shell Wrapper: `./scripts/gitea_control.sh status`
15. **STUPID vs ELEGANT** — Don't fix stupid code, DELETE it. Find the elegant way.
16. **NO GREP FOR DEBUG** — Read FULL logs with `cat`/`tail`. Grep hides context.

---

## Quick Commands

```bash
./scripts/check_servers.sh                    # DEV servers + rate limit
./scripts/start_all_servers.sh --with-vite    # Start everything
./scripts/check_servers.sh --clear-ratelimit  # Clear rate limit
DEV_MODE=true python3 server/main.py          # Backend only
cd locaNext && npm run electron:dev           # Desktop app
./scripts/gitea_control.sh start              # Gitea CI/CD
./scripts/playground_install.sh --launch --auto-login  # Fresh install
./scripts/db_manager.sh status -v             # DB status
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

### I DO THE WORK — No Action Verbs to User

**NEVER say "You" + verb.** I code, I test, I build, I install, I verify, I fix.

| WRONG | RIGHT |
|-------|-------|
| "You should run..." | I run the command myself |
| Push without testing | Test with Playwright BEFORE push |
| Assume fixes work | Screenshots, get PROOF |
| "Try restarting" | STOP → CLEAN → INVESTIGATE → FIX → START |

### Build/Deploy Workflow

```
1. CODE → 2. TEST (Playwright headless, screenshots) → 3. PUSH (GitHub + Gitea)
→ 4. WAIT (SQLite query for build status) → 5. INSTALL (playground_install.sh)
→ 6. VERIFY (CDP tests, screenshots = proof)
```

### PRXR — For Non-Trivial Changes

Plan → 5-Agent Review → Fix Plan → Execute → 5-Agent Review → Fix → Final Check.
Full protocol: [docs/protocols/PRXR.md](docs/protocols/PRXR.md)

---

## Claude Behavior

1. **Be frank** — Bad idea? Say so
2. **Independent** — Give honest opinions
3. **Optimal first** — Best approach first
4. **I do the work** — Never tell user to do things I should do myself

---

## URLs

| Service | URL |
|---------|-----|
| Backend | http://localhost:8888 |
| API Docs | http://localhost:8888/docs |
| Gitea | http://172.28.150.120:3000 |

---

*Hub file — details in linked docs. Last updated: 2026-02-26*
