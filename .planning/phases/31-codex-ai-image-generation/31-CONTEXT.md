# Phase 31: Codex AI Image Generation - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning
**Source:** Auto-discuss with 6-agent swarm research (Ruflo hive-mind, converged)

<domain>
## Phase Boundary

Replace SVG placeholders in Codex with AI-generated images using Gemini (Nano Banana). Entity-type-aware prompts produce character portraits, item icons, region landscapes, and skill effects. Generated images cached on disk by StrKey, served via existing mapdata endpoint. Batch generation for entire categories with progress tracking.

Requirements: IMG-01, IMG-02, IMG-03, IMG-04

</domain>

<decisions>
## Implementation Decisions

### Gemini API Integration
- Use `google-genai` Python SDK with model `gemini-3-pro-image-preview`
- Authentication via `GEMINI_API_KEY` environment variable
- Non-blocking generation: `asyncio.to_thread` wrapping sync Gemini SDK calls
- Exponential backoff on 429/RESOURCE_EXHAUSTED (3 retries)
- Image resolution: 1K (1024px) for all entity types — $0.045/image, good quality/cost balance
- Response modality: `['IMAGE']` only — extract PNG bytes from `part.inline_data.data`

### Prompt Template Design
- Attribute-rich prompts: pull entity attributes (Race, Job, Grade, Element, Desc) from XML
- JSON config mapping `entity_type → prompt_template` with attribute placeholders — easy to tune
- Include name + key attributes + first sentence of description in every prompt
- Aspect ratios per entity type:
  - **1:1** for icons: items, skills, seals, quests, gimmicks, knowledge, scene objects
  - **3:4** for portraits: characters, factions
  - **16:9** for landscapes: regions, skill trees
- Style keywords per type: "game UI icon" (items/skills), "character portrait" (characters), "landscape painting" (regions), "magical sigil" (seals), "heraldic banner" (factions)

### Image Caching
- Disk cache at `server/data/cache/ai_images/by_strkey/{strkey}/generated.png`
- StrKey as unique filename — deterministic, human-readable
- Served via existing `/api/ldm/mapdata/thumbnail/` pattern OR new `/api/ldm/codex/image/{strkey}` endpoint
- HTTP cache headers: `Cache-Control: public, max-age=604800` (7-day browser cache)
- Metadata sidecar JSON per image: model, prompt used, generated_at timestamp
- No TTL expiry — images persist until manually regenerated or cleared

### Fallback & Availability
- If `GEMINI_API_KEY` not set: generation button hidden, placeholders stay, no error — feature silently unavailable
- Availability check: service checks key presence on init, exposes `/api/ldm/codex/image-gen/status`
- Frontend checks status once on Codex page mount — shows/hides generate buttons accordingly
- On generation failure (rate limit, safety block): error toast, keep placeholder, log failure, user can retry
- No disruption to existing Codex functionality when AI generation is unavailable

### Batch Generation UX
- "Generate All Images" button on Codex category page — generates for all entities in current category
- Batch skips entities with cached images — only generates missing ones
- Progress bar in page header: "{completed}/{total} images generated" with percentage
- Progress updates via WebSocket (TrackedOperation pattern from existing codebase)
- Cancel button appears next to progress bar — stops after current image completes
- Show estimated cost before batch start: "{N} images × ~$0.05 = ~${total}"
- Rate limiting: respect 10 IPM (Tier 1), sequential generation with 6-second delay between images

### Single Image Generation & Regeneration
- "Generate Image" button on CodexEntityDetail when entity has placeholder
- "Regenerate" button when entity already has AI image — replaces cached image
- Single generation per request — no multiple variants
- No manual prompt editing — prompts auto-generated from entity attributes
- Loading spinner replaces placeholder during generation (optimistic: show spinner immediately)

### Claude's Discretion
- Exact prompt template wording for each entity type (use research findings as starting point)
- Whether to store prompt templates in Python dict or separate JSON file
- Exact spinner/loading animation design during generation
- Whether metadata sidecar is .json or embedded in image EXIF
- Exact error toast message wording
- Whether to show generation timestamp on entity detail

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Codex System (EXTEND these)
- `server/tools/ldm/services/codex_service.py` — CodexService: entity lookup, categories, FAISS search. Add image generation trigger.
- `server/tools/ldm/schemas/codex.py` — CodexEntity schema with `image_texture` field. Add `ai_generated_image` field.
- `server/tools/ldm/routes/codex.py` — Codex API routes. Add generate-image and batch-generate endpoints.
- `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` — 451 lines. Entity detail with DDS image display + PlaceholderImage fallback. Add generate/regenerate button.
- `locaNext/src/lib/components/ldm/CodexPage.svelte` — Entity grid with thumbnails. Add batch generate button + progress bar.
- `locaNext/src/lib/components/ldm/PlaceholderImage.svelte` — SVG placeholder per entity type. This gets replaced by AI images.
- `locaNext/src/lib/components/ldm/EntityCard.svelte` — Entity type icons + color mapping. Reuse colors for prompt styling.

