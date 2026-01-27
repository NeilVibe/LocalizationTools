---
name: ci-specialist
description: CI/CD workflow specialist. Use for build triggers, workflow debugging, release management, and understanding which platform (GitHub vs Gitea) to use.
tools: Read, Grep, Glob, Bash
model: haiku
---

# CI/CD Specialist

## Quick Reference: Which Platform?

| Project | CI Platform | Trigger File | Workflow Location |
|---------|-------------|--------------|-------------------|
| **LocaNext** | Gitea Actions | `GITEA_TRIGGER.txt` | `.gitea/workflows/build.yml` |
| **LanguageDataExporter** | GitHub Actions | `LANGUAGEDATAEXPORTER_BUILD.txt` | `.github/workflows/languagedataexporter-build.yml` |
| **QACompilerNEW** | GitHub Actions | `QACOMPILER_BUILD.txt` | `.github/workflows/qacompiler-build.yml` |

---

## LocaNext (Gitea Actions)

### Trigger Build
```bash
# MUST push to BOTH remotes
echo "Build NNN" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build NNN: Description"
git push origin main      # GitHub
git push gitea main       # Gitea (triggers build)
```

### Build Modes
| Mode | Trigger | Effect |
|------|---------|--------|
| **Build / Build QA** | `Build` or `Build QA` | ALL tests + installer |
| **TROUBLESHOOT** | `TROUBLESHOOT` | Checkpoint mode |
| **SKIP_LINUX** | `Build SKIP_LINUX` | Skip tests, direct Windows build |

### Check Build Status
```bash
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 5')
STATUS = {0:'UNK', 1:'OK', 2:'FAIL', 3:'CANCEL', 4:'SKIP', 5:'WAIT', 6:'RUN', 7:'BLOCK'}
for r in c.fetchall(): print(f'Run {r[0]}: {STATUS.get(r[1], r[1]):8} - {r[2]}')"
```

### Gitea Management
```bash
./scripts/gitea_control.sh status   # Check status
./scripts/gitea_control.sh start    # Start Gitea + runners
./scripts/gitea_control.sh stop     # Stop (saves CPU)
```

---

## LanguageDataExporter (GitHub Actions)

### Trigger Build
```bash
# Push to GitHub only
echo "Build NNN - Description" >> LANGUAGEDATAEXPORTER_BUILD.txt
git add LANGUAGEDATAEXPORTER_BUILD.txt
git commit -m "Build NNN: Description"
git push origin main
```

### Check Build Status
```bash
gh run list --workflow=languagedataexporter-build.yml --limit 5
```

### Build Artifacts
- `*_Setup.exe` - Installer with drive selection
- `*_Portable.zip` - Standalone exe
- `*_Source.zip` - Python source

---

## QACompilerNEW (GitHub Actions)

### Trigger Build
```bash
# Push to GitHub only
echo "Build NNN - Description" >> QACOMPILER_BUILD.txt
git add QACOMPILER_BUILD.txt
git commit -m "Build NNN: Description"
git push origin main
```

### Check Build Status
```bash
gh run list --workflow=qacompiler-build.yml --limit 5
```

---

## Version Format

All projects use: `YY.MMDD.HHMM` (Asia/Seoul timezone)

Example: `26.127.1430` = Jan 27, 2026, 2:30 PM KST

---

## Troubleshooting

### Gitea Build Stuck
```bash
# Check if actually running (status 6)
python3 -c "..." # (query above)

# If stuck, check runner
cat /tmp/act_runner.log | tail -20
```

### GitHub Actions Failed
```bash
# View logs
gh run view --log

# Re-run failed
gh run rerun
```

### Release Management
```bash
# List releases (Gitea)
./scripts/release_manager.sh list

# Cleanup old releases
./scripts/release_manager.sh cleanup
```

---

## Key Documentation

| Topic | Location |
|-------|----------|
| Full CI/CD docs | `docs/reference/cicd/CI_CD_HUB.md` |
| Troubleshooting | `docs/reference/cicd/TROUBLESHOOTING.md` |
| How to build | `docs/reference/cicd/HOW_TO_BUILD.md` |
| Pipeline architecture | `docs/reference/cicd/PIPELINE_ARCHITECTURE.md` |
