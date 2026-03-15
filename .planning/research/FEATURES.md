# Feature Landscape: v3.0 Game Dev Platform + AI Intelligence

**Domain:** Game localization CAT tool with game dev authoring + AI intelligence
**Researched:** 2026-03-15
**Overall confidence:** MEDIUM-HIGH
**Scope:** NEW features for v3.0 only. v1.0 (scaffolds) and v2.0 (real data + dual platform) already shipped.
**Competitive context:** memoQ, Gridly, Xbench, Phrase, Owlcat LocalizationTool, Eidos-Montreal Codex (internal)

---

## Table Stakes

Features users expect from a professional game localization/dev tool at this tier. Missing = product feels incomplete given the dual-mode promise delivered in v2.0.

| # | Feature | Why Expected | Complexity | Dependencies (v1/v2) | Notes |
|---|---------|--------------|------------|----------------------|-------|
| T1 | **Mock gamedata universe** | Cannot demo ANY Game Dev feature without realistic data. Every v3.0 feature downstream depends on having representative Items, Characters, Regions, Skills with cross-references, image paths, and audio paths. Not user-facing, but absolutely foundational. | High | XML-01 through XML-07 (XMLParsingEngine), QACompiler generators (Item, Character, Region, Skill) | Reverse-engineer from QACompiler generators. Must include: items with DDS image refs, characters with metadata (race, job, gender), regions with X/Y positions, skills with SkillGroup/SkillTree nesting. Cross-reference keys between files (StrKey chains). Enough volume for semantic search to be meaningful (100+ items, 30+ characters, 10+ regions, 50+ skills). |
| T2 | **Category clustering / content type labels** | memoQ lets users filter by content type. Gridly uses "structured content" with typed grids. Xbench allows project-based filtering. Every serious tool lets translators know WHAT they are editing (item description, quest dialogue, UI string, system message). Without this, a 10K-row grid is an undifferentiated wall of text. | Medium | CTX-01 (entity detection), XML-03 (language tables), LanguageDataExporter categorization logic | LanguageDataExporter already has proven categorization logic (folder structure + filename patterns = category). Port it. Categories: Item, Quest, UI, System, Character, Skill, Region. Show as filterable tags in the grid. Auto-detected from file path + XML structure, not manual tagging. |
| T3 | **QA term consistency checks** | Xbench is THE industry standard for terminology QA. memoQ has built-in term base verification. Phrase and Lokalise both flag missing glossary terms. Any localization tool claiming QA capability must flag: glossary term present in source but absent in target translation. This is the single most common QA check in the industry. | Low | CTX-04 (glossary service), Aho-Corasick entity detection (already operational) | QuickCheck Term Check already exists as proven, battle-tested code. Dual Aho-Corasick automaton + noise filter. Integration effort, not invention. Show results inline in the grid (red underline or QA badge per segment). |
| T4 | **QA line consistency checks** | Same source text translated differently across the project = inconsistency. memoQ, Xbench, Phrase, and Trados all flag this. Translators expect it as baseline QA. Inconsistencies erode player trust (same item described two different ways). | Low | SRCH-01 (semantic search), TM-03 (match percentages), QuickCheck Line Check code | QuickCheck Line Check already implemented. Uses source text grouping + translation comparison. Show flagged segments in a dedicated QA panel or inline badges. Can run on-demand or as background check after file load. |
| T5 | **AI translation suggestions** | Gridly, Phrase, and memoQ all offer MT/AI suggestions in 2025-2026. DMM Game Translate demonstrated AI agents for game localization at GDC 2025. The industry has moved past TM-only matching into AI-generated alternatives. Users now expect ranked AI suggestions alongside TM matches. LocaNext already has Qwen3 running locally -- NOT offering suggestions from it is a missed opportunity. | Medium | AISUM-01 through AISUM-05 (Qwen3 endpoint, already operational), TM-01 (TM matching), SRCH-01 (semantic search), Model2Vec + FAISS | LOCAL only via Qwen3 -- this is the differentiator vs cloud-dependent competitors. Show ranked suggestions with confidence scores in a side panel. Confidence = blend of embedding similarity + LLM certainty. Not auto-replace -- suggestions panel only, user clicks to accept. |
| T6 | **Game Dev Grid with file explorer** | Owlcat's LocalizationTool has a directory tree with filter propagation. Gridly uses structured grid views. Every professional tool shows content in a navigable hierarchy, not a flat list. Game devs expect VS Code-like folder browsing for staticinfo. Without a tree view, Game Dev mode is just a table -- no different from Excel. | Medium | DUAL-01 through DUAL-05 (dual UI mode), XML-01 (XMLParsingEngine), UI-01 (grid infrastructure) | Tree view of gamedata folder structure in left panel. Click folder = show contents in grid. Click file = load and display XML structure. Must show parent/child hierarchy within files (SkillGroup > Skill > SkillInfo). Reuse virtual scroll grid but extend for nested/hierarchical data. |

