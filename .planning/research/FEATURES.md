# Feature Landscape: LocaNext v2.0 — Real Data + Dual Platform

**Domain:** Desktop CAT tool + game dev platform / game localization management
**Researched:** 2026-03-15
**Overall confidence:** MEDIUM-HIGH
**Scope:** NEW features for v2.0 only. v1.0 table stakes (editor, TM, search, offline) already shipped.

---

## Table Stakes (for v2.0 scope)

Features that v2.0 MUST deliver for the "make it real" promise. Without these, v2.0 is just v1.0 with more scaffolds.

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| T1 | **Real XML parsing replacing mock fixtures** | v1.0 used mocks. Users opening real game XML files and seeing actual data flow is the entire point of v2.0. Without this, nothing else works. | High | None (foundation) | 10 battle-tested patterns from NewScripts. Sanitizer+recovery handles malformed files. Cross-reference chain resolution across multiple XMLs. `<br/>` tag preservation is CRITICAL. |
| T2 | **Translator merge: exact StringID match** | The most basic merge operation. Every CAT tool does exact-match transfer. QuickTranslate already has this proven. Not having it means the tool can't do its primary job. | Med | T1 (XML parsing) | Direct port from QuickTranslate. StringID-to-StringID transfer of translation values. |
| T3 | **Translator merge: source text match** | When StringIDs differ between file versions but source text is identical, translators expect the tool to find and transfer those matches. Trados/memoQ do this automatically. | Med | T1, T2 | StrOrigin match from QuickTranslate. Handles renamed StringIDs across file revisions. |
| T4 | **Export to XML with format preservation** | Translators export their work back to game-consumable XML. Tags, encoding, `<br/>` newlines, attribute order must survive the round-trip. Broken export = broken game. | Med-High | T1 | lxml raw_attribs pattern from ExtractAnything. XML declaration, encoding, whitespace preservation. Round-trip tests mandatory. |
| T5 | **Export to Excel** | Excel is the lingua franca of localization teams. PMs, reviewers, QA all work in spreadsheets. Every CAT tool exports to Excel. | Med | T1 | xlsxwriter for writing. Column structure: StrOrigin, ENG, Target, Correction, Status, etc. (LanguageDataExporter pattern). |
| T6 | **Dual UI mode detection** | v2.0 promises both Translator and Game Dev modes. Auto-detecting `<LocStr>` nodes vs other XML structures is the minimum to deliver on "dual platform." | Med | T1 | File type heuristic: `<LocStr>` presence = Translator mode. Everything else = Game Dev mode. Mode indicator in editor header. |
| T7 | **Translator-mode column layout** | When in Translator mode, the grid must show translation-relevant columns: Source, Target, Status, Match%, TM Source. This is what translators recognize. | Low | T6, existing grid | Reuses existing virtual grid with different column config. Already have the grid infrastructure from v1.0. |
| T8 | **Game Dev mode column layout** | When in Game Dev mode, the grid must show XML-structure columns: NodeName, Attributes, Values, Children count. Game devs need to see the data structure, not just strings. | Med | T6, existing grid | New column config for the same grid. Must handle nested XML display (parent > child hierarchy). |
| T9 | **DDS-to-PNG image display** | MapDataGenerator integration was scaffolded in v1.0. Showing actual game textures (DDS format) as PNG thumbnails in the context panel is what makes "we understand games" real. | Med | T1 (for StrKey chains) | Pillow 12.x has native DDS support (DdsImagePlugin). No external binary needed. StrKey > UITextureName > DDS chain from KnowledgeInfo XMLs. Cache converted PNGs. |
| T10 | **Graceful missing asset handling** | When images or audio are missing (common in game dev), showing broken icons kills the demo. Placeholder with "Asset not found" is the minimum. | Low | T9 | Styled placeholder component. Not a broken `<img>` tag. |
| T11 | **Language table parsing** | Extracting all language columns (KR, EN, JP, etc.) from loc.xml files correctly. This is the fundamental data extraction that feeds both Translator and Game Dev modes. | Med | T1 | Pattern from LanguageDataExporter. Multiple language attributes per node. |
| T12 | **XML sanitizer + recovery** | Real game data files are messy. Malformed XML, encoding issues, orphan tags. The tool must not crash on bad input. | Med | None | Sanitizer pattern from NewScripts. Try parse > sanitize > retry > report errors. |
| T13 | **Postprocessing pipeline for merge output** | After transferring translations, CJK-specific cleanup is needed: trailing spaces, width normalization, punctuation fixes. QuickTranslate's 7-step pipeline is proven. | Med | T2, T3 | Direct port from QuickTranslate postprocess. CJK-safe. Only modifies Str/Desc fields. |
| T14 | **Bug fixes (offline TMs, paste, folder 404)** | v1.0 shipped with 3 known bugs. Shipping v2.0 without fixing these undermines credibility. | Low-Med | Existing code | FIX-01: SQLite > PostgreSQL TM visibility. FIX-02: TM paste flow. FIX-03: folder creation 404. |

