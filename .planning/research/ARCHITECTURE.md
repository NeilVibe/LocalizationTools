# Architecture Patterns

**Domain:** Game Dev Platform + AI Intelligence (v3.0 milestone for LocaNext)
**Researched:** 2026-03-15
**Confidence:** HIGH (all integration points verified against existing v2.0 source code)

## Recommended Architecture

v3.0 extends the existing Electron + FastAPI + Svelte 5 architecture. No new infrastructure needed -- all features integrate through new services, routes, and components that follow established v2.0 patterns.

### High-Level Integration Map

```
EXISTING (v2.0)                          NEW (v3.0)
===========================              ===========================

server/tools/ldm/services/              server/tools/ldm/services/
  xml_parsing.py         ─────────────→   gamedata_universe.py (mock data gen)
  ai_summary_service.py  ─────────────→   ai_suggestion_service.py (ranked suggestions)
  glossary_service.py    ─────────────→   qa_pipeline_service.py (QuickCheck integration)
  category_mapper.py     ─────────────→   category_cluster_service.py (StringID clustering)
  mapdata_service.py     ─────────────→   placeholder_generator.py (auto-gen missing assets)
  context_service.py     ─────────────→   codex_service.py (entity encyclopedia)
  media_converter.py     ─────────────→   (extends for placeholder flag)

server/tools/ldm/routes/                server/tools/ldm/routes/
  context.py             ─────────────→   codex.py (map, character, item endpoints)
  qa.py                  ─────────────→   qa_pipeline.py (term check + line check)
  mapdata.py                              ai_suggestions.py (ranked translation/naming)
                                          gamedata.py (mock gamedata management)

locaNext/src/lib/components/            locaNext/src/lib/components/
  ldm/VirtualGrid.svelte ─────────────→   ldm/GameDevGrid.svelte (new component)
  ldm/RightPanel.svelte  ─────────────→   (new "AI Suggestions" tab added)
  ldm/QAFooter.svelte    ─────────────→   (extended with QuickCheck results)
  ldm/ContextTab.svelte  ─────────────→   (extended with richer codex links)
  pages/GridPage.svelte  ─────────────→   pages/CodexPage.svelte (new page)
                                          ldm/codex/ (MapView, CharacterCard, ItemCard)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **gamedata_universe.py** (NEW service) | Generate/manage mock gamedata folder structure mimicking real staticinfo XML | XMLParsingEngine (reuse parsing), GlossaryService (entity extraction) |
| **ai_suggestion_service.py** (NEW service) | Generate ranked translation/naming suggestions via Qwen3 + Model2Vec | AISummaryService (shared Ollama endpoint), FAISS index (embeddings), GlossaryService (entity context) |
| **qa_pipeline_service.py** (NEW service) | Run QuickCheck Term Check + Line Check on grid rows | Aho-Corasick automaton (existing GlossaryService), QAResultRepository |
| **category_cluster_service.py** (NEW service) | Classify StringIDs into categories (Item/Quest/UI/Skill/etc) | TwoTierCategoryMapper (extends existing), XMLParsingEngine (file path info) |
| **codex_service.py** (NEW service) | Aggregate entity data for Codex encyclopedia views | GlossaryService (entity index), MapDataService (media), ContextService, Model2Vec+FAISS (similarity) |
| **placeholder_generator.py** (NEW service) | Generate placeholder images/audio for missing assets | MediaConverter (format pipeline), Pillow (image gen), optionally piper-tts |
| **GameDevGrid.svelte** (NEW component) | Hierarchical XML authoring grid for game devs -- tree view + editable attributes | VirtualGrid (shared virtual scrolling logic), RightPanel (AI suggestions tab) |
| **CodexPage.svelte** (NEW page) | Codex encyclopedia page with map, character browser, item browser | Navigation store (new page type), codex API module |
| **MapView.svelte** (NEW component) | Interactive world map with clickable regions | SVG + d3-zoom (transform math only, Svelte owns DOM), codex API |
| **CharacterCard.svelte** (NEW component) | Character detail view with image, metadata, related strings | ImageTab (reuse media display), codex API |
| **ItemCard.svelte** (NEW component) | Item detail view with image, stats, similar items | SemanticResults (reuse similarity display), codex API |

### Data Flow

#### 1. Mock Gamedata Universe

```
Phase start: Generate mock data
  gamedata_universe.py
    ├── Uses QACompiler generator patterns (Item, Character, Region, Skill)
    │     Source: RFC/NewScripts/QACompilerNEW/generators/
    │     Patterns: item.py, character.py, region.py, skill.py
    ├── Creates folder structure: mock_gamedata/StaticInfo/{characterinfo,iteminfo,regioninfo,...}
    ├── Generates realistic XML files with StringIDs, Names, Descs, attributes
    ├── Generates matching stringtable/loc/ files (LocStr format for translator mode)
    ├── Creates mock texture paths and audio event mappings
    └── Outputs: folder on disk + index in GlossaryService + entries in MapDataService

