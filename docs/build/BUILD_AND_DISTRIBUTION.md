# Build & Distribution System

**LIGHT-First Strategy** | **electron-builder + NSIS** | **Post-Install Model Download**

**Last Updated**: 2025-12-14

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Build Tool** | electron-builder 26.x |
| **Installer Format** | NSIS (Nullsoft Scriptable Install System) |
| **CI/CD** | Gitea Actions (primary) + GitHub Actions (secondary) |
| **Output** | `LocaNext_vXX.XXXX.XXXX_Light_Setup.exe` |

> **P28 Change (2025-12-14)**: Replaced Inno Setup with electron-builder's native NSIS.
> Old `.iss` files archived to `installer/deprecated/`.

---

## 🎯 BUILD STRATEGY: LIGHT-First (2025-11-30)

### The Problem
- Git LFS free tier: 1GB bandwidth/month
- Korean BERT model: 447MB
- Each FULL build uses ~894MB bandwidth (model × 2 jobs)
- **Result**: Quota exceeded after first test build

### The Solution
Instead of bundling the 447MB model in builds:
1. **Build LIGHT installer** (~100-150MB) - NO model bundled
2. **User downloads model during install wizard** - Their bandwidth, not GitHub's
3. **No LFS costs** - Model never goes through GitHub Actions

### Comparison
| Aspect | OLD (FULL) | NEW (LIGHT) |
|--------|------------|-------------|
| Build size | ~2GB | ~100-150MB |
| LFS bandwidth/build | ~894MB | ~0MB |
| GitHub Actions | Blocked by quota | No issues |
| Install time | Faster | +5-10 min (model download) |
| Cost | $5/50GB data pack | FREE |

---

## 📦 VERSIONING SCHEME

**Format:** `YYMMDDHHMM` (DateTime-based versioning)

- YY = Year (25 = 2025)
- MM = Month (11 = November)
- DD = Day (30)
- HH = Hour (19)
- MM = Minute (39)

**Example:** `2511301939` = November 30, 2025 at 7:39 PM

**Why?** Clear, sortable, shows when each version was created.

---

## 🔄 VERSION UPDATE WORKFLOW

**CRITICAL: Always run check BEFORE commit/push!**

```bash
# 1. Get new datetime version
NEW_VERSION=$(date '+%y%m%d%H%M')
echo "New version: $NEW_VERSION"

# 2. Update version.py (single source of truth)
# Edit: VERSION = "2511221939" → VERSION = "$NEW_VERSION"

# 3. RUN CHECK BEFORE COMMIT! (This catches mistakes!)
python3 scripts/check_version_unified.py

# 4. Only if check passes (exit code 0), then commit
git add -A
git commit -m "Version unification: v$NEW_VERSION"
git push origin main

# 5. NOW trigger build (when ready for release)
echo "Build LIGHT v$NEW_VERSION" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt
git commit -m "Trigger build v$NEW_VERSION"
git push origin main
```

**Golden Rule:** Never commit version changes without running `check_version_unified.py` first!

---

## 🎯 BUILD TRIGGER - MANUAL CONTROL

**IMPORTANT:** Builds are triggered MANUALLY by YOU, not automatic on every push!

```bash
# Build LIGHT version (recommended - no model bundled)
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt
git commit -m "Trigger LIGHT build v$(date '+%y%m%d%H%M')"
git push origin main
```

**Why Manual Builds?**
- Control when releases happen (not every commit)
- Save GitHub Actions minutes
- No LFS bandwidth issues with LIGHT builds
- Intentional release process

**Build starts automatically AFTER you push BUILD_TRIGGER.txt update.**

Check: https://github.com/NeilVibe/LocalizationTools/actions

---

## 📥 POST-INSTALL MODEL DOWNLOAD

The LIGHT installer includes a post-install step that downloads the Korean BERT model.

### How It Works
1. User runs NSIS installer (.exe)
2. Files are copied (~200MB including embedded Python)
3. On first app launch or via script: model download
4. Model downloaded from Hugging Face to `models/kr-sbert/`
5. App ready to use

