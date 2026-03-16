# Phase 13: AI Summaries - Research

**Researched:** 2026-03-15
**Domain:** Local LLM integration (Ollama + Qwen3) for contextual entity summaries
**Confidence:** HIGH

## Summary

Phase 13 adds AI-generated contextual summaries for game entities (characters, items, regions) powered by local Qwen3 via Ollama. The architecture is straightforward: a new `AISummaryService` on the backend calls Ollama's REST API via httpx (already installed), caches results per StringID in an in-memory dict, and exposes a new endpoint that the existing ContextTab consumes. The ContextTab already renders entity cards -- AI summaries add a new section below the entity metadata.

The critical design decisions are: (1) use httpx directly against `http://localhost:11434/api/generate` -- do NOT install the `ollama` Python package; (2) use Ollama's structured output support with a JSON schema in the `format` parameter to get reliable `{"summary": "..."}` responses; (3) cache per StringID in a simple dict (not database) for this phase; (4) graceful fallback when Ollama is unavailable -- the ContextTab shows an "AI unavailable" badge, not errors or spinners.

The main risk is Qwen3-4B producing unreliable JSON even with structured output constraints. Mitigation: use the `format` parameter with an explicit JSON schema (not just `"json"`), set temperature to 0.3, and add a try/except around JSON parsing with a fallback to raw text extraction. The 117 tok/s performance on RTX 4070 Ti means a 200-token summary takes under 2 seconds -- acceptable for a non-blocking async call.

**Primary recommendation:** Build AISummaryService as a standalone singleton service with httpx async client, structured JSON schema in the format parameter, in-memory dict cache, and a 10-second timeout. Wire it into the existing `/context/{string_id}` response as a new `ai_summary` field.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AISUM-01 | Qwen3-4B/8B endpoint via Ollama responds with structured JSON | Ollama REST API `/api/generate` with `format` parameter accepting JSON schema. Use httpx async POST. Temperature 0.3, num_predict 200. |
| AISUM-02 | Character/item/region metadata generates 2-line contextual summary | Prompt template includes entity type, name, source text, and game context. Schema constrains output to `{"summary": "string", "entity_type": "string"}`. |
| AISUM-03 | Summary appears in ContextTab for selected string | Extend existing `/context/{string_id}` response with `ai_summary` field. ContextTab renders summary below entity cards. |
| AISUM-04 | Summaries cache per StringID to avoid re-generation | In-memory `dict[str, str]` in AISummaryService. Cache hit returns instantly. No TTL needed (summaries are deterministic for same input). |
| AISUM-05 | Graceful fallback when Ollama is unavailable (show "AI unavailable" badge) | httpx ConnectError / TimeoutException caught at service level. Returns `{"ai_summary": null, "ai_status": "unavailable"}`. Frontend shows badge. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 (installed) | Async HTTP client for Ollama REST API | Already a project dependency. Zero new packages. Async-native for FastAPI. |
| Ollama | latest (local binary) | Local LLM server hosting Qwen3 | Already running locally. REST API at localhost:11434. |
| Qwen3-4B | via Ollama | Text generation for summaries | 117 tok/s on RTX 4070 Ti. Fast enough for real-time summaries. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | (installed) | JSON schema generation for structured output | Generate schema from Pydantic model, pass to Ollama `format` parameter |
| loguru | (installed) | Logging for AI service | Standard project logging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx direct | `ollama` Python package | Adds dependency for 1 endpoint call. httpx is already installed. |
| httpx direct | LangChain/LlamaIndex | Massive overkill. We need one prompt-in, JSON-out call. No chains, no RAG. |
| In-memory dict cache | Database table | Over-engineered for summary caching. Dict is simpler, clears on restart which is fine. |
| Qwen3-4B | Qwen3-8B | 8B is higher quality but slower. 4B at 117 tok/s is fast enough. Can switch model name easily. |

**Installation:**
```bash
# NOTHING to install. httpx is already in requirements.txt.
# Ollama + Qwen3 model must be available at localhost:11434.
# Pull model if needed: ollama pull qwen3:4b
```

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/services/
    ai_summary_service.py     # NEW: AISummaryService singleton
