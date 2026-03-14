# Phase 5.1: Contextual Intelligence & QA Engine - Research

**Researched:** 2026-03-14
**Domain:** Aho-Corasick entity detection, glossary extraction, QA checks (Line/Term), game entity context, Svelte 5 UI
**Confidence:** HIGH

## Summary

Phase 5.1 is the most complex phase with 13 requirements, but the core algorithms already exist in proven NewScripts code. The work is **assembly and adaptation**, not invention. QuickSearch provides Aho-Corasick automaton building (`build_automaton()`), glossary extraction with AC validation (`extract_glossary_with_validation()`), and word boundary detection (`is_isolated_match()`). QuickCheck provides the enhanced dual-automaton Term Check, Line Check, category mapping (`TwoTierCategoryMapper`), and glossary extraction. The existing LocaNext QA routes (`server/tools/ldm/routes/qa.py`) already have a working Term Check and Line Check implementation using `ahocorasick` -- this phase enriches them with proper glossary extraction from game data and adds the contextual intelligence layer.

The QACompiler generators (Character, Item, Region, Skill) provide the entity data extraction patterns from staticinfo XML. These generators parse XML files, resolve cross-file references (KnowledgeKey linkage), and extract rich metadata (character names, descriptions, knowledge data). The MapDataService singleton pattern from Phase 5 provides the architecture template for a new `ContextService` that indexes entity data.

**Primary recommendation:** Build a `GlossaryService` that extracts entity names from QACompiler generator patterns, builds an Aho-Corasick automaton for real-time entity detection, and maps detected entities to their rich metadata (images, audio, descriptions). Layer the AI Context tab on top of the existing RightPanel tab infrastructure. Enhance the existing QA footer with Line Check and Term Check powered by proper glossary data.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CTX-01 | Auto-detect character names, display metadata (gender, age, job, race, quests, interactions) | QACompiler `character.py` provides `CharacterEntry` with all these fields. `scan_characters_with_knowledge()` resolves knowledge linkage. |
| CTX-02 | Auto-detect location names, display images and map positions | QACompiler `region.py` provides `FactionNodeData` with KnowledgeKey linkage to location data. |
| CTX-03 | Audio samples for detected characters (direct + indirect) | MapDataService `AudioContext` + QACompiler character data → audio linkage via StrKey/KnowledgeKey. |
| CTX-04 | Image context for detected entities even when not directly linked | MapDataService `ImageContext` + QACompiler knowledge linkage provides indirect image paths via KnowledgeKey chains. |
| CTX-05 | Aho-Corasick automaton from glossary for O(n) real-time detection | QuickSearch `build_automaton()` + `is_isolated_match()` -- exact pattern to reuse. QuickCheck has enhanced dual-automaton version. |
| CTX-06 | Category clustering using QACompiler/LDE technology | QuickCheck `TwoTierCategoryMapper` provides the exact two-tier clustering algorithm (STORY tier + GAME_DATA tier). |
| CTX-07 | "AI Translated" status visible in grid | Simple status column addition. Existing color system: green=confirmed, yellow=draft, gray=empty. Add blue/purple for AI. |
| CTX-08 | Context panel dynamically shows detected entity info per segment | RightPanel already has "AI Context" tab placeholder. Replace with real `ContextTab.svelte`. |
| CTX-09 | Automatic glossary extraction from game data (character, location, item, skill names) | QuickSearch `extract_glossary_with_validation()` pattern. QACompiler generators parse the source XML. |
| CTX-10 | Glossary-to-datapoint mapping (glossary term -> staticinfo path for images/DESC/audio) | QACompiler `base.py` EXPORT index pattern (`build_export_indexes()`) + MapDataService path templates. |
| QA-01 | LINE CHECK integrated (same source, different translations flagged) | QuickCheck `line_check.py` `run_line_check()` -- already partially in `qa.py` routes, enhance with proper filtering. |
| QA-02 | TERM CHECK integrated (glossary term in source but missing translation flagged) | QuickCheck `term_check.py` dual Aho-Corasick -- already partially in `qa.py` routes, enhance with real glossary data. |
| QA-03 | QA results in dedicated panel/tab, not separate tool | RightPanel QA footer exists. Enhance with richer display, filtering, navigation to flagged rows. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyahocorasick | installed | Aho-Corasick automaton for O(n) multi-pattern matching | Already used in qa.py routes and all NewScripts. Proven in production. |
| lxml | installed | XML parsing for staticinfo files | Already used throughout QACompiler generators. Recovery mode handles malformed XML. |
| FastAPI | installed | Backend API endpoints | Existing server architecture, repository pattern. |
| Svelte 5 | installed | Frontend UI (Runes only) | Existing frontend stack with Carbon Components. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| loguru | installed | Logging | All backend services (never print()) |
| Carbon Components Svelte | installed | UI components (Tag, InlineLoading) | RightPanel tabs, QA display |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyahocorasick | flashtext | pyahocorasick already installed and proven in codebase. No reason to switch. |
| lxml | ElementTree | lxml has recovery mode for malformed XML. ElementTree would crash on real game data. |

