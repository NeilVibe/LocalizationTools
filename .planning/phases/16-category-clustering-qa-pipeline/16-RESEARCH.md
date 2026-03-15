# Phase 16: Category Clustering + QA Pipeline - Research

**Researched:** 2026-03-15
**Domain:** Content classification + inline QA for CAT tool translation grid
**Confidence:** HIGH

## Summary

Phase 16 enhances the translation grid with two independent features: (1) auto-detected content categories per row (Item, Quest, UI, Character, etc.) with multi-select filtering, and (2) inline QA feedback for Term Check (glossary consistency) and Line Check (translation uniformity). Both features have substantial existing infrastructure from v1.0 Phase 5.1 and the LanguageDataExporter NewScript that can be reused and extended.

The Category Clustering system has TWO proven implementations to port from: the LanguageDataExporter's `TwoTierCategoryMapper` (EXPORT-path-based, more granular) and the server's existing `category_mapper.py` (simplified path-keyword matching). The LanguageDataExporter version is the authoritative reference because it handles the two-tier algorithm correctly (Tier 1: Dialog/Sequencer story content, Tier 2: keyword-based gamedata classification with priority override). The mock gamedata from Phase 15 uses `SID_{TYPE}_{INDEX}_{NAME|DESC}` StringID format, which makes category classification trivially derivable from the StringID prefix itself.

The QA Pipeline already exists as a fully functional backend with Aho-Corasick term matching, line consistency checking, pattern validation, noise filtering, and a resolve/dismiss flow. The frontend has a `QAMenuPanel.svelte` slide-out panel. What Phase 16 adds is: (a) making QA findings display INLINE in the grid cells rather than only in the side panel, (b) adding a dedicated QA panel with summary counts, and (c) per-cell dismissal of individual findings.

**Primary recommendation:** Reuse the existing QA backend and QAMenuPanel wholesale. Add a `category` field to the row response schema, populate it via the LanguageDataExporter two-tier mapper adapted for the server side, and add inline QA indicators to grid cells.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAT-01 | Auto-classify StringIDs into content categories using LanguageDataExporter two-tier logic | Existing `TwoTierCategoryMapper` in both LDE (`exporter/category_mapper.py`) and server (`services/category_mapper.py`). LDE version is authoritative. Mock data StringID prefixes (`SID_ITEM_`, `SID_CHAR_`, etc.) enable instant classification. |
| CAT-02 | Category column visible and filterable in translation grid | Grid uses `translatorColumns` dict in `VirtualGrid.svelte`. Add `category` column alongside existing `row_num`, `string_id`, `source`, `target`. |
| CAT-03 | Multi-category filter to focus on specific content types | Grid already has `activeFilter` state with dropdown (`filterOptions`). Extend with multi-select category filter. |
| QA-01 | Term Check with dual Aho-Corasick automaton | Fully implemented in `server/tools/ldm/routes/qa.py` with `_build_term_automaton()`, `_run_qa_checks()`. GlossaryService in `glossary_service.py` provides entity extraction + AC automaton. |
| QA-02 | Line Check for inconsistent translations | Fully implemented via `_build_line_check_index()` with O(n) grouping algorithm in `qa.py`. |
| QA-03 | QA results display inline with severity tiers (ERROR/WARNING/INFO) | QAMenuPanel exists but shows results in side panel only. Need inline cell indicators in VirtualGrid rows. Schema already has `severity` field with error/warning values. |
| QA-04 | Dismiss individual QA findings per cell | `resolve_qa_issue` endpoint exists at `POST /qa-results/{result_id}/resolve`. Frontend needs dismiss button per issue in inline view. |
| QA-05 | QA checks run on-demand via dedicated QA panel | `QAMenuPanel.svelte` exists with "Run Full QA" button, summary cards, and issue list. Enhance with category-scoped QA runs. |
| QA-06 | QA panel shows summary counts per check type | `QASummary` schema and `get_file_qa_summary` endpoint already return `{line, term, pattern, total}` counts. Panel already renders 4 summary cards. |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyahocorasick | installed | Dual Aho-Corasick automaton for O(n) term matching | Already used in `glossary_service.py` and `qa.py`. Battle-tested in QuickCheck/QuickSearch. |
| FastAPI | existing | QA endpoints, category API | All backend routes use FastAPI + repository pattern |
| Pydantic | existing | QA schemas (`QAIssue`, `QASummary`, etc.) | All API schemas use Pydantic BaseModel |
| Carbon Components Svelte | existing | Grid UI, tags, dropdowns, notifications | Design system for all LocaNext UI |
| lxml | existing | XML parsing for EXPORT .loc.xml files | Standard XML parser across project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| carbon-icons-svelte | existing | QA severity icons (WarningAltFilled, etc.) | Inline QA indicators in grid cells |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Aho-Corasick | Regex per term | O(n*m) vs O(n) -- AC is 10-100x faster for 50+ terms |
| Server-side category | Client-side category from StringID prefix | Server is authoritative, handles real EXPORT paths too |

