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
├── CI/CD:       ✅ GitHub Actions + ⚠️ Gitea (builds OK, status bug P13.11)
└── Distribution: ✅ Auto-update enabled
```

---

## In Progress

### P13.11: Gitea Windows Build "Job Failed" Status Bug

**Status:** 🔴 ACTIVE - Cleanup phase fails on Windows

**The Problem:**
Build succeeds 100% (ZIP created, tests pass) but act_runner reports "Job failed" during cleanup phase.

```
[SUCCESS] LocaNext LIGHT Build Complete!
Output: LocaNext_v2512081600_Light_Portable.zip (106.8 MB)
...
Cleaning up container for job Build Windows LIGHT Installer
🏁 Job failed    ← FALSE POSITIVE (build actually succeeded!)
```

**Root Cause:**
```go
// act_runner (nektos/act) pkg/container/host_environment.go
return os.RemoveAll(e.Path)  // FAILS on Windows with ERROR_SHARING_VIOLATION
```
- Go process holds file handles on workdir
- Windows can't delete directories with open handles
- No retry logic in act_runner → failure = job marked failed

---

### What We've Tried

| # | Solution | Result |
|---|----------|--------|
| 1 | Remove disabled jobs | ❌ Still fails |
| 2 | persist-credentials: false | ❌ Still fails |
| 3 | Replace checkout with git clone | ❌ Still fails |
| 4 | Upgrade act_runner v0.2.13 | ❌ Still fails |
| 5 | Pre-cleanup with taskkill | ❌ Still fails |
| 6 | Change PWD before cleanup | ❌ Still fails |
| 7 | Custom workdir_parent config | ❌ Still fails |
| 8 | cmd.exe cleanup (not PowerShell) | ⚠️ Deletes files but job still fails |
| 9 | **Ephemeral runner mode** | ⚠️ Runner restarts OK, but cleanup still fails BEFORE exit |
| 10 | Status API workaround | ❌ Rejected (masks real failures) |

**Key Finding:** Ephemeral mode ensures fresh runner per job, but cleanup failure happens BEFORE runner exits. The job is marked "failed" during cleanup, then runner exits.

---

### How GitHub Actions Succeeds

**GitHub's Secret: Fresh Azure VMs**

```
GitHub Actions Windows:
┌─────────────────────────────────────────┐
│  Fresh Azure VM spun up for job         │
│  ↓                                      │
│  Job runs (checkout, build, test)       │
│  ↓                                      │
│  Job completes → VM DESTROYED           │  ← No cleanup needed!
│  ↓                                      │
│  Next job → NEW fresh VM                │
└─────────────────────────────────────────┘
```

- VM is **ephemeral** at the infrastructure level
- No cleanup code runs - whole VM is discarded
- This is why `windows-latest` works perfectly

**Our Situation:**
```
Gitea + act_runner on Windows:
┌─────────────────────────────────────────┐
│  Same Windows host for all jobs         │
│  ↓                                      │
│  Job runs (checkout, build, test)       │
│  ↓                                      │
│  Cleanup phase → os.RemoveAll() FAILS   │  ← Problem here!
│  ↓                                      │
│  Job marked "failed" (false positive)   │
└─────────────────────────────────────────┘
```

---

### Potential Solutions (Ranked)

| # | Solution | Effort | Elegance | Notes |
|---|----------|--------|----------|-------|
| 🥇 | **Hyper-V VM Reset** | Medium | ✅ Elegant | Copy GitHub's approach locally |
| 🥈 | **PR to nektos/act** | Medium | ✅ Upstream | Add retry loop, benefits everyone |
| 🥉 | **WSL2 Build Agent** | High | ⚠️ Complex | Run Windows build from WSL |
| 4 | **Fork act_runner** | High | ⚠️ Maintenance | Patch and maintain our own |
| 5 | **Accept as cosmetic** | None | ❌ Not elegant | Build works, ignore red status |

---

### 🥇 Solution: Hyper-V VM Reset (Copy GitHub)

**Replicate GitHub's fresh-VM approach locally:**

```
Our Hyper-V Setup:
┌─────────────────────────────────────────┐
│  Windows VM in Hyper-V (pre-configured) │
│  - Git, Node, Python, build tools       │
│  - act_runner registered                │
│  - Checkpoint: "Clean-Build-State"      │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  Job triggers → VM runs job             │
│  Job completes → Signal to host         │
│  Host restores checkpoint               │  ← Fresh state!
│  VM ready for next job                  │
└─────────────────────────────────────────┘
```

**Host script (runs on physical Windows machine):**
```powershell
$vmName = "LocaNext-Builder"
$checkpoint = "Clean-Build-State"

while ($true) {
    # Wait for job completion signal
    while (-not (Test-Path "\\VM\share\job_done.txt")) {
        Start-Sleep 5
    }

    # Reset VM to clean state
    Stop-VM -Name $vmName -Force
    Restore-VMCheckpoint -VMName $vmName -Name $checkpoint -Confirm:$false
    Start-VM -Name $vmName

    Remove-Item "\\VM\share\job_done.txt"
}
```

**Pros:**
- 100% clean state each build (like GitHub)
- No cleanup issues possible
- Elegant, standard approach

**Cons:**
- VM startup time (~30-60 sec)
- Requires Hyper-V (Windows Pro/Server)
- More initial setup

---

### Current Status

| Component | Status |
|-----------|--------|
| Build | ✅ Works perfectly (ZIP created) |
| Tests | ✅ All pass |
| Version | ✅ Correct (2512081600) |
| Ephemeral Runner | ✅ Working (restarts after job) |
| Job Status | ❌ Shows "failed" (false positive) |

**Reality:** Build output is 100% correct. Only the displayed status is wrong.

**Next Steps:**
1. Research Hyper-V setup requirements
2. Create VM with build tools pre-installed
3. Implement checkpoint reset workflow
4. Test full build cycle

---

## Recently Completed

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