On app start (lazy):
  server/main.py → gamedata_universe.ensure_mock_data()
    → GlossaryService.build_from_entity_names(extracted_entities)
    → MapDataService.index_from_mock(mock_media_mappings)
```

#### 2. Game Dev Grid (read + edit XML staticinfo)

```
User opens staticinfo file in File Explorer:
  FilesPage → fileType detection = "gamedev" → navigates to GridPage

GridPage renders GameDevGrid (not VirtualGrid) when fileType === "gamedev":
  GameDevGrid.svelte
    ├── Fetches parsed XML tree: GET /api/ldm/gamedata/tree/{file_id}
    │     → XMLParsingEngine.parse_full_tree() (NEW method, returns nested structure)
    ├── Renders hierarchical tree view (parent nodes + child nodes)
    ├── Each node: Name, Desc, attributes as editable cells
    ├── On edit: PATCH /api/ldm/rows/{id} (reuse existing row update)
    │     → AI suggestion request triggered in parallel
    │     → QA pipeline check triggered in parallel
    └── On save: POST /api/ldm/gamedata/save-xml/{file_id}

Right panel shows:
  AI Suggestions tab (new) → ranked naming/translation suggestions
  Image tab (existing) → entity image from mapdata
  Audio tab (existing) → entity audio from mapdata
  Context tab (existing) → AI summary + entity links
```

#### 3. AI Suggestions Pipeline

```
User selects a row (translator or game dev mode):
  Grid row selection
    → POST /api/ldm/ai/suggestions
        {string_id, source_text, entity_type, file_path, mode: "translate"|"naming"}
    → ai_suggestion_service.py:
        1. Model2Vec: find top-K similar entities via existing FAISS index
        2. Aho-Corasick: detect entities in source text via existing GlossaryService
        3. Qwen3: generate ranked suggestions with confidence scores
           Prompt includes: similar entity names, parent context, game genre
        4. Return: [{suggestion, confidence, reasoning, source_type}]
    → RightPanel "AI Suggestions" tab renders ranked list
    → User clicks suggestion → populates grid cell (NEVER auto-replace)
```

#### 4. QA Pipeline (QuickCheck Integration)

```
Two triggers:
  A) Real-time (on cell edit):
    Grid cell blur → POST /api/ldm/qa/pipeline-check
      {row_id, source, target, glossary_terms}
    → qa_pipeline_service.py:
        1. Term Check: Aho-Corasick glossary scan (source has term, target missing)
             Port from: RFC/NewScripts/QuickCheck/core/term_check.py
        2. Line Check: Same source → different translations detected
             Port from: RFC/NewScripts/QuickCheck/core/line_check.py
        3. Return: [{check_type, severity, message, term, positions}]
    → QAFooter updates with new issues (existing component, extended check_types)

  B) Batch (full file):
    File-level "Run QA Pipeline" button → POST /api/ldm/qa/pipeline-file/{file_id}
    → Iterates all rows, runs both checks, stores results in QAResultRepository
    → QAFooter shows aggregate results with existing filtering
