# Roadmap: LocaNext

## Milestones

- v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15
- v2.0 Real Data + Dual Platform (Phases 07-14) -- SHIPPED 2026-03-15
- v3.0 Game Dev Platform + AI Intelligence (Phases 15-21) -- IN PROGRESS

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

### v3.0 Game Dev Platform + AI Intelligence (In Progress)

**Milestone Goal:** Build a full Game Dev authoring experience with AI-powered suggestions, interactive Codex encyclopedia, QA pipeline integration, and category clustering -- all powered by a comprehensive mock gamedata universe for E2E testing.

- [ ] **Phase 15: Mock Gamedata Universe** - Generate realistic XML gamedata matching real staticinfo patterns with cross-references, media refs, and round-trip validation
- [ ] **Phase 16: Category Clustering + QA Pipeline** - Auto-classify content types and integrate Term Check + Line Check QA inline in the editor
- [ ] **Phase 17: AI Translation Suggestions** - Ranked translation suggestions via Qwen3 with confidence scores and click-to-accept
- [ ] **Phase 18: Game Dev Grid + File Explorer** - VS Code-like file explorer with hierarchical XML entity editing grid
- [ ] **Phase 19: Game World Codex** - Interactive encyclopedia with character/item pages, semantic search, inline media
- [ ] **Phase 20: Interactive World Map** - Pan/zoom SVG map with positioned region nodes linked to Codex pages
- [ ] **Phase 21: AI Naming Coherence + Placeholders** - Naming pattern suggestions and auto-generated placeholder assets for missing media

## Phase Details

### Phase 15: Mock Gamedata Universe
**Goal**: Every Game Dev feature has realistic XML data to parse, display, search, and merge against -- no feature builds against empty state
**Depends on**: Nothing (v3.0 foundation -- all subsequent phases depend on this)
**Requirements**: MOCK-01, MOCK-02, MOCK-03, MOCK-04, MOCK-05, MOCK-06, MOCK-07, MOCK-08
**Success Criteria** (what must be TRUE):
  1. Opening the mock gamedata folder in LocaNext produces parseable XML across all entity types (items, characters, regions, skills, gimmicks)
  2. Cross-reference chains resolve correctly (clicking a KnowledgeKey link finds the referenced entity)
  3. Mock language data files load in Translator mode with Korean source text and matching StringIDs
  4. Round-trip validation passes (generate -> parse -> merge -> export -> re-parse produces identical data)
  5. Mock universe contains sufficient volume for meaningful grid performance testing (100+ items, 30+ characters, 10+ regions)
**Plans**: 2 plans

Plans:
- [ ] 15-01-PLAN.md — Generator script + StaticInfo XML + binary stubs + cross-ref/volume/structure tests
- [ ] 15-02-PLAN.md — Language data + EXPORT indexes + round-trip validation tests

### Phase 16: Category Clustering + QA Pipeline
**Goal**: Translators see content categories at a glance and get instant QA feedback on glossary consistency and translation uniformity without leaving the editor
**Depends on**: Phase 15 (mock data for Game Dev mode testing; Translator mode works independently)
**Requirements**: CAT-01, CAT-02, CAT-03, QA-01, QA-02, QA-03, QA-04, QA-05, QA-06
**Success Criteria** (what must be TRUE):
  1. Every row in the translation grid shows its auto-detected content category (Item, Quest, UI, System, Character, Skill, Region, Gimmick)
  2. User can filter the grid by one or more categories to focus on specific content types
  3. QA Term Check flags glossary terms present in source but missing in target translation inline in the editor
  4. QA Line Check flags same source text translated inconsistently across the project
  5. User can dismiss individual QA findings to prevent false positive fatigue
**Plans**: 2 plans

Plans:
- [ ] 16-01: TBD
- [ ] 16-02: TBD
- [ ] 16-03: TBD

### Phase 17: AI Translation Suggestions
**Goal**: Translators get ranked AI-powered translation suggestions for the selected segment that they can accept with one click -- never auto-replacing
**Depends on**: Phase 15 (entity embeddings enrich context), Phase 16 (not strict -- can run in parallel)
**Requirements**: AISUG-01, AISUG-02, AISUG-03, AISUG-04, AISUG-05
**Success Criteria** (what must be TRUE):
  1. Selecting a segment in the translation grid shows ranked AI suggestions in a right-side panel with confidence scores
  2. Clicking a suggestion applies it to the translation field without auto-replacing any existing content
  3. Suggestions consider entity context (type, parent hierarchy, surrounding segments) for relevance
  4. When Qwen3/Ollama is unavailable, the panel shows "AI unavailable" gracefully without crashes or spinners
**Plans**: 2 plans