## Architecture Patterns

### Recommended Architecture

```
Category Flow:
  EXPORT .loc.xml files  ──>  TwoTierCategoryMapper  ──>  StringID->Category index
                                                              │
  Row loaded from DB  ───────────────────────────────>  category field injected
                                                              │
  VirtualGrid.svelte  <──────────────────────────────  category column rendered
                                                              │
  CategoryFilter component  ──>  API query param  ──>  filtered rows returned

QA Flow (existing, enhanced):
  "Run Full QA" button  ──>  POST /files/{id}/check-qa
                                    │
  _build_term_automaton()  ──>  AC automaton (once per file)
  _build_line_check_index() ──>  source->targets index (once per file)
                                    │
  Per row: _run_qa_checks()  ──>  issues[] saved to qa_results table
                                    │
  QAMenuPanel  <──  GET /files/{id}/qa-results (side panel)
  VirtualGrid  <──  qa_flag_count on row (inline indicator)
```

### Pattern 1: Category Classification via StringID Prefix

**What:** For mock data (and many real scenarios), the StringID format `SID_{TYPE}_{INDEX}_{SUFFIX}` allows instant classification without EXPORT path lookup.

**When to use:** When StringIDs follow the standard format.

**Example:**
```python
# Fast path: derive category from StringID prefix
STRINGID_PREFIX_TO_CATEGORY = {
    "SID_ITEM_": "Item",
    "SID_CHAR_": "Character",
    "SID_SKILL_": "Skill",
    "SID_REGION_": "Region",
    "SID_GIMMICK_": "Gimmick",
    "SID_KNOWLEDGE_": "Knowledge",
}

def categorize_by_stringid(string_id: str) -> str:
    """Fast O(1) category lookup from StringID prefix."""
    if not string_id:
        return "Uncategorized"
    sid_upper = string_id.upper()
    for prefix, category in STRINGID_PREFIX_TO_CATEGORY.items():
        if sid_upper.startswith(prefix):
            return category
    return "Other"
```

### Pattern 2: Two-Tier Category Mapper (EXPORT Path Based)

**What:** Full LanguageDataExporter classification using EXPORT folder structure.

**When to use:** When EXPORT folder is available (real projects with .loc.xml files).

**Example (from `exporter/category_mapper.py`):**
```python
# Source: RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/exporter/category_mapper.py

# Tier 1: STORY (Dialog/Sequencer paths)
# Tier 2: GAME_DATA (priority keywords override folder matching)
PRIORITY_KEYWORDS = [
    ("gimmick", "Gimmick"),  # HIGHEST priority
    ("item", "Item"),
    ("quest", "Quest"),
    ("skill", "Skill"),
    ("character", "Character"),
    ("region", "Region"),
    ("faction", "Faction"),
]

# build_stringid_category_index() scans all .loc.xml files
# and returns {StringID: Category} mapping
```

### Pattern 3: Inline QA Indicators in Grid Cells

**What:** Each grid row shows a small QA badge when issues exist.

**When to use:** Always -- replaces the need to open the QA panel to see if a row has issues.

**Example:**
```svelte
<!-- In VirtualGrid row template -->
{#if row.qa_flag_count > 0}
  <span class="qa-badge" title="{row.qa_flag_count} QA issue(s)">
    <WarningAltFilled size={14} />
    <span class="badge-count">{row.qa_flag_count}</span>
  </span>
{/if}
```

