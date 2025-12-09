# LocaNext - Development Roadmap

**Version**: 2512091330 | **Updated**: 2025-12-09 | **Status**: Production Ready

> **Full History**: [docs/history/ROADMAP_ARCHIVE.md](docs/history/ROADMAP_ARCHIVE.md)

---

## Current Status

```
LocaNext v2512090827
├── Backend:     ✅ 55+ API endpoints, async, WebSocket
├── Frontend:    ✅ Electron + Svelte (LocaNext Desktop)
├── Tools:       ✅ XLSTransfer, QuickSearch, KR Similar
├── Tests:       ✅ 912 total (no mocks)
├── Security:    ✅ 86 tests (IP filter, CORS, JWT, audit)
├── CI/CD:       ✅ GitHub Actions + ✅ Gitea (FULLY WORKING!)
└── Distribution: ✅ Auto-update enabled
```

---

## Recently Completed

### P13.11: Gitea Windows Build - COMPLETE ✅ (2025-12-09)

**Status:** ✅ COMPLETE - Patched act_runner v15 solves NUL byte issue

**The Problem (SOLVED):**
Build succeeded but act_runner reported "Job failed" due to NUL bytes in PowerShell output.

**Root Cause Found:**
```go
// PowerShell writes NUL bytes (0x00) to stdout
// act_runner's parseEnvFile() treated NUL byte lines as errors
// Result: "Job failed" even though build was 100% successful
```

**The Solution: Patched act_runner v15**
```go
// File: act/pkg/container/parse_env_file.go
// V15-PATCH: Strip NUL bytes from line (Windows PowerShell bug)
line = strings.ReplaceAll(line, "\x00", "")
trimmed := strings.TrimSpace(line)
if trimmed == "" {
    continue
}
```

**Debugging Journey (v10-v15):**
| Version | Approach | Result |
|---------|----------|--------|
| v10 | Cleanup retry loop | ❌ Wrong location |
| v11 | RemoveAll with backoff | ❌ Still failed |
| v12 | Ignore cleanup errors | ❌ Not the issue |
| v13 | parseEnvFile NUL skip | ⚠️ Close! |
| v14 | More NUL handling | ⚠️ Closer! |
| **v15** | **strings.ReplaceAll NUL byte strip** | ✅ **WORKS!** |

**Current Setup:**
- **Linux Runner**: Manual scripts (`~/gitea/start.sh`)
- **Windows Runner**: NSSM Service (auto-start, ~8.5MB RAM)
  - Service: `GiteaActRunner`
  - Binary: `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner_patched_v15.exe`
  - Mode: Ephemeral (fresh state per job)

**Build Status:**
| Platform | Status | Duration |
|----------|--------|----------|
| GitHub | ✅ SUCCESS | ~10 min |
| Gitea | ✅ SUCCESS | ~1 min |

**Documentation:** [docs/deployment/GITEA_SETUP.md](docs/deployment/GITEA_SETUP.md) - Complete rewrite with full setup guide

---

### P13.12: Smart Build Cache v2.0 ✅ COMPLETE (2025-12-09)

**Status:** ✅ FULLY IMPLEMENTED + VERIFIED

**Smart Cache v2.0 Features:**
- ✅ **Hash-based invalidation** - `requirements.txt` hash auto-refreshes Python cache
- ✅ **Version tracking** - Python/VC++ version changes auto-invalidate
- ✅ **Manifest system** - JSON manifest stores hashes + versions
- ✅ **Future-ready** - `package-lock.json` hash computed (npm cache ready)

**Build Test Results:**
| Build | Cache Status | Result |
|-------|--------------|--------|
| #304 | `[STALE]` (first v2.0) | ✅ Re-downloaded, hash stored |
| #307 | `[VALID]` hash match | ✅ ALL CACHE HITS! |

**Verified Output:**
```
SMART BUILD CACHE SYSTEM v2.0
Hash-based invalidation enabled

[HASH] requirements.txt: 068EFE750AB8
[HASH] package-lock.json: 2210F74C6F85

Cache Validation:
  [VALID] VC++ Redistributable v17.8
  [VALID] Python 3.11.9 + packages (hash: 068EFE750AB8)
  [VALID] NSIS include files

[CACHE HIT] VC++ Redistributable: 24.4 MB (from cache)
[CACHE HIT] Python + packages: 233.8 MB (from cache)
[CACHE HIT] NSIS includes: 20 files (from cache)

Job succeeded
```

**Performance:**
| Scenario | Before | After |
|----------|--------|-------|
| Cold cache | ~3 min | ~3 min (populates cache) |
| Cache hit | ~3 min | **~1.5 min** (all from cache) |

**Cache Structure:**
```
C:\BuildCache\
├── CACHE_MANIFEST.json          # Version tracking + HASHES
├── vcredist\vc_redist.x64.exe   # Static (~25MB)
├── python-embedded\3.11.9\      # Python + packages (~234MB)
└── nsis-includes\*.nsh          # Static (20 files)
```

**Documentation:** [docs/wip/P13_GITEA_CACHE_PLAN.md](docs/wip/P13_GITEA_CACHE_PLAN.md)

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

