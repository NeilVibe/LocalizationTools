# Requirements: LocaNext v3.2

**Defined:** 2026-03-16
**Core Value:** Game developers can explore, understand, and edit hierarchical XML game data in a beautiful tree interface with AI-powered context intelligence — faster and more pleasant than any code editor.

## v3.2 Requirements

### TREE — GameData Hierarchical Tree UI

- [x] **TREE-01**: GameData XML files display as expandable node trees showing parent/child hierarchy (SkillNode ParentId, KnowledgeInfo KnowledgeList nesting, GimmickGroup→GimmickInfo, etc.)
- [x] **TREE-02**: Full folder loading — user selects a gamedata root folder and the entire tree loads with all XML files browsable instantly via pre-indexing
- [x] **TREE-03**: Dynamic node rendering adapts per XML structure — skills show SkillTree→SkillNode→Knowledge hierarchy, items show flat ItemInfo, gimmicks show GimmickGroup→Gimmick nesting, regions show SceneObjectData children
- [x] **TREE-04**: Node detail panel shows all attributes of selected node + its children inline, with editable text fields for name/desc attributes (respects EDITABLE_ATTRS mapping)
- [x] **TREE-05**: Backend XML parser uses clean lxml tree walking (like QACompiler region/skill generators — `el.iter()`, `el.findall()`, parent/child navigation), not flat row extraction
- [x] **TREE-06**: Cross-reference resolution — SkillInfo.LearnKnowledgeKey links to KnowledgeInfo, KnowledgeList links children to parents, all navigable in UI via clickable links
- [x] **TREE-07**: Mock gamedata fixtures expanded with real hierarchical examples (SkillTreeInfo with nested SkillNodes + ParentId, KnowledgeInfo with KnowledgeList children) based on exampleofskillgamedata.txt patterns
- [x] **TREE-08**: Tree UI is BEAUTIFUL — better than VS Code tree view. Proper indentation, color-coded node types, expand/collapse animations, entity icons per type, hover previews

### IDX — Multi-Tier Indexing & Performance

- [x] **IDX-01**: Hashtable index for instant O(1) lookup by Key, StrKey, and entity name across all loaded XML files
- [x] **IDX-02**: FAISS vector index for semantic search across all entity names and descriptions (reuse existing Model2Vec + FAISS infrastructure)
- [x] **IDX-03**: Aho-Corasick automaton built from all entity names for real-time glossary detection in any text field (reuse QuickSearch/QuickCheck patterns)
- [x] **IDX-04**: Auto-glossary extraction — on folder load, build glossary from all entity names/descriptions across the full gamedata tree
- [x] **IDX-05**: Full gamedata folder indexes in under 3 seconds for 5000+ entities

### CTX — Right Panel Context Intelligence

- [x] **CTX-01**: Right panel appears when a node is selected, showing TM suggestions via embedding search (similar words/sentences from loaded language data)
- [x] **CTX-02**: Image display — if selected entity has a texture reference or Codex image, show it in the context panel
- [x] **CTX-03**: Audio playback — if selected entity references a character with voice data, show audio player
- [x] **CTX-04**: Smart search uses 4-tier cascade with conditional 5th tier: (1) Line/whole 100% match with normalized linebreak logic — whole line include + split line matching, (2) Aho-Corasick word-level multi-pattern match across all entity names in single O(n) pass, (3) Line/whole embedding match via Model2Vec (standard default — NOT Qwen embeddings), (4) N-gram matching — CONDITIONAL: only fires if tiers 1-3 return zero results. AI context via Qwen3 uses cascade results to generate summaries.
- [x] **CTX-05**: Entity cross-references shown — what other entities reference this one (skills that use this knowledge, items in this region, etc.)

### IMG — Codex AI Image Generation

- [x] **IMG-01**: AI-generated entity images replace SVG placeholders in Codex using Nano Banana / Gemini image generation
- [x] **IMG-02**: Entity-type aware prompts — character portraits, item icons, region landscape scenes, skill effect icons
- [x] **IMG-03**: Generated images cached on disk with entity StrKey as filename, served via existing `/api/ldm/mapdata/thumbnail/` endpoint
- [ ] **IMG-04**: Batch generation mode — generate images for all entities in a category with progress tracking

### NAV — Navigation & DEV Parity

- [x] **NAV-01**: Files page renamed to "Localization Data" in sidebar tabs
- [x] **NAV-02**: GameDev page renamed to "Game Data" in sidebar tabs
- [x] **NAV-03**: Browser DEV mode uses `showDirectoryPicker` for native folder dialog (parity with Electron)
- [x] **NAV-04**: DEV mode auto-loads mock gamedata on Game Data page mount (no manual path entry needed)
- [x] **NAV-05**: Only language data files (.loc.xml, LocStr) uploadable to Localization Data; only gamedata XML (StaticInfo) loadable in Game Data — strict separation

## v3.3+ Requirements (Deferred)

### Voice Synthesis
- **TTS-01**: CosyVoice 2 integration for AI voice generation of character dialogue
- **TTS-02**: Character voice preview in Codex entity detail pages

### Advanced QA
- **QA-01**: Real-time Aho-Corasick glossary checking on every keystroke during editing
- **QA-02**: AI writing quality analysis (grammar, style consistency, glossary adherence)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full CRUD for game data entities | Read + Edit only — game data is authored in game tools, not in LocaNext |
| Auto-translate/auto-replace | Suggestions only — translator/game dev decides |
| Real game data files for testing | Mock data only — real game data is confidential |
| Google/DeepL API integration | Local AI only — zero cloud dependency |
| Plugin marketplace | Core must work first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 26 | Complete |
| NAV-02 | Phase 26 | Complete |
| NAV-03 | Phase 26 | Complete |
| NAV-04 | Phase 26 | Complete |
| NAV-05 | Phase 26 | Complete |
| TREE-05 | Phase 27 | Complete |
| TREE-07 | Phase 27 | Complete |
| TREE-01 | Phase 28 | Complete |
| TREE-02 | Phase 28 | Complete |
| TREE-03 | Phase 28 | Complete |
| TREE-04 | Phase 28 | Complete |
| TREE-06 | Phase 28 | Complete |
| TREE-08 | Phase 28 | Complete |
| IDX-01 | Phase 29 | Complete |
| IDX-02 | Phase 29 | Complete |
| IDX-03 | Phase 29 | Complete |
| IDX-04 | Phase 29 | Complete |
| IDX-05 | Phase 29 | Complete |
| CTX-01 | Phase 30 | Complete |
| CTX-02 | Phase 30 | Complete |
| CTX-03 | Phase 30 | Complete |
| CTX-04 | Phase 30 | Complete |
| CTX-05 | Phase 30 | Complete |
| IMG-01 | Phase 31 | Complete |
| IMG-02 | Phase 31 | Complete |
| IMG-03 | Phase 31 | Complete |
| IMG-04 | Phase 31 | Pending |

**Coverage:**
- v3.2 requirements: 25 total
- Mapped to phases: 25/25
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 after roadmap creation*
