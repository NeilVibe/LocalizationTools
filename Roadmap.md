# LocaNext - Development Roadmap

**Version**: 2512091000 | **Updated**: 2025-12-09 | **Status**: Production Ready

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
├── CI/CD:       ✅ GitHub Actions + ⚠️ Gitea (P13.11 status bug + P13.12 caching)
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

**Chosen Solution: Patch act_runner**

After 10 failed attempts with workflow-level fixes, the only real solution is patching act_runner's Go code:

```go
// Patch: pkg/container/host_environment.go
func (e *HostEnvironment) Close() error {
    for i := 0; i < 5; i++ {
        if err := os.RemoveAll(e.Path); err == nil {
            return nil
        }
        time.Sleep(time.Duration(i+1) * time.Second)
    }
    return nil  // Ignore cleanup failure - job already succeeded
}
```

**Next Steps:**
1. Fork act_runner repo
2. Apply cleanup retry patch
3. Build custom act_runner.exe
4. Deploy to Windows build machine

**Detailed tracking:** [docs/wip/P13_GITEA_TASKS.md](docs/wip/P13_GITEA_TASKS.md)

---

### P13.12: Build Caching 🔄 NEW

**Status:** 🔄 IN PROGRESS - Implementing smart cache

**Problem:** Every build downloads ~350MB (slow, wasteful)

```
Current downloads per build:
├── VC++ Redistributable     ~25MB   (never changes)
├── Python Embedded         ~145MB   (rarely changes)
├── npm packages            ~100MB   (changes with package-lock.json)
└── NSIS includes            ~1MB    (never changes)
```

**Solution:** Local cache with hash-based invalidation

```
C:\BuildCache\
├── CACHE_MANIFEST.json          # Version tracking + hashes
├── vcredist\vc_redist.x64.exe   # Static
├── python-embedded\3.11.9\      # Python + pip packages
├── npm-cache\<hash>\            # Keyed by package-lock.json hash
└── nsis-includes\*.nsh          # Static
```

**Expected Performance:**
| Scenario | Before | After |
|----------|--------|-------|
| Cold cache | ~5 min | ~5 min |
| Cache hit | ~5 min | **~30 sec** |
| requirements.txt change | ~5 min | ~2 min |

**Next Steps:**
1. Create `setup_build_cache.ps1` script
2. Modify `build.yml` with cache-first logic
3. Test and validate

**Detailed tracking:** [docs/wip/P13_GITEA_TASKS.md](docs/wip/P13_GITEA_TASKS.md)

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

### P17: LocaNext LDM (LanguageData Manager)

**Status:** 🔄 IN PROGRESS (Phase 1-5 Complete - 96%)

**Goal:** Custom-built, powerful, elegant CAT tool for game localization. Google Docs-like real-time collaboration with file explorer, handling 500K-1M rows effortlessly.

**Approach:** 100% custom. No open-source CAT tools. We build everything ourselves.

