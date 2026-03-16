# Phase 31: Codex AI Image Generation - Research

**Researched:** 2026-03-16
**Domain:** Gemini Image Generation API + Codex UI Integration
**Confidence:** HIGH

## Summary

Phase 31 replaces SVG placeholders in the Game World Codex with AI-generated images using Google's Gemini image generation API via the `google-genai` Python SDK (v1.67.0, already installed). The implementation involves three main concerns: (1) a backend service wrapping the Gemini API with prompt templates, disk caching, and batch generation with progress tracking; (2) new REST endpoints for single/batch generation and image serving; (3) frontend integration adding generate/regenerate buttons to CodexEntityDetail and batch generation with progress to CodexPage.

The existing codebase provides strong patterns to reuse: `TrackedOperation` for batch progress tracking via WebSocket, `asyncio.to_thread` for wrapping sync SDK calls, the mapdata thumbnail endpoint pattern for image serving, and the `ai_suggestion_service.py` singleton pattern for the new service.

**Primary recommendation:** Create a new `ai_image_service.py` that wraps the Gemini sync SDK with `asyncio.to_thread`, caches generated PNGs to disk by StrKey, and builds entity-type-aware prompts from XML attributes. Use `TrackedOperation` for batch generation progress. Add `ai_generated_image_url` field to CodexEntity response (computed, not stored in model). Frontend checks `/api/ldm/codex/image-gen/status` on mount to show/hide generation buttons.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use `google-genai` Python SDK with model `gemini-3-pro-image-preview`
- Authentication via `GEMINI_API_KEY` environment variable
- Non-blocking generation: `asyncio.to_thread` wrapping sync Gemini SDK calls
- Exponential backoff on 429/RESOURCE_EXHAUSTED (3 retries)
- Image resolution: 1K (1024px) for all entity types -- $0.045/image
- Response modality: `['IMAGE']` only -- extract PNG bytes from `part.inline_data.data`
- Disk cache at `server/data/cache/ai_images/by_strkey/{strkey}/generated.png`
- StrKey as unique filename -- deterministic, human-readable
- Served via existing `/api/ldm/mapdata/thumbnail/` pattern OR new `/api/ldm/codex/image/{strkey}` endpoint
- HTTP cache headers: `Cache-Control: public, max-age=604800` (7-day browser cache)
- Metadata sidecar JSON per image: model, prompt used, generated_at timestamp
- No TTL expiry -- images persist until manually regenerated or cleared
- If `GEMINI_API_KEY` not set: generation button hidden, placeholders stay, no error
- Availability check: service checks key presence on init, exposes `/api/ldm/codex/image-gen/status`
- Frontend checks status once on Codex page mount -- shows/hides generate buttons accordingly
- On generation failure: error toast, keep placeholder, log failure, user can retry
- "Generate All Images" button on Codex category page -- generates for all entities in current category
- Batch skips entities with cached images -- only generates missing ones
- Progress bar: "{completed}/{total} images generated" with percentage via WebSocket (TrackedOperation)
- Cancel button -- stops after current image completes
- Show estimated cost before batch start: "{N} images x ~$0.05 = ~${total}"
- Rate limiting: respect 10 IPM (Tier 1), sequential generation with 6-second delay between images
- "Generate Image" button on CodexEntityDetail when entity has placeholder
- "Regenerate" button when entity already has AI image -- replaces cached image
- Single generation per request -- no multiple variants
- No manual prompt editing -- prompts auto-generated from entity attributes
- Loading spinner replaces placeholder during generation (optimistic UI)
- Attribute-rich prompts: pull entity attributes (Race, Job, Grade, Element, Desc) from XML
- JSON config mapping `entity_type -> prompt_template` with attribute placeholders
- Aspect ratios: 1:1 for icons (items, skills, seals, quests, gimmicks, knowledge, scene objects), 3:4 for portraits (characters, factions), 16:9 for landscapes (regions, skill trees)
- Style keywords per type: "game UI icon", "character portrait", "landscape painting", "magical sigil", "heraldic banner"

### Claude's Discretion
- Exact prompt template wording for each entity type (use research findings as starting point)
- Whether to store prompt templates in Python dict or separate JSON file
- Exact spinner/loading animation design during generation
- Whether metadata sidecar is .json or embedded in image EXIF
- Exact error toast message wording
- Whether to show generation timestamp on entity detail

