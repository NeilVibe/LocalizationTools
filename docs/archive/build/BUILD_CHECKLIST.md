# LocaNext Build Checklist

**Purpose**: Ensure clean, successful GitHub Actions builds for Electron installer

**Based on**: VRS-Manager proven build protocol

---

## 📋 Pre-Build Checklist

### ✅ 1. Git LFS Verification

**Check LFS files are tracked:**
```bash
git lfs ls-files
```

**Expected output:**
```
9163cf3ca1 - models/kr-sbert/model.safetensors  (446 MB)
1792ae652d - models/kr-sbert/tokenizer.json
```

**Verify .gitattributes:**
```bash
cat .gitattributes | grep "filter=lfs"
```

**Must include:**
```
*.safetensors filter=lfs diff=lfs merge=lfs -text
*.bin filter=lfs diff=lfs merge=lfs -text
```

---

### ✅ 2. Version Verification

**Check current version:**
```bash
cat version.py
```

**Verify version is updated in all locations:**
```bash
python3 scripts/check_version_unified.py
```

**Expected**: All versions match (version.py, BUILD_TRIGGER.txt, Inno Setup, package.json)

---

### ✅ 3. Inno Setup Script Verification

**Check installer script exists:**
```bash
ls -lh installer/locanext_electron.iss
```

**Verify version in Inno Setup:**
```bash
grep "MyAppVersion" installer/locanext_electron.iss
```

**Must match version.py!**

---

### ✅ 4. GitHub Actions Workflow Verification

**Check workflow file:**
```bash
ls -lh .github/workflows/build-electron.yml
```

**Verify workflow is valid:**
```bash
cat .github/workflows/build-electron.yml | grep -E "on:|build-windows:|build-linux:|create-release:"
```

**Expected jobs:**
1. `check-build-trigger` - Reads BUILD_TRIGGER.txt
2. `build-windows` - Builds Windows installer with Inno Setup
3. `build-linux` - Builds Linux AppImage
4. `create-release` - Creates GitHub Release with downloads

---

### ✅ 5. Local Build Test (RECOMMENDED)

**Test local Electron build:**
```bash
cd locaNext
npm run build
npm run build:electron
```

**Verify output:**
```bash
ls -lh locaNext/dist-electron/
```

**Expected:**
- `LocaNext-1.0.0.AppImage` (Linux) or
- `LocaNext Setup 1.0.0.exe` (Windows)

**If local build fails, GitHub Actions will fail too!**

---

### ✅ 6. Documentation Verification

**Check all docs exist:**
```bash
ls docs/BUILD_TROUBLESHOOTING.md
ls docs/BUILD_CHECKLIST.md
ls installer_output/README.md
ls BUILD_TRIGGER.txt
```

**Verify CLAUDE.md has gh CLI commands:**
```bash
grep "gh run" CLAUDE.md
```

---

### ✅ 7. GitHub Authentication

**Check gh CLI is authenticated:**
```bash
gh auth status
```

**Expected:**
```
✓ Logged in to github.com as NeilVibe
✓ Git operations configured
```

---

## 🚀 Triggering a Build

### Step 1: Update BUILD_TRIGGER.txt

**Add build command to BUILD_TRIGGER.txt:**
```bash
echo "Build FULL v2511221939" >> BUILD_TRIGGER.txt
```

**Verify:**
```bash
tail -5 BUILD_TRIGGER.txt
```

### Step 2: Commit and Push

```bash
git add BUILD_TRIGGER.txt
git commit -m "Trigger build v2511221939

Request full Electron installer build with BERT model.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
git push origin main
```

### Step 3: Monitor Build

**Check if workflow started:**
```bash
gh run list --limit 3
```

**Watch live logs:**
```bash
gh run watch
```

**View failed logs (if build fails):**
```bash
gh run view --log-failed
```

---

## 🔍 Build Monitoring with gh CLI

### List Recent Builds
```bash
gh run list --limit 5
```

### Get Latest Build Status
```bash
gh run view $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')
```