**Installation:**
```bash
# Nothing to install -- all dependencies already present
python3 -c "import ahocorasick; from lxml import etree; print('All deps OK')"
```

## Architecture Patterns

### Recommended Project Structure
```
server/
├── tools/ldm/services/
│   ├── mapdata_service.py          # Existing (Phase 5)
│   ├── glossary_service.py         # NEW: Glossary extraction + AC automaton
│   └── context_service.py          # NEW: Entity context resolution
├── tools/ldm/routes/
│   ├── qa.py                       # ENHANCE: Better Line/Term Check with real glossary
│   ├── context.py                  # NEW: Entity context API endpoints
│   └── glossary.py                 # NEW: Glossary management endpoints
└── utils/
    └── qa_helpers.py               # Existing: is_isolated(), check_pattern_match()

locaNext/src/lib/components/ldm/
├── RightPanel.svelte               # ENHANCE: Wire AI Context tab
├── ContextTab.svelte               # NEW: Entity context display
├── QAFooter.svelte                 # NEW: Enhanced QA display (extract from RightPanel)
└── EntityCard.svelte               # NEW: Character/Location/Item card component
```

### Pattern 1: GlossaryService (Singleton with Lazy Loading)
**What:** Service that extracts glossary from game data and builds Aho-Corasick automaton.
**When to use:** Follow the MapDataService singleton pattern established in Phase 5.
**Example:**
```python
# Source: Adapted from QuickSearch/core/glossary.py + term_check.py
class GlossaryService:
    """Glossary extraction + Aho-Corasick automaton for entity detection."""

    def __init__(self):
        self._automaton = None              # pyahocorasick.Automaton
        self._entity_index = {}             # term -> EntityInfo
        self._loaded = False

    def build_from_game_data(self, character_names, location_names, item_names, skill_names):
        """Build AC automaton from extracted entity names.

        Reuses QuickSearch's build_automaton() pattern:
        1. Add all entity names as patterns
        2. Store entity metadata in lookup dict
        3. make_automaton() for O(n) scanning
        """
        import ahocorasick
        self._automaton = ahocorasick.Automaton()
        idx = 0
        for name, entity_info in chain(character_names, location_names, item_names, skill_names):
            self._automaton.add_word(name, (idx, name))
            self._entity_index[idx] = entity_info
            idx += 1
        self._automaton.make_automaton()
        self._loaded = True

    def detect_entities(self, text: str) -> List[DetectedEntity]:
        """Scan text for entities using AC automaton.

        Reuses QuickSearch's is_isolated_match() for word boundary check.
        """
        if not self._loaded or not self._automaton:
            return []
        results = []
        for end_index, (pattern_id, original_term) in self._automaton.iter(text):
            start_index = end_index - len(original_term) + 1
            if is_isolated_match(text, start_index, end_index + 1):
                results.append(DetectedEntity(
                    term=original_term,
                    start=start_index,
                    end=end_index + 1,
                    entity=self._entity_index[pattern_id]
                ))
        return results
```