### Deferred Ideas (OUT OF SCOPE)
- Multi-variant generation (generate 3-4 options, user picks best)
- Manual prompt editing for power users
- Image upscaling (1K->2K->4K) via Gemini edit API
- Style consistency across entity types (style reference image)
- Image generation for non-Codex entities (GameData tree nodes)

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IMG-01 | AI-generated entity images replace SVG placeholders in Codex using Nano Banana / Gemini image generation | Gemini SDK verified (v1.67.0 installed), model `gemini-3-pro-image-preview` confirmed, `response_modalities=['IMAGE']` API verified, `part.inline_data` -> PNG bytes extraction pattern documented |
| IMG-02 | Entity-type aware prompts -- character portraits, item icons, region landscape scenes, skill effect icons | EDITABLE_ATTRS mapping in `gamedata_browse_service.py` provides attribute extraction, 6 entity types in ENTITY_TAG_MAP, aspect ratio + style keyword mapping per type defined in decisions |
| IMG-03 | Generated images cached on disk with entity StrKey as filename, served via existing thumbnail endpoint | Disk cache path `server/data/cache/ai_images/by_strkey/{strkey}/generated.png`, mapdata thumbnail endpoint pattern verified in `routes/mapdata.py` (Response with PNG bytes + Cache-Control), `server/data/cache/` directory exists |
| IMG-04 | Batch generation mode -- generate images for all entities in a category with progress tracking | `TrackedOperation` context manager verified in `progress_tracker.py` with DB tracking + WebSocket emission, `asyncio.to_thread` pattern established in 10+ existing callsites, sequential generation with 6-second delay for rate limiting |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | 1.67.0 | Gemini API SDK for image generation | Already installed, official Google SDK, supports image generation with response_modalities=['IMAGE'] |
| Pillow (PIL) | (installed) | Image processing, PNG save/validate | Already a dependency, used for image manipulation if needed |
| FastAPI | (existing) | REST endpoints for generate/serve/status | Existing project framework |
| loguru | (existing) | Logging (never print()) | Project convention |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | to_thread for sync SDK wrapping | Every Gemini API call |
| pathlib | stdlib | Disk cache path management | Cache directory creation and file operations |
| json | stdlib | Metadata sidecar files | Storing generation metadata alongside images |
| time | stdlib | Rate limiting delays | 6-second delay between batch generations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sync SDK + asyncio.to_thread | google-genai async client | Sync is simpler, async client requires different patterns -- the project already uses to_thread in 10+ places |
| Disk cache (filesystem) | SQLite/Redis cache | Filesystem is simpler, human-readable, no extra dependency -- images are large binary files best stored as files |
| JSON sidecar metadata | EXIF embedding | JSON is simpler to read/debug/modify, EXIF requires extra libraries -- recommend JSON sidecar |

**Installation:**
```bash
# Already installed -- no new packages needed
pip show google-genai  # v1.67.0
```

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/services/
  ai_image_service.py          # NEW: Gemini client + prompt builder + cache manager
server/tools/ldm/routes/
  codex.py                     # EXTEND: add generate/batch/status/serve endpoints
server/tools/ldm/schemas/
  codex.py                     # EXTEND: add ai_image_url field to CodexEntity
server/data/cache/ai_images/
  by_strkey/
    {strkey}/
      generated.png            # Cached AI-generated image
      metadata.json            # Generation metadata sidecar
locaNext/src/lib/components/ldm/
  CodexEntityDetail.svelte     # EXTEND: add generate/regenerate button
locaNext/src/lib/components/pages/
  CodexPage.svelte             # EXTEND: add batch generate + progress bar
```

### Pattern 1: AI Image Service (Singleton with Graceful Degradation)
**What:** Service that wraps Gemini SDK, manages disk cache, builds prompts from entity attributes.
**When to use:** Every image generation request (single or batch).
**Example:**
```python
# Source: ai_suggestion_service.py pattern + nano-banana SKILL.md
from google import genai
from google.genai import types

