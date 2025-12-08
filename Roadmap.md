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

### P13.11: FIX Gitea Windows Build "Job Failed" Bug

**Status: FIX APPLIED - NEEDS COMMIT & TEST**

**What was the bug?**
- Gitea builds completed successfully (ZIP created, all steps ✅)
- But act_runner reported "🏁 Job failed" at the very end
- This was a FALSE failure - the build actually worked

**Root cause found (2025-12-08):**
- `.gitea/workflows/build.yml` had a disabled job called `create-release`
- It had `if: false` (never runs) BUT also `needs: [build-windows]`
- act_runner v0.2.11 bug: evaluates disabled job dependencies incorrectly
- This caused false "failed" status during cleanup phase

**Fix applied (NOT YET COMMITTED):**
- Edited `.gitea/workflows/build.yml` (lines 838-843)
- Removed the entire `create-release` job (was ~130 lines of dead code)
- Replaced with a comment explaining why it was removed

**TO COMPLETE THIS FIX:**
```bash
# 1. Commit the changes
git add -A && git commit -m "fix: Remove disabled create-release job (act_runner status bug)"

# 2. Push to both remotes
git push origin main && git push gitea main

# 3. Test with a Gitea build
echo "Test v$(date +%y%m%d%H%M)" >> GITEA_TRIGGER.txt
git add GITEA_TRIGGER.txt && git commit -m "Test Gitea build fix"
git push gitea main

# 4. Check Gitea Actions → should show green ✅
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
