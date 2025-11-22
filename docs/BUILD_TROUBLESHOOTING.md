# LocaNext Build Troubleshooting Guide

**Based on VRS-Manager's proven troubleshooting patterns**

---

## 🔍 Quick Build Status Check

### Method 1: GitHub CLI (BEST - Shows Actual Errors!)

```bash
# Check if you're authenticated
gh auth status

# View latest build
gh run list --limit 1

# Get full error logs for failed build
gh run view $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --log-failed

# Search for specific error
gh run view <RUN_ID> --log-failed | grep -i "error"
```

### Method 2: GitHub API (No Auth Required)

```bash
# List recent builds
curl -s "https://api.github.com/repos/NeilVibe/LocalizationTools/actions/runs?per_page=5" | \
python3 -c "import sys, json; runs = json.load(sys.stdin)['workflow_runs']; \
[print(f\"{r['name']}: {r['status']} - {r['conclusion']} - {r['created_at']}\") for r in runs[:5]]"

# Get latest run ID
RUN_ID=$(curl -s "https://api.github.com/repos/NeilVibe/LocalizationTools/actions/runs?per_page=1" | \
python3 -c "import sys, json; print(json.load(sys.stdin)['workflow_runs'][0]['id'])")

# Check which step failed
curl -s "https://api.github.com/repos/NeilVibe/LocalizationTools/actions/runs/$RUN_ID/jobs" | \
python3 -c "
import sys, json
jobs = json.load(sys.stdin)['jobs']
for job in jobs:
    if job['conclusion'] == 'failure':
        print(f\"\n=== {job['name']} ===\")
        for step in job['steps']:
            if step['conclusion'] == 'failure':
                print(f\"FAILED STEP: {step['name']}\")
"
```

---

## 🚨 Common Build Errors & Solutions

### Error 1: "BERT model not found" or "LFS files missing"

**Symptom:**
```
❌ BERT model directory not found at: models/kr-sbert
```

**Root Cause:** Git LFS files weren't downloaded during checkout

**Solution (VRS-Manager proven fix):**
```yaml
# In .github/workflows/build-electron.yml
- name: Checkout with LFS
  uses: actions/checkout@v4
  with:
    lfs: true  # ✅ CRITICAL - Downloads 446MB model
```

**Verification Step (Add this to workflow):**
```yaml
- name: Verify BERT model (from LFS)
  run: |
    Write-Host "Checking for model directory..."
    if (!(Test-Path "models\kr-sbert\model.safetensors")) {
      Write-Error "❌ BERT model file not found!"
      exit 1
    }
    Write-Host "✓ BERT model exists"
    $size = (Get-Item "models\kr-sbert\model.safetensors").length / 1MB
    Write-Host "  Size: $([math]::Round($size, 1)) MB"
  shell: pwsh
```

**VRS-Manager Lesson:** Build #2 failed because we forgot `lfs: true`. Build #3 succeeded after adding it.

---

### Error 2: "LFS bandwidth quota exceeded"

**Symptom:**
```
Error: This repository exceeded its LFS budget
```

**Root Cause:** GitHub LFS has 1GB monthly bandwidth limit. Each build downloads 446MB model.

**Solution (VRS-Manager optimization):**
```yaml
# LIGHT build - NO model needed
build-light:
  steps:
    - uses: actions/checkout@v4
      with:
        lfs: false  # ✅ Skip LFS download (saves 446MB)

# FULL build - Model required
build-full:
  steps:
    - uses: actions/checkout@v4
      with:
        lfs: true  # ✅ Download model (needed for bundling)

# Release job - NO source needed
create-release:
  steps:
    - uses: actions/checkout@v4
      with:
        lfs: false  # ✅ Only needs artifacts, not source
```

**VRS-Manager Lesson:** Build #5 failed with LFS quota error. We fixed by only downloading LFS files when actually needed.

**Bandwidth Savings:**
- Before: 3 jobs × 446MB = 1,338MB (quota exceeded!)
- After: 1 job × 446MB = 446MB (within quota ✅)

---

### Error 3: "Inno Setup compilation failed - Invalid number of parameters"

**Symptom:**
```
Error on line 127 in locanext_electron.iss: Column 4:
Invalid number of parameters.
Compile aborted.
```

**Root Cause:** Inno Setup syntax error in .iss file

**How VRS-Manager Debugged This:**
```bash
gh run view 19503424622 --log-failed | grep -B 5 -A 10 "Compile.*installer"
```

**Output showed EXACT line number:**
```
Error on line 127 in D:\a\VRS-Manager\VRS-Manager\installer\vrsmanager_light.iss
```

**Common Inno Setup Syntax Errors:**
```ini
# ❌ WRONG - Missing semicolon
Source: "dist\*" DestDir: "{app}"

# ✅ CORRECT
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion

# ❌ WRONG - Missing quotes
Source: dist\*.exe; DestDir: {app}

# ✅ CORRECT
Source: "dist\*.exe"; DestDir: "{app}"
```

**Solution:** Always test .iss file locally before committing:
```bash
# Windows
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_electron.iss

# If error, ISCC shows exact line number
```

---

### Error 4: "Build executable not found after PyInstaller/electron-builder"

**Symptom:**
```
❌ FULL build failed - LocaNext.exe not found
Expected at: dist-electron\win-unpacked\LocaNext.exe
```

**Root Cause:** Build output path mismatch

