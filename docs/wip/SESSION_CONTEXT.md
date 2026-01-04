# Session Context

> Last Updated: 2026-01-04 (Session 26 - Launcher + Mode Switching COMPLETE)

---

## STABLE CHECKPOINT

**Post-Session 26:** Pending Build 453 | **Date:** 2026-01-04

P9 Launcher + Mode Switching COMPLETE. Ready to commit.

---

## Current State

**Build:** 453 (pending) | **Open Issues:** 0
**Tests:** 8 Launcher + 486 API passed, 0 failed
**Status:** P9 Launcher + Offline/Online Mode Switching COMPLETE!

---

## SESSION 26 COMPLETE ✅

### P9: Launcher + Mode Switching ✅ DONE

**Beautiful game-launcher style first screen:**

| Component | File | Status |
|-----------|------|--------|
| Launcher Store | `src/lib/stores/launcher.js` | ✅ NEW |
| Launcher UI | `src/lib/components/Launcher.svelte` | ✅ NEW |
| Layout Integration | `src/routes/+layout.svelte` | ✅ MODIFIED |
| Mode Switching | `src/lib/components/sync/SyncStatusPanel.svelte` | ✅ MODIFIED |
| Logger Debug | `src/lib/utils/logger.js` | ✅ MODIFIED |
| Tests | `tests/launcher.spec.js` | ✅ 8 TESTS |

**Tech Stack:** Svelte 5 (`$state`, `$derived`), Electron 39, Carbon Components

**What Was Built:**
```
┌─────────────────────────────────────┐
│              LocaNext               │  ← Gradient logo
│    Professional Localization        │
│           v25.1214.2330             │
│                                     │
│    ● Central Server Connected       │  ← Server status
│                                     │
│   ╭─────────────╮ ╭─────────────╮   │
│   │Start Offline│ │   Login     │   │  ← Two paths
│   │ No account  │ │ Connect to  │   │
│   │   needed    │ │   server    │   │
│   ╰─────────────╯ ╰─────────────╯   │
│                                     │
├─────────────────────────────────────┤
│  UPDATE PANEL (when available)      │  ← Industry-style
│  ████████████░░░░░ 68% | 12/18 MB   │
└─────────────────────────────────────┘
```

**Mode Switching Flow:**
1. Start Offline → App works without login
2. Click Sync Panel → "Switch to Online" button
3. Login form appears inside Sync Dashboard
4. Enter credentials → Switches to Online mode
5. Green "Online" status, full sync capabilities

**All 8 Tests Passing:**
- Launcher displays correctly
- Server status works
- Start Offline works
- Login works
- Mode switching (offline → online) works
- Cancel login form works

### FilesPage Bug Fixes ✅ DONE

| Bug | Fix |
|-----|-----|
| Project creation navigates back | Now stays in platform context |
| Path duplication on refresh | Created `reloadCurrentFolderContents()` helper |
| Platform context lost | Added `preservePath` parameter |
| Missing optimistic UI | Added to createProject, createFolder, createPlatform |

---

## PRIORITIES (Updated)

| Priority | Feature | Status |
|----------|---------|--------|
| **P9** | **Launcher + Offline/Online** | 📋 PLANNING |
| P8 | Dashboard Overhaul | PLANNED |

### P9: Launcher + Offline/Online Mode

Combines three powerful features:
1. **Launcher Window** - Beautiful pre-login screen
2. **Patch Updates** - Download only changed components (97% savings)
3. **Offline Mode** - Work without login, switch to online when needed

**Implementation Phases:**
| Phase | Task |
|-------|------|
| 1 | Launcher Window (server status, update check) |
| 2 | Offline Mode Foundation (SQLite, no-auth user) |
| 3 | Mode Switching (Online/Offline toggle in app) |
| 4 | Database Adapter (SQLite ↔ PostgreSQL abstraction) |
| 5 | Sync Engine (queue changes, sync on mode switch) |

---

## OPEN ISSUES (0)

All issues resolved!

---

## KEY FILES (Session 26)

### Patch Update System
| File | Purpose |
|------|---------|
| `locaNext/electron/patch-updater.js` | Component-based delta updates |
| `locaNext/electron/preload.js` | IPC bridge for patch functions |
| `locaNext/electron/main.js` | IPC handlers |
| `UpdateModal.svelte` | Beautiful patch update UI |
| `.gitea/workflows/build.yml` | Manifest generation in CI |

### Bug Fixes
| File | Changes |
|------|---------|
| `FilesPage.svelte` | `reloadCurrentFolderContents()`, `preservePath`, optimistic UI |

---

## ARCHITECTURE

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ SQLite (offline storage)  ←   ├─ LDM rows, TM entries
├─ FAISS indexes (local)         └─ Logs
└─ Qwen model (optional)

LAUNCHER (NEW):
├─ Pre-login window
├─ Server status check (no auth)
├─ Patch update download
├─ [Start Offline] or [Login]

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, no login needed)
```

---

## QUICK COMMANDS

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Check servers
./scripts/check_servers.sh

# Playwright tests
cd locaNext && npx playwright test

# Build trigger
echo "Build NNN" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build NNN: Description" && git push origin main && git push gitea main
```

---

*Session 26 | Build 452 pending | Patch System DONE, Launcher PLANNING*
