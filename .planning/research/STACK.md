# Technology Stack

**Project:** LocaNext v3.0 -- Game Dev Platform + AI Intelligence
**Researched:** 2026-03-15
**Scope:** NEW additions only. Existing validated stack is unchanged.

## Existing Stack (DO NOT RE-RESEARCH)

Already validated and shipping in v2.0:
- Electron + Svelte 5 (Runes) + FastAPI + SQLite/PostgreSQL
- FAISS + Model2Vec for semantic search
- Qwen3-4B via Ollama (httpx async) for AI summaries
- lxml for XML parsing (XMLParsingEngine)
- Aho-Corasick (ahocorasick) for entity detection
- Pillow for DDS->PNG, vgmstream-cli for WEM->WAV
- xlsxwriter for writing, openpyxl for reading Excel
- Carbon Components Svelte for UI
- socket.io-client for WebSocket sync

---

## Stack Additions for v3.0

### Frontend: Interactive World Map

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| d3-zoom | ^3.0.0 | Pan/zoom transforms for SVG canvas | Mature, battle-tested, works with raw SVG. No need for d3-geo (this is a fantasy game map, not geographic). Svelte 5 manages the DOM, d3-zoom handles only the math/gestures. |
| d3-force | ^3.0.0 | Force-directed node layout fallback | For auto-positioning nodes when WorldPosition data is missing or sparse. Optional -- only if manual positions are incomplete. |

**Why NOT full D3.js:** Import only d3-zoom and d3-force (tree-shakeable). Full d3 bundle is 290KB+ and we only need transform math + force simulation. Svelte handles all DOM rendering.

**Why NOT svelte-konva / Konva:** Canvas-based rendering loses SVG advantages (CSS styling, accessibility, DOM events on individual nodes). The world map has ~50-200 nodes, not thousands -- SVG performs fine at this scale. Konva adds 150KB for capabilities we do not need.

**Why NOT Leaflet / Mapbox:** These are geographic map libraries. Our world map is a fantasy game map with arbitrary XY positions from XML `WorldPosition` attributes. No tile layers, no lat/lng projections needed.

**Integration pattern:**
```svelte
<script>
  import { zoom, zoomIdentity } from 'd3-zoom';
  import { select } from 'd3-selection';

  let svgElement = $state(null);
  let transform = $state(zoomIdentity);

  $effect(() => {
    if (svgElement) {
      const zoomBehavior = zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => { transform = event.transform; });
      select(svgElement).call(zoomBehavior);
    }
  });
</script>

<svg bind:this={svgElement}>
  <g transform={transform}>
    {#each regions as region (region.strkey)}
      <circle cx={region.x} cy={region.y} r="8" />
    {/each}
  </g>
</svg>
```

**Confidence:** HIGH -- d3-zoom is the standard for SVG pan/zoom. Used by thousands of projects. Svelte 5 integration is straightforward via `$effect` + `bind:this`.

### Frontend: No New UI Framework Additions

| Decision | Rationale |
|----------|-----------|
| No new grid library | Existing virtual grid component handles Game Dev Grid. Add column configs for XML attributes. |
| No tree-view library | Carbon Components has TreeView. Use for XML node hierarchy in Game Dev Grid. |
| No tooltip library | Carbon has Tooltip. Use for map node hover. |
| No modal library | Carbon has Modal/ComposedModal. Use for entity detail panels. |

**Confidence:** HIGH -- Carbon Components already covers all UI primitives needed. Checked existing components in v2.0.

### Backend: Mock Gamedata Generator

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Faker | ^33.0.0 | Generate realistic names, descriptions, text | Battle-tested fake data library. Korean locale support (`ko_KR`). Use for character names, item descriptions, region names. Already in Python ecosystem. |

**Why Faker:** The mock gamedata generator needs realistic-looking Korean and English strings for items, characters, regions, skills. Faker provides locale-aware generation. The XML structure itself comes from studying QACompiler generator patterns (lxml + dataclasses, no new library needed).

**Why NOT random/lorem ipsum:** Mock data must look convincing for executive demos. Faker generates contextually appropriate names and descriptions per locale.

**What we do NOT need:**
- No Jinja2 for XML templates -- lxml `etree.SubElement` is already our pattern from XMLParsingEngine
- No schema validation library -- QACompiler generators already encode the schema knowledge in Python dataclasses
- No JSON Schema -- XML is the format, lxml handles it

**Confidence:** HIGH -- Faker is Python's standard fake data library. 78K+ GitHub stars.

### Backend: AI Translation Suggestions

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| (No new library) | -- | Qwen3 via existing httpx/Ollama | AI suggestions reuse the existing `AISummaryService` pattern. New prompt templates + structured JSON output via Ollama `format` parameter. Zero new dependencies. |