```
P17 Quick Summary:
┌─────────────────────────────────────────────────────────────────────────────┐
│  LocaNext LDM - LanguageData Manager                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Scale:        500K - 1M rows (virtual scroll, server pagination)           │
│  Collaboration: Real-time WebSocket sync between all users                  │
│  UI:           File Explorer + VirtualGrid + Edit Modal                     │
│  Editing:      Source (StrOrigin) = READ-ONLY, Target (Str) = EDITABLE      │
│  Server:       ONE server (FastAPI:8888 + PostgreSQL + Gitea:3000)          │
│  Phases:       6 phases (Foundation → File Explorer → Sync → Scale → CAT)   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Frontend:     locaNext/src/lib/components/ldm/ (FileExplorer, VirtualGrid) │
│  Backend:      server/tools/ldm/ (api.py, websocket.py, tm.py)              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Progress:     Phase 1 [X] Phase 2 [X] Phase 3 [X] Phase 4 [X] Phase 5 [X]  │
│                68/71 tasks (96%) - UI done, Remaining: Glossary, Status     │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Recent Completions (Phase 4-6):**
- ✅ VirtualGrid.svelte - 1M+ row virtual scrolling
- ✅ TM Backend (tm.py) - Word-level Jaccard similarity
- ✅ TM Suggestions Panel - One-click apply in edit modal
- ✅ Keyboard Shortcuts - Ctrl+Enter (save+next), Tab (apply TM), Escape (cancel)
- ✅ Demo Screenshots - 11 images captured (docs/demos/ldm/)
- ✅ Upload Performance Test - 16MB/103,500 rows in ~50 seconds (~2,070 rows/sec)
- ✅ **UI Enhancements (Phase 6.0):** Smooth hover transitions, row highlight, selected row state
- ✅ **Demo Folder Reorganization:** Subfolders for navigation, project-mgmt, grid, editing, ui-interactions

**Future Enhancement: WebTranslatorNew Reference**
Explored `RessourcesForCodingTheProject/WebTranslatorNew/` for reusable logic:
- 5-tier cascade search (perfect match → embeddings → n-grams)
- Qwen embedding model + FAISS HNSW for semantic search
- Dual-threshold system (cascade=0.92, context=0.49)
- Data preprocessing with majority voting deduplication

See: `RessourcesForCodingTheProject/WebTranslatorNew/README.md`

**Detailed task tracking:** See [docs/wip/P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md)

> **Jump to sections:** [UX Flow](#ux-flow-how-users-work) | [File Formats](#file-format-parsing-rules) | [Architecture](#deployment-architecture-one-server-for-everything) | [Development Phases](#development-phases)

---

#### What is LocaNext LDM?

```
LocaNext Platform
├── XLSTransfer        ← Existing tool (Excel operations)
├── QuickSearch        ← Existing tool (Dictionary search)
├── KR Similar         ← Existing tool (Fuzzy matching)
└── LDM                ← NEW: LanguageData Manager
    ├── File Explorer  (projects, folders, upload)
    ├── Grid Editor    (1M rows, virtual scroll)
    ├── Real-time Sync (WebSocket collaboration)
    └── CAT Features   (TM, Glossary, QA)