### View Failed Logs (BEST for debugging)
```bash
gh run view $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --log-failed
```

### Search Logs for Errors
```bash
gh run view <RUN_ID> --log-failed | grep -i "error\|failed\|missing"
```

### Get Context Around Error
```bash
gh run view <RUN_ID> --log-failed | grep -B 10 -A 10 "Compile.*installer"
```

---

## ❌ Common Build Errors (VRS-Manager Lessons)

### Error 1: Missing LFS Files
**Symptom:**
```
❌ BERT model not found at: models/kr-sbert/model.safetensors
```

**Solution:**
```yaml
# In .github/workflows/build-electron.yml
- uses: actions/checkout@v4
  with:
    lfs: true  # ← Must be true for builds that need model!
```

---

### Error 2: LFS Bandwidth Quota
**Symptom:**
```
Error: batch response: This repository is over its data quota
```

**Solution:**
- Only use `lfs: true` in jobs that NEED the model (build-windows, build-linux)
- Use `lfs: false` in release job (only needs artifacts, not source)
- Each LFS download = 446MB against quota!

---

### Error 3: Inno Setup Syntax Error
**Symptom:**
```
Error on line 127 in installer script
```

**Solution:**
```bash
# Get EXACT line number with gh CLI
gh run view --log-failed | grep "Error on line"

# Check that line in Inno Setup script
sed -n '127p' installer/locanext_electron.iss
```

---

### Error 4: Version Mismatch
**Symptom:**
```
Installer compiled but filename doesn't match expected version
```

**Solution:**
```bash
# Run unified version check
python3 scripts/check_version_unified.py

# Fix any mismatches
```

---

### Error 5: Missing Model Files
**Symptom:**
```
❌ Missing required file: config.json
```

**Solution:**
```bash
# Verify all model files are tracked by LFS
cd models/kr-sbert/
ls -lh
git lfs ls-files

# If files are missing, ensure they're in .gitattributes
```

---

## ✅ Successful Build Indicators

**GitHub Actions:**
- ✅ All 4 jobs pass (check-trigger, build-windows, build-linux, create-release)
- ✅ Green checkmarks on all steps
- ✅ Artifacts uploaded successfully

**Release Created:**
- ✅ GitHub Release appears at `/releases`
- ✅ Download links work:
  - `LocaNext_v2511221939_Setup.exe` (~2GB)
  - `LocaNext.AppImage` (~2GB)

**Verification:**
```bash
gh release list
gh release view v2511221939
```

---

## 📊 Build Metrics (From VRS-Manager)

**Typical Build Times:**
- Check trigger: ~30 seconds
- Windows build: ~15-20 minutes
- Linux build: ~10-15 minutes
- Create release: ~2-3 minutes
- **Total: ~30-40 minutes**

**LFS Bandwidth Usage:**
- Windows build: 446 MB (model download)
- Linux build: 446 MB (model download)
- Release job: 0 MB (lfs=false)
- **Total per build: ~900 MB**

**GitHub Actions Minutes:**
- Windows runner: ~20 minutes
- Linux runner: ~15 minutes
- **Total per build: ~35 minutes**

---

## 🎯 Best Practices

1. **Always test local build first** - Saves GitHub Actions minutes
2. **Use gh CLI for debugging** - Shows EXACT errors (not just "failed")
3. **Monitor LFS bandwidth** - You have 1 GB/month free
4. **Manual builds only** - Don't trigger on every commit
5. **Version verification** - Run `check_version_unified.py` before build
6. **Document failures** - Add to BUILD_TROUBLESHOOTING.md if new error

---

## 📚 Related Documentation

- **BUILD_TROUBLESHOOTING.md** - Error solutions from VRS-Manager
- **CLAUDE.md** - gh CLI command reference
- **installer/locanext_electron.iss** - Inno Setup script
- **.github/workflows/build-electron.yml** - Build workflow
- **BUILD_TRIGGER.txt** - Manual build trigger

---

**Last Updated**: 2025-11-22
**Build Protocol Version**: 1.0 (based on VRS-Manager)
**Status**: Ready for production builds
