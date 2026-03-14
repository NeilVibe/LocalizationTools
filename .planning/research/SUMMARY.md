# Project Research Summary

**Project:** LocaNext Demo-Ready CAT Tool
**Domain:** Desktop CAT tool / game localization management platform
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH

## Executive Summary

LocaNext is a desktop CAT (Computer-Assisted Translation) tool built for game localization, running as an Electron app with a Svelte 5 frontend and FastAPI Python backend. The research confirms that the existing stack is competitive — Svelte 5, FastAPI, PostgreSQL/SQLite, FAISS, and Qwen require no rewrites or replacements. The path to demo-ready is not about adding new technology; it is about polishing the existing foundation into a coherent, professional experience that executives recognize as a real CAT tool. The two core assets that are already built and genuinely differentiate LocaNext from memoQ/Trados — local semantic search (FAISS + Qwen) and transparent offline/online parity — need to be surfaced prominently in the demo flow rather than buried.

The recommended approach is to build in three demo-focused phases: first, establish the performance foundation (virtual scrolling grid + polished file/TM explorer); second, complete the core translation workflow (TM matching with diff highlighting, upload/export round-trip, QA checks, concordance); third, demonstrate the differentiators (semantic search, local AI pretranslation, offline mode resilience, TM leverage statistics). This order follows feature dependencies: the grid must perform before any translation features can be demoed confidently, and the basic TM workflow must work before differentiators make sense to an executive audience.

The highest-risk item across all research is grid performance. A 10,000+ segment file that stutters or lags ends any executive demo before it starts. Virtual scrolling is not optional — it is the single most critical technical decision in Phase 1. The second major risk is upload-export round-trip fidelity: exported XML must be structurally identical to input, preserving `<br/>` tags (already a documented issue in CLAUDE.md), attribute order, and encoding. These two items should be treated as Phase 1 and Phase 2 blockers respectively, not nice-to-haves.

## Key Findings

### Recommended Stack

The existing stack requires no core changes. Electron + Svelte 5 + FastAPI + Carbon Components is the right combination for a professional desktop CAT tool. The only new dependencies needed are narrow and phase-specific: a virtual scrolling library for the grid (TanStack Virtual is the leading candidate; Svelte 5 runes compatibility needs verification at implementation time) and `diff-match-patch` for word-level TM diff highlighting in Phase 2. No new database, no new ML model, no framework switches.

**Core technologies:**
- **Electron:** Desktop shell — cross-platform, already configured, no change needed
- **Svelte 5 (Runes):** Frontend — fast reactivity, already in use, mandatory runes-only patterns ($state, $derived, $effect)
- **FastAPI:** Python backend — async API, already serving all endpoints
- **Carbon Components (IBM):** UI library — already integrated, professional enterprise look
- **PostgreSQL / SQLite:** Database pair — online/offline parity via repository abstraction layer
- **FAISS + Qwen (2.3GB):** Semantic search + local AI pretranslation — the key differentiators, already built
- **diff-match-patch (new, Phase 2):** Word-level diff highlighting for TM matches — lightweight, stable Google library
- **TanStack Virtual (new, Phase 1):** Virtual scrolling for the translation grid — verify Svelte 5 runes compat before committing

### Expected Features

Based on competitive analysis against memoQ, Trados, Smartcat, and Phrase, plus game-localization-specific requirements.

**Must have (table stakes — demo fails without these):**
- Polished, fast grid with virtual scrolling — the demo foundation; lag = instant credibility loss
- Side-by-side source/target editor — the layout executives recognize as a "real CAT tool"
- TM lookup with match percentages and diff highlighting — core value prop; 100%/fuzzy/new
- File explorer + TM tree — already exist, need visual polish
- File upload + export (end-to-end round-trip) — "upload > translate > export" is the demo narrative
- Segment status indicators — color-coded confirmed/draft/empty per row
- Keyboard navigation — Tab/Enter/Ctrl+Enter; makes the demo feel professional and "real"
- Basic QA checks — visible pass/fail before export; Trados and memoQ both have this

