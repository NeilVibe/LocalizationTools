# WIP - Work In Progress

**Updated:** 2025-12-28 | **Build:** 415 (STABLE)

---

## NEW - Priority Features

| Priority | Feature | WIP Doc | Status |
|----------|---------|---------|--------|
| **P1** | QA UIUX Overhaul | [QA_UIUX_OVERHAUL.md](QA_UIUX_OVERHAUL.md) | DONE |
| **P2** | View Mode Settings | [VIEW_MODE_SETTINGS.md](VIEW_MODE_SETTINGS.md) | PLANNING |
| **P2** | Font Settings Enhancement | [FONT_SETTINGS_ENHANCEMENT.md](FONT_SETTINGS_ENHANCEMENT.md) | PLANNING |
| **P2** | Gitea Clean Kill Protocol | [GITEA_CLEAN_KILL_PROTOCOL.md](GITEA_CLEAN_KILL_PROTOCOL.md) | IMPLEMENTED |
| **P2** | LanguageTool Lazy Load | [LANGUAGETOOL_LAZY_LOAD.md](LANGUAGETOOL_LAZY_LOAD.md) | IMPLEMENTED |
| **P3** | Offline/Online Mode | [OFFLINE_ONLINE_MODE.md](OFFLINE_ONLINE_MODE.md) | PLANNING |
| **P4** | Color Parser Extension | [COLOR_PARSER_EXTENSION.md](COLOR_PARSER_EXTENSION.md) | DOCUMENTED |
| **P5** | Advanced Search | [ADVANCED_SEARCH.md](ADVANCED_SEARCH.md) | PLANNING |

### P1: QA UIUX Overhaul ✅ DONE
Fixed QA panel stability:
- Added 30s timeout on API calls
- Added error UI with retry button
- Added cancel button during QA check
- Close button always works
- Fixed freeze bug (safe getter for checkType)

### P2: View Mode Settings (NEW)
MemoQ-style inline editing option:
- Modal Mode (current) - double-click opens modal
- Inline Mode - edit directly in grid
- TM/QA side panel on single-click
- Optional TM/QA column in grid

### P2: Font Settings Enhancement
Add missing font options:
- Font Family (System, Inter, Noto Sans, Source Han CJK, Consolas)
- Font Color (Default, Black, Dark Gray, Blue, Green)
- Settings dropdown menu UX

### P2: Gitea Clean Kill Protocol ✅ DONE
Management script: `./scripts/gitea_control.sh`
- `status` - Check CPU/RAM/Build status
- `restart` - Fix high CPU issues
- `monitor` - Live monitoring

### P2: LanguageTool Lazy Load ✅ DONE
Auto start/stop on demand:
- Saves ~900MB RAM when not in use
- Auto-starts when grammar check requested
- Auto-stops after 5 min idle

### P3: Offline/Online Mode (COMPLEX)
Work offline when server unavailable:
- Auto-sync on reconnect
- Conflict resolution (reviewed rows protected)
- Merge modes (full vs edit-only)

---

## ACTIVE - In Development

### Color Tag Display - WORKING
**Goal:** Display `<PAColor0xffe9bd23>text<PAOldColor>` with actual colors

| Step | Task | Status |
|------|------|--------|
| 1 | Create colorParser.js | DONE |
| 2 | Create ColorText.svelte | DONE |
| 3 | Integrate into VirtualGrid | DONE |
| 4 | Test in browser | DONE |

**WIP Doc:** [COLOR_TAG_DISPLAY.md](COLOR_TAG_DISPLAY.md)

---

## BACKLOG

| Priority | Feature | Status |
|----------|---------|--------|
| P6 | File Delete + Recycle Bin | BACKLOG |

---

## Start Here

**[SESSION_CONTEXT.md](SESSION_CONTEXT.md)** - Current state + next steps

---

## System Status

| Status | Value |
|--------|-------|
| **Open Issues** | 0 |
| **Tests (Linux)** | 1,399 |
| **Build** | 415 (STABLE) |
| **Auto-Update** | VERIFIED WORKING |

---

## Active WIP Docs

| File | Purpose |
|------|---------|
| [SESSION_CONTEXT.md](SESSION_CONTEXT.md) | Session state |
| [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Bug tracker (0 critical) |
| [VIEW_MODE_SETTINGS.md](VIEW_MODE_SETTINGS.md) | P2 - Modal vs Inline editing |
| [QA_UIUX_OVERHAUL.md](QA_UIUX_OVERHAUL.md) | P1 - QA panel fixes (DONE) |
| [FONT_SETTINGS_ENHANCEMENT.md](FONT_SETTINGS_ENHANCEMENT.md) | P2 - Font options |
| [GITEA_CLEAN_KILL_PROTOCOL.md](GITEA_CLEAN_KILL_PROTOCOL.md) | P2 - Gitea management (DONE) |
| [LANGUAGETOOL_LAZY_LOAD.md](LANGUAGETOOL_LAZY_LOAD.md) | P2 - Grammar lazy load (DONE) |
| [OFFLINE_ONLINE_MODE.md](OFFLINE_ONLINE_MODE.md) | P3 - Offline work |
| [COLOR_PARSER_EXTENSION.md](COLOR_PARSER_EXTENSION.md) | P4 - Color format guide |
| [ADVANCED_SEARCH.md](ADVANCED_SEARCH.md) | P5 - Search modes |
| [COLOR_TAG_DISPLAY.md](COLOR_TAG_DISPLAY.md) | Color tag display (DONE) |
| [CONFUSION_HISTORY.md](CONFUSION_HISTORY.md) | Mistake tracker |

---

*Hub file - details in SESSION_CONTEXT.md*