```

---

#### Work Breakdown: Two Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WORK BREAKDOWN                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COMPONENT 1: LocaNext Desktop App (Frontend)                                │
│  ═══════════════════════════════════════════                                 │
│  Location: locaNext/src/                                                     │
│                                                                              │
│  New files to create:                                                        │
│  ├── routes/ldm/+page.svelte           # LDM main page                       │
│  ├── lib/components/ldm/               # LDM components                      │
│  │   ├── FileExplorer.svelte           # Project/folder tree                 │
│  │   ├── VirtualGrid.svelte            # 1M row grid (virtual scroll)        │
│  │   ├── CellEditor.svelte             # Inline editing                      │
│  │   ├── PresenceBar.svelte            # Who's online                        │
│  │   └── FilterBar.svelte              # Search/filter                       │
│  └── lib/stores/ldm.js                 # LDM state management                │
│                                                                              │
│  Work: Add new tab "LDM" to LocaNext sidebar                                 │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COMPONENT 2: Server Backend (FastAPI)                                       │
│  ═════════════════════════════════════                                       │
│  Location: server/tools/ldm/                                                 │
│                                                                              │
│  New files to create:                                                        │
│  ├── __init__.py                                                             │
│  ├── api.py                            # REST endpoints                      │
│  │   ├── GET  /api/ldm/projects        # List projects                       │
│  │   ├── POST /api/ldm/projects        # Create project                      │
│  │   ├── GET  /api/ldm/files/{id}/rows # Paginated rows                      │
│  │   ├── POST /api/ldm/files/upload    # Upload file                         │
│  │   └── PUT  /api/ldm/rows/{id}       # Update row                          │
│  ├── websocket.py                      # Real-time sync                      │
│  │   ├── /ws/ldm/{file_id}             # Join file room                      │
│  │   ├── cell_update                   # Broadcast edits                     │
│  │   └── presence                      # Who's online                        │
│  ├── models.py                         # Database models                     │
│  │   ├── LDMProject                                                          │
│  │   ├── LDMFolder                                                           │
│  │   ├── LDMFile                                                             │
│  │   └── LDMRow                                                              │
│  └── file_handlers/                    # Reuse from QuickSearch/XLSTransfer  │
│      ├── txt_handler.py                                                      │
│      ├── xml_handler.py                                                      │
│      └── xlsx_handler.py                                                     │
│                                                                              │
│  Work: Add LDM router to server/main.py                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### Critical Requirements

| Requirement | Scale | Notes |
|-------------|-------|-------|
| **Row count** | 500K - 1M rows | Typical language data files |
| **Real-time sync** | Multi-user | Changes visible to all instantly |
| **File explorer** | Projects/Folders | Organize files like VS Code |
| **Auto-update** | < 100ms | Cell edits sync immediately |

---

#### Reference: How Others Handle Scale (For Learning Only)

| Tool | Max Rows | Technique |
|------|----------|-----------|
| Google Sheets | ~5M cells | Virtual scroll + server pagination |
| Gridly | 100K+ | WebSocket + cell locking |
| Excel Online | ~1M rows | Chunked loading |

**We use same techniques, custom implementation.**

---

#### What We Already Have (Reuse!)

```
Existing Infrastructure:
├── WebSocket server       → Real-time sync foundation ✅
├── QuickSearch parser.py  → TXT/TSV/XML parsing ✅
├── XLSTransfer           → Excel handling ✅
├── KR Similar            → Fuzzy matching ✅
├── QA Tools              → Glossary/pattern checks ✅
└── User authentication   → Multi-user ready ✅
```

**Don't rebuild** - extend and reuse!

---

#### UX Flow: How Users Work

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. OPEN APP                                                                 │
│     └── User opens LocaNext → Clicks "LDM" tab                               │
│                                                                              │
│  2. FILE EXPLORER (Left Panel)                                               │
│     ├── See project/folder tree                                              │
│     ├── Create new folder: Right-click → "New Folder"                        │
│     ├── Upload file: Drag & drop OR click "Upload"                           │
│     └── File auto-parsed → stored in database (fast, efficient)              │
│                                                                              │
│  3. GRID VIEW (Right Panel)                                                  │
│     ├── Click file → Grid loads with beautiful columns                       │
│     ├── See: StringID | Source (KR) | Target (Translation) | Status          │
│     ├── Source column = READ ONLY (Korean original, grey background)         │
│     └── Target column = EDITABLE (translation, white background)             │
│                                                                              │
│  4. EDIT FLOW (Modal)                                                        │
│     ├── Single-click cell → Select row (highlight)                           │
│     ├── Double-click Target cell → MODAL opens                               │
│     │   ┌─────────────────────────────────────────┐                          │
│     │   │  Edit Translation                    [X]│                          │
│     │   ├─────────────────────────────────────────┤                          │
│     │   │  StringID: menu_start                   │                          │
│     │   │                                         │                          │
│     │   │  Source (KR):        [READ ONLY]        │                          │
│     │   │  ┌─────────────────────────────────┐    │                          │
│     │   │  │ 게임 시작                        │    │                          │
│     │   │  └─────────────────────────────────┘    │                          │
│     │   │                                         │                          │
│     │   │  Target (EN):        [EDITABLE]         │                          │
│     │   │  ┌─────────────────────────────────┐    │                          │
│     │   │  │ Start Game                      │    │                          │
│     │   │  └─────────────────────────────────┘    │                          │
│     │   │                                         │                          │
│     │   │  [Cancel]              [Save Changes]   │                          │
│     │   └─────────────────────────────────────────┘                          │
│     └── Click "Save" → Server saves → WebSocket broadcasts to ALL users      │
│                                                                              │
│  5. REAL-TIME SYNC                                                           │
│     ├── Neil saves → Server pushes update                                    │
│     ├── Sarah's grid auto-refreshes (no page reload!)                        │
│     └── Everyone sees latest data instantly                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### Core Rule: Source = Read-Only

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SOURCE vs TARGET RULE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SOURCE TEXT = READ ONLY (Original Korean - never editable)                  │
│  TARGET TEXT = EDITABLE (Translation - what translators modify)              │
│                                                                              │
│  Grid Display:                                                               │
│  ┌──────────┬─────────────────────┬─────────────────────┬────────┐          │
│  │ StringID │ Source (KR) 🔒      │ Target (EN) ✏️       │ Status │          │
│  ├──────────┼─────────────────────┼─────────────────────┼────────┤          │
│  │ menu_01  │ 게임 시작            │ Start Game          │ ✅     │          │
│  │ menu_02  │ 설정                 │ Options             │ ✅     │          │
│  │ menu_03  │ 종료                 │                     │ ⬜     │          │
│  └──────────┴─────────────────────┴─────────────────────┴────────┘          │
│               ↑ Grey, no click     ↑ White, double-click to edit            │
│               (Korean original)    (Translation to edit)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### File Format Parsing Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FILE FORMAT PARSING                                      │
│                     (Based on existing LocaNext codebase)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TXT/TSV (Tab-Separated):                                                    │
│  ════════════════════════                                                    │
│  Column layout (0-indexed):                                                  │
│  [0]       [1]    [2]    [3]    [4]    [5]        [6]                        │
│  StringID  ???    ???    ???    ???    Source     Target                     │
│                                        (KR)       (Translation)              │
│                                                                              │
│  Rule: Index 5 = Source/KR (read-only), Index 6 = Target/Translation (edit)  │
│                                                                              │
│  Example line:                                                               │
│  menu_01 \t ? \t ? \t ? \t ? \t 게임 시작 \t Start Game                       │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  XML (LocStr Format - Our Standard):                                         │
│  ════════════════════════════════════                                        │
│                                                                              │
│  <LocStr StringId="menu_01" StrOrigin="게임 시작" Str="Start Game" />         │
│                              ↑                    ↑                          │
│                              │                    └── Str = Translation      │
│                              │                        (EDITABLE)             │
│                              │                                               │
│                              └── StrOrigin = Korean Original                 │
│                                  (READ-ONLY)                                 │
│                                                                              │
│  Attributes:                                                                 │
│  - StringId   = Unique identifier (e.g., "menu_01")                          │
│  - StrOrigin  = Source text, Korean original (READ-ONLY)                     │
│  - Str        = Target text, Translation (EDITABLE)                          │
│                                                                              │
│  Reference: See QuickSearch parser, xmlregex1.py, krchange.py                │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Database Storage (Normalized):                                              │
│  ══════════════════════════════                                              │
│  ldm_rows table:                                                             │
│  ┌────┬─────────┬──────────────┬──────────────┬────────────┬───────────┐    │
│  │ id │ file_id │ string_id    │ source (KR)  │ target     │ status    │    │
│  ├────┼─────────┼──────────────┼──────────────┼────────────┼───────────┤    │
│  │ 1  │ 42      │ menu_01      │ 게임 시작     │ Start Game │ translated│    │
│  │ 2  │ 42      │ menu_02      │ 설정         │ Options    │ translated│    │
│  │ 3  │ 42      │ menu_03      │ 종료         │ NULL       │ pending   │    │
│  └────┴─────────┴──────────────┴──────────────┴────────────┴───────────┘    │
│                                                                              │
│  Mapping:                                                                    │
│  - XML StrOrigin → DB source column (READ-ONLY)                              │
│  - XML Str       → DB target column (EDITABLE)                               │
│  - TXT index 5   → DB source column (READ-ONLY)                              │
│  - TXT index 6   → DB target column (EDITABLE)                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### UI Design Concept

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LocaNext LDM                                  [User: Neil] [🟢 Connected]   │
├──────────────────────┬──────────────────────────────────────────────────────┤
│  📁 EXPLORER         │  📄 GameStrings_KR_EN.xml                            │
│  ─────────────────   │  ────────────────────────────────────────────────────│
│  ▼ 📂 Project Alpha  │  Filter: [____________] [🔍]  Showing: 1-50 of 847K  │
│    ├── 📂 UI         │  ────────────────────────────────────────────────────│
│    │   ├── 📄 menu   │  # │ StringID    │ Source (KR) 🔒 │ Target (EN) ✏️│ ✓│
│    │   └── 📄 hud    │  ──┼─────────────┼─────────────────┼─────────────┼──│
│    ├── 📂 Dialog     │  1 │ menu_start  │ 게임 시작        │ Start Game  │✅│
│    │   └── 📄 npc    │  2 │ menu_opt    │ 설정            │ Options     │✅│
│    └── 📄 items.xml  │  3 │ menu_exit   │ 종료            │ [🔒Sarah]   │⏳│
│  ▶ 📂 Project Beta   │  4 │ dlg_001     │ 안녕하세요!      │             │⬜│
│                      │  5 │ dlg_002     │ 다시 오셨군요    │ Welcome back│✅│
│  [+ New Project]     │  ──┴─────────────┴─────────────────┴─────────────┴──│
│  [📤 Upload File]    │  ◀◀ ◀ Page 1 of 16,940 ▶ ▶▶   │ Go to row: [___]  │
├──────────────────────┴──────────────────────────────────────────────────────┤
│  👥 Online: Neil (viewing), Sarah (editing row 3), Mike (viewing)           │
└─────────────────────────────────────────────────────────────────────────────┘

Legend:
🔒 Source (KR) = Read-only, Korean original (grey background)
✏️ Target = Editable translation (double-click to open modal)
[🔒Sarah] = Row locked by Sarah (she has modal open)
✅ = Translated
⬜ = Not translated
⏳ = Being edited
```