### Pattern 4: Multi-Select Category Filter

**What:** Dropdown or checkbox group allowing selection of multiple categories.

**When to use:** For CAT-03 requirement.

**Example:**
```svelte
<!-- Carbon MultiSelect for category filtering -->
<script>
  let selectedCategories = $state([]);
  const categoryOptions = [
    { id: "Item", text: "Item" },
    { id: "Character", text: "Character" },
    { id: "Quest", text: "Quest" },
    { id: "Skill", text: "Skill" },
    { id: "Region", text: "Region" },
    { id: "Gimmick", text: "Gimmick" },
    { id: "UI", text: "UI" },
    { id: "Other", text: "Other" },
  ];
</script>
```

### Anti-Patterns to Avoid
- **Client-side-only category classification:** Category must come from server to match LanguageDataExporter logic. Client can cache but not compute.
- **Running QA on every keystroke:** QA checks should be on-demand (button click or file-level), never per-character. The AC automaton build takes O(glossary_size) time.
- **Separate QA database table per check type:** All QA results already share a single `qa_results` table with `check_type` discriminator. Do not split.
- **Rewriting QA backend:** The existing `qa.py` routes are complete and tested. Extend, do not rewrite.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-pattern string matching | Loop through patterns | `pyahocorasick` AC automaton | O(text_len) vs O(text_len * num_patterns). Already in project. |
| Category classification | New classification system | Port `TwoTierCategoryMapper` from LDE | Battle-tested with real game data, handles edge cases (KnowledgeInfo_Item -> Item, not Knowledge) |
| QA result persistence | Custom storage | Existing `QAResultRepository` (PostgreSQL + SQLite parity) | Full CRUD + resolve + bulk create already implemented |
| QA panel UI | New panel component | Existing `QAMenuPanel.svelte` | 689 lines, fully functional, just needs enhancement |
| Word boundary detection | Regex-only isolation | `is_isolated()` from `qa_helpers.py` | Handles Korean compound words correctly |
| Noise filtering | Manual threshold tuning | `_apply_noise_filter()` in `qa.py` | MAX_ISSUES_PER_TERM=6, proven production filter |

**Key insight:** 80%+ of the backend for this phase already exists from v1.0 Phase 5.1. The primary work is: (1) adding the category column to the grid, (2) building the StringID-to-category index on file load, and (3) adding inline QA indicators to grid cells.

## Common Pitfalls

### Pitfall 1: Category Index Not Available at Row Load Time
**What goes wrong:** Category classification requires scanning EXPORT .loc.xml files, but rows are loaded from the database without EXPORT path context.
**Why it happens:** The category mapping is built from the EXPORT folder structure, which is separate from the language data files loaded into the grid.
**How to avoid:** Build the StringID->Category index when a project/folder is opened (similar to how GlossaryService initializes). Cache it in memory. Inject `category` into row responses via a lookup.
**Warning signs:** Category showing as "Uncategorized" for all rows despite valid StringIDs.

### Pitfall 2: Korean Word Boundary False Positives in Term Check
**What goes wrong:** Term Check flags partial matches inside Korean compound words.
**Why it happens:** Korean syllable blocks can contain substring matches that are not isolated terms.
**How to avoid:** Always use `is_isolated()` from `qa_helpers.py`. It checks for adjacent Korean characters (U+AC00-U+D7A3) and word characters.
**Warning signs:** Term Check reporting 100+ issues for common Korean particles.

### Pitfall 3: Noise Filter Masking Real Issues
**What goes wrong:** `_apply_noise_filter()` removes terms with >6 occurrences, hiding genuine consistency problems.
**Why it happens:** MAX_ISSUES_PER_TERM=6 was tuned for QuickSearch/QuickCheck data volumes, may need adjustment for larger files.
**How to avoid:** Make the threshold configurable. Log filtered terms. Allow user to see "filtered out" count.
**Warning signs:** QA summary shows 0 term issues but manual review finds problems.