---

## Differentiators

Features that set LocaNext apart. Not expected in every tool, but create the "wow" that justifies the product's existence. These are what make executives lean forward during a demo.

| # | Feature | Value Proposition | Complexity | Dependencies (v1/v2) | Notes |
|---|---------|-------------------|------------|----------------------|-------|
| D1 | **Game World Codex -- Character/Item encyclopedia** | NO competitor offers an integrated interactive encyclopedia. memoQ has term bases (flat glossary lists). Gridly has structured grids (spreadsheets). Nobody has a browsable, searchable Codex with images, audio, and cross-references linking characters to quests to regions. Eidos-Montreal built "Codex" internally for Guardians of the Galaxy and called the metadata/context "the most helpful element for foreign-language actors." LocaNext would be the first PRODUCT to offer this. | High | MEDIA-01 through MEDIA-04 (DDS/WEM preview), SRCH-01 (semantic search), CTX-01 (entity detection), T1 (mock gamedata) | Character pages: name, image, race, job, gender, age, quest appearances, related characters. Item pages: name, image, description, category, stats, similar items via Model2Vec. Both translators AND game devs use it -- translators for translation context, game devs for lore reference while writing. Searchable via Model2Vec + FAISS. |
| D2 | **Game World Codex -- Interactive world map** | Visual, spatial context for localization is extremely rare. No commercial tool offers an interactive map linking regions to characters, quests, and items. This is the single highest "wow factor" feature for executive demos. Mass Effect's codex and Assassin's Creed encyclopedias prove players value this -- now give the same experience to the people MAKING the game. | Very High | T1 (mock gamedata with region positions), D1 (Codex pages to link to), D3.js + Canvas/SVG rendering | D3.js + Svelte is proven tech (multiple working examples in Svelte playground). Hover location = tooltip with name, description, key NPCs. Click location = detail panel with linked quests, connected characters, items. Data sourced from QACompiler Region generator (has X/Y positions). Custom map background (stylized game world, not real-world geography). |
| D3 | **AI naming coherence for game devs** | Unique to LocaNext. No competitor checks whether a new item name is coherent with existing naming patterns across thousands of entities. A game dev writing "Blade of the Forgotten" should know that 12 other items already use "Forgotten" and what naming pattern they follow. Prevents the slow drift of naming inconsistency that plagues large games. | Medium | Model2Vec + FAISS index (already operational), AISUM-01 (Qwen3 endpoint), T1 (mock gamedata indexed) | Vector embeddings find similar existing entities by name + description. Qwen3 analyzes naming patterns and suggests coherent alternatives. Show as: "Similar existing names: Forgotten Shore, Forgotten Temple, Forgotten Blade. Suggestion: consider 'Forsaken' or 'Lost' for variety." NEVER auto-replace -- suggestions only, game dev confirms in grid. |
| D4 | **Auto-generated placeholder images for missing assets** | When a StringID references an image that doesn't exist yet (common during early development), generate a contextual placeholder instead of showing a broken icon or "not found." Translators and game devs get visual context even when assets are incomplete. No competitor does this -- they all show blank/broken states. | Medium | MEDIA-01 (DDS pipeline), AISUM-01 (Qwen3 for context description), T1 (mock gamedata) | Primary: Gemini image generation via Nano Banana skill (produces actual contextual images). Fallback: styled SVG placeholder with entity name + category-specific icon (sword for weapons, shield for armor, etc.). Cache generated placeholders per StringID. Show "[AI Generated]" badge to distinguish from real assets. |
| D5 | **Offline AI for all features -- zero cloud dependency** | Gridly, Phrase, memoQ all require cloud connectivity for AI features. LocaNext runs Qwen3-4B locally at 117 tok/s on RTX 4070 Ti. Demo works on an airplane. Full AI pipeline (suggestions, naming, summaries) without internet. This is a genuine competitive moat for security-conscious game studios who cannot send game data to cloud APIs. | Already built (foundation) | AISUM-01 through AISUM-05 (v2.0), Ollama + CUDA | v2.0 already has the Qwen3 endpoint for summaries. v3.0 extends it with translation suggestions (T5) + naming coherence (D3). The foundation is proven -- new features are prompt engineering + UI, not infrastructure. |