### Pattern 2: Entity Context Resolution (QACompiler Generator Pattern)
**What:** Extract entity metadata from staticinfo XML using QACompiler's proven parsing patterns.
**When to use:** When building the glossary from game data.
**Example:**
```python
# Source: QACompilerNEW/generators/character.py scan_characters_with_knowledge()
# Simplified for LocaNext context service:

def extract_character_glossary(character_folder: Path, knowledge_map: dict) -> List[tuple]:
    """Extract character names for glossary.

    Pattern from QACompiler: scan characterinfo_*.staticinfo.xml,
    resolve KnowledgeKey for rich metadata.
    """
    glossary = []
    for path in character_folder.rglob("characterinfo_*.staticinfo.xml"):
        root = parse_xml_file(path)
        if root is None:
            continue
        for el in root.iter("CharacterInfo"):
            name = el.get("CharacterName") or ""
            strkey = el.get("StrKey") or ""
            knowledge_key = _find_knowledge_key(el)
            if name:
                glossary.append((name, EntityInfo(
                    type="character",
                    name=name,
                    strkey=strkey,
                    knowledge_key=knowledge_key,
                    source_file=path.name,
                    # metadata resolved from knowledge_map
                )))
    return glossary
```

### Pattern 3: Dual Aho-Corasick for Term Check (QuickCheck Enhancement)
**What:** Use two automatons -- one for source terms, one for translations -- for efficient O(n) term checking.
**When to use:** Enhancing the existing Term Check in qa.py routes.
**Example:**
```python
# Source: QuickCheck/core/term_check.py build_dual_automatons()
# The existing qa.py rebuilds the automaton per request.
# Enhancement: build ONCE in GlossaryService, reuse across requests.

# Current qa.py (per-request, inefficient):
automaton = ahocorasick.Automaton()
for idx, (term_source, term_target) in enumerate(glossary_terms):
    automaton.add_word(term_source, (idx, term_source, term_target))
automaton.make_automaton()

# Enhanced (service-level, built once):
# GlossaryService holds pre-built automaton
# qa.py just calls glossary_service.detect_terms(source_text)
```

### Pattern 4: Frontend Context Tab (Svelte 5 Runes)
**What:** Replace the placeholder AI Context tab with real entity display.
**When to use:** ContextTab.svelte component rendering detected entities.
**Example:**
```svelte
<!-- Source: Adapted from existing ImageTab/AudioTab pattern in Phase 5 -->
<script>
  let { selectedRow = null } = $props();
  let entities = $state([]);
  let loading = $state(false);

  $effect(() => {
    if (selectedRow?.string_id) {
      fetchContext(selectedRow.string_id);
    }
  });

  async function fetchContext(stringId) {
    loading = true;
    const res = await fetch(`/api/ldm/context/${stringId}`);
    if (res.ok) entities = await res.json();
    loading = false;
  }
</script>
```

### Anti-Patterns to Avoid
- **Rebuilding AC automaton per request:** The automaton should be built ONCE when game data is loaded/configured, then reused across all requests. Current qa.py builds it per request -- fix this.
- **Parsing XML on every context lookup:** Parse staticinfo files ONCE at service initialization, store in memory indexes.
- **Blocking server startup with game data parsing:** Use lazy initialization (like MapDataService) -- parse on first configure call, not on server start.
- **Duplicating QACompiler code:** Port the PATTERNS, not the full generators. We need the XML parsing and entity extraction logic, not the Excel output.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-pattern string matching | Custom regex loop | pyahocorasick `Automaton` | O(n) vs O(n*m), handles thousands of patterns simultaneously |
| Word boundary detection | Custom Unicode logic | `is_isolated_match()` from QuickSearch/qa_helpers | Already handles Korean+CJK+Latin boundaries correctly |
| Glossary filtering | Custom filter pipeline | `glossary_filter()` from QuickSearch/utils/filters.py | Handles sentence filtering, punctuation, length, min_occurrence in correct order |
| Category clustering | Custom keyword matching | `TwoTierCategoryMapper` from QuickCheck | Two-tier algorithm with priority keywords and standard patterns already proven |
| XML sanitization | Custom XML cleaner | `sanitize_xml()` from QACompiler base.py | Handles malformed entities, br-tag normalization, tag stack repair |

**Key insight:** Every complex algorithm in this phase exists in working, tested code within QuickSearch, QuickCheck, or QACompiler. The implementation is porting patterns to the LocaNext service architecture, not inventing new algorithms.

## Common Pitfalls

### Pitfall 1: Korean Compound Word False Matches
**What goes wrong:** Aho-Corasick finds substring matches within compound Korean words (e.g., matching "Iron" inside "Ironclad").
**Why it happens:** Korean and CJK text doesn't use spaces between all words.
**How to avoid:** ALWAYS use `is_isolated_match()` / `is_word_boundary()` after AC matches. QuickSearch defaults to ISOLATED mode for this reason.
**Warning signs:** Large number of entity detections per string, nonsensical matches.

