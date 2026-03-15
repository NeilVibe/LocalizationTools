# Requirements: LocaNext v3.0

**Defined:** 2026-03-15
**Core Value:** Game Dev authoring platform with AI-powered suggestions, interactive Codex, and integrated QA -- all local, zero cloud dependency.

## v3.0 Requirements

Requirements for v3.0 milestone. Each maps to roadmap phases.

### Mock Gamedata

- [x] **MOCK-01**: System generates a realistic mock gamedata folder structure matching real staticinfo XML patterns (items, characters, regions, skills, knowledge, gimmicks)
- [x] **MOCK-02**: Mock data includes cross-reference chains between entities (KnowledgeKey, StrKey, LearnKnowledgeKey links)
- [x] **MOCK-03**: Mock data includes DDS image file references and WEM audio file references per entity
- [x] **MOCK-04**: Mock data includes language data files (languagedata_eng.xml, etc.) with LocStr entries matching mock Korean source text
- [x] **MOCK-05**: Mock data includes EXPORT index files (.loc.xml) with StringID mappings per file
- [x] **MOCK-06**: Mock data includes region WorldPosition coordinates and NodeWaypointInfo route data for map visualization
- [x] **MOCK-07**: Mock universe has sufficient volume for meaningful testing (100+ items, 30+ characters, 10+ regions, 50+ skills, 20+ gimmicks)
- [x] **MOCK-08**: Mock data passes round-trip validation (parse -> merge -> export -> re-parse produces consistent results)

### Category Clustering

- [x] **CAT-01**: System auto-classifies StringIDs into content categories (Item, Quest, UI, System, Character, Skill, Region, Gimmick) using LanguageDataExporter two-tier logic
- [x] **CAT-02**: Category column is visible and filterable in the translation grid
- [x] **CAT-03**: User can filter grid by one or more categories to focus on specific content types

### QA Pipeline

- [x] **QA-01**: Term Check detects glossary terms present in source but missing in target translation using dual Aho-Corasick automaton
- [x] **QA-02**: Line Check detects same source text translated inconsistently across the project
- [x] **QA-03**: QA results display inline in the editor with severity tiers (ERROR/WARNING/INFO)
- [x] **QA-04**: User can dismiss individual QA findings per cell (prevents false positive fatigue)
- [x] **QA-05**: QA checks run on-demand via a dedicated QA panel in the editor
- [x] **QA-06**: QA panel shows summary counts per check type (term issues, line issues)

### AI Suggestions

- [x] **AISUG-01**: AI translation suggestions appear in a right-side panel for the selected segment using Qwen3
- [x] **AISUG-02**: Suggestions are ranked with confidence scores (embedding similarity + LLM certainty blend)
- [x] **AISUG-03**: User clicks a suggestion to apply it to the translation field (never auto-replace)
- [x] **AISUG-04**: AI suggestions consider context (entity type, parent hierarchy, surrounding segments) in prompts
- [x] **AISUG-05**: Graceful fallback when Qwen3/Ollama is unavailable (show "AI unavailable" state, no crash)

### AI Naming Coherence

- [x] **AINAME-01**: When editing a Name field in Game Dev mode, system shows similar existing entity names via Model2Vec embedding search
- [x] **AINAME-02**: AI suggests coherent naming alternatives based on existing patterns via Qwen3
- [x] **AINAME-03**: Suggestions display as a non-blocking panel -- game dev confirms in the grid, never auto-replace

### Game Dev Grid

- [x] **GDEV-01**: File explorer panel shows gamedata folder structure matching real gamedata paths
- [x] **GDEV-02**: User clicks a folder/file in explorer to load its contents in the grid
- [x] **GDEV-03**: Grid displays XML entity hierarchy (parent-child nesting visualized with indentation/depth)
- [x] **GDEV-04**: User can edit Name, Desc, and text attributes of existing entities inline in the grid
- [x] **GDEV-05**: Grid shows entity metadata columns appropriate to the data type (Key, StrKey, KnowledgeKey, etc.)
- [x] **GDEV-06**: Changes are saved back to the data model with proper XML attribute encoding (br-tag preservation)
- [x] **GDEV-07**: Game Dev Grid reuses virtual scroll engine for performance with large files (1000+ entities)

### Game World Codex

- [x] **CODEX-01**: Character encyclopedia page shows name, image, description, race, job, quest appearances, related entities
- [x] **CODEX-02**: Item encyclopedia page shows name, image, description, category, stats, similar items via Model2Vec
- [x] **CODEX-03**: Codex is searchable via semantic search (Model2Vec + FAISS) across all entity types
- [x] **CODEX-04**: Both translators and game devs can access Codex pages for reference while working
- [x] **CODEX-05**: Codex pages show inline images (DDS->PNG) and audio playback (WEM->WAV) when available

