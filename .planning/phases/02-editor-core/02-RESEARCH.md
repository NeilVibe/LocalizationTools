# Phase 2: Editor Core - Research

**Researched:** 2026-03-14
**Domain:** Svelte 5 translation grid, virtual scrolling, inline editing, XML export
**Confidence:** HIGH

## Summary

Phase 2 targets the translation grid -- the central UI surface of LocaNext. The VirtualGrid.svelte component (3,714 lines) already exists with substantial functionality: variable-height virtual scrolling, inline editing (MemoQ-style), search with four modes (contain/exact/not_contain/fuzzy), status filters (all/confirmed/unconfirmed/qa_flagged), Ctrl+S confirm, reference columns, color tag editing, and undo/redo. The backend APIs are mature: paginated rows with search/filter (`GET /files/{file_id}/rows`), row updates (`PUT /rows/{row_id}`), and file export/download (`GET /files/{file_id}/download`). Export rebuilds XML/TXT/XLSX from database rows using extra_data for attribute preservation.

This phase is primarily about **hardening, polishing, and verifying** existing functionality rather than building from scratch. The VirtualGrid already handles 10K+ segments via paginated virtual scrolling (PAGE_SIZE=100, BUFFER_ROWS=8, binary search positioning). Inline editing already works with contenteditable and PAColor tag rendering. The key gaps are: (1) the Ctrl+S "overflow to next row" bug (EDIT-04) needs investigation and fixing, (2) status indicators use a 2-state scheme (reviewed=teal, everything else=gray) but the requirement calls for 3-state (green=confirmed, yellow=draft, gray=empty), (3) the export needs verification that br-tags are preserved correctly through the full pipeline, and (4) the overall UI needs polishing to "executive-demo-ready" quality (UI-01).

**Primary recommendation:** Focus on bug fixes (EDIT-04 save overflow), status indicator rework (3-state color coding), export validation (br-tag round-trip), and UI polish. Most building blocks exist -- this is a refinement phase.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EDIT-01 | Virtual scrolling grid handles 10K+ segments without jank | Existing VirtualGrid has variable-height virtualization with binary search, page-based loading (100 rows/page), throttled scroll handling. Needs performance validation, not rebuild. |
| EDIT-02 | Segment status indicators with color coding (confirmed/draft/empty) | Current: 2-state (teal=reviewed, gray=everything else). Needs: 3-state (green=confirmed, yellow=draft, gray=empty). CSS changes + status mapping. |
| EDIT-03 | Search and filter segments by text and by status | Already implemented: 4 search modes (contain/exact/not_contain/fuzzy), status filters (all/confirmed/unconfirmed/qa_flagged). Needs polish and verification. |
| EDIT-04 | Ctrl+S saves without overflowing to next row (bug fix) | saveInlineEdit() and confirmInlineEdit() exist. Bug likely in contenteditable blur/focus race condition during save+move-to-next. |
| EDIT-05 | Editing and saving translations works reliably | Inline editing uses contenteditable with PAColor rendering, save via PUT /rows/{row_id}. Needs reliability testing. |
| EDIT-06 | Export workflow produces correct output in original format | Backend has _build_xml_file_from_dicts, _build_txt_file_from_dicts, _build_excel_file_from_dicts. Uses extra_data for attribute preservation. br-tag round-trip needs validation. |
| UI-01 | Main translation grid reworked to production-quality, executive-demo-ready | VirtualGrid is functional but needs visual polish: typography, spacing, hover states, transitions, color scheme consistency with Carbon. |
</phase_requirements>

## Standard Stack

### Core (Already in Use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte 5 | ^5.0.0 | UI framework | Project standard, Runes only |
| carbon-components-svelte | ^0.95.0 | UI component library | Project standard |
| carbon-icons-svelte | ^13.0.0 | Icons | Project standard |
| socket.io-client | ^4.6.0 | Real-time sync | Project standard for multi-user |

### Backend (Already in Use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (server) | REST API | Project standard |
| SQLite / PostgreSQL | (dual) | Database | Offline/online parity |

### Supporting (No New Dependencies)
This phase requires NO new npm packages. All needed functionality exists in the current stack.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom virtual scrolling | TanStack Virtual | STATE.md flagged "TanStack Virtual + Svelte 5 runes compatibility unverified". Current custom solution works. Don't migrate now -- too risky for a polish phase. |
| contenteditable editing | textarea | contenteditable supports PAColor inline rendering. Textarea would lose WYSIWYG colors. Keep contenteditable. |

## Architecture Patterns

