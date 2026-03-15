# Phase 17: AI Translation Suggestions - Research

**Researched:** 2026-03-15
**Domain:** AI-powered translation suggestions via local Qwen3 LLM + Model2Vec embeddings
**Confidence:** HIGH

## Summary

Phase 17 adds a new "AI Suggestions" tab to the existing RightPanel, showing ranked translation suggestions when a translator selects a segment. The backend creates a new `ai_suggestion_service.py` that orchestrates three steps: (1) find similar translated segments via Model2Vec + FAISS, (2) detect entity context via existing GlossaryService, (3) generate ranked suggestions via Qwen3/Ollama with confidence scores. The frontend adds a new `AISuggestionsTab.svelte` component that follows the exact same patterns as `TMTab.svelte` (card-based list, click-to-apply).

This phase is a natural extension of Phase 13 (AI Summaries) which already proved the Qwen3/Ollama integration pattern. The key differences: (1) structured output returns multiple ranked suggestions instead of a single summary, (2) confidence scoring blends embedding similarity with LLM certainty, (3) debouncing is critical because suggestion generation takes 2-5 seconds vs the 1-2 second summary generation.

**Primary recommendation:** Add a new tab to RightPanel (not a new panel). Backend service follows the singleton pattern from `AISummaryService`. Use 500ms debounce + request cancellation + in-memory cache to prevent UI freezes during rapid navigation.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AISUG-01 | AI translation suggestions appear in a right-side panel for the selected segment using Qwen3 | New "AI Suggestions" tab in existing RightPanel. Backend `ai_suggestion_service.py` calls Ollama REST API. Follows proven AISummaryService pattern. |
| AISUG-02 | Suggestions ranked with confidence scores (embedding similarity + LLM certainty blend) | Model2Vec finds top-K similar segments from FAISS index. Qwen3 returns structured JSON with per-suggestion confidence. Final score = weighted blend (0.4 * embedding_sim + 0.6 * llm_confidence). |
| AISUG-03 | User clicks a suggestion to apply it to the translation field (never auto-replace) | Identical to TMTab's `applyTM` event dispatch pattern. Click dispatches event up through RightPanel -> GridPage -> VirtualGrid.applyTMToRow(). No new mechanism needed. |
| AISUG-04 | AI suggestions consider context (entity type, parent hierarchy, surrounding segments) | Prompt includes: entity_type from CategoryService, surrounding segment source/target pairs (2 before + 2 after), detected entity names from GlossaryService. |
| AISUG-05 | Graceful fallback when Qwen3/Ollama is unavailable (show "AI unavailable" state, no crash) | Identical to ContextTab's existing `aiStatus === 'unavailable'` pattern. httpx ConnectError/TimeoutException caught, returns `{suggestions: [], status: "unavailable"}`. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Qwen3-4B via Ollama | qwen3:4b | LLM inference for generating suggestions | Already deployed in v2.0 Phase 13. 117 tok/s on RTX 4070 Ti. Local, zero cloud dependency. |
| httpx | existing | Async HTTP client for Ollama REST API | Already used in `ai_summary_service.py`. Supports async/await, timeouts, structured error handling. |
| Model2Vec + FAISS | existing | Embedding similarity for finding related segments | Already used for TM search. 256-dim embeddings, 79x faster than Qwen. |
| Pydantic | existing | Structured JSON schema for Ollama output | Already used for `AISummaryResponse`. Qwen3 supports Pydantic schema constraint via `format` parameter. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Carbon Components Svelte | existing | UI components (InlineLoading, Tag, icons) | All UI states: loading, empty, unavailable, results |
| loguru | existing | Structured logging | All service operations. Never print(). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Qwen3 structured output | Free-text LLM output + regex parsing | Structured JSON via Pydantic schema is more reliable. Free-text requires fragile parsing. |
| In-memory cache | Redis/SQLite cache | Overkill for single-user desktop app. In-memory dict per service instance is sufficient. |
| New panel component | Extend ContextTab | Separate tab is cleaner -- ContextTab already handles entity detection + AI summaries. Suggestion is a distinct workflow. |