**Should have (differentiators — make the demo impressive):**
- Semantic search (FAISS) — already built; the "wow moment" vs Trados/memoQ; find similar translations even with different wording
- Local AI pretranslation (Qwen) — already built; "zero cloud costs, zero data leakage" is a stronger pitch than yet-another-MT-API
- Concordance search — leverages existing semantic search
- TM leverage statistics — "This file is 60% pre-translated" — executives love ROI numbers
- Glossary/terminology panel — auto-detected terms shown as user navigates segments
- Offline mode demo — pull the network cable, keep working; validates the offline/online architecture

**Defer (Phase 3+):**
- MapDataGenerator integration — visually impressive but significant integration work; Phase 4
- Character limits + variable highlighting — game-specific polish; Phase 4
- Real-time multi-user collaboration — infrastructure exists, full implementation is Phase 5
- Audit log — enterprise compliance feature; Phase 5
- Dark mode — low effort, any phase

**Anti-features (explicitly out of scope):**
- Cloud MT APIs (Google Translate, DeepL) — breaks offline story, distracts from Qwen differentiator
- WYSIWYG in-context game preview — rendering nightmare; use image references (MapDataGenerator) instead
- 100+ file format support — XML primary, Excel for import/export, maybe XLIFF; three formats done well
- Plugin/extension marketplace — premature; build after core is stable and proven

### Architecture Approach

The backend architecture (Repository pattern, DB Factory, 3-mode online/offline/recovery detection) is sound and does not need redesign. The demo-ready work is almost entirely UI architecture. The key pattern is **selected-segment-driven panels**: `selectedSegmentId` is the single source of truth, and all side panels (TM matches, glossary, QA results) react to it via Svelte 5 `$derived` and `$effect`. This is the interaction model that every professional CAT tool uses and that experienced translators will instinctively understand. Crucially, components must call the same API endpoints regardless of online/offline mode — the backend routes to the correct repository. UI code should not contain `if (offlineMode)` branches.

**Major components:**
1. **TranslationGrid** — core editor with virtual scrolling; source/target columns, cell editing, keyed `{#each}` by segment ID; optimistic UI on every edit
2. **TMPanel** — TM matches for selected segment with word-level diff highlighting, glossary terms, concordance results; auto-triggers on segment navigation
3. **FileExplorer + TMExplorerTree** — navigation trees, already exist, need polish; show active TMs for current file prominently
4. **SearchBar** — find/replace and concordance search with 300ms debounce; prevents API hammering on every keystroke
5. **QAPanel** — QA check runner with pass/fail indicators and navigation back to errors in the grid
6. **StatusBar + LeverageStats** — progress indicators, current TM info, and match percentage breakdown for executive ROI narrative

### Critical Pitfalls

1. **Grid performance death** — Rendering all DOM rows instead of virtual scrolling will destroy any demo on a real production file (10K+ segments). Virtual scrolling is mandatory from the first commit. Test with 20,000-row files during development. If there is any perceptible scroll lag, it is not ready.
2. **Upload-export lossy round-trip** — XML exported after translation must be structurally identical to input. The `<br/>` preservation issue is already documented in CLAUDE.md because it burned time before. Automated round-trip diff tests in CI are required before this feature is marked done.
3. **TM match display without diff highlighting** — Showing "94% match" without highlighting what changed is incomplete compared to memoQ/Trados. Any experienced CAT tool user will notice. `diff-match-patch` must ship alongside the match percentage display, not as a follow-up.
4. **Offline/online mode mismatch** — Repository pattern is designed but not all paths are validated. SQLite and PostgreSQL have different SQL dialects, constraint behaviors, and transaction semantics. Every feature must be tested in both modes before being marked complete.
5. **Keyboard shortcut conflicts with Electron** — Ctrl+S, Ctrl+F and other shortcuts need to be registered through Electron's accelerator system to prevent Electron/Chrome defaults from firing alongside in-app behavior.

## Implications for Roadmap

Based on combined research, suggested phase structure:

### Phase 1: Performance Foundation

**Rationale:** The grid is the product. Every other feature is built on top of it, and a lagging grid ends the demo before it starts. The feature dependency graph from FEATURES.md is explicit: T14 (polished grid) is the root dependency for everything else. This must be solved first.
**Delivers:** Fast translation grid with virtual scrolling; polished File Explorer and TM Explorer tree navigation; segment status indicators; keyboard navigation foundation; overall layout that looks like a professional CAT tool.
**Addresses:** T14 (polished grid), T1 (side-by-side editor), T4 (file explorer polish), T5 (TM tree polish), T9 (segment status indicators), T11 (keyboard navigation)
**Avoids:** Pitfall 1 (grid performance death), Pitfall 5 (demo flow fragility from unpolished navigation)
**New library:** TanStack Virtual — verify Svelte 5 runes compatibility before committing; fallback to svelte-virtual-list or custom if incompatible