class AIImageService:
    MODEL = "gemini-3-pro-image-preview"
    CACHE_DIR = Path("server/data/cache/ai_images/by_strkey")

    def __init__(self):
        self._api_key = os.environ.get("GEMINI_API_KEY")
        self._client = genai.Client(api_key=self._api_key) if self._api_key else None
        self._available = self._client is not None

    def get_cached_image_path(self, strkey: str) -> Optional[Path]:
        """Check if AI image exists in cache."""
        path = self.CACHE_DIR / strkey / "generated.png"
        return path if path.exists() else None

    def generate_image(self, entity: CodexEntity) -> bytes:
        """Sync Gemini call -- MUST be wrapped in asyncio.to_thread."""
        prompt = self._build_prompt(entity)
        aspect = self._get_aspect_ratio(entity.entity_type)

        response = self._client.models.generate_content(
            model=self.MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect,
                    image_size="1K"
                )
            )
        )

        for part in response.parts:
            if part.inline_data:
                return part.inline_data.data
        raise ValueError("No image in response")
```

### Pattern 2: Async Endpoint with to_thread (Established Pattern)
**What:** FastAPI async endpoint wrapping sync blocking work.
**When to use:** Single and batch image generation endpoints.
**Example:**
```python
# Source: server/tools/ldm/routes/tm_indexes.py lines 64-92
@router.post("/codex/generate-image/{strkey}")
async def generate_image(strkey: str, current_user = Depends(...)):
    svc = get_ai_image_service()
    codex = _get_codex_service()
    entity = codex.get_entity_by_strkey(strkey)  # Need to add this method

    png_bytes = await asyncio.to_thread(svc.generate_image, entity)
    svc.save_to_cache(strkey, png_bytes)

    return {"status": "generated", "image_url": f"/api/ldm/codex/image/{strkey}"}
```

### Pattern 3: Batch Generation with TrackedOperation
**What:** Sequential batch generation with progress tracking + cancellation.
**When to use:** "Generate All" for a category.
**Example:**
```python
# Source: server/utils/progress_tracker.py TrackedOperation pattern
async def batch_generate(entity_type: str, user_id: int):
    svc = get_ai_image_service()
    codex = _get_codex_service()
    entities = codex.list_entities(entity_type).entities

    # Filter to those without cached images
    to_generate = [e for e in entities if not svc.get_cached_image_path(e.strkey)]

    with TrackedOperation("AI Image Generation", user_id,
                          tool_name="Codex", total_steps=len(to_generate)) as op:
        for i, entity in enumerate(to_generate):
            if cancel_requested:  # Check cancellation flag
                break
            png_bytes = await asyncio.to_thread(svc.generate_image, entity)
            svc.save_to_cache(entity.strkey, png_bytes)
            op.update((i + 1) / len(to_generate) * 100,
                      f"{i+1}/{len(to_generate)} images generated",
                      completed_steps=i + 1, total_steps=len(to_generate))
            await asyncio.sleep(6)  # Rate limit: 10 IPM = 6s between calls
```

### Pattern 4: Image Serving Endpoint (Reuse mapdata pattern)
**What:** Serve cached PNG with long cache headers.
**When to use:** Frontend image display.
**Example:**
```python
# Source: server/tools/ldm/routes/mapdata.py get_thumbnail pattern
@router.get("/codex/image/{strkey}")
async def get_codex_image(strkey: str, current_user = Depends(...)):
    svc = get_ai_image_service()
    cached = svc.get_cached_image_path(strkey)
    if not cached:
        raise HTTPException(404, "No generated image for this entity")

    png_bytes = cached.read_bytes()
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800"}
    )