## Architecture Patterns

### Recommended Project Structure

```
server/tools/ldm/services/
  ai_suggestion_service.py     # NEW -- Qwen3 suggestion generation + caching
server/tools/ldm/routes/
  ai_suggestions.py            # NEW -- REST endpoint for suggestion requests
locaNext/src/lib/components/ldm/
  AISuggestionsTab.svelte      # NEW -- Suggestions tab component
  RightPanel.svelte            # MODIFIED -- add 5th tab "AI Suggestions"
locaNext/src/lib/components/pages/
  GridPage.svelte              # MODIFIED -- handle applySuggestion event
```

### Pattern 1: Service Singleton (follow AISummaryService)

**What:** Backend service as a singleton with in-memory cache, graceful Ollama fallback, and Pydantic schema constraint.
**When to use:** For any AI inference service.
**Example:**
```python
# Source: server/tools/ldm/services/ai_summary_service.py (existing pattern)
class AISuggestionService:
    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen3:4b"
    TIMEOUT = 15.0  # Longer than summary -- suggestions need more tokens

    def __init__(self):
        self._cache: Dict[str, list] = {}
        self._available: Optional[bool] = None

    async def generate_suggestions(
        self, string_id: str, source_text: str, target_lang: str,
        entity_type: str, surrounding_context: list[dict],
    ) -> dict:
        cache_key = f"{string_id}:{target_lang}"
        if cache_key in self._cache:
            return {"suggestions": self._cache[cache_key], "status": "cached"}

        # Step 1: Find similar segments via Model2Vec + FAISS
        similar = self._find_similar_segments(source_text)

        # Step 2: Build context-enriched prompt
        prompt = self._build_prompt(source_text, target_lang, entity_type,
                                     surrounding_context, similar)

        # Step 3: Call Ollama with structured output
        try:
            result = await self._call_ollama(prompt)
            self._cache[cache_key] = result
            return {"suggestions": result, "status": "generated"}
        except (httpx.ConnectError, httpx.TimeoutException):
            self._available = False
            return {"suggestions": [], "status": "unavailable"}
```

### Pattern 2: Tab in RightPanel (follow TMTab)

**What:** New tab component with click-to-apply interaction.
**When to use:** For any content that appears in the right side panel based on row selection.
**Example:**
```svelte
<!-- Source: locaNext/src/lib/components/ldm/TMTab.svelte (existing pattern) -->
<!-- AISuggestionsTab follows identical structure -->
<script>
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();

  let { selectedRow = null } = $props();
  let suggestions = $state([]);
  let loading = $state(false);
  let status = $state(null);

  function handleApplySuggestion(suggestion) {
    dispatch('applySuggestion', { target: suggestion.text });
  }
</script>
```

### Pattern 3: Debounced Fetch with Request Cancellation

**What:** Prevent queueing dozens of Ollama requests during rapid navigation.
**When to use:** Any AI inference triggered by row selection.
**Example:**
```svelte
<script>
  let abortController = $state(null);
  let debounceTimer = $state(null);

  $effect(() => {
    const stringId = selectedRow?.string_id;
    if (!stringId) { suggestions = []; return; }

    // Cancel previous request
    if (abortController) abortController.abort();
    if (debounceTimer) clearTimeout(debounceTimer);

    // Debounce 500ms
    debounceTimer = setTimeout(async () => {
      abortController = new AbortController();
      loading = true;
      try {
        const response = await fetch(url, {
          headers: getAuthHeaders(),
          signal: abortController.signal
        });
        // ... handle response
      } catch (err) {
        if (err.name !== 'AbortError') { error = err.message; }
      } finally {
        loading = false;
      }
    }, 500);
  });
</script>
```

### Anti-Patterns to Avoid