---

## Differentiators

Features that set v2.0 apart from generic CAT tools. These are NOT expected in memoQ/Trados/Phrase but are genuinely impressive for game localization.

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| D1 | **Fuzzy matching via Model2Vec embeddings** | Most CAT tools use edit-distance fuzzy matching (Levenshtein). LocaNext uses semantic vector similarity. "Find translations that MEAN similar things, not just look similar." This is the v1.0 wow factor extended to merge operations. | Med | T2, T3, Model2Vec index | Already have Model2Vec + FAISS from v1.0. Apply the same pipeline to merge: when exact and source-match fail, find semantically similar source strings above threshold. |
| D2 | **AI context summaries via local Qwen3** | No CAT tool offers on-device LLM-generated context summaries. Translators see "This is a weapon description for a legendary sword in the Crimson Region, used by warrior-class characters." Zero cloud, zero cost. | Med-High | T1 (parsed data), Ollama | Qwen3-4B at 117 tok/s on RTX 4070 Ti. Structured JSON output. 2-line contextual summary per string. Cache per StringID. Graceful "AI unavailable" badge when Ollama is down. |
| D3 | **Position-aware XML merge for Game Dev** | General CAT tools don't handle game dev XML merging (add/remove/modify nodes while preserving document structure). This is game-dev-specific and genuinely useful for data authors. | High | T6, T8, T1 | Not match-type based (unlike Translator merge). Operates at node level: detect added/removed/modified nodes. Preserve XML document order. Handle parent > children > sub-children depth. |
| D4 | **Cross-reference chain resolution** | Resolving StrKey > UITextureName > DDS across multiple XML files to show contextual images. No CAT tool does multi-file join-key resolution for game assets. | Med-High | T1, T9 | QACompiler pattern: join keys across XML files. Build chains at file load time, cache for lookup. |
| D5 | **WEM audio playback** | Playing Wwise audio files inline gives translators voice context for dialogue strings. Hearing the tone/delivery while translating is genuinely valuable and unique. | Med | T1 (for audio mapping) | vgmstream-cli converts WEM to WAV. If vgmstream unavailable, fall back to WAV files. Audio player component in context panel. |
| D6 | **StringIdConsumer deduplication** | Fresh consumer per language prevents duplicate StringID processing in multi-language files. Ensures clean output when the same StringID appears across language tables. | Low-Med | T11 | Pattern from QACompiler. One consumer instance per language. Already proven. |
| D7 | **Export to plain tabulated text** | Quick clipboard-friendly export (StringID + source + translation) for ad-hoc review, chat sharing, or integration with external tools. Simpler than Excel, faster than XML. | Low | T1 | Tab-separated values. Simple but useful. No other CAT tool offers this quick-export format natively. |
| D8 | **CLI coverage for merge and export** | Scriptable merge and export operations for automation, CI/CD integration, and batch processing. Most CAT tools are GUI-only. CLI-first is a developer differentiator. | Med | T2, T3, T4, T5, D3 | Extends existing CLI toolkit from v1.0. Commands for translator merge, game dev merge, export in all formats. |

---

## Anti-Features