### Pitfall 2: Automaton Rebuilt Per Request
**What goes wrong:** Building an AC automaton with thousands of terms takes 50-200ms. Doing this per request makes the API sluggish.
**Why it happens:** Current qa.py builds automaton inline during `_run_qa_checks()`.
**How to avoid:** Build the automaton ONCE in GlossaryService during `initialize()`. Store as service-level state. Rebuild only when game data is reconfigured.
**Warning signs:** QA check endpoints taking >500ms.

### Pitfall 3: Glossary Too Large (Noise)
**What goes wrong:** Including all game data as glossary terms creates thousands of false positive QA issues.
**Why it happens:** Short common words appear in glossary (e.g., Korean word for "sword" matches everywhere).
**How to avoid:** Use QuickSearch's proven defaults: `min_occurrence=2`, `max_term_length=25`, `filter_sentences=True`, `max_issues_per_term=6`. The noise filter (`max_issues_per_term`) is critical -- if a term triggers >6 issues, it's likely a false positive.
**Warning signs:** Term Check returning hundreds of issues per file.

### Pitfall 4: Entity Data Not Available in Offline Mode
**What goes wrong:** Staticinfo XML files are on Windows drives (F:\perforce\...). In offline/WSL mode, paths don't exist.
**Why it happens:** QACompiler generators assume direct file system access to game data.
**How to avoid:** Use the same strategy as MapDataService -- graceful degradation. Service reports "not configured" if paths don't exist. Context tab shows "Configure branch/drive in Settings to enable". Entity detection still works if glossary was previously loaded.
**Warning signs:** FileNotFoundError on service initialization.

### Pitfall 5: Blocking UI with Large Context Responses
**What goes wrong:** Context panel tries to display all entity data at once, causing lag.
**Why it happens:** A single string might reference 5+ entities, each with images, audio, descriptions.
**How to avoid:** Use the Phase 5 per-tab lazy fetch pattern. Only load entity details when the context tab is active. Paginate or collapse entity cards.
**Warning signs:** Context API responses >100KB, UI jank when switching to context tab.

### Pitfall 6: KnowledgeKey Resolution Complexity
**What goes wrong:** Entity data requires multi-hop XML lookage (CharacterInfo -> KnowledgeKey -> KnowledgeInfo -> image/audio paths).
**Why it happens:** Game data uses cross-file references extensively.
**How to avoid:** Pre-build all indexes at initialization time (like QACompiler does with `load_knowledge_data()` and `build_export_indexes()`). Store the resolved metadata, not the raw keys.
**Warning signs:** Missing context for entities that should have rich metadata.

## Code Examples

### Aho-Corasick Automaton Building (from QuickSearch)
```python
# Source: QuickSearch/core/term_check.py build_automaton()
import ahocorasick

def build_automaton(glossary_terms):
    automaton = ahocorasick.Automaton()
    term_to_info = {}
    for idx, (term, info) in enumerate(glossary_terms):
        automaton.add_word(term, (idx, term))
        term_to_info[idx] = info
    automaton.make_automaton()
    return automaton, term_to_info
```

### Word Boundary Check (from QuickSearch + qa_helpers)
```python
# Source: server/utils/qa_helpers.py is_isolated()
def is_isolated_match(text, start, end):
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    before_is_word = bool(re.match(r'[\w\uac00-\ud7af]', before))
    after_is_word = bool(re.match(r'[\w\uac00-\ud7af]', after))
    return not before_is_word and not after_is_word
```

### Glossary Filter Pipeline (from QuickSearch)
```python
# Source: QuickSearch/utils/filters.py glossary_filter()
def glossary_filter(pairs, length_threshold=25, filter_sentences=True, min_occurrence=2):
    filtered = [(s, t) for s, t in pairs if s and t]
    filtered = [(s, t) for s, t in filtered if len(s) < length_threshold]
    filtered = [(s, t) for s, t in filtered if not is_korean(t)]
    if filter_sentences:
        filtered = [(s, t) for s, t in filtered if not is_sentence(s)]
    filtered = [(s, t) for s, t in filtered if not has_punctuation(s)]
    if min_occurrence > 1:
        counts = Counter(s for s, _ in filtered)
        filtered = [(s, t) for s, t in filtered if counts[s] >= min_occurrence]
    return filtered
```

