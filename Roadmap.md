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

**Proposed Solutions (Ranked by Elegance):**

| Rank | Solution | Effort | Impact | Notes |
|------|----------|--------|--------|-------|
| 🥇 | **F. Ephemeral Runner** | Medium | ✅ ELEGANT | Like GitHub Actions VMs |
| 🥈 | **G. Hyper-V Checkpoint** | Medium | ✅ Fresh VM | Reset after each job |
| 🥉 | **B. PR to nektos/act** | Medium | ✅ Upstream fix | Benefits everyone |
| 4 | **A. Fork & Patch** | High | ✅ Permanent | Maintain fork |
| 5 | **E. Runner Auto-Restart** | Low | ⚠️ Hacky | Works but slow |
| 6 | **C. Commit Status API** | Low | ⚠️ Masks failures | Currently testing |

---

### 🥇 Solution F: Ephemeral Runner (MOST ELEGANT)

**This is how GitHub Actions works** - fresh runner for each job!

act_runner has `--ephemeral` mode ([PR #649](https://gitea.com/gitea/act_runner/pulls/649), [Gitea #33570](https://github.com/go-gitea/gitea/pull/33570)):
```bash
# Register ephemeral runner (one-shot)
./act_runner register --ephemeral --instance http://localhost:3000 --token TOKEN --name windows-ephemeral --labels windows:host
```

**How it works:**
1. Runner registers with `--ephemeral` flag
2. Accepts ONE job, executes it
3. After job completes → runner **EXITS** (releasing ALL handles!)
4. Wrapper script re-registers for next job

**Wrapper script concept:**
```batch
:loop
act_runner.exe register --ephemeral -c config.yaml --instance %GITEA_URL% --token %TOKEN% --name win-runner --labels windows:host
act_runner.exe daemon --once -c config.yaml
goto loop
```

**Pros:**
- Elegant like GitHub Actions (fresh each time)
- No handle issues (process exits = handles released)
- No need to patch code
- Security benefit (single-use credentials)

**Cons:**
- Re-registration overhead (~5-10 seconds between jobs)
- Need registration token (can use organization/instance token)
- Need wrapper script for Windows service

---

### 🥈 Solution G: Hyper-V Checkpoint Reset

**Like fresh Azure VMs but local:**

1. Create Windows VM in Hyper-V with all build tools pre-installed
2. Take checkpoint (snapshot) after clean setup
3. After each job: `Restore-VMSnapshot` to reset VM
4. Wrapper script on host triggers restore

```powershell
# On host machine (not the VM)
$vmName = "LocaNext-Builder"
$checkpointName = "Clean-Build-State"

while ($true) {
    # Wait for job completion marker
    while (-not (Test-Path "\\VM\share\job_complete.txt")) { Start-Sleep 5 }

    # Reset VM to clean state
    Stop-VM -Name $vmName -Force
    Restore-VMCheckpoint -VMName $vmName -Name $checkpointName -Confirm:$false
    Start-VM -Name $vmName

    Remove-Item "\\VM\share\job_complete.txt"
}
```

**Pros:**
- 100% fresh state each build (like GitHub's Azure VMs)
- No cleanup issues at all
- Can test different Windows versions

**Cons:**
- VM startup time (~30-60 seconds)
- More complex setup
- Requires Hyper-V (Windows Pro/Server)

---

### 🥉 Solution B: PR to nektos/act (Upstream Fix)

Add Go's retry loop pattern to `host_environment.go`:
```go
func removeAllWithRetry(path string) error {
    const timeout = 2 * time.Second
    var nextSleep = 1 * time.Millisecond
    start := time.Now()
    for {
        err := os.RemoveAll(path)
        if err == nil || !isWindowsAccessError(err) {
            return err
        }
        if time.Since(start)+nextSleep >= timeout {
            return err
        }
        time.Sleep(nextSleep)
        nextSleep *= 2
    }
}
```

**Pros:** Benefits everyone, no fork maintenance
**Cons:** Could take weeks/months for merge + release

---

### Solution A: Fork & Patch gitea/act

Same as Solution B but maintain our own fork.

**Pros:** Immediate fix
**Cons:** Fork maintenance burden

---

### Solution E: Runner Auto-Restart (via NSSM)

Configure NSSM to restart after each job exit:
```batch
nssm set GiteaActRunner AppExit Default Restart
nssm set GiteaActRunner AppRestartDelay 5000
```

**Pros:** Simple, no code changes
**Cons:** 10-20 second restart delay

---

### Solution C: Commit Status API (Current Workaround)

⚠️ **Note:** This masks real failures - not elegant!

Set commit status before cleanup runs. If real build fails, it still shows success.

**Pros:** Quick to implement
**Cons:** Masks real failures, unstable

---

### Current Implementation Status

| Solution | Status | Notes |
|----------|--------|-------|
| **C. Status API** | 🧪 Testing | Build v2512081445 in progress |
| **F. Ephemeral** | ✅ Created | Scripts ready, needs service update |
| **B. Upstream PR** | 📝 Draft | Will submit after testing F |

**Solution F Implementation (2025-12-08):**

Files created on Windows machine:
```
C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\
├── run_ephemeral.bat        # Ephemeral wrapper script
├── registration_token.txt    # Gitea registration token
└── SETUP_EPHEMERAL.md       # Setup instructions
```

**To activate ephemeral mode (ONE-TIME setup, requires Admin):**

Why admin? NSSM manages Windows services - modifying services requires admin rights.
After setup, the service runs automatically on boot - no more admin needed.

```powershell
# === RUN ONCE IN ADMIN POWERSHELL ===

# Step 1: Stop current service
nssm stop GiteaActRunner

# Step 2: Update to ephemeral script
nssm set GiteaActRunner Application "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\run_ephemeral.bat"
nssm set GiteaActRunner AppParameters ""

# Step 3: Start service
nssm start GiteaActRunner

# Step 4: Verify it's running
nssm status GiteaActRunner
```

**What happens after setup:**
1. Windows service starts `run_ephemeral.bat` automatically
2. Script registers runner with `--ephemeral`
3. Runner accepts ONE job, runs it, EXITS (handles released!)
4. Script loops and re-registers for next job
5. Service auto-starts on Windows boot

**Rollback (if needed):**
```powershell
nssm set GiteaActRunner Application "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner.exe"
nssm set GiteaActRunner AppParameters "-c config.yaml daemon"
nssm restart GiteaActRunner
```

---

### Recommended Path Forward

1. **Immediate**: Test Solution C (currently running)
2. **Short-term**: Implement Solution F (Ephemeral Runner)
   - Create wrapper script for Windows
   - Test with organization token
   - Replace NSSM service
3. **Long-term**: Submit Solution B (PR to nektos/act)

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