```

### Anti-Patterns to Avoid
- **Async Gemini client:** The `google-genai` SDK's sync client is simpler and the project standard is `asyncio.to_thread` for blocking calls (10+ existing usages). Do not introduce the async client.
- **Storing images in database:** Binary blobs in PostgreSQL/SQLite are slow and bloated. Use filesystem cache.
- **Parallel Gemini calls:** Rate limit is 10 IPM (Tier 1). Sequential with delay is the only safe approach.
- **Generating at page load:** Never auto-generate. Only on explicit user action (button click).
- **Hardcoding prompts in endpoints:** Keep prompt templates in the service layer, not scattered across route handlers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress tracking | Custom WebSocket events | TrackedOperation context manager | Auto-creates DB records, emits WebSocket events, auto-completes/fails |
| Exponential backoff | Custom retry loop | `tenacity` (already a dependency of google-genai) | Battle-tested retry with jitter, already installed |
| Image serving | Custom file streaming | FastAPI Response with content=bytes | Same pattern as mapdata thumbnail, proven |
| Entity attribute extraction | Custom XML parsing | CodexService.get_entity() | Already parses all attributes, descriptions, knowledge cross-refs |
| Async wrapping | Custom thread pool | asyncio.to_thread | stdlib, project standard, 10+ existing usages |

**Key insight:** The Codex service already extracts all entity attributes needed for prompt building. The mapdata route already demonstrates image serving. TrackedOperation already handles progress tracking. This phase is largely wiring existing patterns together with a new Gemini API client.

## Common Pitfalls

### Pitfall 1: Rate Limit Exhaustion (429/RESOURCE_EXHAUSTED)
**What goes wrong:** Batch generation fires too many requests, gets rate-limited, all subsequent requests fail.
**Why it happens:** Gemini Tier 1 free tier has 10 images per minute limit. Without explicit throttling, even sequential requests fire too fast.
**How to avoid:** Enforce 6-second `asyncio.sleep()` between batch requests. Use `tenacity` for exponential backoff on 429 errors. Show cost estimate before batch to set user expectations.
**Warning signs:** Multiple 429 errors in logs, batch progress stalling.

### Pitfall 2: Safety Filter Blocking
**What goes wrong:** Gemini refuses to generate certain images (violence, NSFW content in game descriptions).
**Why it happens:** Game entity descriptions may contain combat/violence references that trigger Gemini's safety filters.
**How to avoid:** Prompt templates should include "game UI art style" or "fantasy illustration" to signal artistic intent. On `SAFETY` block response, return a specific error message ("Image could not be generated due to content policy") and log the entity for debugging. Never retry safety blocks (they will always fail for the same input).
**Warning signs:** Specific entities consistently failing generation.

### Pitfall 3: Missing or Insufficient Entity Attributes
**What goes wrong:** Prompts generate generic/wrong images because entity attributes are sparse.
**Why it happens:** Some XML entities have minimal attributes (just StrKey and name, no description or type-specific attrs).
**How to avoid:** Prompt builder should gracefully degrade -- use available attributes, skip missing ones. Always include the entity name. Add a fallback style for entities with no description: "A fantasy [entity_type] named [name]".
**Warning signs:** Generated images looking generic or wrong type.

### Pitfall 4: StrKey Path Injection
**What goes wrong:** Malicious StrKey values create files outside the cache directory.
**Why it happens:** StrKeys from XML could contain `../` or other path traversal characters.
**How to avoid:** Sanitize StrKey before using as directory name: strip `/`, `\`, `..`, null bytes. Verify the resolved path is within CACHE_DIR using `Path.resolve()` comparison.
**Warning signs:** Unexpected file locations in cache directory.

### Pitfall 5: Batch Cancellation Race Condition
**What goes wrong:** Cancel flag not checked between generate and save, or cancel not clean.
**Why it happens:** The Gemini API call takes 5-15 seconds. If user cancels mid-call, the current image should still be saved.
**How to avoid:** Check cancellation BEFORE starting next image, not during. Let current generation complete and save. Use an `asyncio.Event` for cancellation signaling.
**Warning signs:** Partially generated batches with missing last image.

### Pitfall 6: Disk Space Accumulation
**What goes wrong:** Cache grows unbounded as users generate and regenerate images.
**Why it happens:** No TTL expiry (by design), regeneration creates new file but old one was already there.
**How to avoid:** Regeneration overwrites the same file path (by_strkey/{strkey}/generated.png). Log cache size periodically. No automatic cleanup needed per decisions, but track total size.
**Warning signs:** Disk space warnings in logs.

## Code Examples

### Gemini Image Generation (Verified from SDK docs + nano-banana skill)
```python
# Source: nano-banana SKILL.md + google-genai SDK docs
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=["A fantasy warrior character portrait, anime RPG style, detailed armor"],
    config=types.GenerateContentConfig(
        response_modalities=['IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio="3:4",
            image_size="1K"
        )
    )
)

# Extract PNG bytes
for part in response.parts:
    if part.inline_data:
        png_bytes = part.inline_data.data  # raw bytes
        # OR use PIL:
        # image = part.as_image()  # returns PIL.Image
        # image.save("output.png")
