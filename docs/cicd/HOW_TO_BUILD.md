# How to Build

**Quick guide to triggering CI/CD builds**

---

## 3 Build Modes

| Mode | Trigger | Description |
|------|---------|-------------|
| **Build LIGHT** | `Build LIGHT - desc` | Full official build (~200MB) |
| **Build FULL** | `Build FULL - desc` | Same + bundled AI model (~2GB) |
| **TROUBLESHOOT** | `TROUBLESHOOT` | Smart checkpoint: resume from last failure |

---

## Quick Start

```bash
# Official build
echo "Build LIGHT - feature X" >> GITEA_TRIGGER.txt
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
│  7. When done: Build LIGHT (official clean build)                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key:** Checkpoint persists across CI runs (stored in `~/.locanext_checkpoint` on host runner).

---

## Mode Comparison

| Mode | Checkpoint | Build Artifact | Use Case |
|------|------------|----------------|----------|
| Build LIGHT | Clears | Yes (ZIP) | Official release |
| Build FULL | Clears | Yes (ZIP+model) | Full release |
| TROUBLESHOOT | Saves/Resumes | No | Fast debugging iteration |

---

## What Happens

```
You push "Build LIGHT"
         ↓
Pipeline generates version: 25.1213.1640
         ↓
Injects into all files automatically
         ↓
Runs 900+ tests
         ↓
Builds Windows portable ZIP
         ↓
Done! Artifact in installer_output/
```

---

## Monitoring Build

```bash
# Check Gitea UI
http://localhost:3000/neilvibe/LocaNext/actions

# Check latest logs
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -3

# Check errors
cat ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log | grep -E "FAILED|error"
```

---

## Build Output

| File | Location |
|------|----------|
| Portable ZIP | `installer_output/LocaNext_v25.1213.1640_Portable.zip` |
| Auto-updater | `installer_output/latest.yml` |

---

*Last updated: 2025-12-13*
