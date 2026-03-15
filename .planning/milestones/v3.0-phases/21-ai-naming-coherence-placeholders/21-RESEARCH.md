# Phase 21: AI Naming Coherence + Placeholders - Research

**Researched:** 2026-03-15
**Domain:** AI-assisted naming suggestions (Model2Vec + Qwen3) + SVG placeholder asset generation
**Confidence:** HIGH

## Summary

Phase 21 combines two independent feature sets: (1) AI naming coherence that suggests similar entity names when editing Name fields in Game Dev mode, and (2) styled SVG placeholders for missing images and audio across the Codex and Grid views. Both features build entirely on existing infrastructure -- no new libraries or patterns are needed.

The naming coherence feature reuses the exact same CodexService FAISS index (Phase 19) for embedding similarity search and the AISuggestionService pattern (Phase 17) for Qwen3 LLM suggestions. The key architectural decision is whether to add a new backend endpoint or reuse the existing `/codex/search` endpoint. Research shows a **new dedicated endpoint** is cleaner because naming suggestions need entity-type-filtered results with a different response shape (name-focused, no description/media data) and a Qwen3 naming prompt distinct from translation prompts.

The placeholder feature is purely frontend -- CodexEntityDetail already has a basic placeholder (`<ImageIcon size={48} />` on line 136) that needs upgrading to styled SVG with category-specific icons. Audio placeholders need a waveform SVG. Both are static SVG components with no backend changes.

**Primary recommendation:** Split into Plan 01 (naming coherence backend + endpoint) and Plan 02 (naming coherence frontend panel + placeholder SVG components). Both plans are straightforward extensions of Phase 17 and 19 patterns.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AINAME-01 | When editing a Name field in Game Dev mode, system shows similar existing entity names via Model2Vec embedding search | CodexService.search() already provides FAISS-backed semantic search. New endpoint wraps it with name-focused filtering. VirtualGrid inline edit events (line 1196+) provide the trigger point. |
| AINAME-02 | AI suggests coherent naming alternatives based on existing patterns via Qwen3 | AISuggestionService pattern (Ollama REST, structured JSON output, caching) is directly reusable. New NamingCoherenceService with naming-specific prompt. |
| AINAME-03 | Suggestions display as non-blocking panel -- game dev confirms in grid, never auto-replace | AISuggestionsTab pattern (debounced fetch, AbortController, confidence badges, click-to-apply) is directly reusable. New NamingPanel component in GameDevPage or as RightPanel tab. |
| PLACEHOLDER-01 | Missing images show styled SVG placeholder with entity name + category-specific icon | CodexEntityDetail line 135-138 already has image placeholder. Upgrade to SVG with Carbon icon per entity_type. |
| PLACEHOLDER-02 | Missing audio shows waveform SVG placeholder with entity name and "[No Audio]" label | CodexEntityDetail line 211 already has "[No Audio]" text. Upgrade to styled waveform SVG component. |
| PLACEHOLDER-03 | Placeholders cached per StringID for consistent display | Svelte 5 $derived reactivity handles this -- placeholder is deterministic from entity_type + name, so same inputs always produce same output. A simple Map cache in the component or a shared utility ensures consistent display. |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Model2Vec | current | Embedding similarity search for entity names | Already powering Codex FAISS search (Phase 19) |
| FAISS | current | Vector similarity index | Already in CodexService._build_search_index() |
| Ollama/Qwen3 | qwen3:4b | LLM naming pattern suggestions | Already in AISuggestionService (Phase 17) |
| httpx | current | Async HTTP client for Ollama | Already used in ai_suggestion_service.py |
| Pydantic | current | Request/response schemas | Standard across all routes |
| Carbon Components Svelte | current | UI components (Tag, InlineLoading) | Project standard |
| carbon-icons-svelte | ^13.0.0 | Category-specific icons for placeholders | Already imported in CodexEntityDetail |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI | current | REST endpoint routing | New naming endpoint |
| loguru | current | Logging (never print()) | All new Python code |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New NamingCoherenceService | Reuse AISuggestionService directly | Different prompt structure, different caching needs -- separate service is cleaner |
| New API endpoint | Reuse /codex/search | Naming needs Qwen3 suggestions + embedding results combined, codex/search only does embedding |
| SVG placeholder components | Canvas-based placeholders | SVG is simpler, no canvas context needed, Carbon design system alignment |

