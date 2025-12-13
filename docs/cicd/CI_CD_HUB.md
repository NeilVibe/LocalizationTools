# CI/CD Hub

**LocaNext Continuous Integration & Deployment**

---

## Quick Reference

| Need | Go To |
|------|-------|
| Build failed? | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| Pipeline architecture? | [PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md) |
| Version format? | [VERSION_SYSTEM.md](VERSION_SYSTEM.md) |
| Trigger a build? | [HOW_TO_BUILD.md](HOW_TO_BUILD.md) |

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LOCANEXT CI/CD PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TRIGGER: Push to main with "Build LIGHT" in GITEA_TRIGGER.txt     │
│                          ↓                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ JOB 1: check-build-trigger (Linux)                          │   │
│  │ - Parse GITEA_TRIGGER.txt                                   │   │
│  │ - AUTO-GENERATE version: YY.MMDD.HHMM                       │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ JOB 2: safety-checks (Linux)                                │   │
│  │ - Inject version into all files                             │   │
│  │ - Run pytest (900+ tests)                                   │   │
│  │ - Security audit (pip-audit)                                │   │
│  │ - Version unification check                                 │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ JOB 3: build-windows (Windows self-hosted)                  │   │
│  │ - Inject version into all files                             │   │
│  │ - Build Electron app                                        │   │
│  │ - Create portable ZIP                                       │   │
│  │ - Generate latest.yml for auto-updater                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Version System (Factorized)

**UNIFIED FORMAT:** `YY.MMDD.HHMM` (e.g., `25.1213.1540`)

```
Pipeline has EXECUTIVE POWER:
- Auto-generates version at build time
- Injects into ALL files automatically
- No manual version updates needed

VERSION = "25.1213.1540"
         ↓
    ┌────┴────────────────────────────────────┐
    ↓         ↓              ↓          ↓     ↓
version.py  package.json  .iss files   CI   UI
```

**Format benefits:**
- Valid semver (25.1213.1540 = X.Y.Z)
- Human readable (Dec 13, 2025, 15:40 KST)
- Auto-increments with time
- Works everywhere

---

## Build Triggers

### How to Trigger a Build

```bash
# 1. Add trigger line to GITEA_TRIGGER.txt
echo "Build LIGHT - your description" >> GITEA_TRIGGER.txt

# 2. Commit and push
git add GITEA_TRIGGER.txt
git commit -m "Trigger build"
git push origin main && git push gitea main
```

### Build Types & Modes

| Mode | Trigger | Description |
|------|---------|-------------|
| **Build LIGHT** | `Build LIGHT - desc` | ~200MB, model downloads on first run |
| **Build FULL** | `Build FULL - desc` | ~2GB, AI model bundled |
| **TEST ONLY** | `TEST ONLY path/to/test.py` | Run single test file (fast iteration) |
| **TROUBLESHOOT** | `TROUBLESHOOT` | Run all tests, save checkpoint on failure |
| **CONTINUE** | `CONTINUE` | Resume from checkpoint (same CI run only) |

**Note:** Mode keywords must be at **start** of line.

---

## Common Issues & Fixes

### 1. Version Timestamp Too Old

```
❌ Version timestamp TOO FAR: 2512131330 (KST) is 1.1h away from now
```

**This is now AUTO-FIXED by pipeline.** Version is generated at build time.

### 2. Version Check Failed (Documentation)

```
❌ README.md: Expected '25.1213.1503', found '25.1213.1540'
```

**Fixed:** Documentation files are now WARN-ONLY, don't block builds.

### 3. Test Error: use_postgres

```
TypeError: setup_database() got an unexpected keyword argument 'use_postgres'
```

**Fixed:** Removed deprecated parameter from all scripts.

---

## File Locations

| File | Purpose |
|------|---------|
| `.gitea/workflows/build.yml` | Main Gitea pipeline |
| `.github/workflows/build-electron.yml` | GitHub Actions mirror |
| `GITEA_TRIGGER.txt` | Build trigger file |
| `version.py` | Version source of truth |
| `scripts/check_version_unified.py` | Version validation |

---

## Runners

| Runner | Platform | Type | Location |
|--------|----------|------|----------|
| Linux | Ubuntu | Host mode | WSL2 |
| Windows | Windows 11 | Self-hosted | Local machine |

---

## Log Locations

```bash
# Find latest build logs
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -5

# Check for errors
grep -i "error\|failed\|❌" ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log

# Read full log
cat ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/<number>.log
```

---

## Related Documentation

- [../build/BUILD_TROUBLESHOOTING.md](../build/BUILD_TROUBLESHOOTING.md) - Detailed troubleshooting
- [../build/BUILD_AND_DISTRIBUTION.md](../build/BUILD_AND_DISTRIBUTION.md) - Build process details
- [../development/FACTORIZATION_PROTOCOL.md](../development/FACTORIZATION_PROTOCOL.md) - Version factorization

---

*Last updated: 2025-12-13*