server/tools/ldm/routes/
    context.py                # MODIFY: Add ai_summary to response
locaNext/src/lib/components/ldm/
    ContextTab.svelte         # MODIFY: Add AI summary section + badge
```

### Pattern 1: AISummaryService Singleton
**What:** Standalone service with async httpx client, prompt template, cache dict, and graceful fallback.
**When to use:** For all AI summary generation requests.
**Example:**
```python
# Source: Ollama REST API docs + project singleton pattern
from __future__ import annotations

from typing import Dict, Optional
import httpx
from loguru import logger
from pydantic import BaseModel

class AISummaryResponse(BaseModel):
    """Schema passed to Ollama format parameter."""
    summary: str
    entity_type: str

class AISummaryService:
    """Generates AI contextual summaries via local Ollama/Qwen3."""

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen3:4b"
    TIMEOUT = 10.0  # seconds

    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}
        self._available: Optional[bool] = None

    async def generate_summary(
        self, string_id: str, entity_name: str, entity_type: str, source_text: str
    ) -> dict:
        # Cache hit
        if string_id in self._cache:
            return {"ai_summary": self._cache[string_id], "ai_status": "cached"}

        # Build prompt
        prompt = self._build_prompt(entity_name, entity_type, source_text)

        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    self.OLLAMA_URL,
                    json={
                        "model": self.MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": AISummaryResponse.model_json_schema(),
                        "options": {"temperature": 0.3, "num_predict": 200},
                    },
                )
                response.raise_for_status()
                data = response.json()
                # Parse structured output
                import json
                parsed = json.loads(data["response"])
                summary = parsed.get("summary", data["response"])
                self._cache[string_id] = summary
                self._available = True
                return {"ai_summary": summary, "ai_status": "generated"}
        except (httpx.ConnectError, httpx.TimeoutException):
            self._available = False
            return {"ai_summary": None, "ai_status": "unavailable"}
        except Exception as e:
            logger.warning(f"[AI] Summary generation failed: {e}")
            return {"ai_summary": None, "ai_status": "error"}

    def _build_prompt(self, name: str, entity_type: str, source_text: str) -> str:
        return (
            f"You are a game localization assistant. "
            f"Generate a brief 2-line contextual summary for this {entity_type}.\n\n"
            f"Name: {name}\nType: {entity_type}\nSource text: {source_text}\n\n"
            f"Return JSON with 'summary' (2 lines max) and 'entity_type'."
        )

    def clear_cache(self) -> None:
        self._cache.clear()

    def get_status(self) -> dict:
        return {
            "available": self._available,
            "cache_size": len(self._cache),
            "model": self.MODEL,
        }
```

### Pattern 2: Extend Existing Context Endpoint
**What:** Add `ai_summary` field to the existing `/context/{string_id}` response rather than creating a separate endpoint. This keeps the ContextTab's single fetch pattern intact.
**When to use:** When the context endpoint is called with a string_id that has entity metadata.
**Example:**
```python
# In context.py route -- extend the existing get_context_by_string_id
@router.get("/context/{string_id}")
async def get_context_by_string_id(string_id: str, source_text: str = Query(default="")):
    service = get_context_service()
    result = service.resolve_context_for_row(string_id, source_text)
    response = result.to_dict()

    # Add AI summary (non-blocking, graceful fallback)
    ai_service = get_ai_summary_service()
    entity_name = result.entities[0].name if result.entities else string_id
    entity_type = result.entities[0].entity_type if result.entities else "unknown"
    ai_result = await ai_service.generate_summary(string_id, entity_name, entity_type, source_text)
    response["ai_summary"] = ai_result["ai_summary"]
    response["ai_status"] = ai_result["ai_status"]

    return response
