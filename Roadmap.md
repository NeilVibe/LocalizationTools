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

### P13.11: Gitea Windows Build "Job Failed" Status Bug

**Status: KNOWN LIMITATION - Build works, status cosmetic only**

**The bug:** Build succeeds 100% (ZIP created, tests pass) but act_runner reports "🏁 Job failed" during cleanup phase.

| Fix | Description | Result |
|-----|-------------|--------|
| #1 | Remove disabled `create-release` job | ❌ Still fails |
| #2 | Add `persist-credentials: false` | ❌ Still fails |
| #3 | Replace `actions/checkout` with `git clone` | ❌ Still fails |
| #4 | Upgrade act_runner v0.2.11 → v0.2.13 | ❌ Still fails |
| #5 | Enable debug logging | ❌ No additional info |

**Root cause:** nektos/act bug in host mode on Windows
- "Cleaning up container" runs even with no container (host mode)
- Cleanup phase returns failure for unknown reason
- [Gitea forum confirms](https://forum.gitea.com/t/disable-job-cleaning-between-jobs-host-mode/8540) no way to disable cleanup

**Current workaround:** None - this is cosmetic only
- ✅ Build actually succeeds
- ✅ ZIP is created correctly
- ✅ All steps pass
- ❌ Status shows "failed" (false positive)

**Future options:**
- Wait for act_runner fix
- Report issue to gitea/act_runner repo
- Accept cosmetic limitation for local testing (GitHub builds show ✅)

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