### Phase 2: Core Translation Workflow

**Rationale:** With a performant grid established, build the features that define what a CAT tool does: file in, translation work, file out. This is the "upload > translate > export" demo narrative backbone. TM matching with diff highlighting is the centerpiece — must feel complete and polished, not preliminary.
**Delivers:** File upload with XML parsing (br-tag safe), file export with round-trip fidelity, TM lookup with match percentages and word-level diff highlighting, search/filter across segments, QA checks panel, undo/redo in editor.
**Addresses:** T6 (file upload), T7 (export), T2 (TM lookup + match %), T3 (concordance search), T8 (search/filter), T12 (QA checks), T10 (undo/redo)
**Avoids:** Pitfall 3 (upload-export lossy round-trip), Pitfall 4 (TM match without diff highlighting), Pitfall 8 (keyboard shortcut conflicts with Electron)
**New library:** diff-match-patch for TM diff visualization
**CI requirement:** Automated XML round-trip diff tests must be in place before upload/export is marked done

### Phase 3: Differentiators and Demo Polish

**Rationale:** Phases 1-2 make LocaNext a credible CAT tool. This phase makes it impressive — surfacing the capabilities that already exist (FAISS semantic search, Qwen local AI, offline resilience) and adding the executive-facing analytics (TM leverage stats) that anchor the ROI narrative. These are largely UI/UX tasks on top of working infrastructure.
**Delivers:** Semantic search UI with similarity scores and relevance ranking; local AI pretranslation (Qwen) triggered from the editor; TM leverage statistics (match breakdown by tier); offline mode demo validation; glossary/terminology side panel; batch operations; empty state UX and onboarding.
**Addresses:** D1 (semantic search), D3 (local AI pretranslation), D2 (offline mode), D7 (TM leverage stats), D8 (glossary panel), D9 (batch operations)
**Avoids:** Pitfall 2 (offline/online mode mismatch — validate every feature in both modes here), Pitfall 6 (search result flooding), Pitfall 7 (TM assignment confusion), Pitfall 11 (empty state UX)

### Phase 4: Game-Specific Features

**Rationale:** After the core demo is solid, add the game localization specifics that show "we understand games" — character limits, variable placeholder protection, and MapDataGenerator image context. These are impressive additions but require the polished grid from Phase 1 as a stable base.
**Delivers:** Character limit display per cell with over-limit warnings; variable and tag placeholder highlighting and protection against accidental deletion; MapDataGenerator integration for image/audio context alongside translation segments.
**Addresses:** D4 (MapDataGenerator), D5 (character limits + variables)
**Avoids:** Pitfall 10 (CJK display issues — test with Korean/Japanese/Chinese text specifically), MapDataGenerator image loading pitfall (lazy-load thumbnails, never block grid rendering)

### Phase 5: Enterprise and Collaboration

**Rationale:** Long-term enterprise features that require the stable, proven core to exist first. Real-time collaboration infrastructure already exists in the WebSocket layer; full implementation requires conflict resolution design which is complex and should not be rushed.
**Delivers:** Real-time multi-user collaboration with live presence indicators; audit log (who changed what, when); dark mode; advanced workflow features.
**Addresses:** D6 (real-time collab), D10 (dark mode), D11 (audit log)

### Phase Ordering Rationale

- Grid performance (Phase 1) is a hard prerequisite: every subsequent feature is demoed through the grid; there is no point building TM matching on top of a slow foundation.
- Upload/export (Phase 2) before differentiators (Phase 3) because the demo narrative requires a complete workflow before individual wow moments make sense to an executive audience.
- Differentiators in Phase 3 leverage already-built infrastructure (FAISS, Qwen) — these are primarily UI tasks, making them faster to implement than net-new features.
- Game-specific features (Phase 4) defer MapDataGenerator integration because it carries an image-loading performance risk that must not be introduced before the grid is proven stable at scale.
- Anti-features (MT APIs, plugin marketplace, WYSIWYG preview, 100+ format support) are excluded from all phases — they consume effort without advancing the demo-ready or enterprise-sales narrative.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** TanStack Virtual + Svelte 5 runes compatibility is unverified. Research the exact integration pattern before writing grid code. If incompatible, evaluate svelte-virtual-list or custom implementation.
- **Phase 2:** XML round-trip fidelity CI approach needs a concrete plan — define what "structurally identical" means (attribute order, whitespace, encoding, tag preservation) and how to assert it automatically before implementation begins.
- **Phase 3:** FAISS semantic search result ranking and similarity threshold tuning needs experimentation with real production data — what score cutoff means "not useful to show"?