```

### Pattern 3: Frontend AI Badge in ContextTab
**What:** ContextTab shows a summary section with "AI unavailable" badge when Ollama is down.
**When to use:** Always -- the badge state is driven by the `ai_status` field in the response.
**Example:**
```svelte
<!-- In ContextTab.svelte -->
{#if aiStatus === 'unavailable'}
  <div class="ai-badge-unavailable" data-testid="ai-unavailable-badge">
    <WarningAlt size={16} />
    <span>AI unavailable</span>
  </div>
{:else if aiSummary}
  <div class="ai-summary" data-testid="ai-summary">
    <span class="ai-label">AI Summary</span>
    <p class="ai-text">{aiSummary}</p>
  </div>
{/if}
```

### Anti-Patterns to Avoid
- **Separate AI endpoint:** Do NOT create `/api/ldm/ai/summary/{string_id}` -- adds a second network request from ContextTab. Extend the existing context endpoint instead.
- **Blocking on AI:** Do NOT make the context response wait for AI if Ollama is slow. If AI takes > 10s, return context without summary and let frontend show "generating..." only if needed.
- **Database caching:** Do NOT add an `ai_summary` column to the rows table. In-memory dict is sufficient. Summaries are cheap to regenerate.
- **ollama Python package:** Do NOT install it. httpx does the same thing with zero new dependencies.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema for structured output | Manual JSON schema dict | `Pydantic.model_json_schema()` | Pydantic generates valid JSON Schema from Python types. Already a dependency. |
| HTTP client for Ollama | requests / urllib | httpx async | Already installed, async-native, matches FastAPI patterns |
| LLM orchestration | Custom retry/chain logic | Simple try/except with timeout | We need ONE call. No chains, no agents, no RAG. |
| Summary formatting | Complex post-processing | Prompt engineering + schema constraint | Let the model do the formatting. Schema enforces structure. |

**Key insight:** This is the simplest possible LLM integration -- one prompt in, one JSON out. Any abstraction beyond httpx + try/except is over-engineering.

## Common Pitfalls

### Pitfall 1: Ollama Not Running
**What goes wrong:** httpx.ConnectError on POST to localhost:11434. Unhandled exception crashes the context endpoint.
**Why it happens:** Ollama is not always running. Users may not have it installed.
**How to avoid:** Catch `httpx.ConnectError` and `httpx.TimeoutException` explicitly. Return `{"ai_summary": null, "ai_status": "unavailable"}`. Frontend shows badge, not error.
**Warning signs:** Context endpoint returns 500 instead of 200 with empty AI fields.

### Pitfall 2: Qwen3 JSON Output Unreliability
**What goes wrong:** Even with `format` parameter, small models occasionally produce malformed JSON or unexpected fields.
**Why it happens:** Qwen3-4B is a small model. Constrained decoding helps but isn't perfect.
**How to avoid:** Use Ollama's `format` parameter with a Pydantic-generated JSON schema (not just `"json"`). Parse with `json.loads()` in a try/except. If parsing fails, fall back to raw `data["response"]` as plain text.
**Warning signs:** `json.JSONDecodeError` in logs.

### Pitfall 3: Timeout Blocking Context Response
**What goes wrong:** AI generation takes 5-10 seconds, making the entire context panel slow to load.
**Why it happens:** Cold model load or GPU contention.
**How to avoid:** Set httpx timeout to 10 seconds. Consider making AI summary a separate async field that loads after initial context. For Phase 13, a 10s timeout with graceful fallback is acceptable.
**Warning signs:** ContextTab shows loading spinner for > 3 seconds consistently.

### Pitfall 4: Cache Key Collisions
**What goes wrong:** Same StringID with different source text produces different summaries but cache returns stale one.
**Why it happens:** Cache keyed on StringID only, but source text can change.
**How to avoid:** For Phase 13, StringID-only cache is correct -- the source text for a given StringID doesn't change within a session. If source text editing is added later, cache should be invalidated on row edit.
**Warning signs:** Summary content doesn't match displayed source text.

### Pitfall 5: httpx Client Lifecycle
**What goes wrong:** Creating a new `httpx.AsyncClient()` per request adds overhead and can leak connections.
**Why it happens:** Using `async with httpx.AsyncClient()` in each call creates/destroys the connection pool each time.
**How to avoid:** Create the httpx.AsyncClient once in `__init__` and reuse it. Close it in a cleanup method. OR use the context manager pattern per-call (simpler, acceptable for low-frequency calls like AI summaries).
**Warning signs:** "Too many open connections" errors under load.

## Code Examples

Verified patterns from official sources and project conventions:

### Ollama REST API Call with Structured Output
```python
# Source: https://docs.ollama.com/capabilities/structured-outputs
# Ollama supports JSON schema in the format parameter since v0.5
import httpx
import json
from pydantic import BaseModel

class SummarySchema(BaseModel):
    summary: str
    entity_type: str

async def call_ollama(prompt: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:4b",
                "prompt": prompt,
                "stream": False,
                "format": SummarySchema.model_json_schema(),
                "options": {"temperature": 0.3, "num_predict": 200},
            },
        )
        resp.raise_for_status()
        return json.loads(resp.json()["response"])