- **Triggering Ollama on every keystroke:** Source text changes during editing should NOT trigger suggestions. Only row SELECTION triggers suggestions.
- **Auto-replacing existing translations:** The `applySuggestion` event MUST set the cell value only when the cell is empty or when explicitly clicked. Never overwrite existing content silently.
- **Blocking the main thread on Ollama:** All Ollama calls are async. The UI must show "loading" state and remain interactive during inference.
- **Creating a new panel instead of a tab:** The RightPanel already has a tabbed architecture (TM, Image, Audio, AI Context). Adding a 5th tab is the correct approach.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM inference | Custom model loading | Ollama REST API (`/api/generate`) | Already deployed, handles GPU allocation, model management |
| Embedding similarity | Custom cosine similarity loop | Existing EmbeddingEngine + FAISS index | Already handles Model2Vec loading, dimensionality, batch encoding |
| Entity context detection | Custom text scanning | GlossaryService + Aho-Corasick automaton | Already indexed, O(text_length) scan |
| Structured LLM output | Regex parsing of free text | Pydantic schema via Ollama `format` param | Guarantees valid JSON structure |
| Click-to-apply mechanism | New event chain | Existing `applyTM` pattern (dispatch up through RightPanel -> GridPage -> VirtualGrid) | Proven in TMTab, exact same data flow |
| Debouncing | Custom timer management | Standard `setTimeout` + `AbortController` pattern | No library needed for simple debounce in a Svelte $effect |
| Category/entity type | Custom classification | CategoryService.categorize_by_stringid() | Already O(k) prefix lookup, 7 categories |

**Key insight:** This phase is 80% integration of existing services (Ollama, Model2Vec, GlossaryService, CategoryService) with a new orchestration layer (AISuggestionService) and a new UI tab. Very little new invention needed.

## Common Pitfalls

### Pitfall 1: Ollama Request Queue Backup
**What goes wrong:** Rapid row navigation queues 10+ Ollama requests. Each takes 2-5 seconds. GPU memory pressure causes OOM or extreme slowness.
**Why it happens:** Qwen3-4B generates ~200 tokens per suggestion request. At 117 tok/s, that's ~2 seconds minimum. Users navigate faster than inference.
**How to avoid:** (1) Debounce 500ms. (2) Cancel in-flight requests via AbortController. (3) Limit concurrent Ollama requests to 1. (4) Cache results per source_text hash.
**Warning signs:** GPU utilization stays at 100% after user stops navigating. UI shows stale loading indicators.

### Pitfall 2: Confidence Score Drift
**What goes wrong:** LLM-reported confidence scores are not calibrated. Qwen3-4B might report 0.95 confidence for a mediocre suggestion.
**Why it happens:** LLM confidence is a logit-based probability, not a quality metric. It reflects token prediction certainty, not translation accuracy.
**How to avoid:** Blend scores: `final_score = 0.4 * embedding_similarity + 0.6 * llm_confidence`. Clamp to [0.0, 1.0]. Show as percentage badge, not absolute quality.
**Warning signs:** All suggestions showing 90%+ confidence. Users losing trust in scores.

### Pitfall 3: Context Window Overflow
**What goes wrong:** Including too much surrounding context (10+ segments) overflows Qwen3-4B's effective context window, degrading output quality.
**Why it happens:** Qwen3-4B has 32K context but quality degrades significantly beyond 4K tokens in practice.
**How to avoid:** Limit context to: source text (~100 tokens) + 4 surrounding segments (~200 tokens) + entity metadata (~50 tokens) + similar segments (~200 tokens) = ~550 tokens input. Leave room for output.
**Warning signs:** Suggestions become generic or repetitive regardless of context.

### Pitfall 4: Stale Cache Serving Wrong Suggestions
**What goes wrong:** User edits the source text of a segment, but cached suggestions are still based on the old source text.
**Why it happens:** Cache key is `string_id:target_lang` but source text can change during editing.
**How to avoid:** Cache key MUST include a hash of the source text: `f"{string_id}:{target_lang}:{hash(source_text)}"`. Clear cache for a StringID when its source is modified.
**Warning signs:** Suggestions don't match the visible source text.

## Code Examples

