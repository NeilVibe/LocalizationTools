# LanguageDataExporter CI/CD Guide

## Build System: GitHub Actions

**Workflow:** `.github/workflows/languagedataexporter-build.yml`
**Trigger File:** `LANGUAGEDATAEXPORTER_BUILD.txt` (at repo root)

---

## How to Trigger a Build

```bash
# 1. Add trigger line
echo "Build NNN: <description>" >> LANGUAGEDATAEXPORTER_BUILD.txt

# 2. Commit and push
git add -A && git commit -m "Build NNN: <description>" && git push origin main
```

---

## Check Build Status

```bash
# Quick status (last 3 builds)
gh run list --workflow=languagedataexporter-build.yml --limit 3

# Watch live logs
gh run watch

# View specific run
gh run view <run-id>
```

---

## What the Build Does

### Job 1: Code Validation (Ubuntu)
1. **Syntax Check** - `py_compile` on all .py files
2. **Import Check** - Validates all modules can be imported
3. **Flake8** - Critical errors only (E9, F63, F7, F82)
4. **Security Audit** - `pip-audit` for vulnerable dependencies

### Job 2: Build & Release (Windows)
1. **PyInstaller** - Creates standalone executable
2. **Inno Setup** - Creates installer with drive selection
3. **Portable ZIP** - Creates no-install version
4. **GitHub Release** - Uploads all artifacts

---

## Build Outputs

| Artifact | Description |
|----------|-------------|
| `LanguageDataExporter_vX.X.X_Setup.exe` | Installer (recommended) |
| `LanguageDataExporter_vX.X.X_Portable.zip` | No-install version |
| `LanguageDataExporter_vX.X.X_Source.zip` | Source code |

---

## Version Format

`YY.MMDD.HHMM` (Korean time, auto-generated)

Example: `26.128.1934` = 2026-01-28 19:34

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Build not triggered | Check trigger file has new "Build" line |
| Import validation fails | Check `requirements.txt` has all dependencies |
| Flake8 fails | Fix undefined names, unused imports |
| PyInstaller fails | Check `.spec` file and hidden imports |

---

## Files

| File | Purpose |
|------|---------|
| `LanguageDataExporter.spec` | PyInstaller configuration |
| `installer/LanguageDataExporter.iss` | Inno Setup script |
| `requirements.txt` | Python dependencies |
| `config.py` | Contains VERSION constant |

---

*See also: [NewScripts README](../README.md) for full CI/CD guide*