```

### Prompt Template Design (Recommended)
```python
# Prompt templates per entity type -- store in service as Python dict
PROMPT_TEMPLATES = {
    "character": (
        "A character portrait for a fantasy RPG game. "
        "Name: {name}. Race: {Race}. Job: {Job}. "
        "{description_clause}"
        "Style: detailed character portrait, anime RPG art, "
        "dramatic lighting, upper body shot. "
        "{grade_glow}"
    ),
    "item": (
        "A game item icon for a fantasy RPG. "
        "Item: {name}. Type: {ItemType}. "
        "{description_clause}"
        "Style: game UI icon, clean edges, centered on dark background, "
        "slight glow effect. "
        "{grade_glow}"
    ),
    "skill": (
        "A skill effect icon for a fantasy RPG game. "
        "Skill: {name}. "
        "{description_clause}"
        "Style: game UI skill icon, magical effect, "
        "glowing energy, centered on dark circular background."
    ),
    "region": (
        "A landscape scene for a fantasy RPG game region. "
        "Region: {name}. "
        "{description_clause}"
        "Style: landscape painting, wide establishing shot, "
        "atmospheric lighting, fantasy world environment."
    ),
    "gimmick": (
        "A magical seal or sigil icon for a fantasy RPG game. "
        "Seal: {name}. "
        "{description_clause}"
        "Style: magical sigil, glowing runes, centered on dark background, "
        "mystical energy."
    ),
}

# Grade-based glow intensity keywords
GRADE_GLOW = {
    "Common": "",
    "Uncommon": "Slight magical glow. ",
    "Rare": "Bright magical aura. ",
    "Epic": "Intense purple-gold magical aura. ",
    "Legendary": "Brilliant golden divine radiance. ",
}
```

### Frontend Generate Button (Svelte 5 Runes pattern)
```svelte
<!-- In CodexEntityDetail.svelte -->
<script>
  let generating = $state(false);
  let aiImageUrl = $state(null);
  let imageGenAvailable = $state(false);

  // Check availability on mount
  $effect(() => {
    fetch(`${API_BASE}/api/ldm/codex/image-gen/status`, { headers: getAuthHeaders() })
      .then(r => r.json())
      .then(data => { imageGenAvailable = data.available; })
      .catch(() => { imageGenAvailable = false; });
  });

  async function generateImage() {
    generating = true;
    try {
      const res = await fetch(`${API_BASE}/api/ldm/codex/generate-image/${entity.strkey}`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        aiImageUrl = `${API_BASE}${data.image_url}?t=${Date.now()}`; // cache bust
      }
    } finally {
      generating = false;
    }
  }
