# WIP - Work In Progress

**Updated:** 2025-12-28

---

## ACTIVE NOW

### Advanced Search - PLANNING
**Goal:** Add search modes (Contain, Exact, Not Contain, Fuzzy) + field selectors

| Step | Task | Status |
|------|------|--------|
| 1 | Create WIP doc | DONE |
| 2 | Add search mode dropdown to UI | PENDING |
| 3 | Add field selector to UI | PENDING |
| 4 | Extend backend API | PENDING |
| 5 | Implement fuzzy search (Model2Vec) | PENDING |

**WIP Doc:** [ADVANCED_SEARCH.md](ADVANCED_SEARCH.md)

---

### Color Tag Display - TESTING
**Goal:** Display `<PAColor0xffe9bd23>text<PAOldColor>` with actual colors

| Step | Task | Status |
|------|------|--------|
| 1 | Create colorParser.js | DONE |
| 2 | Create ColorText.svelte | DONE |
| 3 | Integrate into VirtualGrid | DONE |
| 4 | Test in browser | PENDING |

**Test Data:** `tests/fixtures/sample_language_data.txt` (20 rows with real color tags)

**WIP Doc:** [COLOR_TAG_DISPLAY.md](COLOR_TAG_DISPLAY.md)

---

## BACKLOG

| Priority | Feature | Status |
|----------|---------|--------|
| P6 | File Delete + Recycle Bin | BACKLOG |
| P7 | Font Settings UI | BACKLOG |

---

## Start Here

**[SESSION_CONTEXT.md](SESSION_CONTEXT.md)** - Current state + next steps

---

## System Status

| Status | Value |
|--------|-------|
| **Open Issues** | 0 |
| **Tests (Linux)** | 1,399 |
| **Build** | 409 |
| **Auto-Update** | VERIFIED WORKING |

---

## Active WIP Docs

| File | Purpose |
|------|---------|
| [SESSION_CONTEXT.md](SESSION_CONTEXT.md) | Session state |
| [ADVANCED_SEARCH.md](ADVANCED_SEARCH.md) | Search modes feature |
| [COLOR_TAG_DISPLAY.md](COLOR_TAG_DISPLAY.md) | Color tag display |
| [CONFUSION_HISTORY.md](CONFUSION_HISTORY.md) | Mistake tracker (SHORTENED) |

---

*Hub file - details in SESSION_CONTEXT.md*
