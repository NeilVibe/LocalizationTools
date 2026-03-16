# Requirements: LocaNext v3.2

**Defined:** 2026-03-16
**Core Value:** Game developers can explore, understand, and edit hierarchical XML game data in a beautiful tree interface with AI-powered context intelligence — faster and more pleasant than any code editor.

## v3.2 Requirements

### TREE — GameData Hierarchical Tree UI

- [ ] **TREE-01**: GameData XML files display as expandable node trees showing parent/child hierarchy (SkillNode ParentId, KnowledgeInfo KnowledgeList nesting, GimmickGroup→GimmickInfo, etc.)
- [ ] **TREE-02**: Full folder loading — user selects a gamedata root folder and the entire tree loads with all XML files browsable instantly via pre-indexing
- [ ] **TREE-03**: Dynamic node rendering adapts per XML structure — skills show SkillTree→SkillNode→Knowledge hierarchy, items show flat ItemInfo, gimmicks show GimmickGroup→Gimmick nesting, regions show SceneObjectData children
- [ ] **TREE-04**: Node detail panel shows all attributes of selected node + its children inline, with editable text fields for name/desc attributes (respects EDITABLE_ATTRS mapping)
- [ ] **TREE-05**: Backend XML parser uses clean lxml tree walking (like QACompiler region/skill generators — `el.iter()`, `el.findall()`, parent/child navigation), not flat row extraction
- [ ] **TREE-06**: Cross-reference resolution — SkillInfo.LearnKnowledgeKey links to KnowledgeInfo, KnowledgeList links children to parents, all navigable in UI via clickable links
- [ ] **TREE-07**: Mock gamedata fixtures expanded with real hierarchical examples (SkillTreeInfo with nested SkillNodes + ParentId, KnowledgeInfo with KnowledgeList children) based on exampleofskillgamedata.txt patterns
- [ ] **TREE-08**: Tree UI is BEAUTIFUL — better than VS Code tree view. Proper indentation, color-coded node types, expand/collapse animations, entity icons per type, hover previews

### IDX — Multi-Tier Indexing & Performance

- [ ] **IDX-01**: Hashtable index for instant O(1) lookup by Key, StrKey, and entity name across all loaded XML files
- [ ] **IDX-02**: FAISS vector index for semantic search across all entity names and descriptions (reuse existing Model2Vec + FAISS infrastructure)
- [ ] **IDX-03**: Aho-Corasick automaton built from all entity names for real-time glossary detection in any text field (reuse QuickSearch/QuickCheck patterns)
- [ ] **IDX-04**: Auto-glossary extraction — on folder load, build glossary from all entity names/descriptions across the full gamedata tree
- [ ] **IDX-05**: Full gamedata folder indexes in under 3 seconds for 5000+ entities

### CTX — Right Panel Context Intelligence

- [ ] **CTX-01**: Right panel appears when a node is selected, showing TM suggestions via embedding search (similar words/sentences from loaded language data)
- [ ] **CTX-02**: Image display — if selected entity has a texture reference or Codex image, show it in the context panel
- [ ] **CTX-03**: Audio playback — if selected entity references a character with voice data, show audio player
- [ ] **CTX-04**: AI context summary — Qwen3 provides automatic context analysis of the selected entity using 5-tier cascade smart search (exact match → hashtable → Aho-Corasick → FAISS semantic → LLM inference)
- [ ] **CTX-05**: Entity cross-references shown — what other entities reference this one (skills that use this knowledge, items in this region, etc.)

### IMG — Codex AI Image Generation

- [ ] **IMG-01**: AI-generated entity images replace SVG placeholders in Codex using Nano Banana / Gemini image generation
- [ ] **IMG-02**: Entity-type aware prompts — character portraits, item icons, region landscape scenes, skill effect icons
- [ ] **IMG-03**: Generated images cached on disk with entity StrKey as filename, served via existing `/api/ldm/mapdata/thumbnail/` endpoint
- [ ] **IMG-04**: Batch generation mode — generate images for all entities in a category with progress tracking

### NAV — Navigation & DEV Parity

- [ ] **NAV-01**: Files page renamed to "Localization Data" in sidebar tabs
- [ ] **NAV-02**: GameDev page renamed to "Game Data" in sidebar tabs
- [ ] **NAV-03**: Browser DEV mode uses `showDirectoryPicker` for native folder dialog (parity with Electron)
- [ ] **NAV-04**: DEV mode auto-loads mock gamedata on Game Data page mount (no manual path entry needed)
- [ ] **NAV-05**: Only language data files (.loc.xml, LocStr) uploadable to Localization Data; only gamedata XML (StaticInfo) loadable in Game Data — strict separation

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
| NAV-01 | Phase 26 | Pending |
| NAV-02 | Phase 26 | Pending |
| NAV-03 | Phase 26 | Pending |
| NAV-04 | Phase 26 | Pending |
| NAV-05 | Phase 26 | Pending |
| TREE-05 | Phase 27 | Pending |
| TREE-07 | Phase 27 | Pending |
| TREE-01 | Phase 28 | Pending |
| TREE-02 | Phase 28 | Pending |
| TREE-03 | Phase 28 | Pending |
| TREE-04 | Phase 28 | Pending |
| TREE-06 | Phase 28 | Pending |
| TREE-08 | Phase 28 | Pending |
| IDX-01 | Phase 29 | Pending |
| IDX-02 | Phase 29 | Pending |
| IDX-03 | Phase 29 | Pending |
| IDX-04 | Phase 29 | Pending |
| IDX-05 | Phase 29 | Pending |
| CTX-01 | Phase 30 | Pending |
| CTX-02 | Phase 30 | Pending |
| CTX-03 | Phase 30 | Pending |
| CTX-04 | Phase 30 | Pending |
| CTX-05 | Phase 30 | Pending |
| IMG-01 | Phase 31 | Pending |
| IMG-02 | Phase 31 | Pending |
| IMG-03 | Phase 31 | Pending |
| IMG-04 | Phase 31 | Pending |

**Coverage:**
- v3.2 requirements: 25 total
- Mapped to phases: 25/25
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 after roadmap creation*
