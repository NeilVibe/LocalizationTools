# Architecture Patterns -- v13.0 Production Path Resolution

**Domain:** Game localization tool -- path resolution from StringId to media files
**Researched:** 2026-03-26
**Confidence:** HIGH

## Current Architecture

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| PerforcePathService | 11 path templates, drive/branch substitution, WSL conversion | MegaIndex (provides paths), MapDataService (configures) |
| MegaIndex | 35 dicts, 7-phase build, all cross-reference chains | PerforcePathService (gets paths), MapDataService (provides data) |
| MapDataService | Image/audio context lookups, caching, fuzzy matching | MegaIndex (reads data), Routes (serves API) |
| MediaConverter | DDS->PNG, WEM->WAV conversion with caching | Routes (called by streaming endpoints) |
| mapdata routes | REST API endpoints (7 total) | MapDataService, PerforcePathService, MediaConverter |
| ImageTab.svelte | Image context display with thumbnail | mapdata API |
| AudioTab.svelte | Audio player with script text | mapdata API |
| RightPanel.svelte | Tab container for context panels | ImageTab, AudioTab, TMTab, ContextTab, AISuggestionsTab |

### Data Flow: StringId to Image

```
StringId -(C7)-> (entity_type, entity_strkey)
entity_strkey -(C1)-> KnowledgeInfo.UITextureName
UITextureName -(D9)-> DDS file Path
DDS Path -(MediaConverter)-> PNG bytes
PNG bytes -(FileResponse)-> Browser <img>
```

### Data Flow: StringId to Audio

```
StringId -(R3)-> event_name
event_name -(D10)-> WEM file Path
WEM Path -(MediaConverter)-> WAV file
WAV file -(FileResponse)-> Browser <audio>

event_name -(C4)-> Korean script (via D11->D12)
event_name -(C5)-> English script (via D11->D13)
```

## Patterns to Follow

### Pattern 1: Singleton Service with Lazy Init

All backend services use the same pattern. Follow it for any new services.

```python
_service_instance: Optional[MyService] = None

def get_my_service() -> MyService:
    global _service_instance
    if _service_instance is None:
        _service_instance = MyService()
    return _service_instance
```

### Pattern 2: AbortController for Frontend API Calls

Both ImageTab and AudioTab use AbortController for request cancellation. New tabs must follow this pattern.

```javascript
$effect(() => {
  const controller = new AbortController();
  fetch(url, { signal: controller.signal })
    .then(...)
    .catch(err => { if (err.name === 'AbortError') return; });
  return () => controller.abort();  // cleanup on re-run
});
```

### Pattern 3: Multi-Tier Lookup with Caching

MapDataService uses progressively weaker matching tiers with result caching:

```
Tier 1: Exact match in pre-indexed dict (O(1))
Tier 2: Bridge lookup via cross-reference chain (O(1))
Tier 3: Fuzzy partial string match (O(n))
Cache: Store result under original key for future O(1) lookups
```

### Pattern 4: Graceful Degradation

MegaIndex build wraps every parser in try/except. Missing folders log warnings but don't crash. MapDataService returns None when unloaded. Frontend shows "No Image/Audio Context" empty states.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Relying Solely on Korean Text Matching (C6)

**What:** C6 builds entity->StringId mappings by matching entity name/desc against StrOrigin text.
**Why bad:** Korean text normalization is lossy. Entity names (e.g., "검은 별의 검") may differ from StrOrigin text (e.g., "검은 별의 검에 대한 설명"). Partial matches fail.
**Instead:** Add StrKey-based matching as primary (entity StrKey embedded in export XML filenames), use text matching as fallback only.

### Anti-Pattern 2: Using C2 for Audio Resolution

**What:** C2 tries `wem_by_event.get(strkey.lower())` -- assuming WEM filename matches entity StrKey.
**Why bad:** WEM files are named after sound events (e.g., `play_varon_greeting_01.wem`), not entity StrKeys (e.g., `CharacterInfo_Varon`).
**Instead:** Always use C3 chain (StringId -> R3.event -> D10.wem). C2 is effectively dead.

### Anti-Pattern 3: Rebuilding MegaIndex on Every Config Change

**What:** Changing branch+drive triggers full MegaIndex rebuild (7 phases, all XML parsing).
**Why bad:** With real Perforce data (thousands of XMLs), rebuild could take 10+ seconds.
**Instead:** Consider incremental path re-resolution without full XML re-parse, or show progress indicator during rebuild.

## MegaIndex Split Strategy (ARCH-02)

Current: 1311 lines in one file with 7 build phases and 35 dicts.

Recommended split by domain:

| New Module | Dicts | Lines (est.) |
|-----------|-------|-------------|
| `mega_index_core.py` | MegaIndex class, build(), stats, singleton | ~150 |
| `mega_index_parsers.py` | Phase 1-3: XML parsers (knowledge, character, item, faction, skill, gimmick, loc, export) | ~500 |
| `mega_index_reverse.py` | Phase 5-6: DevMemo scan, reverse dict builders (R1-R7) | ~200 |
| `mega_index_composed.py` | Phase 7: Composed dict builders (C1-C7) | ~150 |
| `mega_index_api.py` | Public API methods (get_*, find_*, all_entities, entity_counts) | ~200 |
| `mega_index_schemas.py` | Already separate (167 lines) | 167 (no change) |

Total: ~1200 lines across 5 files + 1 existing schema file.
