# Feature Landscape: LocaNext CAT Tool (Demo-Ready)

**Domain:** Desktop CAT tool / game localization management platform
**Researched:** 2026-03-14
**Overall confidence:** MEDIUM-HIGH (based on memoQ docs, Trados features, Smartcat help, Phrase/Memsource docs, game localization guides)

---

## Table Stakes

Features users (and especially executive audiences) expect. Missing = product feels incomplete or amateurish in a demo.

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| T1 | **Side-by-side source/target editor** | Every CAT tool shows source and target columns. Executives recognize this layout instantly. | Med | LocaNext has a grid — ensure it looks polished with clear source/target separation |
| T2 | **Translation Memory lookup with match percentages** | Core value prop of any CAT tool. TM matches must show 100%, fuzzy (75-99%), and no-match with visual color coding. | Med | Already have FAISS + exact search. Need percentage display and color-coded match indicators in the UI |
| T3 | **Concordance search** | Ability to highlight text and search across all TMs for that phrase. Every major tool (memoQ, Trados, Smartcat) has this. | Med | Leverage existing FAISS semantic search. Add a right-click or Ctrl+F concordance panel |
| T4 | **File explorer / project tree** | Hierarchical navigation of platforms > projects > folders > files. Standard in memoQ, Trados. | Low | Already exists (FilesPage.svelte). Polish the tree UI |
| T5 | **TM tree with assignment** | TMs organized in a tree, assignable to platform/project/folder scope. memoQ has this exact pattern. | Low | Already exists (TMExplorerTree.svelte). Already designed with assignment levels |
| T6 | **File upload and parsing** | Import files (XML, XLIFF, Excel) and parse into translatable segments. | Med | Exists but needs end-to-end validation. XML with `<br/>` preservation is critical |
| T7 | **Export / download workflow** | Export translated files back to original format. Executives will ask "and then what happens?" | Med | Must produce clean output files. Demo flow: upload > translate > export |
| T8 | **Search and filter in editor** | Find text across segments, filter by status (translated/untranslated/fuzzy). Every CAT tool has this. | Low-Med | Basic search likely exists. Add status filters (confirmed, draft, empty) |
| T9 | **Segment status indicators** | Visual status per row: confirmed, draft, untranslated, fuzzy match applied. Color-coded. | Low | Icons or colored indicators in the grid. Green=confirmed, yellow=fuzzy, red=empty |
| T10 | **Undo/redo in editor** | Executives will test this. Missing undo = "this feels unfinished." | Low | Standard text editing. Ensure grid cells support Ctrl+Z |
| T11 | **Keyboard navigation** | Tab between segments, Enter to confirm, Ctrl+Enter to confirm and advance. Power users expect this. | Low-Med | Critical for demo fluidity — shows the tool is "real" |
| T12 | **Basic QA checks** | Tag verification, missing translations, number consistency. Trados and memoQ both have extensive QA. | Med | Already have QA repository interface. Need visible QA panel with pass/fail indicators |
| T13 | **User authentication** | Login screen with user/password. Enterprise = multi-user aware. | Low | Already exists (JWT auth, offline mode detection) |
| T14 | **Responsive, polished grid** | Smooth scrolling through thousands of segments. No lag, no jank. Virtual scrolling for large files. | Med-High | This is the #1 demo killer if it feels slow. Virtual scrolling is mandatory for files with 10K+ segments |

---

## Differentiators

