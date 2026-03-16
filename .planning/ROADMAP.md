# Roadmap: LocaNext

## Milestones

- v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15
- v2.0 Real Data + Dual Platform (Phases 07-14) -- SHIPPED 2026-03-15
- v3.0 Game Dev Platform + AI Intelligence (Phases 15-21) -- SHIPPED 2026-03-15
- v3.1 Debug + Polish + Svelte 5 Migration (Phases 22-25) -- SHIPPED 2026-03-16
- v3.2 GameData Tree UI + Context Intelligence + Image Gen (Phases 26-31) -- IN PROGRESS

## Phases

<details>
<summary>v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15</summary>

- [x] Phase 01: Stability Foundation (3/3 plans) -- completed 2026-03-14
- [x] Phase 02: Editor Core (3/3 plans) -- completed 2026-03-14
- [x] Phase 03: TM Workflow (3/3 plans) -- completed 2026-03-14
- [x] Phase 04: Search and AI Differentiators (2/2 plans) -- completed 2026-03-14
- [x] Phase 05: Visual Polish and Integration (2/2 plans) -- completed 2026-03-14
- [x] Phase 05.1: Contextual Intelligence & QA Engine (5/5 plans) -- completed 2026-03-14
- [x] Phase 06: Offline Demo Validation (2/2 plans) -- completed 2026-03-14

</details>

<details>
<summary>v2.0 Real Data + Dual Platform (Phases 07-14) -- SHIPPED 2026-03-15</summary>

- [x] Phase 07: XML Parsing Foundation + Bug Fixes (3/3 plans) -- completed 2026-03-15
- [x] Phase 08: Dual UI Mode (2/2 plans) -- completed 2026-03-15
- [x] Phase 09: Translator Merge (2/2 plans) -- completed 2026-03-15
- [x] Phase 10: Export Pipeline (1/1 plan) -- completed 2026-03-15
- [x] Phase 11: Image & Audio Pipeline (2/2 plans) -- completed 2026-03-15
- [x] Phase 12: Game Dev Merge (2/2 plans) -- completed 2026-03-15
- [x] Phase 13: AI Summaries (2/2 plans) -- completed 2026-03-15
- [x] Phase 14: E2E Validation + CLI (2/2 plans) -- completed 2026-03-15

</details>

<details>
<summary>v3.0 Game Dev Platform + AI Intelligence (Phases 15-21) -- SHIPPED 2026-03-15</summary>

- [x] Phase 15: Mock Gamedata Universe (2/2 plans) -- completed 2026-03-15
- [x] Phase 16: Category Clustering + QA Pipeline (2/2 plans) -- completed 2026-03-15
- [x] Phase 17: AI Translation Suggestions (2/2 plans) -- completed 2026-03-15
- [x] Phase 18: Game Dev Grid + File Explorer (2/2 plans) -- completed 2026-03-15
- [x] Phase 19: Game World Codex (2/2 plans) -- completed 2026-03-15
- [x] Phase 20: Interactive World Map (2/2 plans) -- completed 2026-03-15
- [x] Phase 21: AI Naming Coherence + Placeholders (2/2 plans) -- completed 2026-03-15

</details>

<details>
<summary>v3.1 Debug + Polish + Svelte 5 Migration (Phases 22-25) -- SHIPPED 2026-03-16</summary>

- [x] Phase 22: Svelte 5 Migration (3/3 plans) -- completed 2026-03-15
- [x] Phase 23: Bug Fixes (4/4 plans) -- completed 2026-03-15
- [x] Phase 24: UIUX Polish (2/2 plans) -- completed 2026-03-15
- [x] Phase 25: Comprehensive API E2E Testing (10/10 plans) -- completed 2026-03-16

</details>

### v3.2 GameData Tree UI + Context Intelligence + Image Gen (IN PROGRESS)

**Milestone Goal:** Rework the Game Data page from flat grid to hierarchical XML tree navigator with parent/child node expansion, add a right-side context panel with TM suggestions/images/audio/AI context, generate AI images for Codex, and achieve sub-second lookup via multi-tier indexing.

