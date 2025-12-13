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
