# LocaNext - Development Roadmap

**Version**: 2512080549 | **Updated**: 2025-12-08 | **Status**: Production Ready

> **Full History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)

---

## Current Status

```
LocaNext v2512080549
├── Backend:     ✅ 55+ API endpoints, async, WebSocket
├── Frontend:    ✅ Electron + Svelte (LocaNext Desktop)
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar
├── Tests:       ✅ 912 total (no mocks)
├── Security:    ✅ 86 tests (IP filter, CORS, JWT, audit)
├── CI/CD:       ✅ GitHub Actions + ⚠️ Gitea (builds OK, status bug)
└── Distribution: ✅ Auto-update enabled
```

---

## In Progress

### P13.11: Gitea Windows Build Pipeline

```
STATUS: ⚠️ BUILD WORKS, STATUS REPORTING BUG

THE BUILD ACTUALLY SUCCEEDS:
├── Portable ZIP created: LocaNext_v2512080549_Light_Portable.zip (106.8 MB)
├── All verification steps pass: [PASS] All critical files present!
├── Build Complete runs: [SUCCESS] LocaNext LIGHT Build Complete!
└── BUT: act_runner reports "Job failed" during cleanup (FALSE NEGATIVE)

ARTIFACT LOCATION (on Windows runner):
C:\WINDOWS\system32\config\systemprofile\.cache\act\{hash}\hostexecutor\installer_output\
└── LocaNext_v{VERSION}_Light_Portable.zip

ARCHITECTURE:
├── Gitea Server     → WSL Linux (localhost:3000)
├── Linux Runner     → WSL (handles ubuntu-latest jobs) ✅
└── Windows Runner   → Windows native (act_runner v0.2.11 as SYSTEM service) ✅
```

### COMPLETED FIXES (2025-12-08):
```
[✅] Inno Setup path issues → Switched to portable ZIP (bypass NSIS/Inno)
[✅] NSIS include files missing → Changed electron-builder target to "dir"
[✅] Embedded Python check failing → Made informational for LIGHT builds
[✅] Artifact upload failing → Removed (actions/upload-artifact@v4 not supported on Gitea)
[✅] Version not extracted → Fixed with ::set-output syntax
[✅] Job dependencies causing issues → Made build-windows standalone
[✅] Tools directory missing → Create before copying scripts
```

### KNOWN ISSUE - act_runner v0.2.11 Status Bug:
```
SYMPTOM:
- All workflow steps succeed (✅ marks everywhere)
- ZIP file created correctly with proper version
- Post-checkout cleanup succeeds
- THEN: "🏁 Job failed" during "Cleaning up container" phase

EVIDENCE:
- Log shows: "✅ Success - Post Checkout code"
- Log shows: "Cleaning up container for job Build Windows LIGHT Installer"
- Log shows: "🏁 Job failed" (7 seconds later, no error between)

ROOT CAUSE:
- Unknown bug in act_runner v0.2.11 when running on Windows as SYSTEM service
- May be related to how act_runner reports composite job status
- All steps succeed but final job status is incorrectly marked as failed

WORKAROUND OPTIONS:
1. Ignore status, manually verify artifact exists
2. Add post-build script to copy artifact out of cache
3. Upgrade act_runner when new version available
4. File issue on nektos/act repository
```

### REMAINING WORK:
```
[📋] OPTION A: Accept current state (build works, ignore false failure)
     - Document known issue
     - Create script to retrieve artifacts from runner cache
     - Monitor for act_runner updates

[📋] OPTION B: Debug act_runner issue further
     - Check act_runner logs on Windows: C:\GiteaRunner\*.log
     - Try different act_runner versions
     - Test with different job configurations

[📋] OPTION C: Alternative build approach
     - Build directly on Windows (no CI/CD)
     - Use PowerShell script triggered by webhook
     - Mirror builds from GitHub Actions instead
```

### FILES MODIFIED (for next Claude reference):
```
.gitea/workflows/build.yml - Main workflow (many changes)
  - Removed needs: dependency from build-windows
  - Added "Get Version from Source" step (reads version.py directly)
  - Removed artifact upload step
  - Changed electron-builder to "dir" target
  - Added portable ZIP creation instead of Inno Setup
  - Removed "Test Backend" step (no embedded Python in LIGHT)
  - Added "Build Complete" success marker step

installer/locanext_light.iss - Added skipifsourcedoesntexist flags
locaNext/package.json - win.target: "dir" (bypass NSIS)
version.py - Current: 2512080549
```

### HOW TO TEST BUILD (for next Claude):
```bash
# 1. Update version
NEW_VER=$(date '+%y%m%d%H%M')
# Edit version.py, .iss files, README, CLAUDE.md

# 2. Run version check
python3 scripts/check_version_unified.py

# 3. Add trigger
echo "Build LIGHT v$NEW_VER - description" >> GITEA_TRIGGER.txt

# 4. Commit and push
git add -A && git commit -m "message"
git push origin main && git push gitea main

# 5. Wait ~200 seconds, check logs
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/*/1*.log | head -3
tail -50 ~/gitea/data/actions_log/neilvibe/LocaNext/XX/YYY.log

# 6. Check for success markers in log:
#    - "[OK] Portable ZIP created: LocaNext_v{VERSION}_Light_Portable.zip"
#    - "[SUCCESS] LocaNext LIGHT Build Complete!"
#    - Ignore "Job failed" - it's a false negative
```

---

## Recently Completed

### P13.10: Build Separation (2025-12-07) ✅

Separated GitHub and Gitea build triggers:
- GitHub: `BUILD_TRIGGER.txt` (production)
- Gitea: `GITEA_TRIGGER.txt` (local testing)

### P16: QuickSearch QA Tools (2025-12-06) ✅

5 QA endpoints + frontend tab for glossary checking.

### P15: Monolith Migration (2025-12-06) ✅

All 3 tools verified with production test files.

---

## Future Priorities

### P17: LanguageData Manager (CAT Tool)

Full-featured translation memory management:
- Import/Export TMX, XLIFF
- Fuzzy matching
- Term base integration

### P18: Platform UI/UX Overhaul

Modern UI redesign:
- Dashboard improvements
- Theme customization
- Keyboard shortcuts

### P19: Performance Monitoring

- Query optimization
- Memory profiling
- Load testing

---

## Quick Commands

```bash
# Start servers
python3 server/main.py           # Backend (8888)
cd locaNext && npm run electron:dev  # Desktop app

# Testing
RUN_API_TESTS=1 python3 -m pytest -v

# Build (GitHub production)
python3 scripts/check_version_unified.py
echo "Build LIGHT vXXXX" >> BUILD_TRIGGER.txt
git push origin main

# Build (Gitea local test)
echo "Build LIGHT vXXXX" >> GITEA_TRIGGER.txt
git push gitea main
```

---

## Key Principles

1. **Monolith is Sacred** - Copy logic exactly, only change UI
2. **Backend is Flawless** - Never modify core without permission
3. **Log Everything** - Use `logger`, never `print()`
4. **Test with Real Data** - No mocks for core functions
5. **Version Before Build** - Run `check_version_unified.py`

---

*For detailed history of all completed work, see [ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)*
