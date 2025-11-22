# Installer Output Directory

This directory contains compiled Windows installers created by Inno Setup.

## Files Generated Here:

- `LocaNext_v2511221939_Setup.exe` - Windows installer (~2GB with BERT model)

## Build Process:

1. Electron builds the app: `locaNext/dist-electron/win-unpacked/`
2. Inno Setup packages it with:
   - Electron app binaries
   - Korean BERT model (446MB from `models/kr-sbert/`)
   - Documentation
   - User guides
3. Output: Single `.exe` installer file

## Usage:

```bash
# Windows only - Compile installer with Inno Setup
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_electron.iss

# Output appears here as:
# LocaNext_v<VERSION>_Setup.exe
```

## GitHub Actions:

The automated build workflow (`.github/workflows/build-electron.yml`) will:
1. Build Electron app
2. Compile this installer
3. Upload as artifact
4. Create GitHub Release with download link

## Note:

This directory is gitignored (installers are too large for git).
Download installers from GitHub Releases instead.
