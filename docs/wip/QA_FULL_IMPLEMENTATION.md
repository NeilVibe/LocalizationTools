# QA FULL Mode Implementation

**Status:** DONE | **Created:** 2025-12-23

---

## GITEA ONLY

**QA FULL will NEVER run on GitHub.** Too complicated, LFS bandwidth limits.

| Platform | QA | QA FULL |
|----------|-----|---------|
| **GitHub** | Yes | **NO** |
| **Gitea** | Yes | **YES** |

GitHub workflow rejects `Build QA FULL` triggers with clear message.

---

## What QA FULL Does

**Problem:** Some enterprise deployments have zero internet access.

**Solution:** Bundle everything into a large installer that works completely offline.

| Component | Size | Location After Install |
|-----------|------|------------------------|
| Qwen model | ~900MB (compressed) | `resources/models/qwen-embedding/` |
| Python deps | included | `resources/tools/python/` |
| VC++ Redist | ~20MB | Silent install |
| Base app | ~170MB | Same as QA |
| **Actual Total** | **1,177 MB** | |

---

## Implementation Checklist - ALL DONE

### Phase 1: CI Detection - DONE

- [x] Parse `Build QA FULL` from GITEA_TRIGGER.txt
- [x] Set `build_type=FULL` environment variable
- [x] Block QA FULL on GitHub (LFS limits)

**Files modified:**
- `.gitea/workflows/build.yml` - Simplified to 3 modes, QA always on
- `.github/workflows/build-electron.yml` - Rejects QA FULL with clear message

### Phase 2: Model Download in CI - DONE (Already Existed)

- [x] Download Qwen during Gitea build (line 1275)
- [x] Uses sentence-transformers to download
- [x] Verifies model.safetensors exists

**File:** `.gitea/workflows/build.yml` (step already existed)

### Phase 3: VC++ Redistributable - DONE (Already Existed)

- [x] Smart cache downloads VC++ Redist (line 1043)
- [x] Bundled in installer
- [x] Silent install during app installation

**File:** `.gitea/workflows/build.yml` (step already existed)

### Phase 4: Add Models to extraResources - DONE

- [x] Dynamically adds models to package.json extraResources for FULL builds
- [x] Only runs when `build_type=FULL`

**File:** `.gitea/workflows/build.yml` (new step 2.6 added)

### Phase 5: App-Side Detection - DONE

- [x] main.js checks bundled location first (`resources/models`)
- [x] Falls back to download location (`appRoot/models`)
- [x] first-run-setup.js skips download if model bundled
- [x] Logs "Model bundled (offline installer)" for QA FULL

**Files modified:**
- `locaNext/electron/main.js` - Smart path detection
- `locaNext/electron/first-run-setup.js` - Skip download if bundled

---

## Trigger Commands

```bash
# QA FULL build (Gitea only) - creates ~2GB offline installer
echo "Build QA FULL" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build QA FULL" && git push gitea main

# Regular QA build - creates ~150MB installer (model downloads on first run)
echo "Build" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

## Disk Usage Strategy

**Problem:** 2GB x 20 releases = 40GB disk terrorism

**Solution:** Smart cleanup based on build type

| Build Type | Max Releases | Max Disk |
|------------|--------------|----------|
| **QA FULL** | 3 | ~6GB |
| **QA (LIGHT)** | 10 | ~1.5GB |

**Implementation:** `.gitea/workflows/build.yml` cleanup step checks `build_type` and adjusts `MAX_RELEASES` accordingly.

---

## Testing Plan

1. **CI Test:** ✅ PASSED - v25.1223.0811 (1,177 MB)
2. **Install Test:** TODO - Need `playground_FULL.sh` script
3. **Function Test:** TODO - Verify Qwen model loads without download
4. **Reject Test:** Trigger QA FULL on GitHub, verify rejection
5. **Cleanup Test:** Verify old FULL releases are deleted (max 3 kept)

### Future: playground_FULL.sh

Script to test FULL installer in Playground (when needed):
- Download FULL installer from Gitea
- Install to Playground
- Verify bundled model detected
- Test offline mode (no model download)

---

## Files Modified

| File | Change |
|------|--------|
| `.gitea/workflows/build.yml` | Simplified modes, QA always on, model bundling |
| `.github/workflows/build-electron.yml` | Rejects QA FULL trigger |
| `locaNext/electron/main.js` | Smart model path detection |
| `locaNext/electron/first-run-setup.js` | Skip download if bundled |

---

*Implementation Complete | 2025-12-23*