---

## Anti-Features

Features to explicitly NOT build in v3.0. Tempting but wrong.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|--------------|-----------|-------------------|
| A1 | **Full CRUD in Game Dev Grid (create new nodes)** | Creating new XML nodes requires schema validation, parent-child hierarchy rules, key generation, cross-reference integrity. QACompiler generators READ data -- they do not CREATE it. Building a full XML authoring engine is enormous scope and the schema rules are not formally documented anywhere. | Read + Edit only for v3.0. Game devs can view full XML structure and modify existing Name/DESC/attribute values. Node creation is v4+. |
| A2 | **Cloud MT integration (DeepL, Google Translate)** | Breaks the offline-first promise that is LocaNext's competitive moat. Adds API key management, rate limiting, cost tracking, and error handling for external services. Cloud MT is commodity -- every competitor already has it. | Qwen3 local only. If users want cloud MT, they paste results into the tool. LocaNext differentiates on LOCAL AI, not cloud APIs. |
| A3 | **Real-time collaborative editing (multi-cursor)** | WebSocket sync exists for data updates, but real-time cursor sharing and conflict resolution for simultaneous editing requires OT/CRDT algorithms. Massive engineering effort for a demo feature. Google Docs took years to get this right. | Keep existing WebSocket sync for data state. Single-user editing per segment is fine. Collaborative = shared data, not shared cursors. |
| A4 | **Voice synthesis for missing audio** | Quality voice synthesis requires large models (2GB+), language-specific voice profiles, and results are often uncanny valley. CJK voice synthesis is particularly weak in open-source models. A bad voice demo is worse than no voice demo. | Styled audio placeholder (waveform SVG with entity name and "[No Audio]" label). If real WEM audio exists, play it (already built in v2.0). If not, show placeholder gracefully. |
| A5 | **Spell check / grammar check** | Requires language-specific dictionaries for every target language. CJK support is weak in most spellcheckers. Qwen3-4B at 4B parameters is not reliable enough for grammar correction. Half-baked spell check (missing errors or false positives) is worse than no spell check. | Use QA term/line consistency checks (T3, T4) -- these are more valuable and proven. Defer spell check to v4+ with a larger model or dedicated spellcheck library. |
| A6 | **WYSIWYG in-context preview** | Rendering game UI as it appears in-game requires engine integration, font rendering with game fonts, layout simulation, and screen capture. This is closer to building a game engine preview than a localization feature. | Game World Codex + inline images/audio provide visual context without in-game rendering. Context summaries from Qwen3 describe where text appears. |
| A7 | **Plugin/extension marketplace** | Premature architecture. Core v3.0 features must be solid before opening an extension API. Plugin APIs create backward compatibility obligations and API surface that constrains future development. | Build all v3.0 features directly into the core. Consider plugin architecture as a v5+ initiative once the product is stable. |
| A8 | **XLIFF/TMX import/export** | Industry-standard interchange formats for TMS interop. Important for enterprise adoption, but v3.0 scope is game dev platform + AI intelligence, not enterprise integration. Adding format support is straightforward but orthogonal to the v3.0 vision. | Keep XML + Excel + plain text exports from v2.0. XLIFF/TMX can be a quick addition in v4.0 if enterprise customers request it. |
| A9 | **AI autocorrection / writing quality scoring** | Providing real-time writing feedback (grammar, style, quality scores) sounds impressive but Qwen3-4B lacks the nuance for style consistency analysis. Wrong suggestions erode trust faster than no suggestions. | AI naming coherence (D3) covers the highest-value use case (naming consistency). General writing quality requires a larger model or fine-tuning. |
| A10 | **Drag-and-drop map editing** | The world map is for VISUALIZATION and CONTEXT, not for authoring region data. Adding drag-and-drop editing means two-way data binding to XML, undo/redo on spatial data, and collision detection. Massive scope for minimal value. | Map is read-only. Click to view details, hover for tooltips. Editing happens in the Game Dev Grid. |
| A11 | **AI image generation via cloud (Gemini/DALL-E)** | Cloud dependency for image generation contradicts offline-first. Also, generated game art rarely matches a studio's art style. | Simple Pillow-based placeholders (colored rectangles with text overlay + category icon). Optionally integrate Nano Banana for demo scenarios only. |