### Two-Tier Category Mapping (from QuickCheck)
```python
# Source: QuickCheck/core/category_mapper.py TwoTierCategoryMapper
# Tier 1 (STORY): Dialog -> 4 sub-categories, Sequencer -> 'Sequencer'
# Tier 2 (GAME_DATA): Priority keywords first, then standard patterns
PRIORITY_KEYWORDS = [
    ("gimmick", "Gimmick"), ("item", "Item"), ("quest", "Quest"),
    ("skill", "Skill"), ("character", "Character"), ("region", "Region"),
    ("faction", "Faction"),
]
```

### Line Check from Pairs (from QuickSearch)
```python
# Source: QuickSearch/core/line_check.py run_line_check_from_pairs()
# Simplified pattern for LocaNext integration:
def find_inconsistencies(pairs):
    groups = defaultdict(lambda: defaultdict(int))
    for src, tgt in pairs:
        groups[src][tgt] += 1
    return {src: list(tgts.keys()) for src, tgts in groups.items() if len(tgts) > 1}
```

### RightPanel Tab Wiring (Svelte 5 -- existing pattern)
```svelte
<!-- Source: locaNext/src/lib/components/ldm/RightPanel.svelte -->
<!-- Current placeholder at line 148-153: -->
{:else if activeTab === 'context'}
  <!-- Replace placeholder with: -->
  <ContextTab {selectedRow} />
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-request AC automaton build | Service-level pre-built automaton | This phase | 50-200ms saved per QA check request |
| No glossary in LocaNext (TM-only term check) | Game data glossary extraction | This phase | Real entity detection, not just TM-based |
| Separate QA tools (QuickCheck standalone) | Integrated QA in editor | This phase | Translators don't leave LocaNext |
| Placeholder AI Context tab | Rich entity context display | This phase | Context-aware translation |

**Deprecated/outdated:**
- QuickSearch's single-automaton Term Check: QuickCheck's dual-automaton is superior (O(1) translation presence check instead of O(n) substring search per match)
- QACompiler's ENG BASE mode: Not needed for LocaNext integration (KR BASE only, matching Phase 5.1 requirements)

## Open Questions

1. **Mock Data Strategy for Demo**
   - What we know: Staticinfo XML files are on Windows drives, not always available
   - What's unclear: How much mock data to bundle for offline demo
   - Recommendation: Create a small fixture set of character/item/location data (~20 entities) for testing and demo. Load from bundled JSON when XML paths unavailable.

2. **AI Translated Status Storage**
   - What we know: CTX-07 requires "AI Translated" visible in grid
   - What's unclear: Should this be a new status value in the existing status column, or a separate boolean flag?
   - Recommendation: Add as a separate `translation_source` field (values: "human", "ai", "tm") on the row model. Display via a small icon/badge, not the status color system (which is about confirmation state).

3. **Glossary Service Initialization Trigger**
   - What we know: MapDataService uses explicit `/mapdata/configure` endpoint
   - What's unclear: Should glossary build from same configure call, or separate endpoint?
   - Recommendation: Same configure call triggers both MapData + Glossary initialization (they share branch/drive settings). Add `/context/configure` or extend `/mapdata/configure`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `/home/neil1988/LocalizationTools/pytest.ini` |
| Quick run command | `python3 -m pytest tests/unit -x -q --no-header` |
| Full suite command | `python3 -m pytest tests/unit tests/stability -x -q --no-header` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CTX-05 | AC automaton builds and detects entities | unit | `python3 -m pytest tests/unit/ldm/test_glossary_service.py -x` | Wave 0 |
| CTX-09 | Glossary extraction from game data | unit | `python3 -m pytest tests/unit/ldm/test_glossary_service.py::test_extract_glossary -x` | Wave 0 |
| CTX-10 | Glossary-to-datapoint mapping | unit | `python3 -m pytest tests/unit/ldm/test_context_service.py -x` | Wave 0 |
| CTX-01 | Character name detection + metadata | unit | `python3 -m pytest tests/unit/ldm/test_context_service.py::test_character_context -x` | Wave 0 |
| CTX-02 | Location name detection + images | unit | `python3 -m pytest tests/unit/ldm/test_context_service.py::test_location_context -x` | Wave 0 |
| CTX-06 | Category clustering | unit | `python3 -m pytest tests/unit/ldm/test_category_mapper.py -x` | Wave 0 |
| CTX-08 | Context panel API endpoint | unit | `python3 -m pytest tests/unit/ldm/test_routes_context.py -x` | Wave 0 |
| QA-01 | Line Check with proper filtering | unit | `python3 -m pytest tests/unit/ldm/test_routes_qa.py::test_line_check -x` | Exists (enhance) |
| QA-02 | Term Check with real glossary | unit | `python3 -m pytest tests/unit/ldm/test_routes_qa.py::test_term_check -x` | Exists (enhance) |
| CTX-07 | AI Translated status in grid | e2e | `npx playwright test e2e/context-panel.spec.ts -x` | Wave 0 |
| CTX-03 | Audio for detected characters | unit | `python3 -m pytest tests/unit/ldm/test_context_service.py::test_audio_context -x` | Wave 0 |
| CTX-04 | Image for detected entities | unit | `python3 -m pytest tests/unit/ldm/test_context_service.py::test_image_context -x` | Wave 0 |
| QA-03 | QA results in editor panel | e2e | `npx playwright test e2e/qa-panel.spec.ts -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/unit -x -q --no-header`
- **Per wave merge:** `python3 -m pytest tests/unit tests/stability -x -q --no-header`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_glossary_service.py` -- covers CTX-05, CTX-09
- [ ] `tests/unit/ldm/test_context_service.py` -- covers CTX-01, CTX-02, CTX-03, CTX-04, CTX-10
- [ ] `tests/unit/ldm/test_category_mapper.py` -- covers CTX-06
- [ ] `tests/unit/ldm/test_routes_context.py` -- covers CTX-08
- [ ] `tests/fixtures/mock_gamedata/` -- mock staticinfo XML for character, item, region entities
- [ ] Enhance `tests/unit/ldm/test_routes_qa.py` -- covers QA-01, QA-02 with glossary-powered checks

