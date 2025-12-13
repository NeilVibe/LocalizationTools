# How to Build

**Quick guide to triggering CI/CD builds**

---

## Quick Start

```bash
# 1. Add trigger
echo "Build LIGHT - your description" >> GITEA_TRIGGER.txt

# 2. Commit and push
git add GITEA_TRIGGER.txt
git commit -m "Trigger build: your description"
git push origin main && git push gitea main
```

That's it! Pipeline auto-generates version and builds.

---

## Build Types

| Type | Trigger | Size | Use Case |
|------|---------|------|----------|
| LIGHT | `Build LIGHT` | ~200MB | Regular builds, testing |
| FULL | `Build FULL` | ~2GB | Release with bundled AI model |
| TEST ONLY | `TEST ONLY tests/path.py` | N/A | Fast iteration on test fixes |

---

## TROUBLESHOOT MODE (Checkpoint/Resume)

When build fails, use TROUBLESHOOT mode for fast iteration:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TROUBLESHOOT WORKFLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. TROUBLESHOOT - Start troubleshooting session                 │
│     ↓                                                            │
│  2. Tests run, FAILS at test X                                   │
│     → Checkpoint saved: "test X"                                 │
│     ↓                                                            │
│  3. Fix the issue                                                │
│     ↓                                                            │
│  4. CONTINUE - Resume from checkpoint                            │
│     → Runs test X first                                          │
│     → If passes, continues remaining tests                       │
│     ↓                                                            │
│  5. Repeat 3-4 until all pass                                    │
│     ↓                                                            │
│  6. Build LIGHT - Official clean build                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Commands

```bash
# Start troubleshooting (saves checkpoints on failure)
echo "TROUBLESHOOT - Start debugging session" >> GITEA_TRIGGER.txt

# After fixing, resume from last failure
echo "CONTINUE - Resume from checkpoint" >> GITEA_TRIGGER.txt

# When all passes, do official build
echo "Build LIGHT - Official release" >> GITEA_TRIGGER.txt
```

---

## TEST ONLY MODE (Single File)

Run only a specific test file:

```bash
echo "TEST ONLY tests/integration/server_tests/test_api_endpoints.py" >> GITEA_TRIGGER.txt
```

---

## Mode Comparison

| Mode | Trigger | Checkpoints | Build | Use Case |
|------|---------|-------------|-------|----------|
| OFFICIAL | `Build LIGHT` | No | Yes | Release build |
| TROUBLESHOOT | `TROUBLESHOOT` | Saves on fail | No | Start debugging |
| CONTINUE | `CONTINUE` | Resumes | No | After fix |
| TEST ONLY | `TEST ONLY path` | No | No | Single file test |

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

### Check if build started

```bash
# Gitea UI
http://localhost:3000/neilvibe/LocaNext/actions
```

### Check build logs

```bash
# Find latest
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -3

# Check errors
grep -i "error\|failed" ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log
```

---

## Build Failed?

1. **Check logs** (see above)
2. **Read** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **Fix** the issue
4. **Push** new trigger

---

## Build Output

After successful build:

| File | Location |
|------|----------|
| Portable ZIP | `installer_output/LocaNext_v25.1213.1640_Portable.zip` |
| Auto-updater manifest | `installer_output/latest.yml` |

---

## Tips

### Trigger Format Matters

Mode keywords must be at the **start** of the line:

```bash
# Correct:
TEST ONLY tests/path/to/test.py
TROUBLESHOOT
CONTINUE
Build LIGHT - description

# Wrong (mode keyword in description):
Build LIGHT - TROUBLESHOOT fix      # Will detect as Build, not TROUBLESHOOT
TEST ONLY tests/foo.py - CONTINUE   # Correct - CONTINUE is in description
```

### Don't Specify Version

```bash
# Old way (don't do this)
echo "Build LIGHT v2512131540" >> GITEA_TRIGGER.txt

# New way (let pipeline decide)
echo "Build LIGHT - feature X" >> GITEA_TRIGGER.txt
```

### Always Dual Push

```bash
# Push to both remotes
git push origin main && git push gitea main
```

### Check Before Push

```bash
# Run tests locally first
python3 -m pytest tests/ -v --tb=short

# Check version system
python3 scripts/check_version_unified.py
```

---

*Last updated: 2025-12-13*