---

#### Core Features (Phase 1-2)

| Feature | Priority | Description |
|---------|----------|-------------|
| **File Explorer** | P0 | Project/folder tree, upload, organize |
| **Virtual Grid** | P0 | Render only visible rows (50 at a time) |
| **Server Pagination** | P0 | Backend serves rows on-demand |
| **Real-time Sync** | P0 | WebSocket broadcasts cell changes |
| **Presence Indicators** | P0 | See who's editing what |
| **Search/Filter** | P0 | Server-side search (indexes) |
| **Auto-save** | P0 | Changes saved immediately |

#### Advanced Features (Phase 3-4)

| Feature | Priority | Description |
|---------|----------|-------------|
| **Translation Memory** | P1 | Fuzzy matching (reuse KR Similar) |
| **Glossary Panel** | P1 | Term suggestions (reuse QA Tools) |
| **QA Checks** | P1 | Missing tags, inconsistencies |
| **Keyboard Shortcuts** | P1 | Ctrl+Enter confirm, Tab next |
| **Status Workflow** | P2 | Draft → Review → Approved |
| **Version History** | P2 | Track all changes, rollback |
| **TMX/XLIFF Export** | P2 | Standard format interop |
| **Permissions** | P2 | Project roles (owner, editor, viewer) |

---

#### Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Svelte)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  FileExplorer.svelte     │  VirtualGrid.svelte      │  PresenceBar.svelte   │
│  - Project tree          │  - Virtual scrolling     │  - Online users       │
│  - Drag & drop upload    │  - Only renders ~50 rows │  - Who's editing      │
│  - Context menu          │  - Infinite scroll       │  - Cursor positions   │
│                          │  - Cell locking          │                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                           WebSocket Connection                               │
│  - cell_update: {file_id, row, col, value, user}                            │
│  - cursor_move: {file_id, row, user}                                        │
│  - presence: {file_id, users_online}                                        │
│  - file_lock: {file_id, row, user, locked}                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              BACKEND (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  server/tools/ld_manager/                                                    │
│  ├── __init__.py                                                             │
│  ├── api.py              # REST endpoints (CRUD, pagination, search)         │
│  ├── websocket.py        # Real-time sync handler                            │
│  ├── storage.py          # File storage (upload, projects, folders)          │
│  ├── sync_engine.py      # Conflict resolution (last-write-wins or OT)       │
│  └── file_handlers/                                                          │
│      ├── txt_handler.py  # Reuse QuickSearch parser                          │
│      ├── xml_handler.py  # Reuse QuickSearch parser                          │
│      └── xlsx_handler.py # Reuse XLSTransfer                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                              DATABASE (PostgreSQL)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Tables:                                                                     │
│  - projects (id, name, owner_id, created_at)                                 │
│  - folders (id, project_id, parent_id, name)                                 │
│  - files (id, folder_id, name, format, row_count, created_at)                │
│  - rows (id, file_id, row_num, string_id, source, target, status, updated_by)│
│  - edit_history (id, row_id, old_value, new_value, user_id, timestamp)       │
│  - active_sessions (file_id, user_id, cursor_row, last_seen)                 │
│                                                                              │
│  Indexes:                                                                    │
│  - rows: (file_id, row_num) for pagination                                   │
│  - rows: (file_id, source) for search (GIN/trigram)                          │
│  - rows: (file_id, string_id) for lookup                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### Performance Requirements

| Metric | Target | Strategy |
|--------|--------|----------|
| Load 1M row file | < 5 sec | Stream to DB, index async |
| Display grid | < 200ms | Virtual scroll (50 rows) |
| Search 1M rows | < 500ms | PostgreSQL trigram index |
| Cell edit sync | < 100ms | WebSocket broadcast |
| Scroll to row N | < 100ms | Direct DB offset query |
| Concurrent users | 50+ | WebSocket rooms per file |

---

#### Data Flow: Cell Edit

```
User A edits cell
       │
       ▼
┌──────────────┐     WebSocket      ┌──────────────┐
│  Frontend A  │ ──────────────────▶│   Backend    │
└──────────────┘  {row:3, col:target │              │
                   value:"새 번역"}   │  1. Validate │
                                     │  2. Save DB  │
                                     │  3. Broadcast│
                                     └──────┬───────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ▼                       ▼                       ▼
            ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
            │  Frontend A  │       │  Frontend B  │       │  Frontend C  │
            │  (confirm)   │       │  (update)    │       │  (update)    │
            └──────────────┘       └──────────────┘       └──────────────┘
```

---

#### Conflict Resolution Strategy

**Option 1: Last-Write-Wins (Simple)**
- Whoever saves last, wins
- Show "overwritten" notification
- Good enough for most cases

**Option 2: Cell Locking (Recommended for P17)**
- When user clicks cell → lock it
- Others see "🔒 Editing: Neil"
- 30 sec timeout auto-unlock
- No conflicts possible

**Option 3: OT/CRDT (Future)**
- Operational Transform (Google Docs style)
- Complex but allows true simultaneous editing
- Consider for P18 if needed

---

#### Development Phases

**Phase 1: Foundation (Database + Basic API)** ✅ COMPLETE
```
Backend (server/tools/ldm/):
- [x] Create models in server/database/models.py (6 LDM models)
- [x] Tables auto-created via Base.metadata.create_all()
- [x] Create api.py with CRUD endpoints
- [x] File upload endpoint (parse TXT/XML → store rows in DB)
- [x] Paginated rows endpoint (GET /files/{id}/rows?page=1&limit=50)

Frontend (locaNext/src/):
- [x] Add "LDM" to apps menu in header
- [x] Create LDM.svelte component
```

**Phase 2: File Explorer + Basic Grid** ✅ COMPLETE
```
Backend:
- [x] Projects/folders CRUD API
- [x] File tree endpoint (nested structure)
- [x] txt_handler.py (parse TXT, col 5=source, col 6=target)
- [x] xml_handler.py (parse XML LocStr, StrOrigin=source, Str=target)

Frontend:
- [x] FileExplorer.svelte (project/folder tree, upload modal)
- [x] DataGrid.svelte (display rows, pagination, edit modal)
- [x] Connect to API, show real data
```

**Phase 3: Editing + Real-time Sync**
```
Backend:
- [ ] WebSocket handler (server/tools/ldm/websocket.py)
- [ ] Room management (join/leave file)
- [ ] Broadcast cell updates to all clients
- [ ] Row locking (when modal open → lock row for that user)

Frontend:
- [ ] EditModal.svelte (modal for editing target text)
  - Source field = read-only (display only)
  - Target field = editable textarea
  - Save button → API call → WebSocket broadcast
- [ ] Double-click target cell → open modal
- [ ] WebSocket connection to backend
- [ ] Receive updates, refresh grid row
- [ ] PresenceBar.svelte (who's online)
- [ ] Show "🔒 Sarah" on locked rows (modal open by another user)
```

**Phase 4: Virtual Scrolling (1M Rows)**
```
Backend:
- [ ] Optimized pagination (OFFSET/LIMIT with indexes)
- [ ] PostgreSQL trigram index for search

Frontend:
- [ ] VirtualGrid.svelte (render only visible ~50 rows)
- [ ] Infinite scroll / pagination controls
- [ ] "Go to row N" navigation
- [ ] Server-side search with instant results
```

**Phase 5: CAT Features**
```
Backend:
- [ ] Translation Memory API (reuse KR Similar fuzzy matching)
- [ ] Glossary suggestions API (reuse QA Tools)
- [ ] Status workflow (Draft → Review → Approved)

Frontend:
- [ ] TM Panel (show suggestions while editing)
- [ ] Glossary Panel (term lookup)
- [ ] Status column with workflow
- [ ] Keyboard shortcuts (Ctrl+Enter, Tab)
```

**Phase 6: Polish & Scale**
```
- [ ] Version history / rollback
- [ ] TMX/XLIFF export
- [ ] Project permissions (owner, editor, viewer)
- [ ] Performance tuning for 50+ concurrent users
- [ ] Offline mode (read-only cache)
```

---

#### Grid Library Decision

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **AG-Grid** | Feature-rich, proven at scale | Heavy (300KB+), complex API, license | ❌ Overkill |
| **TanStack Table** | Headless, lightweight, flexible | Need custom virtualization | ⚠️ Maybe |
| **Svelte-Virtual-List** | Simple, Svelte-native | Basic, need to build grid | ⚠️ Maybe |
| **Custom** | Full control, minimal bundle | More dev time | ✅ Recommended |

**Recommendation:** Custom virtual grid with Svelte
- We only need: rows, columns, edit, scroll
- 1M rows = just a number (virtual scroll renders 50)
- Full control over WebSocket integration
- Smaller bundle, faster load

---

#### Deployment Architecture: ONE Server For Everything

**Key Point:** You only need ONE server machine. Everything runs together.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     YOUR ONE COMPANY SERVER                                 │
│                     (2 CPU, 2GB RAM, 50GB disk)                             │
│                     Any cheap VM or old office PC                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROCESS 1: FastAPI (main.py)                              Port 8888        │
│  ════════════════════════════════════════════════════════════════════       │
│  │                                                                          │
│  ├── /api/xlstransfer/*      ← XLSTransfer tool                             │
│  ├── /api/quicksearch/*      ← QuickSearch tool                             │
│  ├── /api/kr-similar/*       ← KR Similar tool                              │
│  ├── /api/ld-manager/*       ← LD Manager (NEW - same server!)              │
│  ├── /api/admin/*            ← Admin Dashboard API                          │
│  ├── /ws/ld-manager          ← WebSocket for real-time collaboration        │
│  └── /ws/tasks               ← WebSocket for task updates                   │
│                                                                             │
│  RAM: ~200MB                                                                │
│                                                                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROCESS 2: PostgreSQL                                     Port 5432        │
│  ════════════════════════════════════════════════════════════════════       │
│  │                                                                          │
│  ├── users, sessions         ← Auth for everyone                            │
│  ├── telemetry               ← Usage stats                                  │
│  ├── ld_projects             ← LD Manager projects                          │
│  ├── ld_folders              ← LD Manager folder tree                       │
│  ├── ld_files                ← LD Manager files                             │
│  └── ld_rows                 ← LD Manager data (handles 1M rows easily)     │
│                                                                             │
│  RAM: ~300MB                                                                │
│                                                                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROCESS 3: Gitea (patch server)                           Port 3000        │
│  ════════════════════════════════════════════════════════════════════       │
│  │                                                                          │
│  └── Hosts LocaNext releases for auto-update                                │
│      (Already set up! ~/gitea/)                                             │
│                                                                             │
│  RAM: ~100MB                                                                │
│                                                                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TOTAL RESOURCES: ~600MB RAM, 1-2 CPU cores                                 │
│  This handles: 50+ concurrent users, 1M+ rows, all tools                    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

**Visual: How Users Connect**

```
                    ┌─────────────────────────────────┐
                    │      YOUR ONE SERVER            │
                    │      server.company:8888        │
                    │                                 │
 Users              │  ┌───────────────────────────┐  │
 ─────              │  │     FastAPI :8888         │  │
                    │  │  (ALL tools + LD + Admin) │  │
 Neil's LocaNext ───┼──┤                           │  │
 Sarah's LocaNext ──┼──┤         ↕                 │  │
 Mike's LocaNext ───┼──┤                           │  │
 Admin Dashboard ───┼──┤    PostgreSQL :5432       │  │
                    │  │                           │  │
                    │  └───────────────────────────┘  │
                    │                                 │
                    │  ┌───────────────────────────┐  │
 Auto-Update ───────┼──┤     Gitea :3000           │  │
                    │  │   (patch downloads)       │  │
                    │  └───────────────────────────┘  │
                    │                                 │
                    └─────────────────────────────────┘
```

---

#### Server Setup (IT Admin - One Time)

```bash
# On your company server (Linux)

# 1. Start PostgreSQL (usually already running as service)
sudo systemctl start postgresql

# 2. Start FastAPI backend (all tools including LD Manager)
python3 server/main.py --host 0.0.0.0 --port 8888

# 3. Start Gitea (for auto-updates)
cd ~/gitea && ./start.sh

# That's it! Three commands.
```

---

#### LocaNext App Configuration

```javascript
// Users configure once in Settings
const config = {
  // Company server URL (IT provides this)
  serverUrl: "http://server.company.local:8888",

  // All tools use same server:
  // - XLSTransfer, QuickSearch, KR Similar
  // - LD Manager (real-time collaboration)
  // - Admin Dashboard
};
```

**User Flow:**
1. User opens LocaNext app
2. First time: Enter server URL (IT provides: `server.company.local:8888`)
3. Login with company credentials
4. All tools work, LD Manager syncs in real-time with everyone

---

#### Connection States

| State | Icon | Behavior |
|-------|------|----------|
| Connected | 🟢 | Real-time sync, see who's editing |
| Reconnecting | 🟡 | Auto-retry, edits queued |
| Offline | 🔴 | Read-only mode (no conflict risk) |

---

#### What To Tell Your Company

```
"Server requirements for LocaNext platform:

 Hardware: ONE small server
 - 2 CPU cores
 - 2 GB RAM
 - 50 GB disk

 Software: 3 lightweight processes
 - FastAPI (Python web server)
 - PostgreSQL (database)
 - Gitea (auto-update server)

 Handles:
 - All localization tools
 - Real-time collaboration (50+ users)
 - 1 million rows of language data
 - Auto-updates for desktop app

 Cost estimate:
 - Cloud VM: ~$20/month
 - Old office PC: Free
 - Raspberry Pi 4: ~$100 one-time"
```

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