### Existing Project Structure (No Changes)
```
locaNext/src/lib/
  components/
    ldm/
      VirtualGrid.svelte    # 3,714 lines - THE translation grid
      ExplorerGrid.svelte   # File browser grid (not touched in this phase)
      ColorText.svelte      # PAColor tag rendering
      TMQAPanel.svelte      # Side panel for TM/QA
      PresenceBar.svelte    # Multi-user presence
    pages/
      GridPage.svelte       # Container for VirtualGrid + TMQAPanel
  utils/
    colorParser.js          # PAColor <-> HTML conversion
    api.js                  # API base, auth headers
  stores/
    ldm.js                  # File join/leave, row locking
    preferences.js          # User preferences (columns, font)
    navigation.js           # Page routing, file open state
```

### Pattern 1: Virtual Scrolling Architecture (Existing)
**What:** Binary search for row position + page-based data loading + height cache
**When to use:** Already in place, don't rebuild
**Key constants:**
```javascript
const MIN_ROW_HEIGHT = 48;
const MAX_ROW_HEIGHT = 800;
const BUFFER_ROWS = 8;
const PAGE_SIZE = 100;
const PREFETCH_PAGES = 2;
```

### Pattern 2: Inline Editing Flow (Existing)
**What:** Double-click target cell -> contenteditable -> PAColor rendering -> save on Enter/blur
**Flow:**
1. `startInlineEdit(row)` -- acquire lock, set contenteditable content
2. `handleInlineEditKeydown(e)` -- handle Ctrl+S (confirm), Enter (save+next), Escape (cancel)
3. `saveInlineEdit(moveToNext)` -- convert HTML -> PAColor -> file format, PUT to API
4. `confirmInlineEdit()` -- same but sets status='reviewed', dispatches TM add

### Pattern 3: Status Model (Current vs Required)
**Current statuses in DB:** pending, translated, reviewed, approved, untranslated
**Current UI mapping:** 2-state (reviewed/approved = teal, everything else = gray)
**Required UI mapping per EDIT-02:** 3-state
- Green = confirmed (reviewed, approved)
- Yellow = draft (translated)
- Gray = empty (pending, untranslated, no target text)

### Pattern 4: Export Pipeline (Existing)
**What:** GET /files/{file_id}/download -> repo.get_rows_for_export() -> _build_{format}_file_from_dicts()
**Formats:** XML, TXT, XLSX
**XML reconstruction:** Uses extra_data dict for preserving all original attributes beyond stringid/strorigin/str

### Anti-Patterns to Avoid
- **Do NOT rewrite VirtualGrid from scratch.** 3,714 lines of battle-tested code. Refine it.
- **Do NOT switch to TanStack Virtual.** Compatibility with Svelte 5 runes is unverified (noted in STATE.md as blocker/concern). Custom solution works.
- **Do NOT add new npm dependencies.** Everything needed is already available.
- **Do NOT change the status strings in the database.** "pending", "translated", "reviewed", "approved" are used across the entire stack. Only change the UI presentation layer.
- **Do NOT use Svelte 4 patterns.** No `$:`, no `export let`. Runes only: `$state`, `$derived`, `$effect`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Virtual scrolling | Custom from scratch | Existing VirtualGrid implementation | Already handles 10K+ rows with variable heights, binary search, prefetch |
| XML export preservation | Custom XML serializer | Existing `_build_xml_file_from_dicts` + `extra_data` pattern | Already preserves attributes via extra_data dict |
| Color tag editing | Custom rich text editor | Existing `contenteditable` + `colorParser.js` | Already handles PAColor <-> HTML round-trip |
| Row locking | Custom lock system | Existing `ldm.js` lockRow/unlockRow via WebSocket | Already integrated with multi-user presence |

## Common Pitfalls

### Pitfall 1: Contenteditable Save Race Condition (EDIT-04)
**What goes wrong:** Ctrl+S triggers `confirmInlineEdit()` which saves and moves to next row. The blur event from losing focus ALSO triggers `saveInlineEdit()`. Double save can corrupt data or overflow text into wrong row.
**Why it happens:** `isCancellingEdit` flag exists but may not cover the confirm-then-move flow correctly.
**How to avoid:** Investigate the exact race condition. The `saveInlineEdit()` function checks `if (!inlineEditingRowId || isCancellingEdit) return;` but `confirmInlineEdit()` doesn't set `isCancellingEdit` before clearing `inlineEditingRowId`. After confirm, if blur fires, `inlineEditingRowId` is null so save returns early -- but timing matters.
**Warning signs:** Text from one row appears in the next row after Ctrl+S.

### Pitfall 2: br-tag Format Mismatch in Export
**What goes wrong:** XML files store newlines as `&lt;br/&gt;` (escaped). Excel uses `<br>` (unescaped). TXT uses `\n`. If the format detection is wrong during save or export, linebreaks corrupt.
**Why it happens:** `formatTextForSave()` detects format from `fileName.toLowerCase()`. If fileName is missing the extension, defaults to keeping `\n` (TXT mode).
**How to avoid:** Verify format detection in save path. Test round-trip: upload XML with br-tags -> edit -> save -> export -> verify br-tags intact.
**Warning signs:** Exported XML contains literal `\n` instead of `<br/>`.