**Why no new library:**
- httpx async already calls Ollama REST API
- Pydantic already defines response schemas
- Model2Vec + FAISS already do semantic similarity for finding similar entities
- The "suggestion" feature is a new **prompt + API endpoint**, not a new library

**New service pattern (extends existing):**
```python
class AITranslationSuggestionService:
    """Reuses Ollama endpoint. New prompt templates for translation suggestions."""
    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen3:4b"

    async def suggest_translations(
        self, source_text: str, context: dict, similar_entries: list[dict]
    ) -> list[dict]:
        # 1. Model2Vec finds similar TM entries (existing FAISS index)
        # 2. Qwen3 generates ranked alternatives with confidence
        # 3. Return structured suggestions
        ...
```

**Confidence:** HIGH -- extends proven v2.0 AI pipeline.

### Backend: QuickCheck QA Integration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| (No new library) | -- | Port QuickCheck core logic | `term_check.py` and `line_check.py` use ahocorasick (already installed). Port the `TermCheck` and `LineCheck` classes into LocaNext server services. |

**What gets ported:**
- `core/term_check.py` -- Dual Aho-Corasick automaton for glossary term consistency
- `core/line_check.py` -- Same-source different-translation inconsistency detection
- `core/preprocessing.py` -- Text normalization for consistency checks

**What does NOT get ported:**
- `core/lang_check.py` -- Language detection (FastText model, 125MB). Not needed in v3.0.
- `core/glossary_extractor.py` -- Already have glossary via TM entries
- Excel writing utilities -- LocaNext has its own export pipeline

**Confidence:** HIGH -- QuickCheck is our own code, patterns are proven, ahocorasick already in requirements.

### Backend: Category Clustering

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| (No new library) | -- | Port LanguageDataExporter clustering | `TwoTierCategoryMapper` and `TierClassifier` from LanguageDataExporter + QuickCheck. Pure Python with path-based heuristics + keyword matching. No ML needed. |

**What gets ported:**
- `clustering/tier_classifier.py` -- STORY vs GAME_DATA tier classification
- `clustering/dialog_clusterer.py` -- Fine-grained dialog categories
- `clustering/gamedata_clusterer.py` -- Keyword-based game data categories
- `exporter/category_mapper.py` -- Combined category mapping (already partially ported to QuickCheck)

**Confidence:** HIGH -- pure Python, no external dependencies, proven logic.

### Backend: Placeholder Image Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Pillow | (already installed) | Generate colored placeholder images | Create simple colored rectangles with entity name text overlay. 64x64 or 128x128 PNG placeholders when DDS textures are missing. |

**Why NOT Nano Banana / Gemini:** The DEFERRED_IDEAS.md mentions Nano Banana for AI-generated images. For v3.0, simple colored placeholders with text are sufficient. AI image generation is a separate future feature -- it requires Gemini API (cloud dependency, violates offline-first constraint). Colored placeholders with category-based colors (blue for characters, green for items, brown for regions) provide enough visual context.

**Confidence:** HIGH -- Pillow is already installed, `ImageDraw.text()` is trivial.

### Backend: Placeholder Audio Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| piper-tts | ^1.4.1 | Local neural TTS for placeholder voice audio | Fast, offline, ONNX-based. ~50MB model files. Generates WAV from text. Supports multiple languages. Runs on CPU (no CUDA needed). |

**Why piper-tts:** The DEFERRED_IDEAS.md calls for AI voice synthesis for missing audio. Piper is the best local/offline TTS engine: no cloud dependency, fast inference, natural-sounding voices, Python package available via pip.

**Why NOT cloud TTS (Google/Azure):** Violates offline-first constraint. LocaNext must work without internet.

**Why NOT espeak/festival:** Low quality robotic voices. Piper uses neural VITS models -- significantly better quality.

**Installation:**
```bash
pip install piper-tts  # ~5MB package
# Download voice model separately (~50MB per voice)
# Korean: ko_KR-kss-low.onnx
# English: en_US-lessac-medium.onnx
```

**IMPORTANT caveat:** piper-tts is OPTIONAL for v3.0. If model download is too heavy for the build pipeline, defer to a later phase. Simple silence WAV files (Pillow/wave module can generate these) are an acceptable MVP fallback.

**Confidence:** MEDIUM -- piper-tts works well standalone but integration with PyInstaller builds needs testing. Model files add to build size.

---

## NPM Additions Summary

```bash
cd locaNext
npm install d3-zoom d3-selection
# Optional, only if force-directed layout needed:
npm install d3-force
```

**Total new frontend weight:** ~45KB minified (d3-zoom + d3-selection). Negligible for an Electron app.

## Pip Additions Summary

