# MapDataGenerator CI/CD Documentation

## Overview

MapDataGenerator uses GitHub Actions for automated builds and releases with **comprehensive 5-check validation**.

## Local Validation (RUN BEFORE PUSHING!)

```bash
# Full validation (mirrors CI)
python ci_validate.py

# Quick mode (skip slow checks)
python ci_validate.py --quick

# With fix suggestions
python ci_validate.py --fix

# Skip GUI test (headless systems)
python ci_validate.py --no-gui

# With Xvfb on Linux
xvfb-run python ci_validate.py
```

**ALWAYS run `ci_validate.py` before pushing!** It catches errors that would fail CI.

## Trigger File

**Location**: `MAPDATAGENERATOR_BUILD.txt` (repo root)

Add a line like `Build 001` to trigger a build when pushed to main.

## Workflow

**File**: `.github/workflows/mapdatagenerator-build.yml`

### Jobs

1. **validation** - Check build trigger, generate version
2. **safety-checks** - 5 comprehensive validation checks
3. **build-and-release** - PyInstaller build + Inno Setup installer

### Version Format

Auto-generated: `YY.MMDD.HHMM` (Korean time)

Example: `26.0201.1430`

## Trigger Build

```bash
# Add build trigger
echo "Build" >> MAPDATAGENERATOR_BUILD.txt
git add MAPDATAGENERATOR_BUILD.txt
git commit -m "Trigger MapDataGenerator build"
git push origin main
```

## Check Status

```bash
# Via GitHub CLI
gh run list --workflow=mapdatagenerator-build.yml

# View specific run
gh run view <run-id>

# Watch logs
gh run watch
```

## Outputs

After successful build:

- `MapDataGenerator_v{VERSION}_Setup.exe` - Windows installer
- `MapDataGenerator_v{VERSION}_Portable.zip` - Portable ZIP
- `MapDataGenerator_v{VERSION}_Source.zip` - Source code

## Validation Checks (5 Total)

| Check | What It Catches | Blocking? |
|-------|-----------------|-----------|
| 1. Python Syntax | SyntaxError, parse errors | Yes |
| 2. Module Imports | Missing imports (INCLUDING GUI!) | Yes |
| 3. Flake8 | Undefined names, critical errors | Yes |
| 4. Security Audit | Vulnerable dependencies | No (warning) |
| 5. GUI Smoke Test | **ttk/tk runtime crashes** | Yes |

### CHECK 5 is CRITICAL!

The GUI smoke test catches errors that static analysis CANNOT detect:

```python
# This bug passed all static checks but crashed the app:
bg = ttk_frame.cget("background")  # TclError: unknown option "-background"

# The GUI smoke test CATCHES this by actually instantiating the app!
```

## Module Validation List

These modules are validated in CI:

```python
'config',
'core.xml_parser',
'core.language',
'core.linkage',
'core.search',
'core.dds_handler',
'utils.filters',
# GUI modules - CRITICAL! These must be validated!
'gui.app',
'gui.result_panel',
'gui.search_panel',
'gui.map_canvas',
'gui.image_viewer',
'gui.audio_viewer',
```

## Dependencies

See `requirements.txt`:

- lxml >= 4.9.0
- Pillow >= 10.0.0
- pillow-dds >= 1.0.0 (Windows only)
- matplotlib >= 3.7.0

## Troubleshooting

### Build Fails at Validation

1. Run `python ci_validate.py` locally to reproduce
2. Check the safety-checks job logs for:
   - Syntax errors (Check 1)
   - Import failures (Check 2)
   - Undefined names (Check 3 - Flake8 F82)
   - GUI crashes (Check 5)

### GUI Smoke Test Fails

Most common: **ttk vs tk widget API mismatch**

```python
# WRONG - ttk widgets don't support cget("background")
bg = self.frame.cget("background")

# CORRECT - Use ttk.Style
style = ttk.Style()
bg = style.lookup("TLabelframe", "background") or "#f0f0f0"
```

See `VALIDATION_PROTOCOL.md` for full ttk/tk compatibility guide.

### Build Fails at PyInstaller

Common issues:
- Missing hidden imports (add to `.spec` file)
- DLL dependencies on Windows
- Module not in validation list (add to `MODULES_TO_CHECK`)

### Installer Fails

- Check Inno Setup script path
- Verify `dist/MapDataGenerator` folder exists

## Files

| File | Purpose |
|------|---------|
| `ci_validate.py` | Local validation script (run before push!) |
| `VALIDATION_PROTOCOL.md` | Full validation documentation |
| `.github/workflows/mapdatagenerator-build.yml` | CI workflow |
| `MAPDATAGENERATOR_BUILD.txt` | Build trigger file |

---

*Last updated: 2026-02-01*
