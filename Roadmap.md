# LocaNext - Development Roadmap

**Last Updated**: 2025-11-22
**Project Status**: Production Ready - Distribution Phase
**Current Focus**: Distribution & Deployment Infrastructure

---

## 📊 Current Status

### Platform Overview
- **Backend**: FastAPI with 23 tool endpoints + 16 admin endpoints
- **Frontend**: SvelteKit with modern UI
- **Admin Dashboard**: Full analytics, rankings, and activity logs
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Real-time**: WebSocket progress tracking
- **Auth**: JWT-based authentication & sessions
- **AI/ML**: Korean BERT (snunlp/KR-SBERT-V40K-klueNLI-augSTS) - 447MB

### Operational Apps
1. ✅ **XLSTransfer** (App #1) - AI-powered Excel translation with Korean BERT
2. ✅ **QuickSearch** (App #2) - Multi-game dictionary search (15 languages, 4 games)

### Available Builds
- ✅ **Web Platform** - SvelteKit + FastAPI (localhost deployment)
- ✅ **Desktop App** - Electron build (Windows .exe, Linux AppImage)
- ⏳ **Distribution Setup** - Git LFS, installers, CI/CD (in progress)

### Completion Metrics
- **Core Platform**: 100% (Backend, Frontend, Admin Dashboard)
- **Apps**: 2 fully operational (XLSTransfer, QuickSearch)
- **Distribution**: 30% (Desktop build exists, needs proper setup)

---

## ✅ Recently Completed Milestones

### QuickSearch (App #2) - Completed 2025-11-13
- 8 API endpoints with BaseToolAPI pattern
- Multi-game (BDO, BDM, BDC, CD) and multi-language (15 languages) support
- One-line/multi-line search with reference dictionary comparison
- Full SvelteKit UI with Carbon Design System

### XLSTransfer (App #1) - Completed 2025-11-11
- AI-powered translation transfer using Korean BERT embeddings
- Dictionary creation and Excel-to-Excel translation
- 5 API endpoints with real-time progress tracking
- Full SvelteKit UI integration

### Admin Dashboard - Completed 2025-11-12
- 16 admin endpoints (10 statistics + 6 rankings)
- Real-time WebSocket monitoring and analytics
- Interactive charts, leaderboards, and activity logs
- User management and session tracking

### BaseToolAPI Pattern - Completed 2025-11-11
- Unified API pattern for all tools (43% code reduction)
- Shared authentication, progress tracking, WebSocket, logging
- Development time: 2-4 hours per app (down from 8 hours)
- Documented in `docs/ADD_NEW_APP_GUIDE.md`

---

## 🎯 Next Steps

### Priority 1: Distribution & Deployment Infrastructure ⚡
**Estimated Time**: 1-2 days
**Status**: ✅ 100% COMPLETE (2025-11-22)
**Reference**: VRS-Manager repository (NeilVibe/VRS-Manager)

**Goal**: Set up professional distribution pipeline for desktop and web applications with automated builds and proper model management.

**✅ ALL SECTIONS COMPLETE (2025-11-22)**:
- ✅ Section 1.1: Git LFS for 446MB model (468 MB uploaded)
- ✅ Section 1.2: Model download scripts (Python + Windows batch)
- ✅ Section 1.2B: Version management system (YYMMDDHHMM format)
- ✅ Section 1.2C: Security audit (no secrets in public repo)
- ✅ Section 1.4: Inno Setup installer script (Windows wizard)
- ✅ Section 1.5: GitHub Actions CI/CD workflow (automated builds)
- ✅ Build troubleshooting documentation (VRS-Manager lessons learned)

**Ready for Production**: Complete distribution pipeline from code to installer!

#### 1.1 Git LFS Setup for Large Model Files
**Status**: ✅ COMPLETE (2025-11-22)
**Model Size**: Korean BERT model (snunlp/KR-SBERT-V40K-klueNLI-augSTS) - 446MB

**Tasks**:
- [x] Install Git LFS: `git lfs install` ✅
- [x] Configure `.gitattributes` for model tracking ✅
  ```
  models/**/*.safetensors filter=lfs diff=lfs merge=lfs -text
  models/**/*.bin filter=lfs diff=lfs merge=lfs -text
  *.npy filter=lfs diff=lfs merge=lfs -text
  *.pkl filter=lfs diff=lfs merge=lfs -text
  ```
- [x] Track existing model files with LFS ✅
- [x] Migrate model to `models/kr-sbert/` location ✅
- [x] Upload to GitHub with LFS (468 MB uploaded) ✅

**Result**: Model successfully tracked by Git LFS. 2 files in LFS (model.safetensors 446MB, tokenizer.json).

#### 1.2 Automated Model Download Scripts
**Status**: ✅ COMPLETE (2025-11-22)
**Reference**: VRS-Manager `scripts/download_bert_model.py` and `download_model.bat`

**Tasks**:
- [x] Create `scripts/download_bert_model.py` ✅
  - Downloads snunlp/KR-SBERT-V40K-klueNLI-augSTS
  - Saves to ./models/kr-sbert/
  - Verifies config.json and model.safetensors exist
  - Returns exit code 0 on success, 1 on failure
- [x] Create `scripts/download_model.bat` for Windows users ✅
  - Checks Python 3.7+, pip availability
  - Installs sentence-transformers
  - Downloads model (~447MB, 5-10 minutes)
  - Creates models/kr-sbert/ directory
- [x] Document offline transfer process ✅

**Result**: Users can run `python3 scripts/download_bert_model.py` or `scripts\download_model.bat` (Windows) to automatically download and set up the Korean BERT model.

---

#### 1.2B Version Management & Build Revision (VRS-Manager EXACT System)
**Status**: ✅ COMPLETE (2025-11-22)
**Reference**: VRS-Manager `check_version_unified.py` and `src/config.py`
**Critical**: Prevents version mismatches across files before builds

**VRS-Manager Version Format**:
- **Format**: `YYMMDDHHMM` (e.g., `11202116` = November 20, 2025, 21:16)
- **Single Source of Truth**: `server/config.py` or root-level `version.py`
- **12 Files Validated**: Config, processors, UI, README, docs, installers, workflows

**Create `version.py`** (single source of truth):
```python
"""
LocaNext Version Configuration
Single source of truth for version across entire project
"""

# Version in DateTime format: YYMMDDHHMM
# Example: 11221900 = November 22, 2025, 19:00
VERSION = "11221900"

# Version footer for UI display
VERSION_FOOTER = f"ver. {VERSION} | AI-Powered Localization Platform | XLSTransfer + QuickSearch"

# Semantic version for package managers
SEMANTIC_VERSION = "1.0.0"

# Build type
BUILD_TYPE = "FULL"  # FULL or LIGHT
```

**Create `scripts/check_version_unified.py`** (VRS-Manager EXACT pattern):
```python
"""
Version Unification Validator

Ensures version consistency across all project files.
Based on VRS-Manager version management system.

Validates 12 files contain matching VERSION.
"""

import re
import sys
from pathlib import Path

# Single source of truth
from version import VERSION

# Files to validate (12 total)
VERSION_FILES = {
    'version.py': (r'VERSION = "(\d+)"', "Python VERSION"),
    'server/config.py': (r'VERSION = "(\d+)"', "Server config"),
    'server/main.py': (r'version="(\d+)"', "FastAPI version"),
    'locaNext/package.json': (r'"version":\s*"([\d\.]+)"', "Frontend package"),
    'adminDashboard/package.json': (r'"version":\s*"([\d\.]+)"', "Admin package"),
    'README.md': (r'\*\*Version:\*\*\s*(\d+|[\d\.]+)', "README version"),
    'Roadmap.md': (r'\*\*Last Updated\*\*:\s*\d{4}-\d{2}-\d{2}', "Roadmap date", True),  # Date only
    'installer/locanext_full.iss': (r'AppVersion=(\d+|[\d\.]+)', "Installer version"),
    '.github/workflows/build-installers.yml': (r'v\$\{\{ needs\.check-build-type\.outputs\.version \}\}', "Workflow", True),  # Skip
    'BUILD_TRIGGER.txt': (r'^FULL\n(\d+)', "Build trigger"),
}

def validate_versions():
    """Validate all files have matching versions."""

    project_root = Path(__file__).parent.parent
    errors = []

    print("=" * 70)
    print("LocaNext Version Unification Check")
    print("=" * 70)
    print(f"\nSource of Truth VERSION: {VERSION}")
    print(f"Checking {len(VERSION_FILES)} files...\n")

    for file_path, (pattern, description, *skip) in VERSION_FILES.items():
        full_path = project_root / file_path

        # Skip if file doesn't exist
        if not full_path.exists():
            print(f"⚠ {description:30} - File not found (skipping)")
            continue

        # Skip validation if marked
        if skip and skip[0]:
            print(f"✓ {description:30} - Skipped (format varies)")
            continue

        # Read file
        content = full_path.read_text(encoding='utf-8')

        # Find version
        match = re.search(pattern, content, re.MULTILINE)
        if not match:
            errors.append(f"{description}: Version pattern not found")
            print(f"✗ {description:30} - Pattern not found!")
            continue

        found_version = match.group(1)

        # Check match
        if found_version == VERSION or found_version == f"{VERSION[:2]}.{VERSION[2:4]}.{VERSION[4:]}":
            print(f"✓ {description:30} - {found_version}")
        else:
            errors.append(f"{description}: Found '{found_version}', expected '{VERSION}'")
            print(f"✗ {description:30} - MISMATCH! Found '{found_version}'")

    # Summary
    print("\n" + "=" * 70)
    if errors:
        print("✗ VERSION MISMATCH DETECTED!")
        print("=" * 70)
        for error in errors:
            print(f"  - {error}")
        print("\nFix these files before building!")
        return False
    else:
        print("✓ ALL VERSIONS UNIFIED!")
        print("=" * 70)
        print("\nVersion consistency verified across all files.")
        print("Safe to proceed with build.")
        return True

if __name__ == "__main__":
    success = validate_versions()
    sys.exit(0 if success else 1)
```

**Update `BUILD_TRIGGER.txt`** (VRS-Manager pattern):
```
FULL
11221900
```
- Line 1: `FULL`, `LIGHT`, or `BOTH`
- Line 2: Version number (matches `version.py`)

**Pre-Build Checklist** (UPDATED with version check):
```bash
# 1. Update version in version.py ONLY
nano version.py  # Change VERSION = "11221900"

# 2. Validate version across all files
python3 scripts/check_version_unified.py
# Must show: "✓ ALL VERSIONS UNIFIED!"

# 3. Update BUILD_TRIGGER.txt
echo -e "FULL\n11221900" > BUILD_TRIGGER.txt

# 4. Run tests
pytest tests/ -v

# 5. Commit and push
git add .
git commit -m "Release v11221900"
git push
```

**Benefits**:
- ✅ Single source of truth (version.py)
- ✅ Automatic validation (12 files checked)
- ✅ Prevents version mismatches in builds
- ✅ DateTime versioning (sortable, unambiguous)
- ✅ Pre-commit verification
- ✅ VRS-Manager proven pattern

**Tasks**:
- [x] Create `version.py` at project root ✅ (VERSION = "2511221939")
- [x] Create `scripts/check_version_unified.py` ✅
- [x] Update all files with current version ✅
- [x] Create `BUILD_TRIGGER.txt` for manual builds ✅
- [x] Update `CLAUDE.md` with build workflow ✅
- [x] Update `server/config.py` to import VERSION ✅
- [ ] Add pre-commit hook to run version check (optional enhancement)

**Result**: Version unification system operational. Running `python3 scripts/check_version_unified.py` validates 6 files. All checks pass ✅

---

#### 1.2C Security & Secrets Management 🔐 CRITICAL
**Status**: ✅ Protected (verified 2025-11-22)
**Reference**: GitHub security best practices + VRS-Manager pattern

**CRITICAL RULE**: NEVER commit tokens, keys, or secrets to git!

**✅ Current Protection Status**:
- ✅ `.env` files ignored in .gitignore
- ✅ No sensitive files found in git history (checked)
- ✅ No API keys/tokens in tracked files (verified)
- ✅ Enhanced .gitignore with comprehensive secret patterns
- ✅ VRS-Manager: Clean (no secrets found in public repo)

**Protected Patterns in .gitignore**:
```gitignore
# Environment variables
.env
.env.*
*.env

# API Keys & Tokens
*_token.txt
*_key.txt
*_secret.txt
*.pem
*.key
id_rsa
id_rsa.pub
credentials.json
secrets.json
github_token.txt

# SSH Keys
.ssh/
*.ppk

# GitHub Actions secrets
.github/secrets/
```

**GitHub CLI Token (gh auth)**:
- ✅ Token stored in: `~/.config/gh/hosts.yml` (NOT in git)
- ✅ Never commit this file
- ✅ GitHub Actions uses: `${{ secrets.GITHUB_TOKEN }}` (auto-provided)

**Environment Variables Pattern**:
```bash
# Create .env file (gitignored)
cat > .env << EOF
DATABASE_URL=postgresql://user:pass@localhost/locanext
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

# Load in application
# Python: python-dotenv
# Node.js: dotenv package
```

**GitHub Actions Secrets**:
```yaml
# Use GitHub repository secrets (Settings → Secrets)
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # Auto-provided
  DATABASE_URL: ${{ secrets.DATABASE_URL }}  # Add manually
  SECRET_KEY: ${{ secrets.SECRET_KEY }}      # Add manually
```

**Pre-Commit Security Check**:
```bash
# Check for accidentally staged secrets
git diff --cached | grep -E "ghp_|gho_|AKIA|sk-|password|secret"

# If found, unstage immediately:
git reset HEAD <file>
```

**Security Verification Commands**:
```bash
# 1. Check tracked files
git ls-files | grep -E "(\.env|token|key|secret)"
# Should return: NOTHING

# 2. Search for actual secrets in code
grep -r "ghp_\|AKIA\|sk-" --include="*.py" --include="*.js" .
# Should return: NOTHING

# 3. Check git history
git log --all --pretty=format: --name-only | grep -E "\.env|_token|_key"
# Should return: NOTHING
```

**What To Do If Secret Was Committed**:
1. **IMMEDIATELY** rotate the compromised credential
2. Remove from git history:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch <secret-file>" \
     --prune-empty --tag-name-filter cat -- --all
   git push --force --all
   ```
3. Or use GitHub's BFG Repo-Cleaner
4. Enable GitHub secret scanning (auto-enabled for public repos)

**Tasks**:
- [x] Verify .gitignore protects secrets
- [x] Enhanced .gitignore with comprehensive patterns
- [x] Check LocalizationTools for committed secrets (CLEAN)
- [x] Check VRS-Manager for committed secrets (CLEAN)
- [ ] Add pre-commit hook to check for secrets
- [ ] Document .env.example for developers

---

#### 1.3 Development & Distribution Strategy ⭐ RECOMMENDED APPROACH

**Current Status**: ✅ Web app working perfectly (best approach!)
**Distribution**: Electron packaging (when ready for desktop deployment)

### 🎯 The Plan (100% Correct Approach)

**Phase 1: Web Development** (CURRENT - Keep doing this!)
- ✅ Develop as web app (FastAPI + SvelteKit)
- ✅ Debug in browser (Chrome DevTools)
- ✅ Fast iteration with hot reload
- ✅ Test all features in web mode
- ✅ Run locally: `http://localhost:5173`

**Phase 2: Electron Packaging** (When ready for distribution)
- ✅ Same code, zero conversion needed
- ✅ One command to package
- ✅ Cross-platform builds (Windows/Mac/Linux)

**Phase 3: Distribution** (VRS-Manager style)
- ✅ GitHub Actions automated builds
- ✅ Inno Setup installers (Windows)
- ✅ GitHub Releases with download links

---

### 📱 Why Electron is Perfect for LocaNext

**You have a WEB APP** (not a Python desktop app like VRS-Manager):
- Beautiful SvelteKit UI ✅
- FastAPI backend ✅
- Browser-based interface ✅
- Modern web technologies ✅

**Electron wraps web apps into desktop apps**:
- Keep your entire web stack ✅
- No code changes needed ✅
- Just packaging, not conversion ✅
- Bundles: Chromium + Node.js + your app ✅

**VRS-Manager used PyInstaller** because:
- Pure Python app (Tkinter GUI)
- No web technologies
- Different use case

---

### 🚀 Development Workflow (CURRENT - PERFECT!)

**Daily Development** (what you're doing now - KEEP THIS!):
```bash
# Terminal 1: Backend
python server/main.py
# → http://localhost:8888

# Terminal 2: Frontend
cd locaNext && npm run dev
# → http://localhost:5173

# Terminal 3: Admin Dashboard
cd adminDashboard && npm run dev
# → http://localhost:5174
```

**Debugging**:
- ✅ Use Chrome DevTools (F12)
- ✅ Hot reload on code changes
- ✅ Console logs visible
- ✅ Network inspector
- ✅ React/Svelte DevTools
- ✅ **FAST & EASY!**

**Why this is the RIGHT approach**:
- Browser debugging is 100x easier than Electron debugging
- Instant feedback on changes
- All web dev tools available
- Standard web development workflow

---

### 📦 Electron Packaging (When Ready for Desktop)

**Step 1: Configure electron-builder** (one-time setup)

Update `locaNext/package.json`:
```json
{
  "build": {
    "appId": "com.locanext.app",
    "productName": "LocaNext",
    "files": [
      "build/**/*",
      "electron/**/*"
    ],
    "extraResources": [
      {
        "from": "../models/kr-sbert",
        "to": "models/kr-sbert",
        "filter": ["**/*"]
      },
      {
        "from": "../server",
        "to": "server",
        "filter": ["**/*.py", "**/*.json"]
      }
    ],
    "win": {
      "target": "nsis",
      "icon": "assets/icon.ico"
    },
    "linux": {
      "target": "AppImage",
      "category": "Development"
    },
    "mac": {
      "target": "dmg",
      "category": "public.app-category.developer-tools"
    }
  }
}
```

**Step 2: Build for distribution**
```bash
cd locaNext

# Build SvelteKit frontend
npm run build

# Package with Electron
npm run package

# Output:
# - Windows: dist-electron/LocaNext Setup 1.0.0.exe (~2GB with model)
# - Linux: dist-electron/LocaNext-1.0.0.AppImage
# - Mac: dist-electron/LocaNext-1.0.0.dmg
```

**Step 3: Test the build**
```bash
# Install the .exe on a clean Windows machine
# Verify:
# - App launches
# - Backend starts automatically
# - Model loads correctly
# - All features work
```

---

### 🏗️ Electron + VRS-Manager Build System (BEST OF BOTH!)

**Use VRS-Manager's awesome build infrastructure FOR Electron!**

**Create `.github/workflows/build-electron-installers.yml`**:
```yaml
name: Build LocaNext Electron Installers

on:
  push:
    branches: [ main ]
    paths:
      - 'BUILD_TRIGGER.txt'
      - 'server/**'
      - 'locaNext/**'
      - 'models/**'

jobs:
  check-build-type:
    runs-on: ubuntu-latest
    outputs:
      build_app: ${{ steps.check.outputs.build_app }}
      version: ${{ steps.check.outputs.version }}
    steps:
      - uses: actions/checkout@v4

      - name: Check BUILD_TRIGGER.txt
        id: check
        run: |
          BUILD_TYPE=$(sed -n '1p' BUILD_TRIGGER.txt)
          VERSION=$(sed -n '2p' BUILD_TRIGGER.txt)
          echo "build_app=$([[ $BUILD_TYPE == "ELECTRON" || $BUILD_TYPE == "BOTH" ]] && echo true || echo false)" >> $GITHUB_OUTPUT
          echo "version=$VERSION" >> $GITHUB_OUTPUT

  build-windows:
    runs-on: windows-latest
    needs: check-build-type
    if: needs.check-build-type.outputs.build_app == 'true'

    steps:
      - name: Checkout with LFS
        uses: actions/checkout@v4
        with:
          lfs: true  # Download model files

      - name: Verify model files
        run: |
          if (-Not (Test-Path "models\kr-sbert\model.safetensors")) {
            Write-Error "Model missing!"
            exit 1
          }

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Build Electron App
        run: |
          cd locaNext
          npm install
          npm run build
          npm run package

      - name: Create Installer with Inno Setup
        run: |
          choco install innosetup -y
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_electron.iss

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: LocaNext-Windows-Installer
          path: installer_output/*.exe
          retention-days: 7

  build-linux:
    runs-on: ubuntu-latest
    needs: check-build-type
    if: needs.check-build-type.outputs.build_app == 'true'

    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true

      - name: Build AppImage
        run: |
          cd locaNext
          npm install
          npm run build
          npm run package

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: LocaNext-Linux-AppImage
          path: locaNext/dist-electron/*.AppImage
          retention-days: 7

  create-release:
    runs-on: ubuntu-latest
    needs: [check-build-type, build-windows, build-linux]
    if: success()

    steps:
      - uses: actions/checkout@v4

      - name: Download Artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          tag_name: v${{ needs.check-build-type.outputs.version }}
          name: LocaNext v${{ needs.check-build-type.outputs.version }}
          body: |
            ## LocaNext Desktop Application

            **Downloads:**
            - Windows: LocaNext-Setup.exe (~2GB)
            - Linux: LocaNext.AppImage (~2GB)

            **What's Included:**
            - XLSTransfer (AI-powered translation)
            - QuickSearch (Multi-game dictionary)
            - Admin Dashboard
            - Korean BERT model (bundled)

            **Installation:**
            1. Download for your platform
            2. Run installer
            3. Launch from Start Menu/Applications

            🤖 Built with GitHub Actions + Electron
          files: |
            artifacts/**/*.exe
            artifacts/**/*.AppImage
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Benefits**:
- ✅ VRS-Manager's proven build system
- ✅ Applied to Electron builds
- ✅ Automated GitHub releases
- ✅ Multi-platform support
- ✅ LFS for model files
- ✅ Inno Setup for Windows
- ✅ Same workflow, different tech

---

### 📋 Complete Development → Distribution Plan

**Phase 1: Development (NOW - 90% of time)**
```
Work on web app:
  ├─ Edit code in VSCode
  ├─ See changes instantly in browser
  ├─ Use Chrome DevTools for debugging
  ├─ Test with curl/Postman
  └─ Commit when working
```

**Phase 2: Pre-Release (Before distribution)**
```
Prepare for packaging:
  ├─ Update version.py (version number)
  ├─ Run python3 scripts/check_version_unified.py
  ├─ Run all tests: pytest tests/
  ├─ Test full workflow manually
  └─ Update BUILD_TRIGGER.txt
```

**Phase 3: Build (Automated via GitHub Actions)**
```
Push to GitHub:
  ├─ GitHub Actions detects BUILD_TRIGGER.txt
  ├─ Builds Electron app (Windows + Linux)
  ├─ Creates installers with Inno Setup
  ├─ Uploads artifacts (7-day retention)
  └─ Creates GitHub Release (permanent)
```

**Phase 4: Distribution (Users download)**
```
GitHub Releases page:
  ├─ LocaNext-Setup-v1.0.0.exe (Windows)
  ├─ LocaNext-v1.0.0.AppImage (Linux)
  ├─ Installation instructions
  └─ Release notes
```

---

### ✅ Summary: Your Approach is PERFECT!

**What you're doing RIGHT NOW**:
- ✅ Developing web app (FastAPI + SvelteKit)
- ✅ Debugging in browser
- ✅ Fast iteration
- ✅ **THIS IS THE CORRECT APPROACH!**

**When you're ready to distribute**:
- ✅ Package with Electron (one command)
- ✅ Use VRS-Manager's build system
- ✅ GitHub Actions automation
- ✅ Professional installers

**NO conversion needed** - Electron wraps your existing web app!

**Tasks**:
- [x] Continue web development (current workflow)
- [ ] When ready: Configure electron-builder
- [ ] When ready: Set up GitHub Actions (VRS-Manager style)
- [ ] When ready: Create Inno Setup script
- [ ] When ready: Build and distribute

**For PyInstaller approach (VRS-Manager pattern):**

Create `LocaNext.spec` (EXACT VRS-Manager pattern):
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['server/main.py'],  # Entry point
    pathex=[],
    binaries=[],
    datas=[
        ('models/kr-sbert', 'models/kr-sbert'),  # BERT model (447MB)
        ('client/data', 'client/data'),           # App data
        ('images/icon.ico', 'images'),            # Icon
    ],
    hiddenimports=[
        'numpy',
        'pandas',
        'torch',
        'transformers',
        'sentence_transformers',
        'sklearn',
        'fastapi',
        'uvicorn',
        'sqlalchemy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'setuptools', 'distutils'],  # Reduce size
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LocaNext',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression
    console=True,  # True for debugging, False for production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LocaNext'
)
```

**Build commands** (VRS-Manager pattern):
```bash
# FULL version with model
pip install -r requirements.txt
pip install pyinstaller
python3 scripts/download_bert_model.py  # Download model first
pyinstaller LocaNext.spec --clean --noconfirm --distpath dist_full

# Result: dist_full/LocaNext/LocaNext.exe (~2GB with model)
```

**Why PyInstaller over Electron**:
- ✅ Smaller size (~2GB vs ~3GB+ with Electron)
- ✅ Faster startup (no Chromium overhead)
- ✅ True standalone (no Node.js/Chromium dependencies)
- ✅ VRS-Manager proven pattern
- ❌ No web UI (would need to rebuild frontend as desktop UI OR run local server)

**Tasks**:
- [ ] **DECIDE**: Electron vs PyInstaller approach
- [ ] If PyInstaller: Create spec file based on VRS-Manager
- [ ] If PyInstaller: Test FastAPI + frontend bundling together
- [ ] If staying Electron: Skip this, improve Electron build instead

#### 1.4 Inno Setup Installer (VRS-Manager EXACT Pattern)
**Status**: ✅ COMPLETE (2025-11-22)
**Reference**: VRS-Manager `installer/vrsmanager_full.iss` - EXACT implementation
**Tool**: Inno Setup 6 (Windows only)

**Installation**:
```bash
# Download from: https://jrsoftware.org/isdl.php
# Or via Chocolatey:
choco install innosetup
```

**Create `installer/locanext_full.iss` (VRS-Manager EXACT pattern)**:
```ini
; LocaNext FULL Installer (with AI model)
; Based on VRS-Manager installer pattern

[Setup]
AppId={{9B8C4D5E-6F7A-8B9C-0D1E-2F3A4B5C6D7E}}
AppName=LocaNext (FULL)
AppVersion=1.0.0
AppPublisher=Neil Schmitt
AppPublisherURL=https://github.com/NeilVibe/LocalizationTools
DefaultDirName={userdesktop}\LocaNext
DefaultGroupName=LocaNext
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=LocaNext_v1.0.0_Full_Setup
SetupIconFile=images\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
DisableProgramGroupPage=yes
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
; Main executable and dependencies (from PyInstaller dist_full/ OR Electron dist/)
Source: "dist_full\LocaNext\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Model files (447MB)
Source: "models\kr-sbert\*"; DestDir: "{app}\models\kr-sbert"; Flags: ignoreversion recursesubdirs

; Documentation
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs

; Working directories
Source: "Current\README.md"; DestDir: "{app}\Current"; Flags: ignoreversion
Source: "Previous\README.md"; DestDir: "{app}\Previous"; Flags: ignoreversion

[Icons]
Name: "{group}\LocaNext"; Filename: "{app}\LocaNext.exe"
Name: "{group}\Documentation"; Filename: "{app}\README.md"
Name: "{group}\Uninstall LocaNext"; Filename: "{uninstallexe}"
Name: "{userdesktop}\LocaNext"; Filename: "{app}\LocaNext.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LocaNext.exe"; Description: "Launch LocaNext"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove generated files on uninstall
Type: files; Name: "{app}\*.xlsx"
Type: files; Name: "{app}\*.xls"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.json"
Type: filesandordirs; Name: "{app}\Current\*"
Type: filesandordirs; Name: "{app}\Previous\*"
```

**Compile installer**:
```bash
# From project root
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_full.iss

# Output: installer_output/LocaNext_v1.0.0_Full_Setup.exe
```

**Verification steps** (VRS-Manager pattern):
```bash
# Check installer was created
ls -lh installer_output/LocaNext_v*.exe

# Should show file size (varies: ~2GB for FULL, ~200MB for LIGHT)
```

**Tasks**:
- [ ] Install Inno Setup 6
- [ ] Create installer/ directory with locanext_full.iss
- [ ] Build executable first (PyInstaller OR Electron)
- [ ] Compile installer with ISCC.exe
- [ ] Test installer on clean Windows 10/11 VM
- [ ] Verify:
  - Installation wizard completes
  - Model files copied to {app}/models/kr-sbert/
  - Start menu shortcuts created
  - Desktop icon created (if selected)
  - App launches successfully
  - Uninstaller removes files correctly

**Why**: Professional Windows installer. VRS-Manager proven pattern. LZMA2 ultra compression. Wizard UI. Clean uninstall.

#### 1.5 GitHub Actions CI/CD (VRS-Manager EXACT Workflow)
**Status**: ✅ COMPLETE (2025-11-22)
**Reference**: VRS-Manager `.github/workflows/build-installers.yml` - EXACT implementation

**Create `BUILD_TRIGGER.txt`** (version control file):
```
FULL
1.0.0
```
- Line 1: `FULL`, `LIGHT`, or `BOTH` (which builds to create)
- Line 2: Version number (e.g., `1.0.0`)

**Create `.github/workflows/build-installers.yml` (VRS-Manager EXACT pattern)**:
```yaml
name: Build FULL Installer

on:
  push:
    branches: [ main ]
    paths:
      - 'BUILD_TRIGGER.txt'
      - 'server/**'
      - 'client/**'
      - 'models/**'

jobs:
  check-build-type:
    runs-on: ubuntu-latest
    outputs:
      build_full: ${{ steps.check.outputs.build_full }}
      version: ${{ steps.check.outputs.version }}
    steps:
      - uses: actions/checkout@v4

      - name: Check BUILD_TRIGGER.txt
        id: check
        run: |
          BUILD_TYPE=$(sed -n '1p' BUILD_TRIGGER.txt)
          VERSION=$(sed -n '2p' BUILD_TRIGGER.txt)
          echo "build_full=$([[ $BUILD_TYPE == "FULL" || $BUILD_TYPE == "BOTH" ]] && echo true || echo false)" >> $GITHUB_OUTPUT
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "Build type: $BUILD_TYPE, Version: $VERSION"

  build-full:
    runs-on: windows-latest
    needs: check-build-type
    if: needs.check-build-type.outputs.build_full == 'true'

    steps:
      - name: Checkout code with LFS
        uses: actions/checkout@v4
        with:
          lfs: true  # CRITICAL: Download LFS files (model)

      - name: Verify model files
        run: |
          if (-Not (Test-Path "models\kr-sbert\config.json")) {
            Write-Error "Model config.json missing!"
            exit 1
          }
          if (-Not (Test-Path "models\kr-sbert\model.safetensors")) {
            Write-Error "Model safetensors missing!"
            exit 1
          }
          Write-Host "✓ Model files verified"
          Get-ChildItem models\kr-sbert

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build executable with PyInstaller
        run: |
          pyinstaller LocaNext.spec --clean --noconfirm --distpath dist_full
          if (-Not (Test-Path "dist_full\LocaNext\LocaNext.exe")) {
            Write-Error "Build failed - executable not found!"
            exit 1
          }
          Write-Host "✓ Executable built successfully"
          $size = (Get-Item "dist_full\LocaNext\LocaNext.exe").Length / 1MB
          Write-Host "Executable size: $($size.ToString('N2')) MB"

      - name: Install Inno Setup
        run: |
          choco install innosetup -y

      - name: Create installer
        run: |
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_full.iss
          if (-Not (Test-Path "installer_output\LocaNext_v*_Full_Setup.exe")) {
            Write-Error "Installer creation failed!"
            exit 1
          }
          Write-Host "✓ Installer created successfully"
          Get-ChildItem installer_output\*.exe

      - name: Upload installer artifact
        uses: actions/upload-artifact@v4
        with:
          name: LocaNext-Full-Installer
          path: installer_output/LocaNext_v*_Full_Setup.exe
          retention-days: 7

  create-release:
    runs-on: ubuntu-latest
    needs: [check-build-type, build-full]
    if: success()

    steps:
      - uses: actions/checkout@v4

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          tag_name: v${{ needs.check-build-type.outputs.version }}
          name: LocaNext v${{ needs.check-build-type.outputs.version }}
          body: |
            ## LocaNext v${{ needs.check-build-type.outputs.version }}

            ### Downloads
            - **FULL** (~2GB) - Includes AI-powered features with Korean BERT model

            ### Installation
            1. Download the FULL installer
            2. Run the .exe file
            3. Follow the installation wizard
            4. Launch from Start Menu or Desktop

            ### What's Included
            - XLSTransfer (AI-powered translation)
            - QuickSearch (Multi-game dictionary)
            - Admin Dashboard (Analytics & monitoring)
            - Korean BERT model (447MB, bundled)

            🤖 Built with GitHub Actions
          files: |
            artifacts/LocaNext-Full-Installer/*.exe
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Tasks**:
- [ ] Create BUILD_TRIGGER.txt with `FULL` and version
- [ ] Create .github/workflows/build-installers.yml
- [ ] Create LocaNext.spec (PyInstaller config)
- [ ] Create installer/locanext_full.iss (Inno Setup config)
- [ ] Commit and push to main
- [ ] Watch GitHub Actions → Build should trigger automatically
- [ ] Download artifact from Actions tab (7-day retention)
- [ ] OR download from Releases page (permanent)

**Verify with gh CLI**:
```bash
# Watch build live
gh run list
gh run watch <run-id>

# Check for errors
gh run view <run-id> --log-failed

# Download artifact
gh run download <run-id> -n LocaNext-Full-Installer
```

**Why**: VRS-Manager proven pattern. Automated builds on every push. LFS integration for model. Inno Setup installer. GitHub Releases with download links. 7-day artifacts + permanent releases.

#### 1.6 Cross-Platform Build Verification
**Status**: Needs testing

**Tasks**:
- [ ] Test Windows .exe on Windows 10/11
- [ ] Test Linux AppImage on Ubuntu 20.04/22.04
- [ ] Test macOS .app on macOS 12+ (if applicable)
- [ ] Verify model loading in all platforms
- [ ] Check file permissions and execution rights
- [ ] Test installer/uninstaller on all platforms

**Why**: Distribution must work everywhere. Catch platform-specific issues early.

---

### 🔧 Build & Development Workflow (from VRS-Manager)

#### Local Build Setup

**LIGHT Version** (minimal dependencies, ~150MB):
```bash
pip install pandas openpyxl numpy pyinstaller
pyinstaller LocaNext_light.spec --clean --noconfirm --distpath dist_light
```

**FULL Version** (with AI model, ~2GB):
```bash
pip install -r requirements.txt
pip install pyinstaller
python3 scripts/download_bert_model.py
pyinstaller LocaNext.spec --clean --noconfirm --distpath dist_full
```

**Installer Compilation** (Windows with Inno Setup):
```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_light.iss
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_full.iss
```

**Requirements**:
- Python 3.10+
- PyInstaller
- Inno Setup 6 (Windows only, for installers)

---

#### Pre-Build Testing Checklist

**Before building/releasing**:
```bash
# 1. Verify version consistency across files
python3 check_version_unified.py

# 2. Run all tests
pytest tests/ -v
python3 tests/test_dashboard_api.py
python3 tests/test_async_auth.py

# 3. Update documentation if needed

# 4. Commit and push all changes
git add .
git commit -m "Release v[version]"
git push
```

---

#### GitHub CLI (gh) Commands for Build Management

**Authentication** (one-time setup):
```bash
# Install GitHub CLI
# Ubuntu/Debian: sudo apt install gh
# macOS: brew install gh
# Windows: winget install GitHub.cli

# Login with token
gh auth login

# Or use token directly
export GH_TOKEN=your_personal_access_token
echo $GH_TOKEN | gh auth login --with-token
```

**In GitHub Actions** (automatic):
```yaml
# Set GH_TOKEN in workflow steps
env:
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

#### Checking Build Status & History

**List recent workflow runs**:
```bash
gh run list --workflow=build-installers.yml --limit 10
```

**Watch live build progress**:
```bash
gh run watch <run-id>
```

**View specific run details**:
```bash
gh run view <run-id>
```

**View run logs**:
```bash
# View all logs
gh run view <run-id> --log

# View only failed steps
gh run view <run-id> --log-failed

# Search logs for specific text
gh run view <run-id> --log | grep "ERROR"
gh run view <run-id> --log | grep "model"
```

**List workflow runs by status**:
```bash
gh run list --status=failure
gh run list --status=success
gh run list --status=in_progress
```

---

#### Downloading Build Artifacts

**Download from specific run**:
```bash
# List artifacts from a run
gh run view <run-id>

# Download specific artifact by name
gh run download <run-id> -n artifact-name

# Download all artifacts from run
gh run download <run-id>

# Interactive selector
gh run download
```

**Access via Web**:
1. Go to GitHub → Actions tab
2. Click on workflow run
3. Scroll to "Artifacts" section
4. Download (7-day retention)

---

#### Checking Releases

**List releases**:
```bash
gh release list
```

**View specific release**:
```bash
gh release view v1.0.0
```

**Download release assets**:
```bash
gh release download v1.0.0
```

---

#### Workflow Management

**List workflows**:
```bash
gh workflow list
```

**View workflow details**:
```bash
gh workflow view build-installers.yml
```

**Manually trigger workflow**:
```bash
gh workflow run build-installers.yml
```

**View workflow runs**:
```bash
gh workflow view build-installers.yml --yaml
```

---

#### Local Testing of Built Executables

**After building locally**:
```bash
# Test LIGHT version
cd dist_light
./LocaNext  # or LocaNext.exe on Windows

# Test FULL version
cd dist_full
./LocaNext  # Verify model loads correctly
```

**Verify model bundling**:
```bash
# Check if model files exist in distribution
ls -lh dist_full/models/kr-sbert/
# Should show: config.json, model.safetensors, tokenizer files
```

**Test installer** (Windows):
```bash
# Run installer in VM or test machine
installer_output/LocaNext_v[version]_Full_Setup.exe

# Verify:
# - Installation wizard completes
# - Start menu shortcuts created
# - Application launches successfully
# - Uninstaller works correctly
```

---

#### Log Checking During Development

**Server logs** (live):
```bash
# Monitor server logs in real-time
tail -f server/data/logs/server.log

# Search for errors
grep "ERROR" server/data/logs/server.log

# Search for specific operations
grep "xlstransfer" server/data/logs/server.log
```

**GitHub Actions logs**:
- Navigate to Actions tab in repository
- Click on workflow run
- Click on job name (e.g., "build-full")
- View live or completed logs
- Download log files for offline analysis

**Database logs**:
```bash
# Check operation logs in database
sqlite3 server/data/locanext.db "SELECT * FROM log_entries ORDER BY timestamp DESC LIMIT 20;"

# Check error logs
sqlite3 server/data/locanext.db "SELECT * FROM error_logs ORDER BY timestamp DESC LIMIT 10;"
```

---

### Priority 2: Select App #3
**Estimated Time**: 4-6 hours
**Status**: ✅ COMPLETE (2025-11-22)
**Selected**: WordCountMaster V2.0
**Source**: `RessourcesForCodingTheProject/NewScripts/WordCountMaster/`

**✅ COMPLETED TASKS**:
- ✅ Analyzed original wordcount_diff_master.py script (1015 lines)
- ✅ Created backend API: `server/api/wordcount_async.py` using BaseToolAPI
- ✅ Created processor module: `server/tools/wordcount/processor.py`
- ✅ Registered API in `server/main.py`
- ✅ Created frontend component: `locaNext/src/lib/components/apps/WordCountMaster.svelte`
- ✅ Added to navigation menu in `+layout.svelte`
- ✅ Updated routing in `+page.svelte`

**Features Implemented**:
- Upload XML translation files (LanguageData_XXX.xml)
- Select past date for comparison (7 days = Weekly, 30 days = Monthly)
- Process files and generate Excel report with 4 sheets
- Smart categorization (Weekly vs Monthly based on days difference)
- Download generated Excel reports
- View historical runs
- Real-time progress tracking via WebSocket

**Pattern Followed** (proven with XLSTransfer and QuickSearch):
1. ✅ Analyze original script (30 min)
2. ✅ Backend: REST API using BaseToolAPI (2 hours)
3. ✅ Frontend: SvelteKit component with Carbon Design (2 hours)
4. ⏳ Testing: Manual UI + automated tests (pending)
5. ⏳ Documentation: Update README (pending)

---

### Priority 3: Admin Dashboard Authentication
**Estimated Time**: 2-3 hours
**Status**: Pending

**Tasks**:
- [ ] Add login page for admin dashboard
- [ ] Protect admin routes with auth middleware
- [ ] Role-based access control (admin vs regular user)
- [ ] Session management for dashboard

---

### Priority 4: Export Functionality
**Estimated Time**: 3-4 hours
**Status**: Pending

**Tasks**:
- [ ] Export rankings to CSV/Excel
- [ ] Export statistics reports to PDF
- [ ] Export activity logs to CSV
- [ ] Download buttons in dashboard

---

### Priority 5: Production Web Deployment
**Estimated Time**: 4-6 hours
**Status**: Pending

**Tasks**:
- [ ] PostgreSQL setup and migration
- [ ] Environment configuration (.env for production)
- [ ] Frontend build optimization
- [ ] Server deployment (nginx, systemd)
- [ ] SSL/HTTPS setup
- [ ] Backup strategy

---

## 🏗️ Architecture Overview

### Technology Stack

**Frontend:**
- SvelteKit 2.0 - Modern reactive framework
- Chart.js - Interactive data visualizations
- Carbon Design System - IBM's design language
- Socket.IO Client - Real-time WebSocket connection

**Backend:**
- FastAPI - High-performance async Python framework
- SQLAlchemy 2.0 - Modern async ORM
- Socket.IO - WebSocket server for real-time updates
- Pydantic - Data validation and settings management

**Database:**
- SQLite (Development) - Zero-config database
- PostgreSQL (Production) - Robust production database

**ML/AI:**
- Sentence Transformers - Semantic text embeddings
- Korean BERT (snunlp/KR-SBERT-V40K-klueNLI-augSTS) - 447MB
- Three-tier loading: Hugging Face → Local cache → Graceful fallback

**Distribution:**
- PyInstaller - Standalone executables (no Python required)
- Inno Setup - Professional Windows installers with wizard
- GitHub Actions - Automated builds (Windows/Linux/macOS)
- Git LFS - Large file storage for models (447MB+)
- Electron - Desktop app packaging (current)

---

### Project Structure

```
LocalizationTools/
├── locaNext/                   # FRONTEND (SvelteKit)
│   ├── src/
│   │   ├── routes/            # Pages and API routes
│   │   ├── lib/               # Shared components and utilities
│   │   └── stores/            # Svelte stores for state management
│   └── package.json
│
├── adminDashboard/            # ADMIN DASHBOARD (SvelteKit)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte           # Overview page
│   │   │   ├── stats/+page.svelte     # Statistics with charts
│   │   │   ├── rankings/+page.svelte  # User/App rankings
│   │   │   ├── users/+page.svelte     # User management
│   │   │   └── logs/+page.svelte      # Activity logs
│   │   └── lib/
│   │       └── api/client.js          # API client (16 methods)
│   └── package.json
│
├── server/                    # BACKEND (FastAPI)
│   ├── main.py                # FastAPI application entry point
│   ├── config.py              # Server configuration
│   ├── api/                   # API ENDPOINTS
│   │   ├── auth_async.py              # Authentication
│   │   ├── xlstransfer_async.py       # XLSTransfer tool API
│   │   ├── quicksearch_async.py       # QuickSearch tool API
│   │   ├── stats.py                   # Statistics API (10 endpoints)
│   │   ├── rankings.py                # Rankings API (6 endpoints)
│   │   ├── progress_operations.py     # Progress tracking
│   │   ├── base_tool_api.py           # Base class for tools
│   │   └── schemas.py                 # Pydantic models
│   ├── database/              # DATABASE
│   │   ├── models.py          # SQLAlchemy models
│   │   └── db_setup.py        # Database setup
│   ├── utils/                 # UTILITIES
│   │   ├── auth.py            # JWT authentication
│   │   ├── websocket.py       # WebSocket manager
│   │   └── dependencies.py    # FastAPI dependencies
│   ├── tools/                 # TOOL IMPLEMENTATIONS
│   │   ├── xls_transfer/      # XLSTransfer backend
│   │   └── quicksearch/       # QuickSearch backend
│   └── data/                  # Database storage (gitignored)
│
├── tests/                     # TESTS
│   ├── test_dashboard_api.py          # Dashboard API tests (20 tests)
│   ├── test_async_auth.py             # Authentication tests
│   ├── test_async_infrastructure.py   # Infrastructure tests
│   └── integration/                   # Integration tests
│
├── docs/                      # DOCUMENTATION
│   ├── TESTING_GUIDE.md       # How to test the system
│   ├── STATS_DASHBOARD_SPEC.md # Dashboard specification
│   ├── ADMIN_SETUP.md         # Admin setup guide
│   ├── ADD_NEW_APP_GUIDE.md   # How to add new apps (BaseToolAPI)
│   └── PERFORMANCE.md         # Performance benchmarks
│
├── scripts/                   # BUILD & SETUP SCRIPTS
│   └── setup_database.py      # Database initialization
│
├── archive/                   # ARCHIVED CODE
│   └── gradio_version/        # Old Gradio-based version
│
├── Roadmap.md                 # This file
├── requirements.txt           # Python dependencies
└── README.md                  # Project overview
```

---

## 🔑 Key Architectural Principles

### 1. Backend is Flawless
**CRITICAL**: Unless explicitly told there's a bug, **ALL backend code (`server/tools/`) is 100% FLAWLESS**

**Migration Work = Wrapper Layer Only**:
- ✅ Create API endpoints (`server/api/`) that call backend correctly
- ✅ Build GUI components (Svelte) that integrate with backend
- ✅ Add logging, monitoring, error handling at wrapper layer
- ❌ **DO NOT modify** core backend modules unless there's a confirmed bug

### 2. BaseToolAPI Pattern
**All new apps MUST use `BaseToolAPI`** for consistency and speed.

**Shared Features**:
- User authentication
- Operation tracking
- WebSocket progress updates
- File handling
- Error management
- Logging

**Benefits**:
- 43% less code
- 75% faster development
- Consistent API structure
- Built-in progress tracking
- Automatic logging

**Guide**: `docs/ADD_NEW_APP_GUIDE.md`

### 3. Real-time Progress Tracking
**Every long-running operation MUST emit progress updates**

**Components**:
- Database: `active_operations` table
- WebSocket: `progress_update` events
- Frontend: Task Manager component
- Admin: Dashboard monitoring

**Updates Include**:
- `progress_percentage` (0-100%)
- `current_step` (descriptive message)
- `status` (pending, running, completed, failed)
- `started_at`, `completed_at` timestamps

### 4. Comprehensive Logging
**All operations MUST be logged for monitoring and debugging**

**Log Levels**:
- INFO: Normal operations
- WARNING: Recoverable issues
- ERROR: Operation failures
- DEBUG: Detailed diagnostics

**Logged Data**:
- User ID, operation ID
- Tool name, function name
- File info (names, sizes)
- Duration, status
- Error messages and stack traces

### 5. Database Tracking
**All operations MUST be tracked in the database**

**Tables**:
- `users` - User accounts
- `sessions` - Active sessions (JWT)
- `active_operations` - Real-time operation tracking
- `log_entries` - Historical operation logs
- `error_logs` - Error tracking

---

## 📚 How to Add New Apps

### Quick Reference
See `docs/ADD_NEW_APP_GUIDE.md` for complete guide with examples.

### Step-by-Step Process

**1. Create Backend Tool** (`server/tools/your_app/`)
```python
# core.py - Your app's logic
# utils.py - Helper functions
```

**2. Create REST API** (`server/api/your_app_async.py`)
```python
from server.api.base_tool_api import BaseToolAPI

class YourAppAPI(BaseToolAPI):
    def __init__(self):
        super().__init__(tool_name="your_app")

    @self.router.post("/endpoint")
    async def your_endpoint(self, request: Request):
        # Use inherited methods:
        # - self.get_current_user(request)
        # - self.create_operation(user_id, function_name)
        # - self.update_progress(operation_id, percentage, message)
        # - self.complete_operation(operation_id, result)
        # - self.handle_tool_error(operation_id, error)
```

**3. Register Router** (`server/main.py`)
```python
from server.api.your_app_async import YourAppAPI

your_app_api = YourAppAPI()
app.include_router(your_app_api.router, prefix="/api/v2/your_app", tags=["your_app"])
```

**4. Create Frontend Component** (`locaNext/src/lib/components/apps/YourApp.svelte`)
```svelte
<script>
  import { Button, FileUploader, DataTable } from 'carbon-components-svelte';
  // API calls, UI logic
</script>

<div class="your-app">
  <!-- Your UI -->
</div>
```

**5. Add Navigation** (`locaNext/src/routes/+layout.svelte`)
```svelte
<HeaderNavItem text="Your App" href="/your-app" />
```

**6. Test & Document**
- Manual UI testing
- Create test script
- Update README.md
- Create testing report

**Estimated Time**: 2-4 hours per app (with BaseToolAPI)

---

## 🧪 Testing Strategy

### Testing Checklist (for each new app)
1. All API endpoints return 200 OK
2. Frontend UI loads without errors
3. Operations appear in Task Manager with real-time progress
4. Admin dashboard logs operations and updates live
5. Database tracking confirmed
6. Error handling works correctly
7. File upload/download works
8. Authentication works
9. WebSocket updates work

### Monitoring
- Real-time logs in admin dashboard
- Server logs: `server/data/logs/server.log`
- WebSocket progress updates
- Database operation tracking

---

## 🎯 Vision & Goals

### Immediate (1-2 weeks)
- ⚡ **Distribution Infrastructure** (Priority 1)
  - Git LFS for model files
  - PyInstaller builds (full & light)
  - Inno Setup installers
  - GitHub Actions CI/CD
- 🔧 **App #3** (Priority 2)
- 🔐 **Admin auth** (Priority 3)

### Short Term (1 month)
- Professional distribution pipeline operational
- 3-5 apps migrated to platform
- Export functionality (CSV/Excel/PDF)
- Advanced analytics

### Medium Term (2-3 months)
- 10+ apps from RessourcesForCodingTheProject/
- Production web deployment
- User roles & permissions
- Performance optimization

### Long Term (6 months)
- 20+ apps in platform
- Advanced AI features
- Multi-tenancy support
- Plugin system for custom apps

---

## 📖 Documentation

### Platform Docs
- `README.md` - Project overview, quick start, architecture
- `Roadmap.md` - This file (current status, priorities, next steps)
- `docs/ADD_NEW_APP_GUIDE.md` - How to add new apps with BaseToolAPI
- `docs/TESTING_GUIDE.md` - Testing procedures

### API Documentation
- Interactive docs: http://localhost:8888/docs
- Backend health: http://localhost:8888/health

---

## 📝 Distribution Setup - VRS-Manager Reference

### Model Management Pattern (from VRS-Manager)

**Three-Tier Model Loading**:
1. **Online Mode** (First Run): Auto-download from Hugging Face (5-10 min, 447MB)
2. **Local Cache**: Load from `models/kr-sbert/` directory
3. **Graceful Fallback**: Skip AI features if model unavailable

**Directory Structure**:
```
LocaNext/
├── models/
│   └── kr-sbert/              # Korean BERT model (447MB)
│       ├── config.json
│       ├── model.safetensors  # or pytorch_model.bin
│       └── tokenizer files
└── LocaNext.exe               # Desktop app loads model from adjacent folder
```

**Setup Scripts** (to create):
- `scripts/download_bert_model.py` - Python script for automated download
- `scripts/download_model.bat` - Windows batch script with user prompts
- Both verify model integrity (check config.json and weights exist)

**Offline Transfer** (for air-gapped environments):
1. Run download script on internet-connected PC
2. Copy entire `models/` folder
3. Place next to LocaNext.exe on offline PC

---

## 🚀 Quick Start

### Running the Platform

**Terminal 1: Backend**
```bash
source venv/bin/activate
python3 server/main.py
# Server: http://localhost:8888
```

**Terminal 2: Frontend**
```bash
cd locaNext
npm run dev
# Frontend: http://localhost:5173
```

**Terminal 3: Admin Dashboard**
```bash
cd adminDashboard
npm run dev
# Dashboard: http://localhost:5174
```

### Access Points
- **Main App**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5174
- **API Docs**: http://localhost:8888/docs
- **Health Check**: http://localhost:8888/health

### Default Credentials
```
Username: admin
Password: admin123
```

---

## 📚 Key Documentation

### Essential Docs
- `README.md` - Project overview, quick start
- `Roadmap.md` - This file (current status, priorities)
- `docs/ADD_NEW_APP_GUIDE.md` - How to add new apps with BaseToolAPI
- `docs/TESTING_GUIDE.md` - Testing procedures

### Reference Projects
- **VRS-Manager** (NeilVibe/VRS-Manager) - Distribution setup reference
  - Git LFS configuration
  - PyInstaller specs (full & light builds)
  - Inno Setup installers with wizard
  - GitHub Actions CI/CD pipeline
  - Model download automation

---

**Last Updated**: 2025-11-22
**Current Focus**: Distribution & Deployment Infrastructure (Priority 1)
**Next Milestone**: Git LFS + PyInstaller + Inno Setup + GitHub Actions
**Platform Status**: Core Complete - Distribution Phase