</script>
```

### Batch Progress via WebSocket (Existing pattern)
```javascript
// Frontend listens for TrackedOperation WebSocket events
// Source: existing Socket.IO pattern in the codebase
socket.on('operation_start', (data) => {
  if (data.operation_name === 'AI Image Generation') {
    batchInProgress = true;
    batchProgress = 0;
  }
});
socket.on('progress_update', (data) => {
  batchProgress = data.progress_percentage;
  batchStatus = data.current_step;  // "3/20 images generated"
});
socket.on('operation_complete', (data) => {
  batchInProgress = false;
  // Refresh entity list to show new images
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DALL-E 2/3 for image gen | Gemini 3 Pro Image Preview | 2025 | Better quality, integrated text+image, lower cost |
| response_modalities=['TEXT','IMAGE'] | response_modalities=['IMAGE'] | Gemini 3+ | Pure image output without text preamble -- simpler parsing |
| Manual aspect ratio via prompt | image_config.aspect_ratio parameter | google-genai SDK | Reliable aspect ratio control via API parameter |

**Current models (March 2026):**
- `gemini-3.1-flash-image-preview` -- newest, likely fastest, Flash tier
- `gemini-3-pro-image-preview` -- **selected by user**, Pro quality tier
- `gemini-2.5-flash-image` -- older, still available

## Open Questions

1. **Exact rate limit for Gemini 3 Pro Image Preview**
   - What we know: CONTEXT.md specifies 10 IPM (Tier 1), 6-second delay
   - What's unclear: Whether the actual limit has changed since research was done
   - Recommendation: Implement with 6-second delay as decided. If rate limit errors occur, increase delay dynamically via exponential backoff.

2. **Entity lookup by StrKey across all types**
   - What we know: CodexService.get_entity() requires (entity_type, strkey). For single generation from detail page, the entity_type is known. For batch, entities are already listed by type.
   - What's unclear: Whether we need a cross-type StrKey lookup (e.g., for the image serving endpoint)
   - Recommendation: The image serving endpoint only needs the StrKey to find the cached file on disk. No cross-type lookup needed -- the filesystem cache uses StrKey directly.

3. **Cancellation mechanism for batch generation**
   - What we know: TrackedOperation doesn't have built-in cancellation. Need custom solution.
   - What's unclear: Best way to signal cancellation from frontend to background task
   - Recommendation: Use an in-memory dict `{operation_id: asyncio.Event}` in the service. Frontend calls `POST /codex/batch-generate/cancel/{operation_id}`. The batch loop checks the event before each generation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 with pytest-asyncio |
| Config file | `pytest.ini` (existing, comprehensive) |
| Quick run command | `python -m pytest tests/unit/ldm/test_ai_image_service.py -x -v` |
| Full suite command | `python -m pytest tests/unit/ldm/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMG-01 | Gemini SDK generates image, saves to cache, returns PNG | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_generate_image -x` | No -- Wave 0 |
| IMG-01 | PlaceholderImage replaced when AI image available | manual | Playwright screenshot verification | N/A |
| IMG-02 | Prompt templates include entity-type-specific attributes | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_prompt_templates -x` | No -- Wave 0 |
| IMG-02 | Aspect ratio correct per entity type | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_aspect_ratios -x` | No -- Wave 0 |
| IMG-03 | Cache stores and retrieves by StrKey | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_cache_operations -x` | No -- Wave 0 |
| IMG-03 | Serve endpoint returns cached PNG with cache headers | unit | `python -m pytest tests/unit/ldm/test_codex_route.py::test_serve_generated_image -x` | No -- Wave 0 |
| IMG-04 | Batch generates for category, skips cached | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_batch_generation -x` | No -- Wave 0 |
| IMG-04 | Progress updates via TrackedOperation | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_batch_progress -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_ai_image_service.py -x -v`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_ai_image_service.py` -- covers IMG-01, IMG-02, IMG-03, IMG-04 (service layer)
- [ ] Extend `tests/unit/ldm/test_codex_route.py` -- covers IMG-03 (serve endpoint), IMG-01 (generate endpoint)
- [ ] Mock `google.genai.Client` -- must mock Gemini API calls, never hit real API in tests
- [ ] Test fixtures: sample PNG bytes for mock responses, test entity with full attributes

## Sources

### Primary (HIGH confidence)
- `~/.claude/skills/nano-banana/SKILL.md` -- Gemini API usage, model name, SDK patterns
- google-genai SDK v1.67.0 (installed, `pip show google-genai`) -- verified available
- [Google AI Gemini Image Generation docs](https://ai.google.dev/gemini-api/docs/image-generation) -- models, aspect ratios, image_config options
- Existing codebase files (all verified by reading):
  - `server/tools/ldm/services/codex_service.py` -- entity registry, ENTITY_TAG_MAP, attribute extraction
  - `server/tools/ldm/schemas/codex.py` -- CodexEntity model (needs ai_image field)
  - `server/tools/ldm/routes/codex.py` -- existing endpoints to extend
  - `server/utils/progress_tracker.py` -- TrackedOperation pattern
  - `server/tools/ldm/routes/mapdata.py` -- image serving pattern (Response + Cache-Control)
  - `server/tools/ldm/services/ai_suggestion_service.py` -- singleton pattern, graceful degradation
  - `server/tools/ldm/services/gamedata_browse_service.py` -- EDITABLE_ATTRS mapping

### Secondary (MEDIUM confidence)
- Gemini rate limits (10 IPM Tier 1) -- from CONTEXT.md swarm research, not independently verified against current docs
- Pricing ($0.045/image at 1K) -- from CONTEXT.md, actual pricing may vary

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- google-genai v1.67.0 installed, API patterns verified from official docs + skill docs
- Architecture: HIGH -- all integration points read and verified, patterns match existing codebase conventions
- Pitfalls: MEDIUM -- rate limits and safety filters are based on general API knowledge + CONTEXT.md research, not exhaustive testing
- Prompt templates: MEDIUM -- recommended wording is educated guidance, will need tuning with real entities

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (30 days -- Gemini models are fast-moving, check for model updates)
