# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-18 01:00 KST
**Build:** 298 (v25.1217.2220) RELEASED
**Session:** Documentation & Roadmap Update

---

## Current State

**Build 298 stable. Documentation organized. Roadmap updated with future vision.**

| Item | Status |
|------|--------|
| Build | 298 released |
| Open Issues | 0 |
| Playground | Ready, ONLINE mode |
| CDP Toolkit | Organized |

---

## What Was Done This Session

### 1. CDP Testing Toolkit Organized
- Created `testing_toolkit/cdp/README.md` - hub with selectors, navigation map
- Organized test scripts into `tests/login/`, `tests/navigation/`, `tests/tm-viewer/`
- Documented WSL2 constraint: cannot access Windows localhost:9222
- Updated `docs/testing/CDP_TESTING_GUIDE.md` with constraint warning

### 2. Documentation Wiring
- Updated `CLAUDE.md` with CDP testing links
- Fixed Documentation section (restored P36, P25, future/, history/)
- Added "CDP/Playground testing?" to Quick Navigation

### 3. Roadmap Updated with Future Vision
- **LDM as Mother App** - progressively merge monolith features
- Already merged: TM Management, Pretranslation, QA, Glossary extraction
- Future: Legacy Menu for standalone tools (XLS Transfer, QuickSearch, KR Similar)
- Slimmed down "done" content

---

## CDP Testing Toolkit

**Location:** `testing_toolkit/cdp/` (hub: README.md)

| Script | Purpose |
|--------|---------|
| `tests/login/cdp_login.js` | Auto-login |
| `tests/navigation/quick_check.js` | Page state check |
| `tests/tm-viewer/check_tm_status.js` | List TMs with status |
| `tests/tm-viewer/test_tm_viewer_final.js` | TM Viewer & Confirm test |

**Critical:** WSL cannot access Windows localhost:9222. Run scripts on Windows via PowerShell:
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  node test_tm_viewer_final.js
"
```

---

## Build 298 Features (Reference)

| Feature | Status |
|---------|--------|
| TM Viewer (paginated, sort, search) | WORKS |
| TM Confirm (memoQ-style) | WORKS |
| TM Export (TEXT/Excel/TMX) | WORKS |
| Global Toasts | WORKS |
| Metadata Dropdown (7 options) | WORKS |
| Task Manager (22 ops) | WORKS |

---

## Future Vision (from Roadmap)

**Goal:** LDM becomes the "mother app" with all features merged from monolith.

```
Future:
├── LDM ─────────── Mother app (all features)
│   ├── TM Management (done)
│   ├── Pretranslation (done)
│   ├── QA Checks (done)
│   ├── Glossary Extraction (done)
│   ├── Batch Operations (future)
│   └── Reports & Analytics (future)
│
└── Legacy Menu ─── Standalone tools
    ├── XLS Transfer
    ├── Quick Search
    └── KR Similar
```

---

## Playground Details

```
Version:  v25.1217.2220
Path:     C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
Mode:     ONLINE (PostgreSQL)
CDP:      http://127.0.0.1:9222
```

---

## Next Steps

1. Run CDP tests to verify Build 298 features
2. Continue merging monolith features into LDM as needed

---

*This document is the source of truth for session handoff.*
