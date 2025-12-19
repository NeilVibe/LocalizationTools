# Issues To Fix

**Last Updated:** 2025-12-19 | **Build:** 301 (pending)

---

## Quick Summary

| Status | Count | Items |
|--------|-------|-------|
| **Critical Bugs** | **0** | - |
| **Medium Bugs** | **1** | BUG-030 |
| **UI/UX Issues** | **6** | UI-027, UI-031 to UI-035 |
| **Questions** | **1** | Q-001 |
| **Tested & Complete** | **13** | BUG-028, BUG-029, UI-025, UI-026, UI-028, UI-029, UI-030, + 6 more |

---

## Medium Priority Bugs

### BUG-030: WebSocket Shows Disconnected - MEDIUM

**Priority:** MEDIUM | **Component:** Server Status
**Problem:** Server status shows "DB connected" but "WebSocket: disconnected".
**Expected:** WebSocket should connect for real-time sync.
**Notes:** May be normal if WebSocket only connects on-demand. Needs investigation.

---

## UI/UX Issues - TM Viewer

### UI-027: Review "Confirm" Button - NEEDS DECISION

**Component:** TM Viewer
**Status:** KEEP - This is memoQ-style workflow for confirming TM entries.
**Notes:** After code review, this is useful for translation workflow (confirm/unconfirm entries).
**Decision Needed:** Keep as is, or make optional via settings?

---

## UI/UX Issues - Settings

### UI-031: Font Size Setting Not Working

**Component:** Display Settings
**Problem:** Changing font size does nothing.
**Solution:** Fix font size application or remove broken setting.

---

### UI-032: Bold Setting Not Working

**Component:** Display Settings
**Problem:** Toggling bold does nothing.
**Solution:** Fix bold application or remove broken setting.

---

### UI-033: App Settings Empty

**Component:** App Settings
**Problem:** Settings menu is nearly empty - just leads to Preferences which only has font settings.
**Solution:** Either add useful settings or remove empty menu items.

---

## UI/UX Issues - Global

### UI-034: Tooltips Cut Off at Window Edge

**Component:** Global (all tooltips/hover bubbles)
**Problem:** White tooltip bubbles get cut off when near window edge (especially right side).
**Example:** Settings button tooltip on far right is cut off.
**Solution:** Implement smart tooltip positioning (Svelte 5 has solutions for this). Auto-adjust placement so tooltip is always fully visible.

---

## Questions / Clarifications

### Q-001: TM Sync - Automatic or Manual?

**Question:** Should TM sync be automatic or require manual "Sync Indexes" button press?
**User Opinion:** Should be automatic for Model2Vec (fast, cheap).
**Current:** Appears to be manual.
**Decision Needed:** Implement auto-sync on TM changes? Or keep manual?

---

## Model2Vec Confirmation

**Model:** `minishlab/potion-multilingual-128M`
- **101 languages** including Korean ✅
- **29,269 sentences/sec**
- **256 dimensions**
- MIT license

This IS the most powerful multilingual Model2Vec model available. ✅

---

## Completed (Build 301)

| ID | Description | Date |
|----|-------------|------|
| UI-025 | TM Viewer: Removed "Items per page" selector | 2025-12-19 |
| UI-026 | TM Viewer: Removed pagination, added infinite scroll | 2025-12-19 |
| UI-028 | TM Viewer: Removed "Showing rows X-Y" (replaced with scroll hint) | 2025-12-19 |
| UI-029 | File Viewer: Removed download menu (use right-click instead) | 2025-12-19 |
| UI-030 | File Viewer: Info button not found (may already be removed) | 2025-12-19 |
| BUG-028 | Model2Vec missing from embedded Python pip install | 2025-12-19 |
| BUG-029 | Upload as TM - context menu file ref lost | 2025-12-19 |
| UI-024 | Dynamic engine name in build modal | 2025-12-19 |
| BUG-023 | MODEL_NAME NameError fix | 2025-12-18 |
| FEAT-005 | Model2Vec default engine | 2025-12-18 |
| PERF-001 | Incremental HNSW | 2025-12-18 |
| PERF-002 | FAISS factorization | 2025-12-18 |
| Lazy Import | CI timeout fix (kr_similar) | 2025-12-19 |
| Model2Vec | Upgrade to potion-128M | 2025-12-18 |

**Full history:** [ISSUES_HISTORY.md](../history/ISSUES_HISTORY.md)

---

## Priority Order for Next Session

1. **UI-034** - Tooltip positioning (affects entire app)
2. **BUG-030** - WebSocket investigation
3. **UI-031 to UI-033** - Settings cleanup (low priority)
4. **UI-027** - Confirm button decision (keep or remove?)
5. **Q-001** - Auto-sync decision

---

*Updated 2025-12-19 | 0 critical bugs, 1 medium bug, 6 UI/UX issues*