### Backend: Structured Ollama Output for Suggestions

```python
# Source: server/tools/ldm/services/ai_summary_service.py (adapted pattern)
from pydantic import BaseModel
from typing import List

class SuggestionItem(BaseModel):
    text: str
    confidence: float
    reasoning: str

class AISuggestionResponse(BaseModel):
    suggestions: List[SuggestionItem]

# In generate_suggestions():
prompt = self._build_prompt(source_text, target_lang, entity_type, context, similar)
response = await client.post(
    self.OLLAMA_URL,
    json={
        "model": self.MODEL,
        "prompt": prompt,
        "stream": False,
        "format": AISuggestionResponse.model_json_schema(),
        "options": {
            "temperature": 0.7,  # Higher than summary (0.3) for diverse suggestions
            "num_predict": 500,  # More tokens than summary (200)
        },
    },
)
```

### Backend: Context-Enriched Prompt

```python
def _build_prompt(self, source_text, target_lang, entity_type,
                   surrounding, similar_segments):
    similar_examples = "\n".join(
        f"  Source: {s['source']} -> Target: {s['target']} (similarity: {s['score']:.0%})"
        for s in similar_segments[:3]
    )
    context_lines = "\n".join(
        f"  {c['source']} -> {c['target']}"
        for c in surrounding[:4]
    )
    return (
        f"You are a professional game localization translator.\n"
        f"Generate 3 translation suggestions for the source text.\n\n"
        f"Source text: {source_text[:500]}\n"
        f"Target language: {target_lang}\n"
        f"Content type: {entity_type}\n\n"
        f"Similar translated segments:\n{similar_examples}\n\n"
        f"Surrounding context:\n{context_lines}\n\n"
        f"For each suggestion, provide the translated text, a confidence score "
        f"(0.0-1.0), and a brief reasoning for why this translation is appropriate."
    )
```

### Frontend: Suggestion Card (follows TMTab card pattern)

```svelte
<!-- Follow TMTab.svelte card structure exactly -->
<button
  class="suggestion-card"
  onclick={() => handleApplySuggestion(suggestion)}
  title="Click to apply this suggestion"
>
  <div class="suggestion-header">
    <span class="confidence-badge" style="background: {getConfidenceColor(suggestion.confidence)};">
      {Math.round(suggestion.confidence * 100)}%
    </span>
    <span class="confidence-label">{getConfidenceLabel(suggestion.confidence)}</span>
  </div>
  <div class="suggestion-text">{suggestion.text}</div>
  <div class="suggestion-reasoning">{suggestion.reasoning}</div>
</button>
```

### Frontend: Apply Suggestion (reuse applyTM mechanism)