## Sources

### Primary (HIGH confidence)
- QuickSearch/core/term_check.py -- `build_automaton()`, `is_isolated_match()`, `run_term_check()` (read in full)
- QuickSearch/core/glossary.py -- `extract_glossary_with_validation()` with AC validation (read in full)
- QuickSearch/core/line_check.py -- `run_line_check()`, `run_line_check_from_pairs()` (read in full)
- QuickSearch/utils/filters.py -- `glossary_filter()` pipeline (read in full)
- QuickCheck/core/term_check.py -- `build_dual_automatons()`, dual AC scan (read in full)
- QuickCheck/core/line_check.py -- enhanced `run_line_check()` with StringID tracking (read in full)
- QuickCheck/core/category_mapper.py -- `TwoTierCategoryMapper`, `build_export_indexes()` (read in full)
- QuickCheck/core/glossary_extractor.py -- `extract_glossary_for_files()` (read in full)
- QACompiler/generators/base.py -- XML parsing, language tables, knowledge resolution (read in full)
- QACompiler/generators/character.py -- `CharacterEntry`, `scan_characters_with_knowledge()` (read in full)
- server/tools/ldm/services/mapdata_service.py -- singleton pattern, path templates (read in full)
- server/tools/ldm/routes/qa.py -- existing QA infrastructure (read in full)
- server/utils/qa_helpers.py -- `is_isolated()`, `check_pattern_match()` (read in full)
- locaNext RightPanel.svelte -- tab infrastructure, AI Context placeholder (read in full)

### Secondary (MEDIUM confidence)
- QACompiler/generators/item.py -- item extraction pattern (header read)
- QACompiler/generators/region.py -- region extraction pattern (header read)

### Tertiary (LOW confidence)
- None -- all findings are from direct source code reading

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in production code
- Architecture: HIGH -- follows established patterns (MapDataService singleton, QACompiler generators, QuickSearch AC)
- Pitfalls: HIGH -- documented from real issues encountered in QuickSearch/QuickCheck development
- Reuse patterns: HIGH -- every algorithm read in full source code, not assumed

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable -- all source code is local, no external dependencies changing)