### electron-builder NSIS Configuration (package.json)
```json
{
  "nsis": {
    "oneClick": false,
    "allowToChangeInstallationDirectory": true,
    "perMachine": true,
    "installerIcon": "build/icon.ico",
    "uninstallerIcon": "build/icon.ico",
    "artifactName": "LocaNext_v${version}_Light_Setup.${ext}"
  },
  "extraResources": [
    { "from": "../server", "to": "server" },
    { "from": "../tools", "to": "tools" },
    { "from": "../python_embed", "to": "python_embed" }
  ]
}
```

### Fallback for Offline Users
If user doesn't have internet during install:
1. App installs without model
2. XLSTransfer shows "Model not found" message
3. User can run `scripts\download_model.bat` later
4. Or manually copy `models/kr-sbert/` folder from another machine

---

## 🔍 BUILD TROUBLESHOOTING

**Check build logs with gh CLI (BEST method):**

```bash
# Check if authenticated
gh auth status

# List recent builds
gh run list --limit 5

# Get full error logs for failed build
gh run view $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --log-failed

# Search for specific errors
gh run view <RUN_ID> --log-failed | grep -i "error\|failed\|missing"
```

**See docs/BUILD_TROUBLESHOOTING.md for complete debugging guide**

---

## ✅ VERSION UNIFICATION

**WHY CRITICAL:** Version inconsistencies cause confusion for users, documentation mismatches, and make debugging difficult.

**AUTOMATED CHECK:**
```bash
python3 scripts/check_version_unified.py
```

**What it checks:**
- version.py - Single source of truth
- server/config.py - Backend imports VERSION
- locaNext/package.json - Electron app version
- README.md - Documentation version

**MANDATORY WORKFLOW:**
1. Update VERSION in version.py
2. **RUN THIS CHECK** → `python3 scripts/check_version_unified.py`
3. Only if exit code 0 (success) → commit and push
4. Then trigger build (if releasing)

**NEVER commit version changes without running this check first!**

---

## 🔒 SECURITY AUDIT PROTOCOL (Build Pipeline)

**Updated**: 2025-12-01

The build pipeline includes security audits that check for vulnerabilities in dependencies.

### Severity Policy

| Severity | Action | Build Result |
|----------|--------|--------------|
| **All levels** | ⚠️ Log | Build continues - logged for review |

**Why warnings only?** Dependency security audits often report false positives or issues in transitive dependencies we don't directly use. All warnings are logged in CI history for review.

### What Gets Checked

1. **Python Dependencies** (`pip-audit`)
   - Scans all packages in requirements.txt
   - Checks against vulnerability databases
   - Reports severity levels

2. **NPM Dependencies** (`npm audit`)
   - Scans all packages in package-lock.json
   - Uses `--audit-level=high` (only fails on high/critical)
   - Full report logged for tracking

### Viewing Security Warnings

All warnings are logged in GitHub Actions history:

```bash
# View recent build logs
gh run list --limit 5

# Get logs for specific run
gh run view <RUN_ID> --log

# Search for security warnings
gh run view <RUN_ID> --log | grep -i "vulnerab\|warning\|medium\|low"
```

### Fixing Vulnerabilities

**For CRITICAL/HIGH (blocking):**
```bash
# Update specific package
pip install --upgrade <package-name>

# Or update all
pip install --upgrade -r requirements.txt

# Re-run audit locally
pip-audit --desc
```

**For Medium/Low (warnings):**
- Track in issue tracker or fix when convenient
- Review during regular maintenance windows
- Check CI history to see trends

---

## 📚 Related Documentation

- **BUILD_TROUBLESHOOTING.md** - Complete debugging guide
- **BUILD_CHECKLIST.md** - Pre-release checklist
- **PACKAGING_GUIDE.md** - Electron packaging details
- **SECURITY_HARDENING.md** - Full security documentation
- **Roadmap.md** - Current build strategy and status