- [x] **Phase 26: Navigation + DEV Parity** - Rename sidebar tabs, add showDirectoryPicker for browser, auto-load mock data, enforce file type separation (completed 2026-03-16)
- [x] **Phase 27: Tree Backend + Mock Data** - lxml tree walker API and expanded mock fixtures with real hierarchical XML structures (completed 2026-03-16)
- [x] **Phase 28: Hierarchical Tree UI** - Beautiful expandable tree with node detail panel, cross-reference links, and folder loading (completed 2026-03-16)
- [ ] **Phase 29: Multi-Tier Indexing** - Hashtable + FAISS + Aho-Corasick indexing for instant entity lookup across all loaded gamedata
- [ ] **Phase 30: Context Intelligence Panel** - Right panel with TM suggestions, images, audio, AI context via 5-tier cascade search, and cross-references
- [ ] **Phase 31: Codex AI Image Generation** - Nano Banana / Gemini image generation for Codex entities with entity-aware prompts and batch mode

## Phase Details

### Phase 26: Navigation + DEV Parity
**Goal**: The Game Data and Localization Data pages have correct naming, browser DEV mode has full folder picking parity with Electron, and file types are strictly separated between the two modes
**Depends on**: Nothing (v3.2 foundation -- quick wins that rename existing UI and add DEV conveniences)
**Requirements**: NAV-01, NAV-02, NAV-03, NAV-04, NAV-05
**Success Criteria** (what must be TRUE):
  1. Sidebar shows "Localization Data" instead of "Files" and "Game Data" instead of "GameDev"
  2. In browser DEV mode, clicking a folder button on Game Data page opens a native folder picker dialog via showDirectoryPicker
  3. Opening the Game Data page in DEV mode automatically loads mock gamedata without any manual path entry
  4. Attempting to load a LocStr XML file on Game Data page is rejected; attempting to load a StaticInfo XML on Localization Data page is rejected
**Plans**: 1 plan

Plans:
- [ ] 26-01: Sidebar rename + file type enforcement + browser folder picker + DEV auto-load

### Phase 27: Tree Backend + Mock Data
**Goal**: The backend can parse any XML gamedata file into a hierarchical tree structure (parent/child/sibling relationships) and return it as structured JSON, with expanded mock fixtures demonstrating real nesting patterns
**Depends on**: Phase 26 (navigation naming in place, DEV auto-load available for testing)
**Requirements**: TREE-05, TREE-07
**Success Criteria** (what must be TRUE):
  1. API endpoint accepts an XML file path and returns a JSON tree with nested parent/child nodes (not flat rows)
  2. Tree parser uses lxml el.iter(), el.findall(), and parent/child navigation (like QACompiler generators), not flat row extraction
  3. Mock fixtures include SkillTreeInfo with nested SkillNodes + ParentId references, KnowledgeInfo with KnowledgeList children, and GimmickGroup with GimmickInfo nesting
  4. Parser handles all existing mock entity types (iteminfo, characterinfo, skillinfo, knowledgeinfo, gimmickgroupinfo, regioninfo, questinfo, sceneobjectdata, sealdatainfo)
**Plans**: 2 plans

Plans:
- [ ] 27-01-PLAN.md — lxml hierarchical tree parser API endpoint + TreeNode schemas + unit/API tests
- [ ] 27-02-PLAN.md — Expand mock fixtures with multi-branch SkillTree + KnowledgeList nesting

### Phase 28: Hierarchical Tree UI
**Goal**: Users can explore XML gamedata as a beautiful, expandable tree -- navigating parent/child hierarchies, viewing node details, editing text attributes, and following cross-reference links between entities
**Depends on**: Phase 27 (tree parser API returns hierarchical JSON)
**Requirements**: TREE-01, TREE-02, TREE-03, TREE-04, TREE-06, TREE-08
**Success Criteria** (what must be TRUE):
  1. Selecting a gamedata folder loads all XML files as a browsable tree with expand/collapse per node, showing real hierarchy (SkillTree nodes nested under parents, GimmickInfo under GimmickGroup)
  2. Each XML structure type renders appropriately -- skills show SkillTree/SkillNode/Knowledge hierarchy, items show flat ItemInfo list, regions show SceneObjectData children
  3. Clicking a tree node shows its attributes in a detail panel with editable text fields for name/desc attributes (respecting EDITABLE_ATTRS mapping)
  4. Cross-reference keys (e.g., SkillInfo.LearnKnowledgeKey linking to KnowledgeInfo) render as clickable links that navigate to the referenced entity in the tree
  5. Tree UI has proper indentation, color-coded node types, expand/collapse animations, entity icons per type, and hover previews -- visually superior to a code editor tree view
**Plans**: 3 plans