**Status:** 🔄 IN PROGRESS (53% - 68/128 tasks)

**Goal:** Professional CAT tool with 5-tier cascade TM search (WebTranslatorNew architecture)

```
P17 Quick Summary:
┌─────────────────────────────────────────────────────────────────────────────┐
│  LocaNext LDM - LanguageData Manager                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Scale:        500K - 1M rows (virtual scroll, server pagination)           │
│  Collaboration: Real-time WebSocket sync between all users                  │
│  TM System:    5-Tier Cascade + Dual Threshold (WebTranslatorNew)           │
│  Editing:      Source = READ-ONLY, Target = EDITABLE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Progress:     Phase 1-5 [X] Phase 6 [▓] Phase 7-8 [ ]                      │
│                68/128 tasks (53%) - Core done, Full TM System next          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Completed Features:**
- ✅ VirtualGrid.svelte - 1M+ row virtual scrolling
- ✅ Basic TM Panel - One-click apply suggestions
- ✅ Keyboard Shortcuts - Ctrl+Enter, Tab, Escape
- ✅ Real-time WebSocket sync - Multi-user collaboration
- ✅ Row locking - Prevents edit conflicts

**Coming Next: Phase 7 - Full TM System (5-Tier Cascade)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 5-TIER CASCADE + DUAL THRESHOLD                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Tier 1: Perfect Whole Match    Hash O(1)         → 100% (stops cascade)    │
│  Tier 2: Whole Text Embedding   FAISS HNSW        → stops if ≥0.92          │
│  Tier 3: Perfect Line Match     Hash per line     → exact line matches      │
│  Tier 4: Line-by-Line Embedding FAISS per line    → semantic line matches   │
│  Tier 5: Word N-Gram Embedding  1,2,3-grams→FAISS → partial phrase matches  │
├─────────────────────────────────────────────────────────────────────────────┤
│  DUAL THRESHOLD:                                                             │
│  ├── cascade_threshold = 0.92  → PRIMARY (high confidence, auto-apply)      │
│  └── context_threshold = 0.49  → CONTEXT (single best reference)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**User Workflow:**
1. Upload TM file (TMX, Excel, TXT) → System builds indexes
2. Select active TM in LDM
3. Edit translation → TM suggestions appear with confidence levels
4. ✅ PRIMARY (92%+): Safe to apply | ⚠️ CONTEXT (49-92%): Reference only

**Phase 8: LocaNext Nice View (Pattern Rendering)**
- Color codes → rendered in actual colors
- Variables → highlighted pills
- Toggle: [Raw View] ←→ [Nice View]

**Documentation:**
- [LDM_TEXT_SEARCH.md](docs/tools/LDM_TEXT_SEARCH.md) - Full TM system docs
- [P17_LDM_TASKS.md](docs/wip/P17_LDM_TASKS.md) - Detailed task list
- [WebTranslatorNew/](RessourcesForCodingTheProject/WebTranslatorNew/) - Source architecture

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

### P18: Database Optimization

**Status:** ✅ PHASE 1 COMPLETE
**WIP Document:** [P_DB_OPTIMIZATION.md](docs/wip/P_DB_OPTIMIZATION.md)

```
DB OPTIMIZATION - PHASE 1 COMPLETE:
┌─────────────────────────────────────────────────────────────────────────────┐
│  PostgreSQL 14.20 INSTALLED AND RUNNING                                     │
│  Database: localizationtools | User: localization_admin                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  BENCHMARK RESULTS (sampleofLanguageData.txt - 103,500 entries):            │
│  ├── Import:        5.07 seconds (20,419 entries/sec)                       │
│  ├── 700k estimate: ~34 seconds                                             │
│  ├── Hash lookup:   2.14ms                                                  │
│  └── LIKE search:   3.26ms                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  IMPLEMENTED:                                                               │
│  ✅ bulk_insert_tm_entries() - 10x faster TM import with auto SHA256        │
│  ✅ bulk_insert_rows() - Fast LDM file upload                               │
│  ✅ search_rows_fts() - Full-text search with PostgreSQL tsvector           │
│  ✅ add_fts_indexes() - GIN indexes for FTS                                 │
│  ✅ add_trigram_index() - Similarity search (pg_trgm)                       │
│  ✅ chunked_query() - Memory-safe large dataset iteration                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Phase 1 - Quick Wins (COMPLETE):**
- [x] PostgreSQL 14 installed globally
- [x] Batch inserts for TM imports (100k entries → 5 seconds!)
- [x] Full-Text Search (FTS) with PostgreSQL tsvector
- [x] GIN index for trigram similarity search
- [x] db_utils.py created with all optimization functions

**Phase 2 - Performance Tuning (Only If Needed):**
- [ ] Async database operations (only if blocking issues occur)
- [ ] Query optimization (N+1 prevention)

**Note:** Redis/partitioning NOT needed - LocaNext is small team tool (10-50 users)

---

### P19: Platform UI/UX Overhaul

Modern UI redesign:
- Dashboard improvements
- Theme customization
- Keyboard shortcuts

### P20: Performance Monitoring

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
