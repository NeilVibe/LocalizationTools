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

### 🥇 Solution: Hyper-V VM Reset (Copy GitHub's Approach)

**Confirmed:** This is exactly how GitHub does it.
- [Microsoft Blog](https://techcommunity.microsoft.com/t5/azure-compute-blog/how-github-actions-handles-ci-cd-scale-on-short-running-jobs/ba-p/3321114): "7 million VMs reimaged per day"
- GitHub doesn't fix the cleanup bug - they bypass it with infrastructure
- [Issue #2687](https://github.com/actions/runner/issues/2687): Same bug exists in GitHub's self-hosted runners (marked NOT_PLANNED)

**Our Local Version:**
```
Hyper-V Setup:
┌─────────────────────────────────────────┐
│  Windows VM (pre-configured)            │
│  - Git, Node, Python, build tools       │
│  - act_runner registered                │
│  - Checkpoint: "Clean-Build-State"      │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  Job runs → Build completes             │
│  Job ends (cleanup may fail)            │
│  Host detects completion                │
│  Restore-VMCheckpoint                   │  ← Fresh state!
└─────────────────────────────────────────┘
```

---

### Setup Complexity & Risks

**Complexity: MEDIUM** (1-2 hours initial setup)

| Step | Difficulty | Risk |
|------|------------|------|
| Enable Hyper-V | Easy | Low - Windows feature |
| Create Windows VM | Easy | Low - standard wizard |
| Install build tools in VM | Easy | Low - same as current setup |
| Take checkpoint | Easy | Low - one click |
| Write reset script | Medium | Low - PowerShell only |
| Integrate with Gitea workflow | Medium | Medium - timing coordination |

**Requirements:**
- Windows 10/11 Pro or Server (has Hyper-V)
- ~50GB disk for VM
- ~8GB RAM for VM (can share with host)
- Windows license for VM (can use evaluation)

**Risks:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| VM corrupts checkpoint | Low | Keep backup checkpoint |
| Network config issues | Medium | Use external virtual switch |
| Performance slower than bare metal | Low | ~10-20% overhead acceptable |
| Gitea can't reach VM | Medium | Configure proper networking |
| VM doesn't auto-start | Low | Configure Hyper-V auto-start |

**What Could Go Wrong:**
1. **Networking** - VM needs to reach Gitea server and internet
2. **Timing** - Reset script needs to detect job completion reliably
3. **Disk space** - Checkpoints grow over time (need cleanup)

**NOT Dangerous** - Hyper-V is production-grade Microsoft tech. Worst case: VM doesn't work, fall back to current setup.

---

### Alternative: Just Accept It

Given that GitHub also doesn't fix this for self-hosted runners:
- Build works ✅
- Output is correct ✅
- Status shows "failed" (cosmetic) ⚠️

**This is acceptable** for internal/local CI. The build artifact is what matters.

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

**Status:** 📋 PLANNING

**Goal:** Beautiful, fast, clean CAT tool for game localization. Spreadsheet-like UI inspired by [Gridly](https://www.gridly.com/) with the simplicity of Google Sheets.

---

#### Research: How Other CAT Tools Work

| Tool | License | UI Style | Strengths |
|------|---------|----------|-----------|
| [OmegaT](https://omegat.org/) | GPL (Open Source) | Desktop, Java | TMX standard, fuzzy matching, glossaries |
| [Gridly](https://www.gridly.com/) | Commercial | Spreadsheet/Grid | Game-focused, Unreal plugin, modern UI |
| [Smartcat](https://www.smartcat.com/) | Commercial | Segment editor | TM panel, QA checks, collaboration |

**Key insight:** Gridly's success comes from "UI similar to Google Sheets" - teams adapt quickly because it feels familiar.

---

#### What We Already Have (Reuse from QuickSearch)

```
server/tools/quicksearch/
├── parser.py      → TXT/TSV/XML parsing ✅
├── dictionary.py  → Dictionary management ✅
├── searcher.py    → Search functionality ✅
└── qa_tools.py    → QA checks (glossary, patterns) ✅
```

**Don't rebuild** - extend and reuse!

---

#### Core Features (MVP)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Grid Editor** | P0 | Source + Target columns, row-by-row editing |
| **Customizable Columns** | P0 | Add StringID, metadata, notes, status |
| **File Support** | P0 | TXT/TSV, XML (LocStr format), Excel |
| **Search/Filter** | P0 | Fast filtering, regex support |
| **Save/Export** | P0 | Save edits back to original format |

#### Advanced Features (Post-MVP)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Translation Memory** | P1 | Fuzzy matching from existing translations |
| **Glossary Panel** | P1 | Term suggestions while editing |
| **QA Checks** | P1 | Missing tags, inconsistencies (reuse qa_tools.py) |
| **Keyboard Shortcuts** | P1 | Ctrl+Enter confirm, Tab next segment |
| **Status Tracking** | P2 | Draft, Reviewed, Approved states |
| **TMX Import/Export** | P2 | Standard format interop |
| **Diff View** | P2 | Compare versions, show changes |

---

#### UI Design Concept

```
┌─────────────────────────────────────────────────────────────────┐
│  LD Manager                              [Easy Mode ▼] [Save]   │
├─────────────────────────────────────────────────────────────────┤
│  File: sample_localization.xml    │ Filter: [________] [🔍]    │
├─────────────────────────────────────────────────────────────────┤
│  # │ StringID      │ Source (EN)        │ Target (KO)    │ ✓  │
├────┼───────────────┼────────────────────┼────────────────┼────┤
│  1 │ menu_start    │ Start Game         │ 게임 시작       │ ✅ │
│  2 │ menu_options  │ Options            │ 설정           │ ✅ │
│  3 │ menu_exit     │ Exit               │ [editing...]   │ 📝 │
│  4 │ dialog_001    │ Hello, adventurer! │                │ ⬜ │
├─────────────────────────────────────────────────────────────────┤
│  [◀ Prev] [Confirm ✓] [Skip ▶]          Segments: 4/1000      │
└─────────────────────────────────────────────────────────────────┘

Advanced Mode adds:
- Column visibility toggles
- Metadata columns (context, char limit, tags)
- TM suggestions panel
- Glossary panel
- QA warnings panel
```

---

#### Easy Mode vs Advanced Mode

| Mode | Columns | Features |
|------|---------|----------|
| **Easy** | Source, Target, Status | Basic editing, search, save |
| **Advanced** | All customizable | TM, Glossary, QA, metadata, shortcuts |

New users start in Easy mode. Power users toggle to Advanced.

---

#### Technical Architecture

```
Frontend (Svelte):
├── LDManager.svelte          # Main container
├── components/
│   ├── DataGrid.svelte       # AG-Grid or custom virtualized grid
│   ├── CellEditor.svelte     # Inline text editing
│   ├── FilterBar.svelte      # Search/filter controls
│   ├── TMPanel.svelte        # Translation memory suggestions
│   └── StatusBar.svelte      # Progress, segment count

Backend (FastAPI):
├── server/tools/ld_manager/
│   ├── __init__.py
│   ├── editor.py             # Load, edit, save operations
│   ├── tm_matcher.py         # Fuzzy matching (reuse KR Similar?)
│   └── file_handlers/
│       ├── txt_handler.py    # Reuse QuickSearch parser
│       ├── xml_handler.py    # Reuse QuickSearch parser
│       └── xlsx_handler.py   # Reuse XLSTransfer
```

---

#### Performance Requirements

| Metric | Target | Notes |
|--------|--------|-------|
| Load 10K segments | < 2 sec | Virtualized grid, paginated |
| Search 10K segments | < 500ms | Index-based search |
| Save changes | < 1 sec | Incremental save |
| UI responsiveness | 60 FPS | No lag while scrolling |

---

#### Development Phases

**Phase 1: Grid Editor MVP** (Core)
- [ ] Load TXT/XML files into grid
- [ ] Display Source + Target columns
- [ ] Inline editing
- [ ] Save back to file
- [ ] Basic search/filter

**Phase 2: Customization**
- [ ] Easy/Advanced mode toggle
- [ ] Customizable columns
- [ ] Column visibility settings
- [ ] Status tracking

**Phase 3: CAT Features**
- [ ] Translation Memory panel
- [ ] Glossary suggestions
- [ ] QA checks integration
- [ ] Keyboard shortcuts

**Phase 4: Polish**
- [ ] TMX import/export
- [ ] Excel support
- [ ] Diff view
- [ ] Collaboration features (future)

---

#### Open Questions

1. **Grid library?** AG-Grid (powerful) vs custom (lighter)?
2. **Virtualization?** For 10K+ rows performance
3. **Auto-save?** Or manual save only?
4. **File locking?** Multiple users editing same file?

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