Features to explicitly NOT build in v2.0. Tempting but wrong.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|--------------|-----------|-------------------|
| A1 | **Full Game Dev CRUD (create/nest new nodes)** | v2.0 is "read + edit," not full authoring. Creating new XML nodes requires schema validation, parent-child rules, and attribute templates. Massive scope. | Read existing nodes, edit values, merge changes. Full CRUD is v3.0 (GDEV-01, GDEV-02, GDEV-03). |
| A2 | **Game World Codex (interactive encyclopedia)** | Requires ALL XML parsing wired first, plus map rendering, character pages, item pages. Beautiful but enormous. | v3.0 milestone. The XML parsing foundation from v2.0 enables this later. |
| A3 | **AI translation suggestions** | Generating alternative translations needs mature LLM endpoint + embedding index + confidence scoring. The LLM endpoint barely exists yet. | Build the AI summary foundation in v2.0 (AISUM-01 through AISUM-05). Translation suggestions layer on top in v3.0. |
| A4 | **Real-time glossary inconsistency detection** | Aho-Corasick on every keystroke across all entities is a performance challenge. v1.0 has on-demand detection. | Keep on-demand entity detection from v1.0. Real-time is v3.0 optimization. |
| A5 | **XLIFF/TMX import/export** | Industry-standard interchange formats that enable interop with Trados/memoQ. Important eventually, but v2.0 scope is XML game data, not tool interop. | XML + Excel + plain text are the v2.0 export formats. XLIFF/TMX can come in v3.0 if enterprise interop is needed. |
| A6 | **Auto-generate missing images/audio** | Nano Banana for images, voice synthesis for audio. Technically possible but scope explosion. Also requires quality review. | Show graceful placeholders (T10) for missing assets. Auto-generation is v3.0 (AUTOGEN-01, AUTOGEN-02). |
| A7 | **Multi-file batch merge** | Merging across an entire folder of XMLs at once. Useful but complex (conflict resolution, progress tracking, error aggregation). | Single-file merge in v2.0. Batch in v3.0 when single-file is proven solid. |
| A8 | **Schema validation for Game Dev XML** | Validating XML against game-specific schemas (required attributes, valid values, constraints). Requires schema definitions that may not exist. | Basic well-formedness check (XML sanitizer, T12). Schema validation is v3.0 (GDEV-03). |

---

## Feature Dependencies

```
Foundation layer (must be first):
  T1 (Real XML parsing) ──> EVERYTHING ELSE
  T12 (XML sanitizer) ──> T1

Translator merge chain:
  T1 ──> T11 (Language tables) ──> T2 (Exact match) ──> T3 (Source match) ──> D1 (Fuzzy/semantic)
  T2/T3/D1 ──> T13 (Postprocess) ──> T4 (Export XML)
  T2/T3/D1 ──> T5 (Export Excel)
  T2/T3/D1 ──> D7 (Export text)

Dual UI chain:
  T1 ──> T6 (Mode detection) ──> T7 (Translator columns)
                               ──> T8 (Game Dev columns)

Game Dev merge chain:
  T1 ──> T6 ──> T8 ──> D3 (Position-aware merge)

Media pipeline:
  T1 ──> D4 (Cross-ref chains) ──> T9 (DDS > PNG)
  T1 ──> D4 ──> D5 (WEM audio)
  T9/D5 ──> T10 (Missing asset placeholders)

AI pipeline:
  T1 (parsed data) ──> D2 (AI summaries via Qwen3)
  D2 requires Ollama running (graceful degradation if not)

Bug fixes:
  T14 ──> independent (can be done anytime)

CLI:
  D8 ──> depends on T2, T3, T4, T5, D3 being implemented first
```

---

## MVP Recommendation (v2.0 Phase Ordering)

### Phase 1: Foundation (XML parsing + dual UI detection)
1. **T12 — XML sanitizer + recovery** — Must handle bad input before anything else.
2. **T1 — Real XML parsing** — The foundation everything depends on.
3. **T11 — Language table parsing** — Extract translatable data from files.
4. **T6 — Dual UI mode detection** — Route files to correct mode.
5. **T7 + T8 — Column layouts** — Both modes need their columns.
6. **D6 — StringIdConsumer** — Clean deduplication from the start.

### Phase 2: Translator merge (the core value)
7. **T2 — Exact StringID match** — Most common merge operation.
8. **T3 — Source text match** — Handles file version changes.
9. **D1 — Fuzzy/semantic matching** — The differentiator, built on v1.0 infrastructure.
10. **T13 — Postprocessing pipeline** — CJK cleanup after merge.

### Phase 3: Export pipeline
11. **T4 — Export to XML** — Round-trip fidelity with `<br/>` preservation.
12. **T5 — Export to Excel** — xlsxwriter, LanguageDataExporter column structure.
13. **D7 — Export to plain text** — Quick and simple.

### Phase 4: Media pipeline
14. **T9 — DDS-to-PNG** — Pillow native support, straightforward.
15. **D5 — WEM audio** — vgmstream-cli conversion.
16. **D4 — Cross-reference chains** — Wire StrKey > UITextureName > DDS.
17. **T10 — Missing asset placeholders** — Graceful fallback.

