# LocaNext - Development Roadmap

**Version**: 2512081600 | **Updated**: 2025-12-08 | **Status**: Production Ready

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
├── CI/CD:       ✅ GitHub Actions + 🔄 Gitea (ephemeral mode, verifying)
└── Distribution: ✅ Auto-update enabled
```

---

## In Progress

*(No active development tasks - all priorities completed!)*

---

## Recently Completed

### P13.11: Gitea Windows Build "Job Failed" Status Bug (2025-12-08)

**Status:** 🔄 IMPLEMENTED - Awaiting verification build

**Problem:** Build succeeds (ZIP created, tests pass) but act_runner reports "Job failed" during cleanup.

**Root Cause:** Go's `os.RemoveAll()` fails with `ERROR_SHARING_VIOLATION` on Windows. The act_runner process holds file handles that can't be released by child processes.

**Solution:** Ephemeral Runner Mode (like GitHub Actions)
- Runner exits after each job → all handles released
- Wrapper script re-registers for next job
- No hacky workarounds, no masked failures

**Implementation:**
```
C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\
├── run_ephemeral.bat        # Ephemeral wrapper
├── registration_token.txt   # Gitea token
└── config.yaml              # Runner config
```

**Setup (one-time, Admin PowerShell):**
```powershell
nssm set GiteaActRunner Application "C:\...\run_ephemeral.bat"
nssm restart GiteaActRunner
```

**Full documentation:** [WINDOWS_RUNNER_SETUP.md](docs/deployment/WINDOWS_RUNNER_SETUP.md)

---

**Future Improvement: Build Caching**
- Currently downloading ~350MB every build (VC++, Python, npm, pip)
- GitHub Actions has `actions/cache` for elegant caching with staleness checks
- For Gitea, we need to implement similar:
  - Pre-download files to local cache on Windows machine
  - Add cache staleness checks (hash comparison, version checks)
  - Modify workflow to use cache-first approach
- Benefits: Fast builds + clean/reproducible + elegant

---

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
