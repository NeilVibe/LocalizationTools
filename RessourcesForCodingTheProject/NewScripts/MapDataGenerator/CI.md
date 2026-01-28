# MapDataGenerator CI/CD Documentation

## Overview

MapDataGenerator uses GitHub Actions for automated builds and releases.

## Trigger File

**Location**: `MAPDATAGENERATOR_BUILD.txt` (repo root)

Add a line like `Build 001` to trigger a build when pushed to main.

## Workflow

**File**: `.github/workflows/mapdatagenerator-build.yml`

### Jobs

1. **validation** - Check build trigger
2. **safety-checks** - Syntax, imports, Flake8, security audit
3. **build-and-release** - PyInstaller build + Inno Setup installer

### Version Format

Auto-generated: `YY.MMDD.HHMM` (Korean time)

Example: `25.0128.1430`

## Trigger Build

```bash
# Add build trigger
echo "Build 001" >> MAPDATAGENERATOR_BUILD.txt
git add -A
git commit -m "Build 001: MapDataGenerator"
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

## Validation Checks

1. **Python Syntax** - `py_compile` on all `.py` files
2. **Module Imports** - Test importing all core modules
3. **Flake8** - Critical errors only (E9, F63, F7, F82)
4. **Security Audit** - `pip-audit` (non-blocking)

## Dependencies

See `requirements.txt`:

- lxml >= 4.9.0
- Pillow >= 10.0.0
- pillow-dds >= 1.0.0
- matplotlib >= 3.7.0

## Troubleshooting

### Build Fails at Validation

Check the safety-checks job logs for:
- Syntax errors
- Import failures
- Undefined names (Flake8 F82)

### Build Fails at PyInstaller

Common issues:
- Missing hidden imports (add to `.spec` file)
- DLL dependencies on Windows

### Installer Fails

- Check Inno Setup script path
- Verify `dist/MapDataGenerator` folder exists