### Interactive World Map

- [x] **MAP-01**: Interactive map renders region nodes at correct WorldPosition coordinates (X, Z from XML)
- [x] **MAP-02**: Hover over a map node shows tooltip with name, description, and key NPCs
- [x] **MAP-03**: Click a map node opens detail panel linking to Codex pages (characters, items, quests in that region)
- [x] **MAP-04**: Route connections between nodes are visualized (from NodeWaypointInfo waypoints)
- [x] **MAP-05**: Map supports pan and zoom interaction (d3-zoom or equivalent)

### Placeholder Assets

- [x] **PLACEHOLDER-01**: Missing images show a styled SVG placeholder with entity name + category-specific icon instead of broken/blank state
- [x] **PLACEHOLDER-02**: Missing audio shows a waveform SVG placeholder with entity name and "[No Audio]" label
- [x] **PLACEHOLDER-03**: Placeholders are cached per StringID for consistent display

## Future Requirements (v4.0+)

### Game Dev CRUD
- **CRUD-01**: User can create new XML nodes (items, characters, skills) with schema validation
- **CRUD-02**: User can delete/restructure XML node hierarchy

### Enterprise Integration
- **XLIFF-01**: XLIFF/TMX import/export for TMS interoperability
- **COLLAB-01**: Real-time collaborative editing with conflict resolution

### Advanced AI
- **SPELL-01**: Language-specific spell check and grammar checking
- **VOICE-01**: AI voice synthesis for missing audio
- **AUTOGEN-01**: AI image generation for placeholder assets

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full CRUD (create/delete XML nodes) | Schema rules undocumented, QACompiler only reads -- v4.0+ |
| Cloud MT integration | Breaks offline-first competitive moat |
| Real-time collaborative editing | OT/CRDT complexity too high for demo value |
| Voice synthesis (TTS) | CJK quality too poor in open-source |
| AI autocorrection | Qwen3-4B lacks nuance, wrong suggestions erode trust |
| WYSIWYG in-context preview | Requires game engine integration |
| Plugin marketplace | Premature -- core features must stabilize first |
| Drag-and-drop map editing | Map is read-only visualization, not authoring |
| AI image generation via cloud | Contradicts offline-first architecture |
| Spell check / grammar check | CJK support weak, false positives worse than no check |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MOCK-01 | Phase 15 | Complete |
| MOCK-02 | Phase 15 | Complete |
| MOCK-03 | Phase 15 | Complete |
| MOCK-04 | Phase 15 | Complete |
| MOCK-05 | Phase 15 | Complete |
| MOCK-06 | Phase 15 | Complete |
| MOCK-07 | Phase 15 | Complete |
| MOCK-08 | Phase 15 | Complete |
| CAT-01 | Phase 16 | Complete |
| CAT-02 | Phase 16 | Complete |
| CAT-03 | Phase 16 | Complete |
| QA-01 | Phase 16 | Complete |
| QA-02 | Phase 16 | Complete |
| QA-03 | Phase 16 | Complete |
| QA-04 | Phase 16 | Complete |
| QA-05 | Phase 16 | Complete |
| QA-06 | Phase 16 | Complete |
| AISUG-01 | Phase 17 | Complete |
| AISUG-02 | Phase 17 | Complete |
| AISUG-03 | Phase 17 | Complete |
| AISUG-04 | Phase 17 | Complete |
| AISUG-05 | Phase 17 | Complete |
| AINAME-01 | Phase 21 | Complete |
| AINAME-02 | Phase 21 | Complete |
| AINAME-03 | Phase 21 | Complete |
| GDEV-01 | Phase 18 | Complete |
| GDEV-02 | Phase 18 | Complete |
| GDEV-03 | Phase 18 | Complete |
| GDEV-04 | Phase 18 | Complete |
| GDEV-05 | Phase 18 | Complete |
| GDEV-06 | Phase 18 | Complete |
| GDEV-07 | Phase 18 | Complete |
| CODEX-01 | Phase 19 | Complete |
| CODEX-02 | Phase 19 | Complete |
| CODEX-03 | Phase 19 | Complete |
| CODEX-04 | Phase 19 | Complete |
| CODEX-05 | Phase 19 | Complete |
| MAP-01 | Phase 20 | Complete |
| MAP-02 | Phase 20 | Complete |
| MAP-03 | Phase 20 | Complete |
| MAP-04 | Phase 20 | Complete |
| MAP-05 | Phase 20 | Complete |
| PLACEHOLDER-01 | Phase 21 | Complete |
| PLACEHOLDER-02 | Phase 21 | Complete |
| PLACEHOLDER-03 | Phase 21 | Complete |

**Coverage:**
- v3.0 requirements: 45 total
- Mapped to phases: 45/45
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after roadmap creation*
