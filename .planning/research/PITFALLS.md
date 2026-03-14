# Domain Pitfalls: Demo-Ready CAT Tool

**Domain:** Desktop CAT tool / game localization management platform
**Researched:** 2026-03-14

---

## Critical Pitfalls

Mistakes that cause demo failures or require rewrites.

### Pitfall 1: Grid Performance Death
**What goes wrong:** Loading a 10,000+ segment file causes visible lag, janky scrolling, or frozen UI. Executive opens a real production file and the tool stutters.
**Why it happens:** Rendering all DOM rows instead of using virtual scrolling. Svelte reactivity re-rendering entire lists on single-cell edits. No pagination or lazy loading.
**Consequences:** Instant credibility loss. "This can't handle our real files" is a demo-ending statement.
**Prevention:** Virtual scrolling from day one. Only render visible rows (~50-100). Keyed `{#each}` blocks. Debounce search inputs. Test with 20,000-row files during development.
**Detection:** Open the largest XML file from production data. If there is any perceptible delay when scrolling, it is not ready.

### Pitfall 2: Offline/Online Mode Mismatch
**What goes wrong:** Feature works in online mode but silently fails or behaves differently in offline mode. Demo switches to offline and something breaks.
**Why it happens:** Repository pattern is designed but not all implementations are validated. SQLite and PostgreSQL have different SQL dialects, constraint behaviors, and transaction semantics.
**Consequences:** Either the offline demo fails, or worse, data corruption when switching modes.
**Prevention:** Run identical test suites against both SQLite and PostgreSQL implementations. Every feature must be tested in both modes before marking complete.
**Detection:** Playwright tests that run the same workflow in online mode, then repeat in offline mode. Any difference is a bug.

### Pitfall 3: Upload-Export Lossy Round-Trip
**What goes wrong:** File uploaded, translated, exported — but the output file is structurally different from the input. Missing tags, wrong encoding, lost `<br/>` tags, reordered attributes.
**Why it happens:** XML parsing that normalizes or reorders content. String processing that strips or corrupts special characters. The `<br/>` preservation rule in CLAUDE.md exists because this was already a known issue.
**Consequences:** Exported files break the game build pipeline. Enterprise users will not trust a tool that corrupts their data.
**Prevention:** Round-trip tests: upload file, make zero edits, export, binary-diff against original. Any difference (except expected formatting) is a blocker. Preserve original file structure and only modify translated values.
**Detection:** Automated round-trip test in CI. Compare input and output files structurally.

### Pitfall 4: TM Match Display Without Diff Highlighting
**What goes wrong:** TM panel shows "94% match" but does not highlight WHAT is different between the source and the stored TM entry. User cannot see why it is not 100%.
**Why it happens:** Calculating match percentage without implementing diff visualization. The percentage alone is not useful without context.
**Consequences:** Feature feels incomplete compared to memoQ/Trados which both highlight differences in fuzzy matches. Executives who have used other CAT tools will notice.
**Prevention:** Implement word-level diff highlighting alongside match percentage from the start. Use a diff algorithm (e.g., diff-match-patch library) to show insertions/deletions between the current segment and the TM match.
**Detection:** Show a 85% fuzzy match to a translator. If they cannot immediately see what changed, the feature is incomplete.

---

## Moderate Pitfalls

### Pitfall 5: Demo Flow Fragility
**What goes wrong:** Demo works when following the exact planned sequence but breaks when the executive clicks something unexpected (navigating away mid-edit, clicking export before saving, etc.).
**Prevention:** Test the top 10 "wrong order" scenarios. Ensure every page handles being entered from any state. Guard against double-clicks, rapid navigation, and incomplete data states.

### Pitfall 6: Search That Returns Too Much or Too Little
**What goes wrong:** Semantic search returns 500 results for a simple query (no ranking/cutoff), or exact search misses entries due to whitespace/case differences.
**Prevention:** Default search result limit (20 max). Semantic search threshold (minimum similarity score). Case-insensitive exact search. Trim whitespace before matching.

### Pitfall 7: TM Assignment Confusion in UI
**What goes wrong:** User cannot figure out how to make a TM "active" for their current file. The assignment hierarchy (platform > project > folder) is not visually clear.
**Prevention:** Show active TMs for the current file prominently. "Why is my TM not matching?" should never be a question — show a status indicator explaining which TMs are active and why.

### Pitfall 8: Keyboard Shortcut Conflicts with Electron
**What goes wrong:** Ctrl+S saves the file but also triggers Electron's default behavior. Ctrl+F opens both the in-app search and Electron/Chrome's find bar.
**Prevention:** Register all keyboard shortcuts through Electron's accelerator system. Prevent default browser shortcuts in the renderer process. Test every shortcut on Windows.

---

## Minor Pitfalls

### Pitfall 9: Column Width Amnesia
**What goes wrong:** User resizes columns, navigates away, comes back — columns reset to defaults.
**Prevention:** Persist column widths in localStorage or user preferences.

### Pitfall 10: Locale-Specific Display Issues
**What goes wrong:** Korean, Japanese, or Chinese text renders with wrong line height, font, or wrapping in the grid.
**Prevention:** Test grid with CJK text specifically. Use a font stack that includes CJK glyphs. Set appropriate line-height for mixed-script content.

### Pitfall 11: Empty State UX
**What goes wrong:** New user opens the app: blank screen, no guidance. "Now what?"
**Prevention:** Welcome/onboarding state for empty projects. "Upload your first file" prompt. Sample data or demo project pre-loaded.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Grid polish (Phase 1) | Virtual scrolling breaks cell editing | Test edit-while-scrolling, focus management |
| File upload/export (Phase 2) | XML round-trip corruption | Automated diff tests for every supported format |
| TM matching (Phase 2) | Match percentages feel wrong to experienced translators | Validate against memoQ's matching behavior with same test data |
| Semantic search UI (Phase 3) | Results feel random without similarity score context | Always show percentage, sort by relevance, explain threshold |
| Offline mode demo (Phase 3) | Mode switch during active editing loses unsaved changes | Auto-save before mode detection, or prevent switch during editing |
| MapDataGenerator (Phase 5) | Image loading slows down the grid | Lazy-load images, thumbnail cache, do not block grid rendering |

---

## Sources

- memoQ documentation on [translation memory context matching](https://docs.memoq.com/current/en/Concepts/concepts-translation-memories.html)
- Trados [QA checker settings](https://docs.rws.com/en-US/trados-studio-2022-980998/specifying-settings-for-qa-checker-359765)
- LocaNext ARCHITECTURE_SUMMARY.md — existing offline/online parity design
- LocaNext CLAUDE.md — `<br/>` preservation rule, Svelte 5 runes requirements
- [Game localization common issues](https://www.gridly.com/blog/game-localization-guide/) — character limits, variable handling
