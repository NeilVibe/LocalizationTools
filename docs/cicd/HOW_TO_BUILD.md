# How to Build

**Quick guide to triggering CI/CD builds**

---

## Build Modes

| Mode | Trigger | Platform | Description |
|------|---------|----------|-------------|
| **QA** | `Build QA` | Both | ALL tests + light installer (~150MB) |
| **QA FULL** | `Build QA FULL` | Gitea only | ALL tests + offline installer (~2GB) [TODO] |
| **TROUBLESHOOT** | `TROUBLESHOOT` | Both | Smart checkpoint: resume from last failure |

**QA is the default.** Workers technology makes 1000+ tests fast.

---

## Quick Start

```bash
# QA build (default - all tests)
echo "Build QA" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Troubleshoot mode (saves checkpoint on failure)
echo "TROUBLESHOOT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Troubleshoot" && git push origin main && git push gitea main
```

---

## TROUBLESHOOT Mode (Smart Checkpoint)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TROUBLESHOOT WORKFLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Trigger: TROUBLESHOOT                                        │
│     ↓                                                            │
│  2. CI checks for existing checkpoint                            │
│     ├── No checkpoint? Run all tests                             │
│     └── Checkpoint exists? Run that test first                   │
│     ↓                                                            │
│  3. If test FAILS:                                               │
│     → Save checkpoint to ~/.locanext_checkpoint (PERSISTENT)     │
│     → Exit with failure                                          │
│     ↓                                                            │
│  4. Fix the code                                                 │
│     ↓                                                            │
│  5. Trigger: TROUBLESHOOT (again)                                │
│     → Runs failed test first                                     │
│     → If passes, continues remaining tests                       │
│     ↓                                                            │
│  6. Repeat 3-5 until all tests pass                              │
│     ↓                                                            │
│  7. When done: Build QA (official clean build)                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key:** Checkpoint persists across CI runs (stored in `~/.locanext_checkpoint` on host runner).

---

## Mode Comparison

| Mode | Checkpoint | Build Artifact | Use Case |
|------|------------|----------------|----------|
| QA | Clears | Yes (~150MB) | Official release |
| QA FULL | Clears | Yes (~2GB) | Offline release (Gitea only) |
| TROUBLESHOOT | Saves/Resumes | No | Fast debugging iteration |

---

## What Happens

```
You push "Build QA"
         ↓
Pipeline generates version: 25.1213.1640
         ↓
Injects into all files automatically
         ↓
Runs 1000+ tests
         ↓
Builds Windows installer (.exe)
         ↓
Done! Artifact in installer_output/
```

---

## Monitoring Build

### Quick Status Check (SQL)

```bash
# Check build status via Gitea SQLite database
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 5')
STATUS = {0:'UNKNOWN', 1:'SUCCESS', 2:'FAILURE', 3:'CANCELLED', 4:'SKIPPED', 5:'WAITING', 6:'RUNNING', 7:'BLOCKED'}
for r in c.fetchall():
    print(f'Run {r[0]}: {STATUS.get(r[1], r[1]):8} - {r[2]}')"
```

**Status codes:** 0=UNKNOWN, 1=SUCCESS, 2=FAILURE, 3=CANCELLED, 4=SKIPPED, 5=WAITING, **6=RUNNING**, 7=BLOCKED

### Other Methods

```bash
# Gitea UI (if available)
http://172.28.150.120:3000/neilvibe/LocaNext/actions

# Check latest logs (backup method)
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -3
```

---

## Build Output

| File | Location |
|------|----------|
| Portable ZIP | `installer_output/LocaNext_v25.1213.1640_Portable.zip` |
| Auto-updater | `installer_output/latest.yml` |

---

## After Build: INSTALL vs UPDATE

**⚠️ These are COMPLETELY DIFFERENT operations.**

| | UPDATE | INSTALL |
|--|--------|---------|
| **What** | Auto-updater downloads new version | Fresh installation from .exe |
| **When** | App already installed (most common!) | First time, clean slate, testing first-run |
| **Time** | 30 sec - 2 min | 2-5 min |
| **How** | Open app → notification → Download → Restart | `./scripts/playground_install.sh` |

### UPDATE (Most Common)

```
1. Open LocaNext (already installed in Playground)
2. App auto-checks on startup
3. Download notification appears
4. Click "Download" → "Install & Restart"
5. App restarts with new version
```

### INSTALL (Only When Needed)

```bash
./scripts/playground_install.sh --launch --auto-login
```

Use INSTALL only for:
- First time setup
- Testing first-run experience
- Clean slate testing
- Major version upgrades

**See [DOC-001: Install vs Update Confusion](../wip/DOC-001_INSTALL_VS_UPDATE_CONFUSION.md) for details.**

---

*Last updated: 2025-12-28*