### Phase 5: Game Dev merge
18. **D3 — Position-aware XML merge** — Node-level operations, most complex feature.

### Phase 6: AI summaries
19. **D2 — Qwen3 context summaries** — Requires Ollama, structured JSON, caching.

### Phase 7: CLI + bugs + validation
20. **D8 — CLI merge/export commands** — Scriptable operations.
21. **T14 — Bug fixes** — Offline TMs, paste, folder 404.
22. E2E round-trip validation tests.

### Defer to v3.0:
- **A1** (Full Game Dev CRUD): Needs schema definitions, parent-child rules.
- **A2** (Codex): Needs all XML parsing + map rendering + entity pages.
- **A3** (AI translation suggestions): Needs mature LLM + embedding pipeline.
- **A6** (Auto-gen images/audio): Needs Nano Banana + voice synthesis integration.

---

## Competitive Context

### What major CAT tools offer that LocaNext v2.0 matches:
- TM matching with exact + fuzzy (Trados, memoQ, Phrase all have this)
- XML file handling with tag preservation (standard across all tools)
- Export to Excel (universal requirement)
- QA checks (tag verification, structural validation)

### What LocaNext v2.0 offers that competitors do NOT:
- **Semantic fuzzy matching** via vector embeddings (competitors use edit-distance only)
- **Local AI context summaries** with zero cloud dependency (unique)
- **Game asset preview** (DDS textures, WEM audio inline) -- no CAT tool does this
- **Dual Translator/Game Dev mode** in one tool -- competitors serve translators only
- **Position-aware XML merge** for game data authoring -- unique to game dev workflow
- **Full offline parity** with transparent mode switching (most tools are cloud-only or desktop-only, not both)
- **CLI-first merge/export** for automation (most CAT tools are GUI-only)

### Industry trends (2025-2026) that validate v2.0 direction:
- **Local AI adoption accelerating**: Enterprise security teams increasingly prefer on-device models over cloud APIs. LocaNext's Qwen3 local inference aligns perfectly.
- **Context-aware translation**: Smartling's RAG-powered prompt tooling, XTM's visual context -- the industry is moving toward giving translators more context. LocaNext's AI summaries + game asset preview are ahead of this curve.
- **Game localization specialization**: Gridly, LocalizeDirect, and XTM Cloud all added game-specific features in 2025. The market recognizes game localization as a distinct vertical. LocaNext's dual-mode approach is uniquely positioned.

---

## Sources

- [CAT Tools Comparison 2026](https://geotargetly.com/blog/cat-tools) -- Feature comparison across major tools
- [memoQ vs Trados vs Phrase](https://better-i18n.com/en/blog/cat-tools-comparison-guide/) -- Detailed feature matrix
- [AI in Localization Roadmap 2025-2028](https://medium.com/@hastur/embracing-ai-in-localization-a-2025-2028-roadmap-a5e9c4cd67b0) -- Industry direction for LLM integration
- [Smartling AI Translation Growth](https://www.smartling.com/company-news/growth-in-ai-translation-in-2025) -- 218% growth in AI translation adoption
- [Pillow DDS Support](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) -- Native DdsImagePlugin in Pillow 12.x (HIGH confidence)
- [vgmstream WEM playback](https://github.com/vgmstream/vgmstream) -- WEM-to-WAV conversion tool
- [XTM Visual Localization](https://xtm.cloud/use-cases/game-translation/) -- Visual context in game localization
- [TMX Standard](https://www.maxprograms.com/articles/tmx.html) -- Translation memory exchange format
- [Fuzzy Matching (Wikipedia)](https://en.wikipedia.org/wiki/Fuzzy_matching_(computer-assisted_translation)) -- Edit-distance vs semantic approaches
- [Gridly Game Localization Guide](https://www.gridly.com/blog/game-localization-guide/) -- Game-specific localization workflow patterns
- LocaNext v1.0 FEATURES.md (internal) -- Previous milestone feature analysis
- NewScripts source code patterns (internal) -- 10 XML parsing patterns, QuickTranslate merge logic, LanguageDataExporter export patterns

---

*Researched: 2026-03-15 for v2.0 milestone planning*
*Supersedes: v1.0 FEATURES.md (demo-ready scope)*
*Confidence: MEDIUM-HIGH -- core features well-understood from NewScripts patterns; AI summary and Game Dev merge less proven in production*