```

### Graceful Fallback Pattern
```python
# Source: Project convention -- ContextService pattern from Phase 5.1
try:
    result = await call_ollama(prompt)
    return {"ai_summary": result["summary"], "ai_status": "generated"}
except (httpx.ConnectError, httpx.TimeoutException):
    logger.debug("[AI] Ollama not available")
    return {"ai_summary": None, "ai_status": "unavailable"}
except (json.JSONDecodeError, KeyError) as e:
    logger.warning(f"[AI] Failed to parse response: {e}")
    return {"ai_summary": None, "ai_status": "error"}
```

### ContextTab AI Summary Section (Svelte 5)
```svelte
<!-- Source: Project convention -- ContextTab existing pattern -->
<script>
  import { WarningAlt } from "carbon-icons-svelte";
  let aiSummary = $state(null);
  let aiStatus = $state(null);

  $effect(() => {
    // Extracted from fetch response
    aiSummary = data?.ai_summary || null;
    aiStatus = data?.ai_status || null;
  });
</script>

{#if aiStatus === 'unavailable'}
  <div class="ai-badge" data-testid="ai-unavailable-badge">
    <WarningAlt size={14} />
    <span>AI unavailable</span>
  </div>
{:else if aiSummary}
  <div class="ai-summary" data-testid="ai-summary">
    <span class="summary-label">AI Summary</span>
    <p class="summary-text">{aiSummary}</p>
  </div>
{/if}
```

### Test Pattern -- Mock Ollama
```python
# Source: Project test convention from test_context_service.py
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

@pytest.mark.asyncio
async def test_generate_summary_success():
    """AI summary returns structured JSON when Ollama is available."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": json.dumps({"summary": "A brave warrior from the north.", "entity_type": "character"})
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        service = AISummaryService()
        result = await service.generate_summary("STR_01", "Varon", "character", "Varon the warrior")
        assert result["ai_summary"] == "A brave warrior from the north."
        assert result["ai_status"] == "generated"

@pytest.mark.asyncio
async def test_generate_summary_ollama_unavailable():
    """Returns unavailable status when Ollama is not running."""
    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.side_effect = httpx.ConnectError("Connection refused")
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        service = AISummaryService()
        result = await service.generate_summary("STR_01", "Varon", "character", "Varon the warrior")
        assert result["ai_summary"] is None
        assert result["ai_status"] == "unavailable"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `format: "json"` (plain JSON mode) | `format: {json_schema}` (structured output) | Ollama v0.5 (2024) | Reliable JSON structure enforcement. Use schema, not just "json". |
| `ollama` Python package | httpx direct REST | Project decision | Zero new dependencies. One endpoint call doesn't need a client library. |
| Cloud LLM APIs (OpenAI, etc.) | Local Ollama + Qwen3 | Project constraint | Zero cloud dependency, zero cost, full privacy. |

**Deprecated/outdated:**
- `format: "json"` without schema: Still works but less reliable. Use full JSON schema for consistent output.
- `ollama` Python package for simple use cases: Over-engineering when httpx is already installed.

## Open Questions

1. **Qwen3 model variant (4B vs 8B)**
   - What we know: 4B gives 117 tok/s, 8B gives ~60 tok/s (estimated). Both produce reasonable summaries.
   - What's unclear: Quality difference for game entity summaries specifically.
   - Recommendation: Start with `qwen3:4b` for speed. Model name is a constant -- trivial to switch later.

2. **Prompt template refinement**
   - What we know: Basic prompt works. Structured output with schema helps.
   - What's unclear: Optimal prompt for game localization context (different entity types need different context).
   - Recommendation: Start with a generic prompt template. Refine based on actual output quality during testing. Can add entity-type-specific prompts in a follow-up.

3. **Cache invalidation strategy**
   - What we know: In-memory dict clears on server restart. StringID-based key is correct for Phase 13.
   - What's unclear: Should cache survive restarts? Should it invalidate when source text changes?
   - Recommendation: Keep it simple -- in-memory dict, no persistence, no TTL. Revisit if users report stale summaries.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | `pytest.ini` |
| Quick run command | `python -m pytest tests/unit/ldm/test_ai_summary_service.py -x` |
| Full suite command | `python -m pytest tests/unit/ldm/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AISUM-01 | Ollama returns structured JSON via httpx | unit | `python -m pytest tests/unit/ldm/test_ai_summary_service.py::test_generate_summary_success -x` | No -- Wave 0 |
| AISUM-02 | Prompt generates 2-line summary with entity metadata | unit | `python -m pytest tests/unit/ldm/test_ai_summary_service.py::test_prompt_includes_entity_metadata -x` | No -- Wave 0 |
| AISUM-03 | Summary appears in context endpoint response | unit | `python -m pytest tests/unit/ldm/test_routes_context.py::test_context_includes_ai_summary -x` | No -- Wave 0 |
| AISUM-04 | Cache hit returns instantly without re-generation | unit | `python -m pytest tests/unit/ldm/test_ai_summary_service.py::test_cache_hit_skips_ollama -x` | No -- Wave 0 |
| AISUM-05 | Graceful fallback when Ollama unavailable | unit | `python -m pytest tests/unit/ldm/test_ai_summary_service.py::test_ollama_unavailable_returns_badge -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_ai_summary_service.py -x`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_ai_summary_service.py` -- covers AISUM-01, AISUM-02, AISUM-04, AISUM-05
- [ ] Update `tests/unit/ldm/test_routes_context.py` -- covers AISUM-03 (add test for ai_summary in response)
- [ ] No new framework install needed -- pytest + pytest-asyncio already configured

## Sources

### Primary (HIGH confidence)
- Ollama structured outputs docs: https://docs.ollama.com/capabilities/structured-outputs -- format parameter with JSON schema
- LocaNext codebase: `server/tools/ldm/services/context_service.py` -- existing singleton pattern, service structure
- LocaNext codebase: `server/tools/ldm/routes/context.py` -- existing endpoint to extend
- LocaNext codebase: `locaNext/src/lib/components/ldm/ContextTab.svelte` -- existing frontend to extend
- Project STACK.md: httpx 0.28.1 installed, Ollama REST API pattern documented

### Secondary (MEDIUM confidence)
- Ollama API docs: https://github.com/ollama/ollama/blob/main/docs/api.md -- /api/generate endpoint parameters
- Ollama blog: https://ollama.com/blog/structured-outputs -- structured output examples and best practices

### Tertiary (LOW confidence)
- Qwen3-4B summary quality for game entities -- needs prototype testing with real data (flagged in STATE.md blockers)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- httpx already installed, Ollama REST API well-documented, zero new dependencies
- Architecture: HIGH -- extending existing ContextService/ContextTab pattern, singleton service matches project conventions
- Pitfalls: HIGH -- Ollama unavailability is the primary risk, mitigation is straightforward (try/except + badge)
- Prompt engineering: MEDIUM -- basic prompt works but quality depends on Qwen3-4B's capabilities with game entity metadata

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- Ollama API is mature, httpx is stable)