**Installation:** No new packages needed. Everything is already installed.

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/
  services/naming_coherence_service.py   # NEW: embedding search + Qwen3 naming
  routes/naming.py                       # NEW: REST endpoint
  schemas/naming.py                      # NEW: request/response models
  routes/__init__.py                     # UPDATE: export naming_router
  router.py                              # UPDATE: include naming_router

locaNext/src/lib/components/ldm/
  NamingPanel.svelte                     # NEW: naming suggestions panel
  PlaceholderImage.svelte                # NEW: styled SVG image placeholder
  PlaceholderAudio.svelte                # NEW: styled SVG audio placeholder
  CodexEntityDetail.svelte               # UPDATE: use new placeholder components
  RightPanel.svelte                      # UPDATE: add naming tab (conditional on gamedev mode)

tests/unit/ldm/
  test_naming_coherence_service.py       # NEW: service unit tests
  test_naming_route.py                   # NEW: route unit tests
```

### Pattern 1: NamingCoherenceService (follows AISuggestionService pattern)
**What:** Backend service combining CodexService FAISS search with Qwen3 naming suggestions
**When to use:** When user edits a Name field in Game Dev mode
**Example:**
```python
# Source: Based on ai_suggestion_service.py pattern (Phase 17)
class NamingCoherenceService:
    """Find similar entity names + generate coherent naming alternatives."""

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen3:4b"
    TIMEOUT = 15.0

    def __init__(self) -> None:
        self._cache: Dict[str, dict] = {}
        self._available: Optional[bool] = None

    def find_similar_names(self, name: str, entity_type: str, limit: int = 10) -> list[dict]:
        """Use CodexService FAISS index to find similar entity names."""
        from server.tools.ldm.routes.codex import _get_codex_service
        codex = _get_codex_service()
        results = codex.search(query=name, entity_type=entity_type, limit=limit)
        return [{"name": r.entity.name, "strkey": r.entity.strkey,
                 "similarity": r.similarity, "entity_type": r.entity.entity_type}
                for r in results.results]

    async def suggest_names(self, name: str, entity_type: str,
                            similar_names: list[dict]) -> dict:
        """Generate coherent naming alternatives via Qwen3."""
        cache_key = f"{entity_type}:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = self._build_naming_prompt(name, entity_type, similar_names)
        # ... Ollama call (same pattern as AISuggestionService.generate_suggestions)
```

### Pattern 2: Debounced Naming Panel (follows AISuggestionsTab pattern)
**What:** Frontend panel showing similar names + AI suggestions on Name field edit
**When to use:** When user is editing a Name field in Game Dev grid
**Example:**
```svelte
<!-- Source: Based on AISuggestionsTab.svelte pattern (Phase 17) -->
<script>
  let { editingName = '', entityType = '' } = $props();
  let similarNames = $state([]);
  let aiSuggestions = $state([]);
  let loading = $state(false);
  let abortController = null;
  let debounceTimer = null;

  $effect(() => {
    if (!editingName || editingName.length < 2) return;
    // 500ms debounce + AbortController (same pattern as AISuggestionsTab)
    if (debounceTimer) clearTimeout(debounceTimer);
    if (abortController) abortController.abort();
    loading = true;
    debounceTimer = setTimeout(() => { /* fetch naming suggestions */ }, 500);
  });