Features that set LocaNext apart. Not expected in every CAT tool, but impressive in a demo and valuable for game localization specifically.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| D1 | **Semantic search (FAISS vectors)** | "Find translations that mean similar things, not just exact text matches." Most CAT tools only do fuzzy string matching (edit distance). Semantic search using embeddings is genuinely ahead of memoQ/Trados. | Low (already built) | Qwen model + FAISS already exist. **Demo this prominently** — it is the wow factor |
| D2 | **Full offline mode with parity** | Most CAT tools are either desktop-only (Trados) or cloud-only (Phrase/Smartcat). LocaNext does both with transparent switching. memoQ has online/offline but it is clunky. | Med (architecture exists, needs validation) | DB abstraction layer already designed. Validate it works. Demo: pull network cable, keep working |
| D3 | **Local AI pretranslation (Qwen)** | On-device ML model for pretranslation without cloud API costs. No data leaves the machine. Enterprise security teams love this. | Low (already built) | 2.3GB Qwen model runs locally. No API keys, no cloud dependency, no per-word costs |
| D4 | **MapDataGenerator integration** | Visual mapping of image/audio assets to translation strings. Game-specific — no general CAT tool does this. Shows "we understand games." | Med | Standalone Python tool needs organic integration into the grid. Image thumbnails in the translation grid would be visually striking in a demo |
| D5 | **Game-aware context: character limits + variables** | Show character limits per field (UI space constraints), highlight `{variables}` and `<tags>` in source/target. Game localization specific — Trados/memoQ don't do this natively. | Med | Character count display per cell, warning when exceeding limits. Variable placeholder highlighting with protection against accidental deletion |
| D6 | **Real-time multi-user collaboration** | WebSocket-based live editing. See other translators' cursors and changes. Phrase/Smartcat have this for cloud — rare in desktop tools. | High | Infrastructure exists (WebSocket). Full implementation is complex. Save for later phases, but architecture supports it |
| D7 | **TM leverage statistics / analysis** | "Upload a file, instantly see: 45% already translated, 30% fuzzy matches, 25% new." Executives love numbers. Shows ROI. | Med | Analyze file against TMs, produce breakdown: 100% / fuzzy tiers / new. Display as a dashboard widget or modal |
| D8 | **Glossary/terminology panel** | Side panel showing glossary terms detected in current segment. Terms highlighted in source text. | Med | `get_glossary_terms()` already in TM interface. Need UI panel that auto-shows matches as user navigates segments |
| D9 | **Batch operations** | Confirm all fuzzy matches above 95%, pretranslate entire file, bulk status changes. Shows workflow efficiency. | Med | Bulk confirm, bulk pretranslate, bulk export. Important for "at scale" narrative in demos |
| D10 | **Dark mode / theme switching** | Modern apps have this. Quick visual differentiation from older tools like Trados. | Low-Med | Carbon Components supports theming. Toggle in preferences |
| D11 | **Activity/audit log** | "Who changed what, when." Enterprise compliance requirement. Also useful in demos to show accountability. | Med | Log edits with timestamp, user, old/new value. Display in a side panel or modal |

---

## Anti-Features

Features to explicitly NOT build. Either out of scope, counterproductive, or traps that consume effort without value.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|--------------|-----------|-------------------|
| A1 | **Full MT engine integration (Google/DeepL API)** | Distraction from core value. Every tool has MT. LocaNext's differentiator is LOCAL AI (Qwen), not yet-another-API-wrapper. MT APIs also require keys, billing, and network — breaks offline story. | Lean into Qwen local pretranslation. "Zero cloud costs, zero data leakage" is a stronger pitch than "we also call Google Translate" |
| A2 | **WYSIWYG in-context preview** | Rendering game UI in the CAT tool is a massive undertaking (different engines, formats, resolutions). memoQ/Trados don't even do this well for games. | Show image/screenshot references alongside segments (MapDataGenerator). Context without the rendering nightmare |
| A3 | **Plugin/extension marketplace** | Premature. Trados has an app marketplace after 20+ years. Building extension APIs before the core works is a trap. | Hardcode the integrations you need. Extensibility comes after stability |
| A4 | **Automated workflow orchestration** | Complex state machines for translation workflows (assign > translate > review > QA > approve). Enterprise TMS feature, not demo-ready CAT tool feature. | Simple status per segment (draft/confirmed). Manual workflow. Don't over-engineer process management |
| A5 | **Cost estimation / billing** | Phrase and Smartcat have word-count-based pricing calculators. Irrelevant for an internal enterprise tool. | TM leverage statistics (D7) give the cost-saving narrative without building billing infrastructure |
| A6 | **100+ file format support** | Trados supports dozens of formats. LocaNext handles XML game data files. Supporting DOCX, PDF, PO, XLIFF, etc. is scope creep. | XML (primary), Excel (import/export), maybe XLIFF for interop. Three formats, done well |
| A7 | **Mobile app** | Explicitly out of scope per PROJECT.md. Translators don't work on phones. | Desktop-first. Electron app is the product |
| A8 | **Spellcheck / grammar check in all languages** | LanguageTool integration exists but only works online. CJK spellcheck is notoriously unreliable. | QA checks for structural issues (tags, numbers, length). Leave linguistic quality to human reviewers |

---

## Feature Dependencies