### Pitfall 4: Category Filter Breaking Pagination
**What goes wrong:** Virtual scroll pagination assumes contiguous row ranges. Category filtering creates gaps.
**Why it happens:** Current `list_rows` API uses `page` + `PAGE_SIZE` offset. Filtering by category changes total count and page boundaries.
**How to avoid:** Add `category` as a query parameter to the existing `GET /files/{file_id}/rows` endpoint. Let the server handle filtering before pagination.
**Warning signs:** Rows jumping or duplicating when toggling category filters.

### Pitfall 5: QA Re-run Deleting User Dismissals
**What goes wrong:** "Run Full QA" clears all unresolved issues (`delete_unresolved_for_row`) and recreates them, losing user dismissals.
**Why it happens:** `_save_qa_results` calls `delete_unresolved_for_row` before saving new results. Resolved issues are preserved (they have `resolved_at` set).
**How to avoid:** The existing `resolve` endpoint sets `resolved_at`, which is preserved across re-runs. This is already correct. Document to users that "dismiss" = "resolve" and is permanent.
**Warning signs:** Users dismissing issues and then seeing them reappear after re-run. (This should NOT happen with current implementation -- resolved issues have `resolved_at` set.)

## Code Examples

### Existing QA Backend -- Term Check with AC Automaton
```python
# Source: server/tools/ldm/routes/qa.py lines 137-158
def _build_term_automaton(glossary_terms: List[tuple]):
    if not HAS_AHOCORASICK or not glossary_terms:
        return None, {}
    automaton = ahocorasick.Automaton()
    term_map = {}
    for idx, (term_source, term_target) in enumerate(glossary_terms):
        automaton.add_word(term_source, (idx, term_source, term_target))
        term_map[idx] = (term_source, term_target)
    automaton.make_automaton()
    return automaton, term_map
```

### Existing QA Backend -- Line Check Index
```python
# Source: server/tools/ldm/routes/qa.py lines 111-134
def _build_line_check_index(file_rows: List[Dict[str, Any]]) -> Dict[str, List[tuple]]:
    from collections import defaultdict
    index: Dict[str, List[tuple]] = defaultdict(list)
    for row in file_rows:
        source = (row.get("source") or "").strip()
        target = (row.get("target") or "").strip()
        if source and target:
            index[source].append((row.get("id"), row.get("row_num", 0), target))
    return dict(index)
```

### Existing QA Frontend -- QAMenuPanel Structure
```svelte
<!-- Source: locaNext/src/lib/components/ldm/QAMenuPanel.svelte -->
<!-- Already has: summary cards (Total/Pattern/Line/Term), ContentSwitcher filter,
     issue list with clickable items that dispatch 'openEditModal',
     Run Full QA button with abort/cancel support -->
```

### Category Color Mapping (from LDE config)
```json
// Source: RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/category_clusters.json
{
  "Item": "D9D2E9",      // Light purple
  "Quest": "D9D2E9",     // Light purple
  "Character": "F8CBAD",  // Light salmon
  "Gimmick": "D9D2E9",   // Light purple
  "Skill": "D9D2E9",     // Light purple
  "UI": "A9D08E",        // Light green
  "Region": "F8CBAD",    // Light salmon
  "System_Misc": "D9D9D9" // Light gray
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QA in side panel only | QA inline in grid + side panel | Phase 16 (new) | Users see issues without opening panel |
| No category column | Category auto-detected from StringID/EXPORT path | Phase 16 (new) | Translators can filter by content type |
| Simple keyword matching | Two-tier priority keyword algorithm | LanguageDataExporter v3 | KnowledgeInfo_Item.xml correctly categorized as "Item" not "Knowledge" |

**Already implemented (reuse):**
- Full QA backend (term, line, pattern checks)
- QA panel with summary and issue navigation
- Aho-Corasick automaton for term matching
- QA result persistence with resolve/dismiss
- Category mapper (both LDE and server versions)

## Open Questions

1. **Category source for real (non-mock) data**
   - What we know: Mock data has `SID_{TYPE}_` prefix making classification trivial. LDE uses EXPORT .loc.xml file paths.
   - What's unclear: When loading real language data files without EXPORT folder available, how to classify?
   - Recommendation: Use StringID prefix as fast path. Fall back to server-side `TwoTierCategoryMapper` with file path when available. "Uncategorized" is acceptable fallback.

2. **Glossary source for Term Check**
   - What we know: Existing Term Check uses TM entries as glossary (short source < 20 chars). GlossaryService extracts entity names from staticinfo XML.
   - What's unclear: Which glossary source to use for v3.0 -- TM-based, entity-based, or both?
   - Recommendation: Use both. GlossaryService for entity names (auto-extracted), TM entries for user-defined terms. Merge before building AC automaton.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pytest.ini` (root) |
