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
| #6 | Pre-cleanup with file lock release | 🔄 Testing |

**Root cause (Deep Investigation):**

1. Job status determined by `jobError == nil` in [job_executor.go](https://github.com/nektos/act/blob/master/pkg/runner/job_executor.go)
2. `SetJobError(ctx, ctx.Err())` is called when context has error
3. `ctx.Err()` returns `context.Canceled` or `context.DeadlineExceeded`
4. **6-second gap** between "Cleaning up" and "Job failed" suggests context issue during cleanup
5. Windows host mode cleanup (`HostEnvironment.CleanUp`) may be triggering context error

**Related issues found:**
- [nektos/act #587](https://github.com/nektos/act/issues/587) - Windows context canceled (Docker mode, fixed)
- [nektos/act #1561](https://github.com/nektos/act/issues/1561) - Container removal context canceled
- [Gitea forum](https://forum.gitea.com/t/disable-job-cleaning-between-jobs-host-mode/8540) - No cleanup disable option

**Current status:** Cosmetic only - build works
- ✅ ZIP created correctly
- ✅ All steps pass
- ❌ Status shows "failed" (false positive)

**Next steps:**
- Methodical investigation in progress
- Check recent logs, identify exact failure point, build solution incrementally

**Investigation Log:**
| Date | Step | Finding |
|------|------|---------|
| 2025-12-08 | Check logs | Directory locked during cleanup, even after killing node/python/git |
| 2025-12-08 | Add diagnostics | Added PowerShell script to show PWD, running processes, and what's locking files |
| 2025-12-08 | **ROOT CAUSE #1** | **PowerShell PWD was INSIDE the act cache directory!** Windows cannot delete a directory that is the current working directory of ANY running process. Diagnostic output showed: `PWD: C:\...\act\{hash}\hostexecutor` and `Is PWD inside act cache? True` |
| 2025-12-08 | Fix #7 | Add `Set-Location C:\` before cleanup to move PWD out of workdir |
| 2025-12-08 | Fix #7 result | PWD change worked ✅ (`Changed PWD to: C:\`), but error changed from "in use" to "Access denied" |
| 2025-12-08 | **ROOT CAUSE #2** | **Runner config file not loaded!** Checked NSSM service - it ran `act_runner.exe daemon` without `-c config.yaml`. The `workdir_parent` setting in config.yaml was being ignored! |
| 2025-12-08 | Fix #8 | Updated NSSM service: `nssm set GiteaActRunner AppParameters '-c config.yaml daemon'` |
| 2025-12-08 | Fix #8 result | Config now applied ✅ Workdir moved from `C:\...\systemprofile\.cache\act\` to `C:\...\GiteaRunner\_work\` but cleanup still fails |
| 2025-12-08 | Fix #9 | Simplified cleanup step, removed verbose diagnostic |
| 2025-12-08 | Fix #10 | Try to delete workdir ourselves before act_runner cleanup - same error "used by another process" |
| 2025-12-08 | Fix #11 | Add 10 second delay before delete - still fails, some process still holds lock |
| 2025-12-08 | Fix #12 | Use cmd.exe instead of PowerShell - **WORKDIR DELETED SUCCESSFULLY!** But `timeout` command failed |
| 2025-12-08 | Fix #13 | Replace `timeout` with `ping -n 6` (works in non-interactive mode) |

**Key Discovery:** cmd.exe CAN delete the workdir, PowerShell cannot. The PowerShell process likely inherits handles from act_runner that cmd.exe doesn't.

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