Phases with standard patterns (skip research-phase):
- **Phase 4:** Character limits and variable placeholder patterns are straightforward UI features with no library research needed.
- **Phase 5:** Real-time collaboration with WebSockets is well-documented; infrastructure already exists in the codebase. Implementation is engineering, not research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack confirmed correct and competitive. Only 2 new libraries needed, both well-established. TanStack Virtual Svelte 5 compat is the one open question. |
| Features | MEDIUM-HIGH | Grounded in competitive analysis against memoQ, Trados, Smartcat, Phrase official docs. Feature prioritization reflects documented CAT tool sales patterns and executive demo expectations. |
| Architecture | HIGH | Repository pattern and DB abstraction are already designed correctly and documented in ARCHITECTURE_SUMMARY.md. UI patterns (virtual scrolling, selected-segment-driven panels, optimistic UI) are well-established in both the codebase and competitive tools. |
| Pitfalls | HIGH | Critical pitfalls 1-4 are grounded in actual codebase issues (br-tag problem already documented), universal domain knowledge (virtual scrolling), and CAT tool competitive analysis from official docs. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **TanStack Virtual + Svelte 5 runes compatibility:** Not verified. Must check at Phase 1 planning time. This is the highest-priority unknown.
- **Fuzzy match percentage algorithm:** How LocaNext calculates fuzzy match percentages is not documented. Validate that it matches translator expectations (memoQ-compatible behavior) before Phase 2 is marked complete.
- **FAISS index freshness:** When new TM entries are added, does the FAISS index update in real time or require a rebuild? This affects the TM workflow in Phase 2 and Phase 3 and needs validation.
- **SQLite dialect gaps:** Specific queries where PostgreSQL and SQLite behavior diverges in the existing codebase are not inventoried. Needs audit during Phase 2 offline validation work.
- **TMX import/export standard:** Users migrating from memoQ/Trados may expect TMX format support for TM portability. Not researched — may be a Phase 2 or Phase 3 scope addition.

## Sources

### Primary (HIGH confidence)
- LocaNext ARCHITECTURE_SUMMARY.md — existing stack, repository pattern, 3-mode detection
- LocaNext CLAUDE.md — Svelte 5 runes requirements, br-tag preservation rule, optimistic UI mandate
- LocaNext PROJECT.md — technology constraints, scope boundaries
- [memoQ Translation Memory docs](https://docs.memoq.com/current/en/Concepts/concepts-translation-memories.html) — TM management, context matching, assignment patterns, segment-driven panel pattern

### Secondary (MEDIUM confidence)
- [Trados features page](https://www.trados.com/product/features/) — QA checks, editor capabilities, file format support
- [Smartcat Editor overview](https://help.smartcat.com/1539449-editor-functionalities-overview/) — CAT panel layout, concordance, glossary integration
- [Smartcat word match levels](https://help.smartcat.com/cat-tool-word-matches/) — fuzzy match percentage tiers and leverage reporting
- [Smartcat glossary management](https://help.smartcat.com/1539721-working-with-glossary-terms/) — terminology detection, glossary-in-editor workflow
- [CAT Tools Comparison guide](https://better-i18n.com/en/blog/cat-tools-comparison-guide/) — memoQ vs Trados vs Phrase comparison
- [Gridly game localization guide](https://www.gridly.com/blog/game-localization-guide/) — character limits, variable placeholders, game-specific context
- [Phrase game localization](https://phrase.com/solutions/game-localization/) — game-specific CAT features

### Tertiary (LOW confidence)
- [XTM enterprise guide](https://xtm.ai/en-us/blog/cat-tools-guide) — enterprise CAT tool expectations (single source)
- [Trados QA checks](https://www.web-translations.com/blog/quality-control-features-in-trados/) — third-party blog, not official docs

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