### Pitfall 3: Status Mapping Confusion
**What goes wrong:** Requirements say "confirmed/draft/empty" but codebase uses "reviewed/translated/pending". The filter API uses "confirmed/unconfirmed" as aggregate terms.
**Why it happens:** Multiple naming conventions coexist. DB has one set, UI has another, requirements have a third.
**How to avoid:** Keep DB values unchanged. Map in the UI layer only:
- DB "reviewed"/"approved" -> UI "confirmed" (green)
- DB "translated" -> UI "draft" (yellow)
- DB "pending"/"untranslated"/no target -> UI "empty" (gray)

### Pitfall 4: VirtualGrid Performance Regression
**What goes wrong:** Adding new CSS classes, derived calculations, or DOM elements per row degrades scroll performance.
**Why it happens:** Each row render is in the hot path. Even small additions multiply by visible rows.
**How to avoid:** Keep status color changes in CSS only (class toggling, no JS per-row). Avoid adding new derived states that recalculate on scroll. Test with 10K+ rows after changes.

### Pitfall 5: Export Missing extra_data Attributes
**What goes wrong:** XML export drops attributes like DESC, Memo, or other game-specific fields.
**Why it happens:** `_build_xml_file_from_dicts()` iterates `extra_data` dict but the upload parser may not have captured all attributes.
**How to avoid:** Verify the upload -> store -> export round-trip preserves ALL original XML attributes, not just stringid/strorigin/str.

## Code Examples

### Status Color CSS (Proposed 3-State)
```css
/* Source: Derived from existing VirtualGrid.svelte:3451-3470 */

/* Empty: Gray (no target text or untranslated/pending status) */
/* Default styling, no special class needed */

/* Draft: Yellow/amber for translated rows */
.cell.target.status-translated {
  background: rgba(198, 163, 0, 0.12);
  border-left: 3px solid #c6a300;
}

/* Confirmed: Green for reviewed/approved rows */
.cell.target.status-reviewed,
.cell.target.status-approved {
  background: rgba(36, 161, 72, 0.15);
  border-left: 3px solid #24a148;
}
```

### Row Save API Call (Existing Pattern)
```javascript
// Source: VirtualGrid.svelte:1061-1092
const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
  method: 'PUT',
  headers: {
    ...getAuthHeaders(),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    target: textToSave,
    status: 'translated'  // or 'reviewed' for confirm
  })
});
```

### Export Download URL (Existing Pattern)
```javascript
// Source: Derived from server/tools/ldm/routes/files.py:767
// GET /api/ldm/files/{fileId}/download?status_filter=all
const downloadUrl = `${API_BASE}/api/ldm/files/${fileId}/download?status_filter=all`;
```

