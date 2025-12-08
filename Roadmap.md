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
| 2025-12-08 | Fix #13 | Replace `timeout` with `ping -n 6` - workdir deleted ✅ but job still fails |
| 2025-12-08 | Fix #14 | Also delete parent hash - act_runner fails with "pathcmd.txt not found" (it needs the dir!) |
| 2025-12-08 | Fix #15 | Don't delete - just release handles via cmd.exe cd/taskkill, let act_runner clean up - still fails (5.4s timeout) |

**Key Discovery:**
- cmd.exe CAN delete the workdir, PowerShell cannot (handle inheritance issue)
- But act_runner needs the workdir to exist for its cleanup (`act\workflow\pathcmd.txt`)
- Even with cmd.exe releasing handles, act_runner.exe (parent Go process) still holds handles
- The cleanup consistently times out after ~5.4 seconds

**Conclusion:** The issue is in act_runner's host mode cleanup on Windows. The Go process maintains handles on the workdir that child processes cannot release.

---

### P13.11 Deep Dive: Technical Root Cause & Solutions (2025-12-08)

**Exact Technical Root Cause:**
```go
// From nektos/act pkg/container/host_environment.go
func (e *HostEnvironment) Remove() common.Executor {
    return func(_ context.Context) error {
        if e.CleanUp != nil {
            e.CleanUp()
        }
        return os.RemoveAll(e.Path)  // <-- THIS FAILS ON WINDOWS
    }
}
```

1. `os.RemoveAll()` fails with `ERROR_SHARING_VIOLATION` (Windows error 0x20)
2. Go's act_runner.exe process holds file handles on the workdir
3. Child processes (PowerShell, cmd.exe) CANNOT release parent's handles
4. No retry logic, no error handling - failure = job marked as failed

**Go's Own Solution (Go 1.19+):**
Go's testing package has this EXACT same issue and uses a [retry loop with exponential backoff](https://github.com/golang/go/issues/51442):
```go
func removeAll(path string) error {
    const arbitraryTimeout = 2 * time.Second
    var nextSleep = 1 * time.Millisecond
    for {
        err := os.RemoveAll(path)
        if !isWindowsAccessDenied(err) && !isSharingViolation(err) {
            return err
        }
        if time.Since(start) + nextSleep >= arbitraryTimeout {
            return err
        }
        time.Sleep(nextSleep)
        nextSleep += time.Duration(rand.Int63n(int64(nextSleep)))
    }
}
```
This was implemented in Go 1.19 to handle `ERROR_ACCESS_DENIED` and `ERROR_SHARING_VIOLATION`.

**Key Research Findings:**
| Finding | Source |
|---------|--------|
| GitHub Actions Windows uses fresh Azure VMs (not Docker) | GitHub docs |
| Docker can't run native Windows Electron builds | Docker limitation |
| No act_runner config to skip cleanup | [Gitea Forum](https://forum.gitea.com/t/disable-job-cleaning-between-jobs-host-mode/8540) |
| GitHub's own runner has same issue | [actions/runner #2687](https://github.com/actions/runner/issues/2687) |
| `RUNNER_TRACKING_ID=""` trick only prevents process kill, not cleanup | [actions/runner #598](https://github.com/actions/runner/issues/598) |
| [github-act-runner](https://github.com/ChristopherHX/github-act-runner) has better Windows shell handling | Alternative runner |

**Proposed Solutions:**

| Solution | Effort | Impact | Recommendation |
|----------|--------|--------|----------------|
| **A. Fork & Patch gitea/act** | High | ✅ Permanent fix | Best long-term |
| **B. PR to nektos/act** | Medium | ✅ Upstream fix | Submit & wait |
| **C. Commit Status API** | Medium | ✅ Green checks | Good workaround |
| **D. External Cleanup Service** | Low | ⚠️ Dir clean only | Partial fix |
| **E. Runner Auto-Restart** | Low | ⚠️ Releases handles | Hacky workaround |

**Solution A: Fork & Patch gitea/act**
1. Fork `gitea.com/gitea/act` (the soft fork act_runner uses)
2. Modify `pkg/container/host_environment.go` `Remove()` function
3. Add Go's retry loop pattern for Windows
4. Build custom act_runner.exe
5. Deploy on Windows machine
- Pros: Permanent fix, proper solution
- Cons: Need to maintain fork, rebuild on updates

**Solution B: PR to nektos/act**
1. Create PR to upstream [nektos/act](https://github.com/nektos/act)
2. Add retry logic to `host_environment.go`
3. Wait for merge → gitea/act sync → act_runner release
- Pros: No fork maintenance, benefits everyone
- Cons: Could take weeks/months

**Solution C: Commit Status API Workaround**
1. Add Gitea webhook for workflow completion
2. When job "fails" but all steps passed → API call to set commit status "success"
3. Shows green check on commits despite internal "failed" status
- Pros: Visual fix without code changes
- Cons: Workflow still shows "failed" internally

**Solution D: External Cleanup Service**
1. Windows scheduled task monitors workdir
2. Deletes old job directories (older than X minutes)
3. Runs independently, no handle conflicts
- Pros: Keeps disk clean
- Cons: Doesn't fix status

**Solution E: Runner Auto-Restart**
1. Modify NSSM to restart service after each job
2. Service restart releases all Go handles
3. Next job cleanup succeeds
- Pros: Simple, no code changes
- Cons: 10-20 second restart delay between jobs

**Current Decision:** Pursuing Solution B (upstream PR) first, with Solution C as immediate workaround.

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