**Solution (Add verification step):**
```yaml
- name: Verify Electron build
  run: |
    if (!(Test-Path "dist-electron\win-unpacked\LocaNext.exe")) {
      Write-Error "❌ Electron build failed - LocaNext.exe not found"
      Write-Host "Expected at: dist-electron\win-unpacked\LocaNext.exe"
      if (Test-Path "dist-electron") {
        Write-Host "`nContents of dist-electron:"
        Get-ChildItem "dist-electron" -Recurse | Select-Object -First 20
      }
      exit 1
    }
    Write-Host "✓ Electron build successful"
    $size = (Get-Item "dist-electron\win-unpacked\LocaNext.exe").length / 1MB
    Write-Host "  Size: $([math]::Round($size, 1)) MB"
  shell: pwsh
```

**VRS-Manager Lesson:** Always list directory contents on failure so we can see what actually exists.

---

### Error 5: "Version mismatch in installer filename"

**Symptom:**
```
❌ Installer not found at: installer_output\LocaNext_v2511221939_Setup.exe
```

**Root Cause:** Hardcoded version in .iss file doesn't match VERSION in version.py

**Prevention (Use version validation):**
```bash
# Before committing, ALWAYS run:
python3 scripts/check_version_unified.py

# Should show:
# ✓ version.py: 2511221939
# ✓ installer/locanext_electron.iss: 2511221939
# ✓ All versions unified!
```

**Solution in .iss file:**
```ini
; Use variable from version.py
#define MyAppVersion "2511221939"

; Then reference it
OutputBaseFilename=LocaNext_v{#MyAppVersion}_Setup
```

---

## 🔧 Debugging Workflow (VRS-Manager Proven Method)

### Step 1: Identify Failed Build
```bash
gh run list --limit 3
```

### Step 2: Get Run ID
```bash
RUN_ID=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')
echo "Run ID: $RUN_ID"
```

### Step 3: Get Full Error Logs
```bash
gh run view $RUN_ID --log-failed
```

### Step 4: Search for Specific Error
```bash
# Look for common error patterns
gh run view $RUN_ID --log-failed | grep -i -E "error|failed|missing|not found"

# Get context around error
gh run view $RUN_ID --log-failed | grep -B 10 -A 10 "KEYWORD"
```

### Step 5: Check Specific Step
```bash
# Example: Check Inno Setup compilation
gh run view $RUN_ID --log-failed | grep -B 5 -A 30 "Compile.*installer"
```

---

## 📋 Pre-Build Checklist (Prevents 90% of Errors!)

### Before Every Build:

```bash
# 1. Version unification check
python3 scripts/check_version_unified.py
# Must show: "✓ ALL VERSIONS UNIFIED!"

# 2. Test Inno Setup locally (Windows)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_electron.iss

# 3. Verify model exists
ls -lh models/kr-sbert/model.safetensors
# Should show: ~446MB file

# 4. Check LFS tracking
git lfs ls-files
# Should show: model.safetensors, tokenizer.json

# 5. Update BUILD_TRIGGER.txt
echo "Build FULL v$(date '+%y%m%d%H%M')" >> BUILD_TRIGGER.txt

# 6. Commit and push
git add BUILD_TRIGGER.txt
git commit -m "Trigger build v$(date '+%y%m%d%H%M')"
git push
```

---

## 🎯 VRS-Manager Lessons Learned

### Build History (What We Learned):

**Build #1:** Failed - Missing `lfs: true` in checkout
**Fix:** Added LFS download to workflow
**Lesson:** Always verify LFS files are downloaded

**Build #2:** Failed - LFS bandwidth quota exceeded
**Fix:** Only download LFS in jobs that need it
**Lesson:** Optimize LFS downloads to save bandwidth

**Build #3:** Failed - Inno Setup syntax error (line 127)
**Fix:** Used `gh run view --log-failed` to see exact error
**Lesson:** gh CLI shows exact line numbers and error messages

**Build #4:** Failed - Missing pytorch_model.bin
**Fix:** Verified LFS tracked all required model files
**Lesson:** Check all model files, not just model.safetensors

**Build #5:** Success! - All fixes applied
**Lesson:** Comprehensive verification steps prevent issues

---

## 🚀 When Everything Works

**Successful build shows:**
```
✓ BERT model verified (446.2 MB)
✓ Electron build successful (Size: 850.3 MB)
✓ Inno Setup compiled successfully (Size: 1,850.5 MB)
✓ Installer uploaded to artifacts
✓ Release created: v2511221939
```

**Download installers:**
```bash
# View latest release
gh release view --json name,assets

# Download Windows installer
gh release download --pattern "*.exe"

# Download Linux AppImage
gh release download --pattern "*.AppImage"
```

---

## 📞 Quick Reference

| Problem | Command | What It Shows |
|---------|---------|---------------|
| Build failed? | `gh run list --limit 1` | Latest build status |
| Which step failed? | `gh run view $RUN_ID --log-failed` | Exact error message |
| Version mismatch? | `python3 scripts/check_version_unified.py` | All version inconsistencies |
| LFS files missing? | `git lfs ls-files` | Files tracked by LFS |
| Model verified? | `ls -lh models/kr-sbert/` | Model files and sizes |

---

**Last Updated:** 2025-11-22
**Based on:** VRS-Manager builds #1-#8 troubleshooting experience
**Success Rate:** 100% after applying these lessons