### formatTextForSave br-tag Handling (Existing)
```javascript
// Source: VirtualGrid.svelte:1851-1867
function formatTextForSave(text) {
  if (!text) return "";
  const isXML = fileName.toLowerCase().endsWith('.xml');
  const isExcel = fileName.toLowerCase().endsWith('.xlsx') || fileName.toLowerCase().endsWith('.xls');

  if (isXML) {
    return text.replace(/\n/g, '&lt;br/&gt;');  // XML escaped
  } else if (isExcel) {
    return text.replace(/\n/g, '<br>');           // Excel unescaped
  } else {
    return text;                                   // TXT keeps \n
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Modal editing dialog | Inline contenteditable (MemoQ-style) | Phase 2 (earlier iteration) | Much better UX, no popup |
| Fixed row height scrolling | Variable height with binary search | Phase upgrade | Correct row display for multiline content |
| Separate status column | Cell background color indicates status | UI-083 refactor | Cleaner grid, more content space |
| 2-state status (gray/teal) | Needs 3-state (gray/yellow/green) | This phase | Clearer status feedback for translators |

**Deprecated/outdated:**
- Modal editing (`EditModal`) -- removed, replaced by inline editing
- `Go to row` feature -- removed (BUG-001, not useful)
- Status column -- removed, replaced by cell background colors
- TM Results column -- removed per UI-039

## Open Questions

1. **EDIT-04 Root Cause: What exactly causes the "overflow to next row" bug?**
   - What we know: Ctrl+S calls `confirmInlineEdit()` which saves, sets `inlineEditingRowId = null`, and moves to next row via `saveInlineEdit(true)` at the end. Blur handler also fires `saveInlineEdit()`.
   - What's unclear: Whether the bug is in the save race condition, the `moveToNext` logic, the contenteditable DOM state, or the `Enter` (save+next) flow specifically.
   - Recommendation: Reproduce the bug first with Playwright. Add GDP-style microscopic logging around save/confirm/blur handlers to trace the exact sequence.

2. **Export UI: Where does the user trigger file export?**
   - What we know: Backend `GET /files/{file_id}/download` exists. Comment in VirtualGrid line 2225 says "Removed download menu - users download via right-click on file list."
   - What's unclear: Is the right-click export implemented in ExplorerGrid/FilesPage? Does it work end-to-end?
   - Recommendation: Verify the export flow end-to-end. If missing, add to the plan.

3. **UI-01 Scope: How much visual rework is "production-quality, executive-demo-ready"?**
   - What we know: The grid is functional. Carbon components provide a base design system.
   - What's unclear: The exact visual delta between current state and "demo-ready".
   - Recommendation: Take a screenshot of current grid state. Assess gaps against landing page quality. Focus on: consistent typography, proper spacing, smooth transitions, professional color palette.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (frontend E2E) + pytest (backend unit) |
| Config file | `locaNext/playwright.config.ts` (Playwright), `tests/conftest.py` (pytest) |
| Quick run command | `cd locaNext && npx playwright test tests/verify-grid-state.spec.ts --project=chromium` |
| Full suite command | `cd locaNext && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDIT-01 | 10K+ segments scroll without lag | E2E perf | `cd locaNext && npx playwright test tests/grid-performance.spec.ts -x` | Wave 0 |
| EDIT-02 | 3-state color-coded status indicators | E2E visual | `cd locaNext && npx playwright test tests/grid-status-colors.spec.ts -x` | Wave 0 |
| EDIT-03 | Search and filter segments | E2E | `cd locaNext && npx playwright test tests/search-verified.spec.ts -x` | Exists (partial) |
| EDIT-04 | Ctrl+S save without overflow bug | E2E regression | `cd locaNext && npx playwright test tests/grid-save-no-overflow.spec.ts -x` | Wave 0 |
| EDIT-05 | Editing and saving reliably | E2E | `cd locaNext && npx playwright test tests/confirm-row.spec.ts -x` | Exists (partial) |
| EDIT-06 | Export preserves XML structure and br-tags | API integration | `python3 -m pytest tests/integration/test_export_roundtrip.py -x` | Wave 0 |
| UI-01 | Grid is executive-demo-ready | E2E screenshot | `cd locaNext && npx playwright test tests/grid-visual-quality.spec.ts -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd locaNext && npx playwright test tests/confirm-row.spec.ts tests/search-verified.spec.ts -x`
- **Per wave merge:** Full Playwright suite on chromium
- **Phase gate:** All EDIT-* and UI-01 tests green

### Wave 0 Gaps
- [ ] `locaNext/tests/grid-performance.spec.ts` -- covers EDIT-01 (upload 10K file, measure scroll FPS)
- [ ] `locaNext/tests/grid-status-colors.spec.ts` -- covers EDIT-02 (verify 3-state color coding)
- [ ] `locaNext/tests/grid-save-no-overflow.spec.ts` -- covers EDIT-04 (Ctrl+S regression test)
- [ ] `tests/integration/test_export_roundtrip.py` -- covers EDIT-06 (XML upload -> edit -> export -> verify)
- [ ] `locaNext/tests/grid-visual-quality.spec.ts` -- covers UI-01 (screenshot comparison)

## Sources

### Primary (HIGH confidence)
- VirtualGrid.svelte (3,714 lines) -- read lines 1-200, 200-400, 400-700, 700-1000, 1000-1200, 1280-1480, 1830-1910, 3450-3500
- GridPage.svelte -- full read (408 lines)
- ExplorerGrid.svelte -- full read (721 lines)
- server/tools/ldm/routes/rows.py -- read lines 57-200 (GET rows, PUT row)
- server/tools/ldm/routes/files.py -- read lines 767-870 (download), 976-1072 (convert), 1224-1310 (XML/Excel builders)
- server/repositories/interfaces/row_repository.py -- full read (263 lines)
- server/repositories/sqlite/file_repo.py -- read lines 240-358 (row operations, export)
- package.json -- dependency list
- playwright.config.ts -- test configuration

### Secondary (MEDIUM confidence)
- STATE.md -- blocker note about TanStack Virtual compatibility
- REQUIREMENTS.md -- requirement definitions
- ROADMAP.md -- phase definition and success criteria

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed, existing stack is verified
- Architecture: HIGH -- VirtualGrid already exists with all core features
- Pitfalls: HIGH -- direct code inspection reveals race conditions and format handling
- Export pipeline: HIGH -- backend code read directly, format handlers inspected
- Status color mapping: MEDIUM -- requirement uses different terms than codebase, mapping proposed but untested
- EDIT-04 bug root cause: LOW -- exact reproduction not attempted, only code-level hypothesis

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable codebase, no external dependency changes expected)