---

## Feature Dependencies

```
T1 (Mock Gamedata Universe) ─────────────────────────────┐
  Required by everything Game Dev related                 │
  │                                                       │
  ├──> T2 (Category Clustering)                           │
  │      Uses LanguageDataExporter logic on parsed data   │
  │                                                       │
  ├──> T6 (Game Dev Grid + File Explorer)                 │
  │      ├──> D3 (AI Naming Coherence)                    │
  │      │      Needs indexed gamedata + Qwen3            │
  │      └──> D4 (Auto-gen Placeholder Images)            │
  │             Needs entity context for generation        │
  │                                                       │
  ├──> D1 (Codex -- Character/Item Encyclopedia)          │
  │      ├──> Uses MEDIA (DDS/WEM) from v2.0              │
  │      ├──> Uses SRCH (semantic search) from v1.0       │
  │      └──> D2 (Codex -- Interactive World Map)         │
  │             Needs region position data from T1         │
  │             Needs character/item pages from D1         │
  │                                                       │
  └──> D3 (AI Naming Coherence)                           │
         Needs Model2Vec index of all game entities        │
                                                          │
T3 (QA Term Check) ──────────────────────────────────────┘
  INDEPENDENT -- works on ANY loaded file data
  Uses existing Aho-Corasick + glossary from v1/v2
  Does NOT need mock gamedata

T4 (QA Line Check) ──────────────────────────────────────
  INDEPENDENT -- works on ANY loaded file data
  Uses existing semantic search from v1.0

T5 (AI Translation Suggestions) ─────────────────────────
  INDEPENDENT -- extends existing Qwen3 endpoint
  Works on any data, not just game dev data
  Uses TM matching + Model2Vec for context
```

**Critical path:** T1 (Mock Gamedata) is the foundation. Without it, T2, T6, D1, D2, D3, D4 all have nothing to operate on. T3, T4, T5 are INDEPENDENT and can be built in parallel with T1.

---

## MVP Recommendation

### Phase 1 -- Foundation + Quick Wins (build in parallel)
1. **T1 -- Mock Gamedata Universe** -- Reverse-engineer QACompiler generators. Generate Items, Characters, Regions, Skills with cross-references, images, audio. CRITICAL PATH.
2. **T3 -- QA Term Check** -- Port QuickCheck. Low effort, high value, independent of mock data.
3. **T4 -- QA Line Check** -- Port QuickCheck. Low effort, independent.
4. **T2 -- Category Clustering** -- Port LanguageDataExporter logic. Low-medium effort, depends on T1 for game dev data but works immediately on translator data.

### Phase 2 -- Core Game Dev Experience
5. **T6 -- Game Dev Grid + File Explorer** -- Tree view + read/edit of staticinfo. Medium effort, core to v3.0 promise.
6. **T5 -- AI Translation Suggestions** -- Extend Qwen3 with ranked suggestions. Medium effort, table stakes in 2025-2026. Independent of game dev features.

### Phase 3 -- Wow Features (demo-ready differentiators)
7. **D1 -- Codex: Character/Item Encyclopedia** -- Browsable pages with images, audio, cross-references, semantic search. High wow, high effort.
8. **D3 -- AI Naming Coherence** -- Model2Vec similarity + Qwen3 suggestions. Medium effort, unique differentiator.
9. **D4 -- Auto-generated Placeholder Images** -- Pillow placeholders or styled SVG fallback. Medium effort, visual polish.

### Phase 4 -- Crown Jewel
10. **D2 -- Codex: Interactive World Map** -- D3.js + Svelte, region positions, linked entities. Highest wow factor, highest complexity.

### Defer to v4+
- Full CRUD in Game Dev Grid (A1)
- Voice synthesis (A4)
- Spell/grammar check (A5)
- Cloud MT (A2)
- XLIFF/TMX interchange (A8)
- Plugin marketplace (A7)

---

## Competitive Positioning Matrix