```

#### 5. Codex (Interactive Encyclopedia)

```
User navigates to Codex page:
  Navigation store: currentPage = 'codex'
  CodexPage.svelte renders three sub-views (tabs):

  A) World Map:
    GET /api/ldm/codex/regions
      → codex_service.py: aggregate Region entities + WorldPosition from staticinfo
         Source patterns: QACompiler Region generator knows all locations
      → Returns: [{name, description, position: {x, y}, connected_regions, npcs, quests}]
    MapView.svelte renders positioned nodes on SVG
      → d3-zoom handles pan/zoom transforms (math only, Svelte renders SVG nodes)
    Click region → detail panel with full context

  B) Character Browser:
    GET /api/ldm/codex/characters?search=&page=
      → codex_service.py: aggregate Character entities with metadata
      → Returns: [{name, image_url, gender, race, job, quest_appearances}]
    Search: GET /api/ldm/codex/characters/search?q= (Model2Vec semantic search)
    Click character → CharacterCard with full detail

  C) Item Browser:
    GET /api/ldm/codex/items?search=&category=&page=
      → codex_service.py: aggregate Item entities with Model2Vec similarity
      → Returns: [{name, image_url, description, category, similar_items}]
    Click item → ItemCard with detail + similar items list
```

#### 6. Category Clustering

```
On file parse (automatic):
  XMLParsingEngine.parse() → rows with file_path metadata
    → category_cluster_service.classify_rows(rows)
      → TwoTierCategoryMapper (existing, extended with more keywords)
      → Returns: {row_id: category_label} mapping
    → Stored as column in grid data (category column)
    → VirtualGrid/GameDevGrid shows category as filterable Tag column
    → Filter bar gets "Category" dropdown (Item, Quest, Skill, Region, UI, System, etc.)
```

#### 7. Auto-Generated Placeholders

```
When media requested but missing:
  ImageTab/AudioTab → GET /api/ldm/mapdata/image/{strkey}
    → MapDataService: lookup returns has_image=false
    → placeholder_generator.py:
        Image: Generate via Pillow (text overlay on colored background by category)
               OR Gemini API via nano-banana skill (if available, non-blocking)
        Audio: Generate silence placeholder with TTS metadata
               OR local TTS via piper (if available)
    → Cache generated placeholder
    → Return with is_placeholder=true flag
  UI shows placeholder with distinct styling (dashed border, watermark)
```

## Patterns to Follow

### Pattern 1: Service Singleton with Lazy Init
**What:** All new services follow GlossaryService/MapDataService singleton pattern.
**When:** Every new service in `server/tools/ldm/services/`.
**Example:**
```python
_instance: Optional[CodexService] = None

def get_codex_service() -> CodexService:
    global _instance
    if _instance is None:
        _instance = CodexService()
    return _instance
```

### Pattern 2: Route Module Registration
**What:** New routes follow the established `router.py` aggregation pattern.
**When:** Every new route file.
**Example:**
```python
# In router.py, add:
from .routes.codex import router as codex_router
from .routes.ai_suggestions import router as ai_suggestions_router
from .routes.qa_pipeline import router as qa_pipeline_router
from .routes.gamedata import router as gamedata_router

router.include_router(codex_router)
router.include_router(ai_suggestions_router)
router.include_router(qa_pipeline_router)
router.include_router(gamedata_router)
```

### Pattern 3: Navigation Page Registration
**What:** New pages register in navigation store and render in LDM.svelte.
**When:** Adding CodexPage.
**Example:**
```javascript
// navigation.js - add 'codex' to page types:
// currentPage: 'files' | 'tm' | 'grid' | 'tm-entries' | 'codex'

