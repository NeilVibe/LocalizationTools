# Build & Distribution System

**VRS-Manager Pattern** | **Manual Build Triggers** | **Git LFS Management**

---

## 📦 VERSIONING SCHEME

**Format:** `YYMMDDHHMM` (DateTime-based versioning)

- YY = Year (25 = 2025)
- MM = Month (11 = November)
- DD = Day (22)
- HH = Hour (19)
- MM = Minute (39)

**Example:** `2511221939` = November 22, 2025 at 7:39 PM

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
echo "Build FULL v$NEW_VERSION" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt
git commit -m "Trigger build v$NEW_VERSION"
git push origin main
```

**Golden Rule:** Never commit version changes without running `check_version_unified.py` first!

---

## 🎯 BUILD TRIGGER - MANUAL CONTROL

**IMPORTANT:** Builds are triggered MANUALLY by YOU, not automatic on every push!

```bash
# Build FULL version (with 446MB BERT model)
echo "Build FULL v$(date '+%y%m%d%H%M')" >> BUILD_TRIGGER.txt
git add BUILD_TRIGGER.txt
git commit -m "Trigger FULL build v$(date '+%y%m%d%H%M')"
git push origin main
```

**Why Manual Builds?**
- Control when releases happen (not every commit)
- Save GitHub Actions minutes
- Save LFS bandwidth quota (446MB model download)
- Intentional release process

**Build starts automatically AFTER you push BUILD_TRIGGER.txt update.**

Check: https://github.com/NeilVibe/LocalizationTools/actions

---

## ⚠️ GIT LFS BANDWIDTH QUOTA (CRITICAL!)

**GitHub LFS has monthly bandwidth quota:**
- Free tier: 1GB bandwidth/month
- Korean BERT model: 446MB stored in LFS
- Each build downloads model = counts against quota

**The Fix (Use in GitHub Actions):**

```yaml
# Electron build (BERT required for bundling)
build-electron:
  - uses: actions/checkout@v3
    with:
      lfs: true  # ✅ Download BERT model for bundling

# Release job (only needs artifacts, not source)
create-release:
  - uses: actions/checkout@v3
    with:
      lfs: false  # ✅ No source files needed, saves bandwidth
```

**Key Lesson:** Only enable `lfs: true` where BERT model is actually needed!

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

# Get context around error
gh run view <RUN_ID> --log-failed | grep -B 10 -A 10 "Compile.*installer"
```

**Alternative: GitHub API (no auth required):**

```bash
curl -s "https://api.github.com/repos/NeilVibe/LocalizationTools/actions/runs?per_page=5" | \
python3 -c "import sys, json; runs = json.load(sys.stdin)['workflow_runs']; \
[print(f\"{r['name']}: {r['status']} - {r['conclusion']}\") for r in runs[:5]]"
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
- ✅ **version.py** - Single source of truth
- ✅ **server/config.py** - Backend imports VERSION
- ✅ **locaNext/package.json** - Electron app version
- ✅ **README.md** - Documentation version
- ✅ **Roadmap.md** - Project status version
- ✅ **CLAUDE.md** - Master navigation hub

**⚠️ MANDATORY WORKFLOW:**
1. Update VERSION in version.py
2. **RUN THIS CHECK** → `python3 scripts/check_version_unified.py`
3. Only if exit code 0 (success) → commit and push
4. Then trigger build (if releasing)

**NEVER commit version changes without running this check first!**

---

## 📚 Related Documentation

- **BUILD_TROUBLESHOOTING.md** - Complete debugging guide
- **BUILD_CHECKLIST.md** - Pre-release checklist
- **PACKAGING_GUIDE.md** - Electron packaging details
- **DEPLOYMENT.md** - Deployment procedures