```bash
pip install Faker>=33.0.0
# Optional (placeholder audio):
pip install piper-tts>=1.4.0
```

**Total new backend weight:** Faker ~1.5MB. piper-tts ~5MB + ~50MB per voice model.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Map pan/zoom | d3-zoom (math only) | svelte-konva (Canvas) | SVG better for <200 nodes: CSS styling, DOM events, accessibility. Canvas overkill. |
| Map pan/zoom | d3-zoom | @panzoom/panzoom | d3-zoom has better transform API, integrates with d3-force if needed later. |
| Map rendering | Raw SVG + Svelte | Leaflet/Mapbox | Geographic map libs. Our map is fantasy XY positions, not lat/lng. |
| Map rendering | Raw SVG + Svelte | Three.js/WebGL | 3D is unnecessary complexity for a 2D node map. |
| Fake data | Faker | Mimesis | Faker has better Korean locale support, larger community. |
| AI suggestions | Existing Ollama/httpx | ollama Python package | httpx direct is simpler, already proven in v2.0. No new dep. |
| TTS | piper-tts | espeak | Piper sounds natural. espeak sounds robotic. |
| TTS | piper-tts | Coqui TTS | Coqui requires PyTorch (already installed but heavy). Piper uses ONNX -- lighter. |
| Category clustering | Port from LDE | sklearn/ML clustering | Overkill. Path-based heuristics + keywords work perfectly for known XML folder structure. |
| XML mock generation | lxml etree | Jinja2 templates | lxml is already the standard pattern. Templates add abstraction without benefit. |

---

## What We Already Have (No Addition Needed)

| v3.0 Feature | Existing Tech | Notes |
|--------------|---------------|-------|
| Game Dev Grid | Virtual grid component + Carbon | Add new column configurations for XML attributes |
| XML node CRUD | lxml + XMLParsingEngine | Add write-back methods to existing engine |
| Entity detection | Aho-Corasick (ahocorasick) | Already in requirements, used in context panel |
| Semantic search (Codex) | Model2Vec + FAISS | Already operational for TM search. Extend index to game entities. |
| AI summaries (Codex) | Qwen3-4B + httpx + Ollama | Already operational. New prompt templates for Codex context. |
| File explorer tree | Carbon TreeView + existing FilesPage | Extend for gamedata folder structure |
| Image preview | Pillow DDS->PNG pipeline | Already in v2.0 mapdata service |
| Audio preview | vgmstream-cli WEM->WAV | Already in v2.0 mapdata service |
| Export/merge | xlsxwriter/openpyxl + merge engine | Extend for Game Dev mode exports |
| Offline parity | Repository pattern + SQLite/PG | New services follow same pattern |

---

## Integration Points with Existing Stack

### World Map -> Existing Services
- Region XML data parsed by XMLParsingEngine (v2.0)
- `WorldPosition` attribute already extracted by QACompiler region generator
- Entity images served by existing mapdata routes
- Entity details via existing context panel API

### AI Suggestions -> Existing AI Pipeline
- Ollama endpoint reused from AISummaryService
- Model2Vec similarity search reused from TM search
- FAISS index extended to cover game entities (items, characters, regions)
- Structured JSON output via existing Pydantic response models

### QA Pipeline -> Existing Aho-Corasick
- Term Check builds on same ahocorasick automaton as entity detection
- Glossary terms sourced from existing TM entries API
- Results displayed in existing QA panel component

### Mock Data -> Existing XML Patterns
- Generator follows QACompiler generator patterns (base.py, dataclasses)
- XML files written with lxml etree (same as XMLParsingEngine output)
- Folder structure mirrors real staticinfo layout

---

## Sources

- [d3-zoom npm](https://www.npmjs.com/package/d3-zoom) -- SVG pan/zoom transforms
- [d3-force npm](https://www.npmjs.com/package/d3-force) -- Force-directed layout
- [Faker PyPI](https://pypi.org/project/Faker/) -- Python fake data generation
- [piper-tts PyPI](https://pypi.org/project/piper-tts/) -- Local neural TTS (v1.4.1)
- [piper GitHub](https://github.com/rhasspy/piper) -- Fast local TTS engine
- [svelte-konva](https://github.com/konvajs/svelte-konva) -- Considered, not selected (Canvas overkill)
- [Svelte + D3 integration](https://datavisualizationwithsvelte.com/) -- Reference patterns
- QACompiler generators at `RFC/NewScripts/QACompilerNEW/generators/` -- XML schema knowledge
- QuickCheck core at `RFC/NewScripts/QuickCheck/core/` -- QA pipeline source
- LanguageDataExporter clustering at `RFC/NewScripts/LanguageDataExporter/clustering/` -- Category logic
- Existing `server/tools/ldm/services/ai_summary_service.py` -- AI pattern to extend