// LDM.svelte - add codex page rendering:
// {:else if $currentPage === 'codex'}
//   <CodexPage />
```

### Pattern 4: Optimistic UI for Grid Edits
**What:** Grid cell edits update UI immediately, sync to server in background.
**When:** All GameDevGrid cell edits, AI suggestion acceptance.
**Example:**
```svelte
function acceptSuggestion(rowId, field, value) {
    rows[rowIndex][field] = value;  // Optimistic update
    fetch(`${API_BASE}/api/ldm/rows/${rowId}`, {
        method: 'PATCH',
        body: JSON.stringify({ [field]: value }),
        headers: getAuthHeaders()
    }).catch(() => {
        rows[rowIndex][field] = previousValue;  // Revert on failure
    });
}
```

### Pattern 5: Parallel Non-Blocking AI/QA Requests
**What:** AI suggestions and QA checks fire in parallel on row selection, never block the grid.
**When:** Row selection, cell edit blur.
**Example:**
```svelte
async function onRowSelect(row) {
    selectedRow = row;
    // Fire in parallel, never await sequentially
    fetchAISuggestions(row);    // updates AI Suggestions tab
    fetchQAPipelineCheck(row); // updates QAFooter
    fetchMediaContext(row);    // updates Image/Audio tabs
}
```

### Pattern 6: Port-and-Adapt from NewScripts
**What:** Copy core logic from NewScripts, adapt to FastAPI service interface.
**When:** Any feature porting proven NewScripts code (QuickCheck, LDE).
**Key changes when porting:**
- Replace `print/logging` with `loguru`
- Replace file-based I/O with in-memory data structures
- Add `async` to service methods
- Use existing repository pattern for data access
- Keep the algorithmic logic identical
- NEVER import NewScripts modules directly (creates coupling)

### Pattern 7: SVG + d3-zoom (World Map)
**What:** Svelte owns the DOM (SVG elements via `{#each}`). d3-zoom owns only the transform math.
**When:** Interactive visualizations with pan/zoom.
**Key principle:** Never let d3 touch the DOM. Svelte renders, d3 calculates.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate AI Service Per Feature
**What:** Creating ai_translation_service.py, ai_naming_service.py, ai_quality_service.py separately.
**Why bad:** All share the same Ollama endpoint, same timeout handling, same cache pattern. Duplication of connection management and fallback logic.
**Instead:** Single `ai_suggestion_service.py` with mode parameter ("translate", "naming", "quality"). Shared Ollama client, shared cache, shared fallback. Extends existing `AISummaryService` pattern.

### Anti-Pattern 2: New Grid Component from Scratch
**What:** Building GameDevGrid.svelte as completely independent from VirtualGrid.
**Why bad:** Virtual scrolling, cell editing, presence bar, column resizing, search/filter -- all exist in VirtualGrid (4048+ lines). Duplicating even 20% creates maintenance nightmare.
**Instead:** GameDevGrid wraps/extends VirtualGrid's core virtual scrolling and cell editing. Adds tree hierarchy rendering on top. Consider extracting shared scrolling logic into a base module that both components use.

### Anti-Pattern 3: Codex as Separate App
**What:** Adding Codex as a new app in `+page.svelte` alongside XLSTransfer/QuickSearch/LDM.
**Why bad:** Codex is part of the LDM experience -- it shows data from the same parsed files. Separate app breaks navigation flow and context.
**Instead:** Codex is a page within LDM, accessible via navigation store (`currentPage = 'codex'`). Same pattern as `files`, `grid`, `tm` pages.

### Anti-Pattern 4: Loading All Mock Data into Memory at Startup
**What:** Parsing all mock gamedata XML into memory eagerly.
**Why bad:** Real game data has thousands of files. Pattern should scale.
**Instead:** Index entity names + metadata at startup (lightweight Aho-Corasick + dict). Load full XML tree only when user opens a specific file. Cache parsed trees with LRU eviction.

### Anti-Pattern 5: QA Pipeline as Background Task for Single Rows
**What:** Running QuickCheck QA as a background task that sends results via WebSocket.
**Why bad:** For single-row checks, latency matters -- user wants instant feedback (<50ms).
**Instead:** Single-row QA is synchronous (fast, <50ms with Aho-Corasick). Full-file QA uses BackgroundTask with progress tracking (existing TrackedOperation pattern).

### Anti-Pattern 6: d3 DOM Manipulation in Svelte
**What:** Using `d3.select().append()` to create SVG elements in the World Map.
**Why bad:** Fights Svelte's reactivity. Creates elements outside Svelte's awareness.
**Instead:** Use d3 only for math (scales, transforms, forces). Svelte renders with `{#each}`.

### Anti-Pattern 7: AI Auto-Apply
**What:** Having AI suggestions automatically modify translations or names.
**Why bad:** Users lose trust if AI changes their work without consent.
**Instead:** Always show suggestions in a panel. User explicitly clicks to apply. This is a core design principle for v3.0.

### Anti-Pattern 8: Generating Mock Data Without Round-Trip Testing
**What:** Building the mock generator without testing XMLParsingEngine can read the output.
**Why bad:** Subtle XML formatting issues (attribute order, namespace, encoding) break parsing silently.
**Instead:** Write round-trip tests: generate XML -> parse with XMLParsingEngine -> verify all fields extracted correctly.

## New vs Modified Components (Explicit)

### Backend -- NEW Files (12 files)

| File | Type | Purpose |
|------|------|---------|
| `services/gamedata_universe.py` | Service | Mock gamedata generation and management |
| `services/ai_suggestion_service.py` | Service | Ranked AI suggestions (translate + naming modes) |
| `services/qa_pipeline_service.py` | Service | QuickCheck Term Check + Line Check integration |
| `services/category_cluster_service.py` | Service | StringID category classification |
| `services/codex_service.py` | Service | Entity aggregation for Codex views |
| `services/placeholder_generator.py` | Service | Auto-generate missing image/audio placeholders |
| `routes/codex.py` | Route | Codex API endpoints (regions, characters, items, search) |
| `routes/ai_suggestions.py` | Route | AI suggestion endpoints |
| `routes/qa_pipeline.py` | Route | Extended QA pipeline endpoints (term + line check) |
| `routes/gamedata.py` | Route | Mock gamedata management + XML tree endpoints |
| `schemas/codex.py` | Schema | Pydantic models for Codex responses |
| `schemas/ai_suggestions.py` | Schema | Pydantic models for AI suggestion responses |

### Backend -- MODIFIED Files (8 files)

| File | Modification |
|------|-------------|
| `services/xml_parsing.py` | Add `parse_full_tree()` method returning hierarchical node structure |
| `services/category_mapper.py` | Extend TwoTierCategoryMapper with more keywords + sub-categories |
| `services/media_converter.py` | Add `is_placeholder` flag to response, delegate to placeholder_generator |
| `services/mapdata_service.py` | Support mock media mappings, `is_placeholder` flag in ImageContext/AudioContext |
| `services/glossary_service.py` | Index mock gamedata entities at startup via gamedata_universe |
| `services/context_service.py` | Add codex link generation to entity context responses |
| `routes/qa.py` | Import and delegate to qa_pipeline_service for extended check types |
| `router.py` | Register 4 new route modules (codex, ai_suggestions, qa_pipeline, gamedata) |

### Frontend -- NEW Files (11 files)

| File | Type | Purpose |
|------|------|---------|
| `components/ldm/GameDevGrid.svelte` | Component | Hierarchical XML authoring grid for game devs |
| `components/ldm/AISuggestionsTab.svelte` | Component | Ranked AI suggestions panel tab in RightPanel |
| `components/ldm/CategoryFilter.svelte` | Component | Category dropdown filter for grid toolbar |
| `components/pages/CodexPage.svelte` | Page | Codex encyclopedia page with sub-views |
| `components/ldm/codex/MapView.svelte` | Component | Interactive world map (SVG + d3-zoom) |
| `components/ldm/codex/CharacterCard.svelte` | Component | Character detail view |
| `components/ldm/codex/ItemCard.svelte` | Component | Item detail view with similarity |
| `components/ldm/codex/EntitySearch.svelte` | Component | Semantic search across all entities |
| `stores/codex.js` | Store | Codex state (selected entity, search, filters) |
| `api/codex.js` | API | Codex API client functions |
| `api/ai_suggestions.js` | API | AI suggestions API client |

### Frontend -- MODIFIED Files (6 files)

| File | Modification |
|------|-------------|
| `components/ldm/RightPanel.svelte` | Add 5th tab "AI Suggestions" with AISuggestionsTab |
| `components/ldm/QAFooter.svelte` | Support new check_types (`term_check`, `line_check` from QuickCheck) |
| `components/ldm/VirtualGrid.svelte` | Add category column, category filter integration in toolbar |
| `components/pages/GridPage.svelte` | Conditionally render GameDevGrid for `fileType === 'gamedev'` |
| `stores/navigation.js` | Add `'codex'` page type to currentPage |
| `components/apps/LDM.svelte` | Add CodexPage rendering + Codex nav button in sidebar |

### Mock Data -- NEW Files

| Path | Purpose |
|------|---------|
| `mock_gamedata/` (folder tree) | Entire mock gamedata universe under server data |
| `mock_gamedata/StaticInfo/characterinfo/*.xml` | Mock character XML files |
| `mock_gamedata/StaticInfo/iteminfo/*.xml` | Mock item XML files |
| `mock_gamedata/StaticInfo/regioninfo/*.xml` | Mock region XML files (with WorldPosition) |
| `mock_gamedata/StaticInfo/skillinfo/*.xml` | Mock skill XML files |
| `mock_gamedata/stringtable/loc/*.xml` | Mock LocStr translation files |
| `mock_gamedata/texture/` | Mock texture references (placeholder PNGs) |
| `mock_gamedata/sound/` | Mock audio references (placeholder WAVs) |

## Suggested Build Order (Dependency-Driven)

```
Phase 1: Mock Gamedata Universe (FOUNDATION -- everything depends on this)
  ├── NEW: gamedata_universe.py, routes/gamedata.py
  ├── MOD: glossary_service.py, mapdata_service.py
  └── Output: mock_gamedata/ folder with realistic XML + media mappings

Phase 2: Category Clustering (LOW RISK, HIGH VALUE, needs Phase 1 data)
  ├── NEW: category_cluster_service.py, CategoryFilter.svelte
  ├── MOD: category_mapper.py, VirtualGrid.svelte
  └── Output: category column visible in existing grid

Phase 3: QA Pipeline Integration (PROVEN LOGIC from QuickCheck)
  ├── NEW: qa_pipeline_service.py, routes/qa_pipeline.py
  ├── MOD: qa.py, QAFooter.svelte
  ├── Port from: QuickCheck/core/term_check.py, line_check.py
  └── Output: term/line check active in QAFooter for both modes

Phase 4: AI Suggestions (CORE AI, needs Phase 1 for embeddings)
  ├── NEW: ai_suggestion_service.py, routes/ai_suggestions.py, AISuggestionsTab.svelte
  ├── MOD: RightPanel.svelte (add 5th tab)
  ├── Uses: existing FAISS + Model2Vec + Qwen3 via Ollama
  └── Output: ranked suggestions in right panel for any selected row

Phase 5: Game Dev Grid (HIGHEST COMPLEXITY, benefits from Phases 2-4)
  ├── NEW: GameDevGrid.svelte
  ├── MOD: xml_parsing.py (parse_full_tree), GridPage.svelte
  ├── Integrates: AI suggestions, QA pipeline, category filtering
  └── Output: hierarchical XML editor for staticinfo files

Phase 6: Codex (SHOWCASE, needs Phase 1 entities + Phase 4 search)
  ├── NEW: codex_service.py, routes/codex.py, CodexPage.svelte
  ├── NEW: codex/MapView.svelte, CharacterCard.svelte, ItemCard.svelte, EntitySearch.svelte
  ├── NEW: stores/codex.js, api/codex.js
  ├── MOD: navigation.js, LDM.svelte, context_service.py
  └── Output: interactive encyclopedia with map, character browser, item browser

Phase 7: Auto-Generated Placeholders (POLISH, last)
  ├── NEW: placeholder_generator.py
  ├── MOD: media_converter.py, mapdata_service.py, ImageTab.svelte, AudioTab.svelte
  └── Output: placeholder images/audio for missing assets with distinct UI styling
```

**Phase ordering rationale:**
- Phase 1 (Mock Data) is the foundation -- every other feature needs realistic data to test and demo. Without it, nothing works end-to-end.
- Phases 2-4 (Clustering, QA, AI) are independent of each other but all need Phase 1. They enhance the EXISTING grid before building the new one, providing immediate demo value.
- Phase 5 (Game Dev Grid) is the most complex UI component. Building after QA and AI means it integrates them from day one rather than retrofitting.
- Phase 6 (Codex) is the visual showcase. Depends on all entity data being indexed (Phase 1) and semantic search working (Phase 4).
- Phase 7 (Placeholders) is polish that makes the demo complete but has lowest priority.

**Parallelization opportunity:** Phases 2, 3, and 4 are independent and can be built in parallel by separate agents/sessions.

## Scalability Considerations

| Concern | Mock Data (100s of entities) | Real Data (10K entities) | Full Scale (100K+ entities) |
|---------|-----|-----|-----|
| Entity Index | In-memory dict, instant | Aho-Corasick automaton (existing), ~10MB | Same AC, ~50MB, still O(n) text scan |
| FAISS Search | Flat index, <10ms | IVF index, <50ms | IVF with nprobe tuning, <100ms |
| AI Suggestions | Single Qwen3 call, ~2s | Same, context window limits apply | Queue + cache, batch similar requests |
| Codex Load | All entities in memory | Paginated API, lazy load details | Paginated + search index |
| XML Tree Parse | Single file <100ms | Single file <100ms (same) | File-level, no full-corpus parse needed |
| QA Pipeline | Real-time <50ms per row | Same (AC is O(n) on text length) | Same, batch mode for full-file |
| Category Clustering | Instant (keyword match) | Instant (same algorithm) | Instant (no ML, just keyword matching) |
| World Map SVG | Trivial | Use clustering/LOD | Canvas fallback needed |
| Mock Data Gen | <1s | ~10s | ~2min |

For v3.0, all features target the 100-10K entity range. 100K is future enterprise territory.

## Sources

- **Codebase inspection (HIGH confidence):**
  - `server/tools/ldm/services/` -- all 17 existing service files analyzed
  - `server/tools/ldm/routes/` -- all 22 existing route files analyzed
  - `server/tools/ldm/router.py` -- route registration pattern (99 lines)
  - `locaNext/src/lib/components/ldm/` -- all 25 component files listed
  - `locaNext/src/lib/stores/navigation.js` -- page types, navigation actions
  - `locaNext/src/lib/stores/ldm.js` -- WebSocket state, cell updates
  - `locaNext/src/lib/components/pages/` -- GridPage, FilesPage, TMPage structure
  - `locaNext/src/routes/+page.svelte` -- app routing pattern (LDM as default)
  - `RFC/NewScripts/QACompilerNEW/generators/` -- 12 generator files for staticinfo patterns
- **Project context:**
  - `.planning/PROJECT.md` -- v2.0 shipped state, v3.0 scope
  - `.planning/DEFERRED_IDEAS.md` -- detailed feature specs with tech stack summary