</script>
```

### Pattern 3: SVG Placeholder Components
**What:** Deterministic SVG placeholders with category-specific Carbon icons
**When to use:** When entity image or audio is missing/fails to load
**Example:**
```svelte
<!-- PlaceholderImage.svelte -->
<script>
  import { User, ShoppingCart, Lightning, GameWireless, Earth } from "carbon-icons-svelte";
  let { entityType = '', entityName = '' } = $props();

  const ICONS = {
    character: User,
    item: ShoppingCart,
    skill: Lightning,
    gimmick: GameWireless,
    region: Earth,
  };
  let IconComponent = $derived(ICONS[entityType] || ShoppingCart);
</script>

<svg viewBox="0 0 160 120" class="placeholder-svg">
  <rect width="160" height="120" fill="var(--cds-layer-02)" rx="4"/>
  <foreignObject x="40" y="20" width="80" height="60">
    <svelte:component this={IconComponent} size={48} />
  </foreignObject>
  <text x="80" y="105" text-anchor="middle" fill="var(--cds-text-03)"
        font-size="10">{entityName?.slice(0, 20) || entityType}</text>
</svg>
```

### Anti-Patterns to Avoid
- **Auto-replacing names:** Never. AINAME-03 explicitly says "game dev confirms in the grid, never auto-replace."
- **Blocking the grid during suggestions:** Use debounce + AbortController. AISuggestionsTab already proves this pattern works.
- **Generating unique SVGs per call:** Placeholders must be deterministic from (entityType, entityName). Same inputs = same visual output. Cache key = `${entityType}:${entityName}`.
- **Calling Ollama without similarity context:** Always send similar_names to Qwen3 so it can see existing naming patterns. Without this context, suggestions will be generic and unhelpful.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Entity name similarity search | Custom embedding + distance calc | CodexService.search() + FAISS | Already built, tested, indexed for 350+ entities |
| LLM structured output | Raw string parsing | Pydantic model_json_schema() + Ollama format param | AISuggestionService already proves this pattern |
| Debounced async requests | Custom debounce logic | Copy AISuggestionsTab pattern (500ms + AbortController) | Battle-tested, handles rapid input correctly |
| Category-specific icons | Custom SVG icon set | Carbon Icons (carbon-icons-svelte ^13.0.0) | Already in project, consistent with design system |

**Key insight:** Phase 21 is almost entirely a remix of Phase 17 (AI suggestions) and Phase 19 (Codex search) patterns. The only truly new code is the naming-specific Qwen3 prompt and the SVG placeholder components.

## Common Pitfalls

### Pitfall 1: Flooding Ollama with naming requests during rapid typing
**What goes wrong:** Each keystroke in the Name field triggers a Qwen3 request, overwhelming Ollama
**Why it happens:** Name fields update on every character input
**How to avoid:** 500ms debounce (same as AISuggestionsTab). Only trigger after user pauses typing. AbortController cancels stale requests.
**Warning signs:** Ollama logs showing queued requests, UI showing stale suggestions

### Pitfall 2: Naming panel showing in Translator mode
**What goes wrong:** Naming coherence panel appears for translators who don't edit entity names
**Why it happens:** RightPanel tabs are shared between modes
**How to avoid:** Conditionally show "Naming" tab only when in Game Dev mode. Check current UI mode before rendering the tab.
**Warning signs:** Tab visible in Translator mode layout

### Pitfall 3: CodexService not initialized when naming endpoint called
**What goes wrong:** First naming request fails because FAISS index hasn't been built
**Why it happens:** CodexService uses lazy initialization (first request triggers scan)
**How to avoid:** CodexService.search() already calls self.initialize() on first request (line 283). The naming service should call through CodexService, not access FAISS directly.
**Warning signs:** Empty similar_names on first request only

### Pitfall 4: Placeholder SVG not rendering in dark mode
**What goes wrong:** SVG text/icons invisible against dark background
**Why it happens:** Hardcoded colors instead of CSS custom properties
**How to avoid:** Use Carbon Design System CSS variables: `var(--cds-text-03)`, `var(--cds-layer-02)`, etc. CodexEntityDetail already uses these correctly.
**Warning signs:** Invisible placeholders in dark theme

### Pitfall 5: Caching naming suggestions with stale entity index
**What goes wrong:** New entities added but naming suggestions reference old index
**Why it happens:** CodexService FAISS index is built once at initialization
**How to avoid:** This is acceptable for Phase 21 scope -- the index rebuilds on service restart. Document as known limitation. Cache key should include a generation counter if needed later.
**Warning signs:** Newly added entities not appearing in similar names

## Code Examples

### Backend: Naming Endpoint (follows ai_suggestions.py pattern)
```python
# Source: Based on routes/ai_suggestions.py and routes/codex.py patterns
@router.get("/naming/similar/{entity_type}")
async def get_similar_names(
    entity_type: str,
    name: str = Query(..., max_length=500, description="Current entity name"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Find similar entity names via embedding search."""
    service = get_naming_coherence_service()
    return service.find_similar_names(name=name, entity_type=entity_type, limit=limit)

@router.get("/naming/suggest/{entity_type}")
async def get_naming_suggestions(
    entity_type: str,
    name: str = Query(..., max_length=500),
    current_user: dict = Depends(get_current_active_user_async),
):
    """Get AI naming pattern suggestions via Qwen3."""
    service = get_naming_coherence_service()
    similar = service.find_similar_names(name=name, entity_type=entity_type, limit=10)
    return await service.suggest_names(name=name, entity_type=entity_type, similar_names=similar)
```

### Backend: Naming Prompt for Qwen3
```python
# Source: Derived from AISuggestionService._build_prompt pattern
def _build_naming_prompt(self, name: str, entity_type: str, similar_names: list[dict]) -> str:
    parts = [
        f"You are a game world designer ensuring naming coherence.",
        f"Entity type: {entity_type}",
        f"Current name being edited: {name}",
        "",
        "Existing similar names in this category:",
    ]
    for sn in similar_names[:10]:
        parts.append(f"  - {sn['name']} (similarity: {int(sn['similarity'] * 100)}%)")
    parts.append("")
    parts.append(
        "Suggest 3 alternative names that are coherent with the existing naming patterns. "
        "Each suggestion must have: name (the suggested name), "
        "confidence (0.0-1.0), reasoning (why it fits the naming pattern)."
    )
    return "\n".join(parts)
```

### Frontend: PlaceholderAudio waveform SVG
```svelte
<!-- PlaceholderAudio.svelte -->
<script>
  let { entityName = '' } = $props();
</script>

<div class="audio-placeholder">
  <svg viewBox="0 0 200 40" class="waveform-svg">
    {#each Array(20) as _, i}
      <rect x={i * 10 + 2} y={20 - (Math.sin(i * 0.8) * 12 + 4)}
            width="6" height={Math.sin(i * 0.8) * 24 + 8}
            rx="2" fill="var(--cds-text-03)" opacity="0.3"/>
    {/each}
  </svg>
  <span class="placeholder-label">{entityName || '[No Audio]'}</span>
</div>
```

### Frontend: Naming suggestions integration with VirtualGrid
```svelte
<!-- Key integration point: detect Name field editing in GameDevPage -->
<!-- VirtualGrid emits inline edit events (line 1196+) -->
<!-- GameDevPage should track which attr is being edited -->
<!-- Pass editingName + entityType to NamingPanel when attr is "Name" -->
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Broken image icon (browser default) | Styled SVG placeholder (Phase 21) | This phase | Professional look for missing assets |
| Plain "[No Audio]" text | Waveform SVG placeholder | This phase | Visual consistency with audio presence |
| Manual naming without guidance | Embedding-similar + LLM suggestions | This phase | Naming pattern consistency across entities |

**No deprecated/outdated items** -- all infrastructure is current from Phases 17-19.

## Open Questions

1. **Where should the Naming Panel render?**
   - What we know: RightPanel has 5 tabs already (TM, Image, Audio, AI Context, AI Suggest). GameDevPage doesn't use RightPanel.
   - What's unclear: Should naming suggestions be a 6th tab in RightPanel (if GameDevPage is refactored to include it) or a separate floating panel specific to GameDevPage?
   - Recommendation: Add as a **dedicated section below the Grid in GameDevPage** or as a **popover/tooltip near the editing cell**. A separate component in GameDevPage is simplest since GameDevPage doesn't currently integrate with RightPanel. Keep it inline with the grid editing flow.

2. **Placeholder caching granularity**
   - What we know: PLACEHOLDER-03 says "cached per StringID for consistent display"
   - What's unclear: Since SVG placeholders are deterministic from (entityType, entityName), is explicit caching even needed? Svelte will re-render the same SVG for same props.
   - Recommendation: Use $derived or a simple Map<string, SVGElement> if there are performance concerns. For Phase 21 scope, deterministic rendering from props is sufficient -- no explicit cache layer needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | pytest.ini |
| Quick run command | `python -m pytest tests/unit/ldm/test_naming_coherence_service.py tests/unit/ldm/test_naming_route.py -x -q` |
| Full suite command | `python -m pytest tests/unit/ldm/ -x -q --no-cov` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AINAME-01 | Similar names returned via embedding search | unit | `python -m pytest tests/unit/ldm/test_naming_coherence_service.py::test_find_similar_names -x` | Wave 0 |
| AINAME-02 | Qwen3 naming suggestions with coherent patterns | unit | `python -m pytest tests/unit/ldm/test_naming_coherence_service.py::test_suggest_names -x` | Wave 0 |
| AINAME-03 | Non-blocking panel display, click-to-apply | manual-only | Manual: verify panel appears, click suggestion applies to field | N/A |
| PLACEHOLDER-01 | Styled SVG image placeholder with category icon | unit | `python -m pytest tests/unit/ldm/test_naming_route.py -x` (route returns placeholder data) | Wave 0 |
| PLACEHOLDER-02 | Waveform SVG audio placeholder | manual-only | Manual: verify waveform renders for missing audio | N/A |
| PLACEHOLDER-03 | Placeholders consistent per StringID | unit | `python -m pytest tests/unit/ldm/test_naming_coherence_service.py::test_similar_names_caching -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_naming_coherence_service.py tests/unit/ldm/test_naming_route.py -x -q --no-cov`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -x -q --no-cov`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_naming_coherence_service.py` -- covers AINAME-01, AINAME-02, AINAME-03 (backend), PLACEHOLDER-03
- [ ] `tests/unit/ldm/test_naming_route.py` -- covers AINAME-01, AINAME-02 route integration

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/services/ai_suggestion_service.py` -- Phase 17 AI suggestion pattern (Ollama, caching, blending)
- `server/tools/ldm/services/codex_service.py` -- Phase 19 FAISS search, entity registry
- `server/tools/ldm/schemas/codex.py` -- CodexEntity model with entity_type, name, image_texture, audio_key
- `server/tools/ldm/routes/ai_suggestions.py` -- Route pattern with Query params, categorize_by_stringid
- `server/tools/ldm/routes/codex.py` -- Codex route pattern with module-level singleton
- `server/tools/ldm/router.py` -- Router registration pattern (include_router)
- `locaNext/src/lib/components/ldm/AISuggestionsTab.svelte` -- Debounced fetch + AbortController + confidence badges
- `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` -- Existing image/audio placeholders (lines 135-138, 211)
- `locaNext/src/lib/components/ldm/RightPanel.svelte` -- Tab architecture (5 tabs)
- `locaNext/src/lib/components/pages/GameDevPage.svelte` -- Game Dev page layout (no RightPanel currently)
- `server/tools/shared/embedding_engine.py` -- Model2Vec engine (get_embedding_engine)

### Secondary (MEDIUM confidence)
- VirtualGrid inline edit events (grep results, lines 1196+) -- edit trigger mechanism
- carbon-icons-svelte ^13.0.0 -- category-specific icons available

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- everything already in project, no new dependencies
- Architecture: HIGH -- directly follows Phase 17 + 19 patterns, all code inspected
- Pitfalls: HIGH -- identified from actual codebase patterns (debounce, dark mode, lazy init)

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- no external dependencies changing)