| Capability | memoQ | Gridly | Xbench | Phrase | Owlcat Tool | **LocaNext v3.0** |
|------------|-------|--------|--------|-------|-------------|-------------------|
| TM matching | Yes | Yes | No (QA only) | Yes | Basic | **Yes (4-mode + semantic)** |
| Term QA checks | Yes (term base) | Partial | **Best in class** | Yes | Tags only | **Yes (QuickCheck dual Aho-Corasick)** |
| Line consistency QA | Yes | No | Yes | Yes | Updated-source only | **Yes (QuickCheck)** |
| AI suggestions | Cloud MT only | Cloud MT only | No | Cloud MT only | No | **Local LLM (Qwen3, offline)** |
| Content categorization | By project | By grid type | No | By tag (manual) | No | **Auto-detected from file path + XML** |
| File explorer / tree | Flat list | Grid views | No | Flat list | **Directory tree** | **VS Code-like tree** |
| Game data structure view | No | Spreadsheet | No | No | No | **Full XML hierarchy** |
| Visual context (images) | No | No | No | Screenshot upload | No | **Inline DDS/WEM + auto-gen placeholders** |
| Audio context | No | No | No | No | No | **Inline WEM playback** |
| Interactive codex | No | No | No | No | No | **Character/Item encyclopedia** |
| Interactive world map | No | No | No | No | No | **D3.js region map** |
| Naming coherence AI | No | No | No | No | No | **Vector + LLM analysis** |
| Offline AI | No | No | No | No | N/A | **Full pipeline (Qwen3 local)** |

**LocaNext v3.0's unique position:** The only tool combining localization QA with game dev data authoring, visual/audio context inline, an interactive game world encyclopedia with map, AI naming coherence, and fully offline AI. No competitor attempts this combination. The closest analog is Eidos-Montreal's internal "Codex" tool -- but that was never productized.

---

## Sources

### HIGH confidence (official docs, open source, first-party presentations)
- [Owlcat LocalizationTool (GitHub)](https://github.com/OwlcatGames/LocalizationTool) -- Open source, inspectable features (directory tree, tag mismatch, spelling filter)
- [Behind Codex -- GDC 2022 (Eidos-Montreal)](https://www.gamedeveloper.com/marketing/behind-codex-the-tool-powering-the-dialogue-of-i-marvel-s-guardians-of-the-galaxy-i-) -- First-party GDC talk on internal localization codex tool
- [Xbench QA on memoQ files](https://docs.xbench.net/user-guide/run-qa-memoq/) -- Official documentation for QA integration
- [Xbench.net](https://www.xbench.net/) -- Industry-standard terminology QA tool
- [D3.js Maps with Svelte](https://dev.to/learners/maps-with-d3-and-svelte-8p3) -- Working tutorial with code examples
- [Svelte D3 World Map Playground](https://svelte.dev/playground/1ee2000a93d748bea7a08aba8d55d6f2) -- Official Svelte playground with working map

### MEDIUM confidence (vendor marketing, industry blogs, GDC recaps)
- [memoQ Game Localization](https://www.memoq.com/solutions/game-localization/) -- Vendor feature claims
- [Gridly Platform](https://www.gridly.com/) -- Vendor feature claims for spreadsheet CMS
- [Gridly AI Translation Guide](https://www.gridly.com/blog/ai-translation-game-localization/) -- Vendor blog on AI in localization
- [DMM Game Translate GDC 2025](https://dmm-game-translate.medium.com/revolutionizing-game-localization-with-ai-agents-our-gdc-2025-journey-4f20832d2f94) -- AI agents for game localization
- [CAT Tools Comparison 2026](https://www.versioninternationale.com/en/blog/cat-tools-localization-2026/) -- Industry review
- [Lokalise Translation QA](https://lokalise.com/product/translation-quality-assurance/) -- Competitor QA features
- [Phrase Localization](https://www.softwaresuggest.com/phrase) -- TMS feature set
- [LQA Guide (LocalizeDirect)](https://www.localizedirect.com/posts/lqa-what-is-game-localization-testing) -- Localization QA workflow overview
- [Gridly Localization QA](https://www.gridly.com/localization-qa/) -- Automated QA features

### Internal (project knowledge, proven code)
- QACompiler generators (Item, Character, Region, Skill) -- Schema knowledge for mock gamedata
- QuickCheck Term Check + Line Check -- Battle-tested QA code to port
- LanguageDataExporter categorization logic -- Proven content type classification
- Model2Vec + FAISS pipeline -- Operational semantic search infrastructure
- Qwen3-4B via Ollama -- Operational local LLM at 117 tok/s

---

*Researched: 2026-03-15 for v3.0 milestone planning*
*Supersedes: v2.0 FEATURES.md (real data + dual platform scope)*
*Confidence: MEDIUM-HIGH -- table stakes well-understood from competitors + existing code; Codex and world map are novel (no direct competitor reference), validated by Eidos-Montreal internal Codex success*