```javascript
// In GridPage.svelte -- identical to handleApplyTMFromPanel
function handleApplySuggestionFromPanel(event) {
  const { target } = event.detail;
  if (virtualGrid && sidePanelSelectedRow) {
    virtualGrid.applyTMToRow(sidePanelSelectedRow.line_number, target);
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TM-only suggestions | TM + AI hybrid suggestions | 2024-2025 (industry shift) | Users expect AI alternatives alongside TM matches |
| Cloud MT (DeepL/Google) | Local LLM (Qwen3/Llama) | 2024-2025 (model quality) | Enables offline AI, privacy compliance |
| Free-text LLM output | Structured JSON output (Pydantic schema) | 2024 (Ollama `format` param) | Reliable parsing, no regex needed |

**Already built (reuse, don't rebuild):**
- Ollama integration: `ai_summary_service.py` (Phase 13)
- Embedding similarity: `embedding_engine.py` + FAISS indexes (v1.0)
- Entity detection: `glossary_service.py` + Aho-Corasick (v1.0)
- Category classification: `category_service.py` (Phase 16)
- Right panel tabbed UI: `RightPanel.svelte` with 4 existing tabs
- Click-to-apply: `TMTab.svelte` -> `applyTM` event chain

## Open Questions

1. **Number of suggestions to generate**
   - What we know: TMTab shows up to 5 matches. LLM can generate as many as asked.
   - What's unclear: Optimal number for UX. More suggestions = more Ollama tokens = slower.
   - Recommendation: Generate 3 suggestions per request. Fast enough (~3s), provides variety.

2. **Similar segments source for context**
   - What we know: FAISS index exists for TM entries. Mock data creates language data with translations.
   - What's unclear: Should we use TM entries, language data rows, or both for finding similar segments?
   - Recommendation: Use TM entries first (existing API). Fall back to language data rows if TM is empty.

3. **Target language detection**
   - What we know: File metadata includes language info. Row data has `source` and `target` fields.
   - What's unclear: How to determine which target language the user is translating into.
   - Recommendation: Derive from file metadata (language pair stored at file level) or use active project settings.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (frontend) + pytest (backend, if test dir exists) |
| Config file | `locaNext/playwright.config.ts` |
| Quick run command | `cd locaNext && npx playwright test tests/ai-suggestions.spec.ts --headed` |
| Full suite command | `cd locaNext && npx playwright test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AISUG-01 | AI suggestions tab appears in RightPanel, shows results on row select | e2e | `cd locaNext && npx playwright test tests/ai-suggestions.spec.ts -x` | No -- Wave 0 |
| AISUG-02 | Suggestions show ranked confidence scores | e2e | `cd locaNext && npx playwright test tests/ai-suggestions.spec.ts -x` | No -- Wave 0 |
| AISUG-03 | Clicking suggestion applies to translation field | e2e | `cd locaNext && npx playwright test tests/ai-suggestions.spec.ts -x` | No -- Wave 0 |
| AISUG-04 | Suggestions include entity context in prompts | unit (backend) | Manual verification via prompt inspection in logs | Manual-only (prompt content is internal) |
| AISUG-05 | Graceful fallback when Ollama unavailable | e2e | `cd locaNext && npx playwright test tests/ai-suggestions.spec.ts -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd locaNext && npx playwright test tests/ai-suggestions.spec.ts -x`
- **Per wave merge:** `cd locaNext && npx playwright test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `locaNext/tests/ai-suggestions.spec.ts` -- covers AISUG-01, AISUG-02, AISUG-03, AISUG-05
- [ ] Backend service unit test (if pytest infrastructure exists) for prompt construction and cache behavior

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/services/ai_summary_service.py` -- Existing Qwen3/Ollama integration pattern (singleton, cache, graceful fallback)
- `locaNext/src/lib/components/ldm/RightPanel.svelte` -- 4-tab architecture, resize/collapse behavior
- `locaNext/src/lib/components/ldm/TMTab.svelte` -- Click-to-apply pattern, card-based suggestion display
- `locaNext/src/lib/components/ldm/ContextTab.svelte` -- Row selection effect, API fetch, unavailable state handling
- `locaNext/src/lib/components/pages/GridPage.svelte` -- Row selection -> side panel data flow, applyTM handler
- `server/tools/ldm/routes/context.py` -- REST endpoint pattern combining multiple services
- `.planning/research/ARCHITECTURE.md` -- v3.0 AI suggestions data flow diagram
- `.planning/research/PITFALLS.md` -- Pitfall 3 (rate limiting) prevention strategy

### Secondary (MEDIUM confidence)
- `.planning/research/FEATURES.md` -- Competitive landscape (T5: AI translation suggestions rationale)
- `.planning/research/STACK.md` -- Existing stack validation (Qwen3-4B, Model2Vec, FAISS)

### Tertiary (LOW confidence)
- Confidence score blending weights (0.4/0.6) -- educated estimate, may need tuning
- Optimal debounce timing (500ms) -- reasonable default, may need adjustment based on UX testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already deployed and proven in v2.0
- Architecture: HIGH -- all integration points verified against existing source code
- Pitfalls: HIGH -- rate limiting pitfall documented in v3.0 research, others derived from AISummaryService patterns
- UI patterns: HIGH -- TMTab and ContextTab provide exact templates

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain, no external dependencies)