### Image Serving (REUSE pipeline)
- `server/tools/ldm/routes/mapdata.py` — GET /mapdata/thumbnail/{texture_name} endpoint. Reference for image serving pattern.
- `server/tools/ldm/services/media_converter.py` — 593 lines. DDS→PNG conversion + LRU cache. Reference for caching pattern.
- `server/tools/ldm/services/mapdata_service.py` — MapDataService: image/audio resolution from metadata. Reference for image lookup chain.

### Progress Tracking (REUSE for batch)
- `server/utils/progress_tracker.py` — TrackedOperation context manager + WebSocket events. Use for batch generation progress.
- `server/utils/websocket.py` lines 244-318 — WebSocket event emitters (operation_start, progress_update, operation_complete).
- `server/api/progress_operations.py` — Progress polling API endpoints.

### Entity Attributes (INPUT for prompts)
- `server/tools/ldm/services/gamedata_browse_service.py` lines 24-38 — EDITABLE_ATTRS mapping per entity type.
- `server/tools/ldm/services/gamedata_tree_service.py` — TreeNode schema with attributes dict.
- `tests/fixtures/mock_gamedata/StaticInfo/` — All mock XML files with entity attribute examples.

### Nano Banana / Gemini API (EXTERNAL)
- Skill docs: `~/.claude/skills/nano-banana/SKILL.md` — Full Gemini image generation API reference
- Model: `gemini-3-pro-image-preview` via `google-genai` Python SDK
- Config: `types.GenerateContentConfig(response_modalities=['IMAGE'], image_config=types.ImageConfig(aspect_ratio, image_size))`

### Async Patterns (REUSE)
- `server/tools/ldm/services/ai_suggestion_service.py` — httpx async pattern with timeout + graceful fallback. Reference for Gemini calls.
- `server/tools/ldm/routes/tm_indexes.py` lines 64-92 — asyncio.to_thread pattern for blocking work. Use for Gemini SDK calls.
- `server/tools/ldm/maintenance/manager.py` — Batch queue with priority + asyncio.gather. Reference for batch generation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **TrackedOperation**: Progress tracking + WebSocket events — use for batch generation
- **MediaConverter caching**: LRU + disk cache pattern — reference for AI image cache
- **CodexEntityDetail.svelte**: Image display with PlaceholderImage fallback — injection point for AI images
- **CodexPage.svelte**: Entity grid with `failedImages` Set — add AI image priority
- **EntityCard.svelte**: Entity type colors — use for prompt styling keywords
- **ai_suggestion_service.py**: httpx async + timeout + graceful fallback — reference for Gemini client
- **gamedata_browse_service.py**: EDITABLE_ATTRS — attribute extraction for prompt building

### Established Patterns
- Svelte 5 Runes: $state(), $derived(), $effect() — mandatory
- Carbon Components: Button, ProgressBar, InlineNotification, ToastNotification
- Optimistic UI: show spinner immediately, revert on failure
- Logger: loguru only, never print()
- API calls: fetch + getAuthHeaders + JSON + AbortController
- WebSocket: Socket.IO for real-time progress updates

### Integration Points
- CodexEntityDetail.svelte: Replace `PlaceholderImage` with AI image when available
- CodexPage.svelte: Add "Generate All" button per category
- codex_service.py: Add method to check/load AI-generated images
- New ai_image_service.py: Gemini client + prompt builder + cache manager
- New routes: POST /codex/generate-image/{strkey}, POST /codex/batch-generate, GET /codex/image-gen/status
- New endpoint: GET /codex/generated-image/{strkey} — serve cached AI image

</code_context>

<specifics>
## Specific Ideas

- Entity-type prompt templates derived from 6-agent swarm research with concrete examples per type
- Grade-based glow intensity: Common=dull, Uncommon=slight, Rare=bright, Epic=intense, Legendary=golden divine
- Element color mapping: Fire=red-orange, Ice=cyan-blue, Lightning=yellow, Darkness=purple, Light=golden
- Character prompts include Race + Job + Age for authentic diversity
- Region prompts include RegionType (Town/Field/Dungeon) for appropriate atmosphere
- Cost estimation before batch: transparent pricing for user decision-making
- Sequential batch with 6-second delay respects Tier 1 rate limit (10 IPM)

</specifics>

<deferred>
## Deferred Ideas

- Multi-variant generation (generate 3-4 options, user picks best) — future enhancement
- Manual prompt editing for power users — future enhancement
- Image upscaling (1K→2K→4K) via Gemini edit API — future enhancement
- Style consistency across entity types (style reference image) — future enhancement
- Image generation for non-Codex entities (GameData tree nodes) — separate phase

</deferred>

---

*Phase: 31-codex-ai-image-generation*
*Context gathered: 2026-03-16 via swarm research + auto-discuss*
