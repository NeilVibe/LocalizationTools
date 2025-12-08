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

**Status: NEXT → Fix #4 (Upgrade act_runner)**

**The bug:** Build succeeds but act_runner reports "🏁 Job failed" during cleanup.

| Fix | Description | Result |
|-----|-------------|--------|
| #1 | Remove disabled `create-release` job | ❌ Failed |
| #2 | Add `persist-credentials: false` to checkout | ❌ Failed |
| #3 | Replace `actions/checkout` with `git clone` | ❌ Failed |
| #4 | **Upgrade act_runner v0.2.11 → v0.2.13** | 🔄 Next |

**Root cause:** act_runner v0.2.11 bug - reports false failure during host mode cleanup on Windows.

**Fix #4 Instructions (Windows Admin PowerShell):**
```powershell
cd C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner
nssm stop GiteaActRunner
move act_runner.exe act_runner_v0.2.11.bak
curl -L -o act_runner.exe https://gitea.com/gitea/act_runner/releases/download/v0.2.13/act_runner-0.2.13-windows-amd64.exe
nssm start GiteaActRunner
```

**After upgrade:** Trigger Gitea build → check if status shows ✅

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