| Quick run command | `python -m pytest tests/unit/ldm/ -x --no-header -q` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAT-01 | StringID auto-classification into categories | unit | `python -m pytest tests/unit/ldm/test_category_service.py -x` | No -- Wave 0 |
| CAT-02 | Category column in grid row response | unit | `python -m pytest tests/unit/ldm/test_rows_category.py -x` | No -- Wave 0 |
| CAT-03 | Multi-category filter on rows endpoint | unit | `python -m pytest tests/unit/ldm/test_rows_category_filter.py -x` | No -- Wave 0 |
| QA-01 | Term Check with AC automaton flags missing terms | unit | `python -m pytest tests/unit/ldm/test_routes_qa.py::TestTermCheck -x` | Partial (existing test file) |
| QA-02 | Line Check flags inconsistent translations | unit | `python -m pytest tests/unit/ldm/test_routes_qa.py::TestLineCheck -x` | Partial (existing test file) |
| QA-03 | QA results include severity tiers | unit | `python -m pytest tests/unit/ldm/test_routes_qa.py::TestQASeverity -x` | Partial |
| QA-04 | Dismiss/resolve individual QA findings | unit | `python -m pytest tests/unit/ldm/test_routes_qa.py::TestResolve -x` | Partial |
| QA-05 | On-demand QA run via panel | integration | `python -m pytest tests/integration/test_qa_pipeline.py -x` | No -- Wave 0 |
| QA-06 | QA summary counts per check type | unit | `python -m pytest tests/unit/ldm/test_routes_qa.py::TestSummary -x` | Partial |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/ -x --no-header -q`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_category_service.py` -- covers CAT-01 (StringID prefix classification + EXPORT path classification)
- [ ] `tests/unit/ldm/test_rows_category.py` -- covers CAT-02 (category field in row response)
- [ ] `tests/unit/ldm/test_rows_category_filter.py` -- covers CAT-03 (multi-category filter query param)
- [ ] `tests/integration/test_qa_pipeline.py` -- covers QA-05 (full QA run on mock data)
- [ ] Existing `tests/unit/ldm/test_routes_qa.py` needs extension for QA-03 severity tiers, QA-04 dismiss, QA-06 summary

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/routes/qa.py` -- existing QA backend (725 lines, fully implemented)
- `server/tools/ldm/services/glossary_service.py` -- GlossaryService with AC automaton (430 lines)
- `server/tools/ldm/services/category_mapper.py` -- server-side category mapper (123 lines)
- `server/utils/qa_helpers.py` -- shared QA utilities (is_isolated, check_pattern_match, etc.)
- `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/exporter/category_mapper.py` -- authoritative two-tier mapper (490 lines)
- `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/category_clusters.json` -- category config with colors
- `locaNext/src/lib/components/ldm/QAMenuPanel.svelte` -- existing QA panel (689 lines)
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` -- translation grid with column system
- `server/tools/ldm/schemas/qa.py` -- QA Pydantic schemas
- `server/repositories/interfaces/qa_repository.py` -- QA repository interface

### Secondary (MEDIUM confidence)
- `RessourcesForCodingTheProject/NewScripts/QuickCheck/core/term_check.py` -- dual AC automaton pattern (more advanced)
- `tests/unit/ldm/test_category_mapper.py` -- existing category mapper tests
- `tests/unit/ldm/test_glossary_service.py` -- existing glossary service tests

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies needed
- Architecture: HIGH -- extending existing patterns (QA backend, grid columns, category mapper)
- Pitfalls: HIGH -- based on analysis of existing code behavior and edge cases

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- internal project patterns, no external dependency changes expected)