Plans:
- [ ] 28-01: Tree component with folder loading, expand/collapse, dynamic node rendering per XML structure
- [ ] 28-02: Node detail panel with attribute display, editable text fields, EDITABLE_ATTRS mapping
- [ ] 28-03: Cross-reference resolution + clickable links + visual polish (colors, icons, animations, hover previews)

### Phase 29: Multi-Tier Indexing
**Goal**: All loaded gamedata entities are indexed for instant lookup -- hashtable for O(1) key lookup, FAISS for semantic similarity, and Aho-Corasick for real-time glossary detection -- all built automatically when a folder loads
**Depends on**: Phase 28 (tree UI loads folders, providing the entity data to index)
**Requirements**: IDX-01, IDX-02, IDX-03, IDX-04, IDX-05
**Success Criteria** (what must be TRUE):
  1. Looking up an entity by Key, StrKey, or exact name returns results instantly (O(1) hashtable) across all loaded XML files
  2. Searching by a description phrase or concept returns semantically similar entities via FAISS vector search (reusing existing Model2Vec + FAISS infrastructure)
  3. Pasting or typing text in any field highlights all recognized entity names found via Aho-Corasick single-pass scan (reusing QuickSearch/QuickCheck automaton patterns)
  4. Loading a gamedata folder automatically extracts a glossary of all entity names and descriptions and builds the Aho-Corasick automaton from them
  5. Full gamedata folder with 5000+ entities indexes completely in under 3 seconds
**Plans**: 3 plans

Plans:
- [ ] 29-01-PLAN.md &mdash; GameDataIndexer + GameDataSearcher: hash, FAISS, AC indexes + 6-tier cascade search engine
- [ ] 29-02-PLAN.md &mdash; API endpoints (build, search, detect, status) + performance validation (<3s for 5000+ entities)
- [ ] 29-03-PLAN.md &mdash; Frontend integration: auto-index on folder load, search bar in GameDataTree, AC glossary highlights in NodeDetailPanel

### Phase 30: Context Intelligence Panel
**Goal**: Selecting any node in the tree opens a right panel showing TM suggestions, related images, audio playback, AI-powered context analysis via 5-tier cascade search, and cross-reference maps -- giving game developers instant, rich context for any entity
**Depends on**: Phase 29 (indexes must exist for cascade search, glossary detection, and semantic lookup)
**Requirements**: CTX-01, CTX-02, CTX-03, CTX-04, CTX-05

**Design Decision -- 4-Tier Cascade + Conditional 5th Tier (CTX-04):**
The smart search uses a cascading strategy where each tier fires only if previous tiers return insufficient results:
1. **Tier 1 - Line/whole 100% match:** Exact string matching with normalized linebreak logic — whole line include + split line matching. Fastest possible, handles br-tag normalization.
2. **Tier 2 - Aho-Corasick word match:** Multi-pattern automaton built from ALL entity names. Single O(n) pass finds every known term simultaneously. Far superior to string.includes() — catches all entity references in one scan.
3. **Tier 3 - Line/whole embedding match via Model2Vec:** Standard default embeddings (NOT Qwen). Fast semantic similarity for conceptually related entities. Sub-millisecond per query with FAISS.
4. **Tier 4 - N-gram matching (CONDITIONAL):** Only fires if tiers 1-3 return ZERO results. Catches partial matches, typos, abbreviations via character n-gram overlap.
5. **AI Context (post-cascade):** Qwen3 generates human-readable context summary using whatever the cascade found. Not a search tier — it's the presentation layer that consumes cascade results.

Tiers 1-3 always fire in sequence (fast to slower). Tier 4 is conditional on empty results. AI summary runs after cascade completes.

**Success Criteria** (what must be TRUE):
  1. Selecting a tree node opens a right panel showing TM suggestions (similar words/sentences found via embedding search in loaded language data)
  2. If the selected entity has a texture reference or Codex image, the context panel displays the image; if it references a character with voice data, an audio player appears
  3. AI context summary appears for the selected entity, with results arriving progressively as each cascade tier completes (fast tiers first, LLM last)
  4. The context panel shows which other entities reference the selected one (skills using this knowledge, items in this region, etc.) as navigable links
**Plans**: 2 plans

Plans:
- [ ] 30-01: Right panel layout + TM embedding suggestions + image/audio display
- [ ] 30-02: 5-tier cascade search engine + AI context summary + cross-reference map