```
T1 (Side-by-side editor) ──> T8 (Search/filter) ──> T9 (Status indicators)
                          ──> T10 (Undo/redo)
                          ──> T11 (Keyboard nav)

T6 (File upload) ──> T7 (Export)
                 ──> D7 (TM leverage stats) -- requires TM + file analysis

T2 (TM lookup + match %) ──> T3 (Concordance search)
                          ──> D8 (Glossary panel)
                          ──> D9 (Batch operations)

T5 (TM tree) ──> T2 (TM lookup) -- TM must be assigned/active to provide matches

T4 (File explorer) ──> T6 (File upload)
                   ──> D4 (MapDataGenerator) -- image/audio mapping in file context

D1 (Semantic search) ──> T3 (Concordance) -- semantic concordance is the differentiator

T14 (Polished grid) ──> EVERYTHING -- if the grid is slow, nothing else matters
```

---

## MVP Recommendation (Demo-Ready)

### Must have for first demo (Phase 1):

1. **T14 — Polished, fast grid** — This is the foundation. If it stutters, the demo fails.
2. **T1 — Side-by-side editor** — The recognizable CAT tool layout.
3. **T4 + T5 — File explorer + TM tree** — Already exist, need polish.
4. **T6 + T7 — Upload + Export** — End-to-end workflow for the demo narrative.
5. **T2 — TM lookup with match percentages** — Core value proposition.
6. **T9 — Segment status indicators** — Visual confirmation the tool tracks translation state.
7. **T11 — Keyboard navigation** — Makes the demo feel professional.
8. **D1 — Semantic search** — Already built. The wow moment. "Watch this find similar translations even with different wording."

### Add for impressive demo (Phase 2):

9. **T3 — Concordance search** — Builds on semantic search.
10. **D3 — Local AI pretranslation** — Already built. Show Qwen in action.
11. **D7 — TM leverage statistics** — "This file is 60% pre-translated." Executives love ROI numbers.
12. **D8 — Glossary panel** — Side panel with auto-detected terms.
13. **T12 — QA checks** — "Before you export, run QA. Zero errors."
14. **D2 — Offline mode demo** — Pull the plug, keep working.

### Defer:

- **D4 (MapDataGenerator):** Visually impressive but requires significant integration work. Phase 3.
- **D5 (Character limits/variables):** Game-specific polish. Phase 3.
- **D6 (Real-time collab):** Infrastructure exists but full implementation is Phase 4+.
- **D10 (Dark mode):** Nice-to-have polish. Any phase.
- **D11 (Audit log):** Enterprise feature, not demo-critical. Phase 4.

---

## What Executives Want to See in a Demo

Based on competitive analysis, these are the "moments" that sell:

1. **Speed** — Open a 10,000-line file instantly. No loading spinner that lasts more than 1 second.
2. **The TM match moment** — Type or navigate to a segment, watch the TM panel instantly show a 94% match with the difference highlighted.
3. **Semantic search surprise** — Search for "The warrior attacks" and find "The fighter strikes" at 87% semantic similarity. This is where LocaNext beats Trados/memoQ.
4. **Upload-to-translate flow** — Drag a file in, see it parsed, see TM matches applied, edit a few segments, export. Under 2 minutes.
5. **Offline resilience** — "What if the server goes down?" Show it working with zero disruption.
6. **Numbers** — "This 50,000-word project: 45% exact match, 25% fuzzy, 30% new. That is 70% less work."

---

## Sources

- [memoQ Translation Memory docs](https://docs.memoq.com/current/en/Concepts/concepts-translation-memories.html) — TM management, context matching, assignment patterns
- [Trados features page](https://www.trados.com/product/features/) — QA checks, file format support, editor capabilities
- [Trados QA checks](https://www.web-translations.com/blog/quality-control-features-in-trados/) — Tag verifier, terminology verifier, number/punctuation checks
- [Smartcat Editor overview](https://help.smartcat.com/1539449-editor-functionalities-overview/) — CAT panel, concordance, glossary integration
- [Smartcat glossary management](https://help.smartcat.com/1539721-working-with-glossary-terms/) — Terminology detection, glossary-in-editor workflow
- [CAT Tools Comparison guide](https://better-i18n.com/en/blog/cat-tools-comparison-guide/) — memoQ vs Trados vs Phrase comparison
- [XTM enterprise guide](https://xtm.ai/en-us/blog/cat-tools-guide) — Enterprise CAT tool expectations
- [Gridly game localization guide](https://www.gridly.com/blog/game-localization-guide/) — Character limits, variable placeholders, context
- [Phrase game localization](https://phrase.com/solutions/game-localization/) — Game-specific CAT features
- [Smartcat word match levels](https://help.smartcat.com/cat-tool-word-matches/) — Fuzzy match percentage tiers and leverage reporting