Plans:
- [ ] 17-01: TBD
- [ ] 17-02: TBD

### Phase 18: Game Dev Grid + File Explorer
**Goal**: Game developers can browse the gamedata folder structure and edit entity attributes inline in a hierarchical grid that handles large files smoothly
**Depends on**: Phase 15 (mock data to browse), Phase 16 (QA checks available on edit), Phase 17 (AI suggestions available on edit)
**Requirements**: GDEV-01, GDEV-02, GDEV-03, GDEV-04, GDEV-05, GDEV-06, GDEV-07
**Success Criteria** (what must be TRUE):
  1. File explorer panel displays gamedata folder structure matching real gamedata paths with expand/collapse
  2. Clicking a file in the explorer loads its XML entities in a hierarchical grid with parent-child nesting visualized
  3. User can edit Name, Desc, and text attributes inline and changes save back with proper XML encoding (br-tag preservation)
  4. Grid shows appropriate metadata columns per data type (Key, StrKey, KnowledgeKey, etc.)
  5. Grid handles large files (1000+ entities) smoothly via virtual scrolling
**Plans**: 2 plans

Plans:
- [ ] 18-01: TBD
- [ ] 18-02: TBD
- [ ] 18-03: TBD

### Phase 19: Game World Codex
**Goal**: Both translators and game devs can browse an interactive encyclopedia of characters, items, and entities with images, audio, cross-references, and semantic search
**Depends on**: Phase 15 (entity data), Phase 18 (grid infrastructure for navigation)
**Requirements**: CODEX-01, CODEX-02, CODEX-03, CODEX-04, CODEX-05
**Success Criteria** (what must be TRUE):
  1. Character encyclopedia page shows name, image, description, race, job, quest appearances, and related entities
  2. Item encyclopedia page shows name, image, description, category, stats, and similar items via semantic search
  3. Codex is searchable via semantic search (Model2Vec + FAISS) across all entity types with relevant results
  4. Codex pages display inline DDS->PNG images and WEM->WAV audio playback when available
**Plans**: 2 plans

Plans:
- [ ] 19-01: TBD
- [ ] 19-02: TBD

### Phase 20: Interactive World Map
**Goal**: Users can visually explore the game world via a pan/zoom map with positioned region nodes that link to Codex pages
**Depends on**: Phase 15 (region position data), Phase 19 (Codex pages for click-through)
**Requirements**: MAP-01, MAP-02, MAP-03, MAP-04, MAP-05
**Success Criteria** (what must be TRUE):
  1. Map renders region nodes at correct WorldPosition coordinates from XML data
  2. Hovering a map node shows tooltip with region name, description, and key NPCs
  3. Clicking a map node opens a detail panel linking to Codex pages for characters, items, and quests in that region
  4. Route connections between region nodes are visualized from NodeWaypointInfo data
  5. Map supports pan and zoom interaction for navigating the full world
**Plans**: 2 plans

Plans:
- [ ] 20-01: TBD
- [ ] 20-02: TBD

### Phase 21: AI Naming Coherence + Placeholders
**Goal**: Game devs get naming pattern suggestions when editing entity names, and all missing media shows styled placeholders instead of broken/blank states
**Depends on**: Phase 15 (entity index), Phase 17 (AI pipeline), Phase 19 (Codex displays placeholders)
**Requirements**: AINAME-01, AINAME-02, AINAME-03, PLACEHOLDER-01, PLACEHOLDER-02, PLACEHOLDER-03
**Success Criteria** (what must be TRUE):
  1. Editing a Name field in Game Dev mode shows similar existing entity names via embedding search
  2. AI suggests coherent naming alternatives based on existing patterns via Qwen3 in a non-blocking panel
  3. Missing images display a styled SVG placeholder with entity name and category-specific icon
  4. Missing audio displays a waveform SVG placeholder with entity name and "[No Audio]" label
**Plans**: 2 plans

Plans:
- [ ] 21-01: TBD
- [ ] 21-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 15 -> 16 -> 17 -> 18 -> 19 -> 20 -> 21
(Phases 16 and 17 can execute in parallel -- they are independent)

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
| 15. Mock Gamedata Universe | 1/2 | In Progress|  | - |
| 16. Category Clustering + QA Pipeline | v3.0 | 0/? | Not started | - |
| 17. AI Translation Suggestions | v3.0 | 0/? | Not started | - |
| 18. Game Dev Grid + File Explorer | v3.0 | 0/? | Not started | - |
| 19. Game World Codex | v3.0 | 0/? | Not started | - |
| 20. Interactive World Map | v3.0 | 0/? | Not started | - |
| 21. AI Naming Coherence + Placeholders | v3.0 | 0/? | Not started | - |