### Phase 31: Codex AI Image Generation
**Goal**: Codex entities get AI-generated images replacing SVG placeholders -- entity-type-aware prompts produce character portraits, item icons, region landscapes, and skill effects, with batch generation for entire categories
**Depends on**: Phase 28 (tree UI provides entity data; Codex already exists from v3.0)
**Requirements**: IMG-01, IMG-02, IMG-03, IMG-04
**Success Criteria** (what must be TRUE):
  1. Codex entities that previously showed SVG placeholders now display AI-generated images (via Nano Banana / Gemini)
  2. Generated images match entity type -- characters get portraits, items get icons, regions get landscape scenes, skills get effect visualizations
  3. Generated images are cached on disk keyed by entity StrKey and served via the existing mapdata thumbnail API endpoint
  4. User can trigger batch generation for an entire category (e.g., "generate all character images") with a progress bar showing completion
**Plans**: 2 plans

Plans:
- [ ] 31-01: Nano Banana / Gemini integration + entity-type-aware prompt templates + disk caching
- [ ] 31-02: Batch generation mode with progress tracking + Codex UI integration

## Progress

**Execution Order:**
Phases execute in numeric order: 26 -> 27 -> 28 -> 29 -> 30 -> 31

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Stability Foundation | v1.0 | 3/3 | Complete | 2026-03-14 |
| 02. Editor Core | v1.0 | 3/3 | Complete | 2026-03-14 |
| 03. TM Workflow | v1.0 | 3/3 | Complete | 2026-03-14 |
| 04. Search and AI Differentiators | v1.0 | 2/2 | Complete | 2026-03-14 |
| 05. Visual Polish and Integration | v1.0 | 2/2 | Complete | 2026-03-14 |
| 05.1. Contextual Intelligence & QA | v1.0 | 5/5 | Complete | 2026-03-14 |
| 06. Offline Demo Validation | v1.0 | 2/2 | Complete | 2026-03-14 |
| 07. XML Parsing Foundation + Bug Fixes | v2.0 | 3/3 | Complete | 2026-03-15 |
| 08. Dual UI Mode | v2.0 | 2/2 | Complete | 2026-03-15 |
| 09. Translator Merge | v2.0 | 2/2 | Complete | 2026-03-15 |
| 10. Export Pipeline | v2.0 | 1/1 | Complete | 2026-03-15 |
| 11. Image & Audio Pipeline | v2.0 | 2/2 | Complete | 2026-03-15 |
| 12. Game Dev Merge | v2.0 | 2/2 | Complete | 2026-03-15 |
| 13. AI Summaries | v2.0 | 2/2 | Complete | 2026-03-15 |
| 14. E2E Validation + CLI | v2.0 | 2/2 | Complete | 2026-03-15 |
| 15. Mock Gamedata Universe | v3.0 | 2/2 | Complete | 2026-03-15 |
| 16. Category Clustering + QA Pipeline | v3.0 | 2/2 | Complete | 2026-03-15 |
| 17. AI Translation Suggestions | v3.0 | 2/2 | Complete | 2026-03-15 |
| 18. Game Dev Grid + File Explorer | v3.0 | 2/2 | Complete | 2026-03-15 |
| 19. Game World Codex | v3.0 | 2/2 | Complete | 2026-03-15 |
| 20. Interactive World Map | v3.0 | 2/2 | Complete | 2026-03-15 |
| 21. AI Naming Coherence + Placeholders | v3.0 | 2/2 | Complete | 2026-03-15 |
| 22. Svelte 5 Migration | v3.1 | 3/3 | Complete | 2026-03-15 |
| 23. Bug Fixes | v3.1 | 4/4 | Complete | 2026-03-15 |
| 24. UIUX Polish | v3.1 | 2/2 | Complete | 2026-03-15 |
| 25. Comprehensive API E2E Testing | v3.1 | 10/10 | Complete | 2026-03-16 |
| 26. Navigation + DEV Parity | 1/1 | Complete    | 2026-03-16 | - |
| 27. Tree Backend + Mock Data | 2/2 | Complete    | 2026-03-16 | - |
| 28. Hierarchical Tree UI | 3/3 | Complete    | 2026-03-16 | - |
| 29. Multi-Tier Indexing | v3.2 | 0/3 | Not started | - |
| 30. Context Intelligence Panel | v3.2 | 0/2 | Not started | - |
| 31. Codex AI Image Generation | v3.2 | 0/2 | Not started | - |
