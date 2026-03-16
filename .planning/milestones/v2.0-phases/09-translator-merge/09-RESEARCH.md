# Phase 09: Translator Merge - Research

**Researched:** 2026-03-15
**Domain:** XML translation merge engine -- porting QuickTranslate's match-type logic + postprocess pipeline into LocaNext
**Confidence:** HIGH

## Summary

Phase 09 is a **direct port** of QuickTranslate's proven merge engine into LocaNext's service architecture. The source code is battle-tested across thousands of real game files. The critical insight is that QuickTranslate already implements exactly what LocaNext needs: three match types (strict/StringID + StrOrigin, StringID-only, StrOrigin-only) plus fuzzy via Model2Vec, a comprehensive 8-step postprocess pipeline, correction parsing with skip guards, and br-tag three-layer defense. The work is integration engineering, not algorithm design.

The main risk is NOT complexity but fidelity. The merge logic has dozens of edge cases that were discovered and fixed over months of production use. Simplifying or "improving" any of these will reintroduce bugs. The postprocess pipeline has 8 steps that must run in exact order. The br-tag defense has three layers that must all be present. The match priority must be strictly ordered. The skip guards (Korean text, "no translation", formulas, integrity issues) must all be ported.

LocaNext's existing infrastructure is well-suited: XMLParsingEngine already provides lxml parsing with sanitization, the embedding engine provides Model2Vec for fuzzy matching, and the row repository pattern gives clean database integration. The new code plugs into existing services as a TranslatorMergeService singleton.

**Primary recommendation:** Port QuickTranslate's `xml_transfer.py`, `postprocess.py`, `xml_io.py`, and `korean_detection.py` logic into a new `server/tools/ldm/services/translator_merge.py` and `server/tools/ldm/services/postprocess.py`. Do NOT simplify or restructure -- replicate the exact logic, adapted only for LocaNext's data model (rows in DB, not files on disk).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TMERGE-01 | Exact StringID match transfers translation values between files | Port `merge_corrections_to_xml()` strict mode -- (StringID, normalized_StrOrigin) tuple key lookup. Also port `merge_corrections_stringid_only()` for StringID-only mode. Both use `_build_correction_lookups()` for pre-computation. |
| TMERGE-02 | StrOrigin match (source text match) transfers when StringID differs | Port strorigin_only mode from `_build_correction_lookups()` and `_fast_folder_merge()`. Uses `normalize_for_matching()` (lowercase + html.unescape + whitespace collapse) with `normalize_nospace()` fallback. |
| TMERGE-03 | Fuzzy matching via Model2Vec finds similar source strings above threshold | Existing `EmbeddingEngine` + `TMSearcher` infrastructure provides FAISS vector search. Need adapter that takes source file rows, embeds StrOrigin text, queries against correction file embeddings, returns matches above threshold. |
| TMERGE-04 | Postprocessing pipeline applies 8-step CJK-safe cleanup after transfer | Port `run_all_postprocess_on_tree()` from `postprocess.py`. 8 steps: newlines, empty-strorigin, no-translation, apostrophes, invisible chars, hyphens, ellipsis (CJK-skip), double-escaped entities. Must run in exact order, on Str/Desc only. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | >=4.9.0 | XML parsing with recovery mode | Already used by XMLParsingEngine. QuickTranslate uses it for all merge ops. |
| Model2Vec | >=0.3.0 | Fuzzy match embeddings | Already used by TM system. 256-dim, 79x faster than Qwen. |
| faiss-cpu | >=1.7.0 | Vector similarity search | Already used by TM indexing. Provides nearest-neighbor for fuzzy matches. |
| numpy | >=1.24.0 | Embedding array operations | Already a dependency. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| loguru | (existing) | Structured logging | All new service files |
| pytest | (existing) | Unit tests | All test files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Model2Vec fuzzy | Edit-distance (Levenshtein) | Model2Vec is semantic, catches paraphrases. Edit-distance only catches typos. Model2Vec is already available. |
| lxml tree manipulation | In-memory row dicts only | LocaNext operates on DB rows, not XML trees. Merge logic works on row dicts, postprocess works on values. No need to manipulate XML trees in LocaNext -- that's QuickTranslate's file-based model. |

**Installation:** No new packages needed. All dependencies already in requirements.txt.

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/services/
    translator_merge.py      # TranslatorMergeService (singleton)
    postprocess.py           # PostprocessPipeline (8-step cleanup)
    korean_detection.py      # is_korean_text() utility
    text_matching.py         # normalize_text, normalize_for_matching, normalize_nospace
server/tools/ldm/routes/
    merge.py                 # POST /api/ldm/files/{id}/merge endpoint
tests/unit/ldm/
    test_translator_merge.py
    test_postprocess.py
    test_text_matching.py
tests/fixtures/xml/
    merge_source.xml         # Source file with corrections
    merge_target.xml         # Target file to merge into
```

### Pattern 1: Service-Level Merge (Not File-Level)

**What:** QuickTranslate operates on XML files directly. LocaNext operates on rows in a database. The merge service must bridge these models: parse corrections from source rows, match against target rows, apply changes to row data, then persist via repository.

**When to use:** All merge operations in LocaNext.

**Example:**
```python
# Source: QuickTranslate xml_transfer.py adapted for LocaNext row model
from __future__ import annotations

class TranslatorMergeService:
    """Merge translations between files using QuickTranslate's match-type logic."""

    def merge_files(
        self,
        source_rows: list[dict],
        target_rows: list[dict],
        match_mode: str = "strict",
        threshold: float = 0.85,
    ) -> MergeResult:
        """
        Merge translations from source rows into target rows.

        Match modes (strict priority ordering):
        1. "strict" - (StringID + StrOrigin) both must match
        2. "stringid_only" - StringID matches, StrOrigin may differ
        3. "strorigin_only" - StrOrigin matches, StringID may differ
        4. "fuzzy" - Model2Vec similarity above threshold

        Returns MergeResult with matched/updated/skipped counts and per-row details.
        """
        # Build correction list from source rows
        corrections = self._parse_corrections(source_rows)

        # Build lookup dicts (exact port from _build_correction_lookups)
        lookup, lookup_nospace = self._build_lookups(corrections, match_mode)

        # Match against target rows
        results = self._apply_matches(target_rows, lookup, lookup_nospace, match_mode)

        # Run postprocess on modified values
        results = self._postprocess(results)

        return results
```

### Pattern 2: Correction Dict Format (Port Exactly)

**What:** QuickTranslate's correction dict has specific keys that the entire merge pipeline depends on. Port the exact format.

**Example:**
```python
# Source: QuickTranslate xml_io.py parse_corrections_from_xml()
correction = {
    "string_id": "UI_Button_OK",           # From StringId attribute
    "str_origin": "확인",                    # From StrOrigin attribute (Korean source)
    "corrected": "OK",                       # From Str attribute (translation)
    "desc_origin": "버튼 설명",              # Optional: DescOrigin
    "desc_corrected": "Button description",  # Optional: Desc translation
    "raw_attribs": {"StringId": "...", ...}, # ALL original attributes
}
```

### Pattern 3: Skip Guards (CRITICAL -- Port All)

**What:** QuickTranslate has 5 skip guards that prevent bad data from entering the merge. Missing any one causes silent data corruption.

**Example:**
```python
# Source: QuickTranslate xml_io.py parse_corrections_from_xml()

# Guard 1: Korean text = untranslated source, NOT a correction
if is_korean_text(str_value):
    continue

# Guard 2: "no translation" literal = NOT a correction
if normalize_whitespace(str_value).lower() == 'no translation':
    continue

# Guard 3: Formula/garbage text (starts with =, +, -, @)
if is_formula_text(str_value):
    continue

# Guard 4: Text integrity issues (broken linebreaks, encoding artifacts)
if is_text_integrity_issue(str_value, from_xml=True):
    continue

# Guard 5: Empty StrOrigin = never write Str (golden rule)
if not str_origin.strip():
    continue
```

### Pattern 4: Transactional Merge (NOT Optimistic UI)

**What:** Merge operations affect hundreds of rows. Optimistic UI is mandatory for single-cell edits but WRONG for batch merge. Use transactional commit.

**Example:**
```python
# Source: PITFALLS.md Pitfall 15
# Merge is transactional: compute all changes, commit all at once
changes = []
for target_row in target_rows:
    match = find_match(target_row, lookups)
    if match:
        changes.append((target_row["id"], match.new_value))

# All-or-nothing commit
if changes:
    await row_repo.bulk_update(changes)
    # Emit WebSocket event AFTER commit succeeds
    emit("merge_complete", {"updated": len(changes)})
```

### Anti-Patterns to Avoid
- **Simplifying match logic:** QuickTranslate has 4 match types for good reason. Do not collapse them into a "smart" unified matcher.
- **Skipping skip guards:** Every guard exists because of a real production bug. Port all 5.
- **Optimistic UI for merge:** Single-cell edits = optimistic. Batch merge = transactional commit with progress.
- **Shared normalize_text:** LocaNext's `server/utils/text_utils.py:normalize_text()` is DIFFERENT from QuickTranslate's. It strips unmatched quotes and removes zero-width chars. For merge matching, port QuickTranslate's version separately -- it does HTML unescape + whitespace collapse + &desc; removal.
- **Running postprocess on StrOrigin:** Postprocess ONLY modifies Str/Desc. StrOrigin/DescOrigin are sacred source data.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text normalization for matching | Custom regex | Port QuickTranslate's `normalize_text()`, `normalize_for_matching()`, `normalize_nospace()` from `text_utils.py` | Three-level normalization (whitespace, case, nospace fallback) handles edge cases |
| Korean text detection | Simple Unicode range check | Port `is_korean_text()` from `korean_detection.py` with full regex `[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]` | Missing Jamo ranges causes false negatives |
| Newline normalization | Simple `\n` to `<br/>` replace | Port `_normalize_newlines()` from `postprocess.py` -- handles 7 newline variants | 20+ newline representations exist in real game data |
| Linebreak conversion for XML | Manual escaping | Port `_convert_linebreaks_for_xml()` from `xml_transfer.py` | Handles double-escaping prevention |
| Formula detection | Ad-hoc checks | Port `is_formula_text()` from `text_utils.py` | Excel formulas (=, +, -, @) in XML cause data corruption |
| Fuzzy matching | Custom cosine similarity | Use existing `EmbeddingEngine.encode()` + `faiss.IndexFlatIP` | Already optimized, handles batch encoding |

**Key insight:** Every utility function in QuickTranslate exists because of a real production bug. They are battle-tested across thousands of files. Port them, don't reinvent them.

## Common Pitfalls

### Pitfall 1: br-tag Corruption in Merge Round-Trip
**What goes wrong:** `<br/>` tags get double-escaped to `&amp;lt;br/&amp;gt;` or stripped entirely during merge.
**Why it happens:** Three representations exist: `&lt;br/&gt;` on disk, `<br/>` in memory (after lxml parse), `<br/>` in Excel. Developers who don't understand this write code that breaks at boundary crossings.
**How to avoid:** Port `_convert_linebreaks_for_xml()` exactly. Run `cleanup_wrong_newlines_on_tree()` (postprocess step 1) after EVERY merge. Test with strings containing `<br/>` at start, end, middle, consecutive, and mixed.
**Warning signs:** Postprocess step 1 fixing counts are non-zero on clean data. `grep -c 'lt;br' output.xml` shows unexpected escaping.

### Pitfall 2: Match-Type Priority Confusion
**What goes wrong:** Wrong translations applied because match priority is violated. Fuzzy match overwrites a correct strict match because it was processed later.
**Why it happens:** Four match types have strict priority: strict > stringid_only > strorigin_only > fuzzy. Processing in wrong order or using "last-wins" without dedup causes wrong translations.
**How to avoid:** Process match types in priority order. For each target row, check strict first, then fall through to looser matches only if no strict match found. Use `_build_correction_lookups()` to pre-compute per-mode dicts.
**Warning signs:** Match type distribution looks wrong (e.g., 90% fuzzy on a file that should have 90% exact). Translation quality drops after merge.

### Pitfall 3: "no translation" Entries Transferred as Real Translations
**What goes wrong:** Source file has entries where Str = "no translation" (placeholder). These get transferred to target, overwriting real translations.
**Why it happens:** The merge treats any non-empty Str as a valid correction. Without the skip guard, "no translation" looks like a translation.
**How to avoid:** Port `_is_no_translation()` guard from `xml_transfer.py`. Check in BOTH parsing (skip when building corrections) AND transfer (skip when applying). Case-insensitive, whitespace-collapsed comparison.
**Warning signs:** Target file suddenly has "no translation" as Str for entries that previously had real translations.

### Pitfall 4: Korean Text Treated as Translation
**What goes wrong:** Source file has untranslated entries where Str is still Korean (same as StrOrigin). These get transferred, overwriting real translations with source text.
**Why it happens:** Korean source text is not empty, so it passes the basic "has Str" check. Without `is_korean_text()` guard, it looks like a valid translation.
**How to avoid:** Port `is_korean_text()` with full regex `[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]`. Skip entries where Str is Korean in correction parsing.
**Warning signs:** After merge, some entries have Korean in the Str field that matches their StrOrigin exactly.

### Pitfall 5: normalize_text Mismatch Between QuickTranslate and LocaNext
**What goes wrong:** LocaNext's `server/utils/text_utils.py:normalize_text()` strips unmatched quotes and removes zero-width chars. QuickTranslate's `normalize_text()` does HTML unescape + whitespace collapse + &desc; removal. Using the wrong one breaks matching.
**Why it happens:** Both are called `normalize_text` but have different behavior. LocaNext's version is for display normalization. QuickTranslate's version is for merge matching.
**How to avoid:** Port QuickTranslate's `normalize_text()`, `normalize_for_matching()`, `normalize_nospace()` into a separate `text_matching.py` module. Use LocaNext's existing `normalize_text()` only for display, never for merge matching.
**Warning signs:** Matches that should be exact fail because normalization produces different output.

## Code Examples

### Correction Parsing with All Skip Guards
```python
# Source: QuickTranslate xml_io.py parse_corrections_from_xml()
def parse_corrections_from_rows(source_rows: list[dict]) -> list[dict]:
    """Parse corrections from source file rows with all skip guards."""
    corrections = []
    for row in source_rows:
        string_id = (row.get("string_id") or "").strip()
        source = (row.get("source") or "").strip()     # StrOrigin
        target = (row.get("target") or "").strip()      # Str (the translation)

        if not string_id or not target:
            continue

        # Guard 1: Korean text = untranslated, NOT a correction
        if is_korean_text(target):
            continue

        # Guard 2: "no translation" literal
        if _is_no_translation(target):
            continue

        # Guard 3: Formula text
        if is_formula_text(target):
            continue

        # Guard 5: Empty source = golden rule violation
        if not source:
            continue

        corrections.append({
            "string_id": string_id,
            "str_origin": source,
            "corrected": target,
            "raw_attribs": row.get("extra_data") or {},
        })

    return corrections
```

### Building Correction Lookups
```python
# Source: QuickTranslate xml_transfer.py _build_correction_lookups()
def build_strict_lookup(corrections: list[dict]) -> tuple[dict, dict]:
    """Build (StringID, StrOrigin) tuple lookup for strict matching."""
    lookup = defaultdict(list)
    lookup_nospace = defaultdict(list)
    for i, c in enumerate(corrections):
        sid_lower = c["string_id"].lower()
        origin_norm = normalize_text_for_match(c.get("str_origin", ""))
        origin_nospace = normalize_nospace(origin_norm)
        lookup[(sid_lower, origin_norm)].append((c["corrected"], i))
        lookup_nospace[(sid_lower, origin_nospace)].append((c["corrected"], i))
    return lookup, lookup_nospace

def build_strorigin_lookup(corrections: list[dict]) -> tuple[dict, dict]:
    """Build StrOrigin-only lookup for source text matching."""
    lookup = {}
    lookup_nospace = {}
    for i, c in enumerate(corrections):
        origin_norm = normalize_for_matching(c.get("str_origin", ""))
        if not origin_norm:
            continue
        origin_nospace = normalize_nospace(origin_norm)
        lookup[origin_norm] = (c["corrected"], i)
        lookup_nospace[origin_nospace] = (c["corrected"], i)
    return lookup, lookup_nospace
```

### 8-Step Postprocess Pipeline
```python
# Source: QuickTranslate postprocess.py run_all_postprocess_on_tree()
POSTPROCESS_STEPS = [
    ("newlines",        _normalize_newlines),        # Step 1: All newlines -> <br/>
    ("empty_strorigin", _enforce_empty_strorigin),   # Step 2: Empty source = empty target
    ("no_translation",  _replace_no_translation),    # Step 3: "no translation" -> source text
    ("apostrophes",     _normalize_apostrophes),     # Step 4: Curly -> ASCII apostrophe
    ("invisible_chars", _cleanup_invisible_chars),   # Step 5: NBSP->space, delete zero-width
    ("hyphens",         _normalize_hyphens),          # Step 6: Unicode hyphens -> ASCII
    ("ellipsis",        _normalize_ellipsis),         # Step 7: ... (skip for CJK)
    ("double_escaped",  _decode_safe_entities),       # Step 8: Double-escaped entities
]

def postprocess_value(value: str, is_cjk: bool = False) -> tuple[str, dict]:
    """Run all postprocess steps on a single value. Returns (cleaned, stats)."""
    stats = {}
    for step_name, step_fn in POSTPROCESS_STEPS:
        if step_name == "ellipsis" and is_cjk:
            continue  # CJK languages keep Unicode ellipsis
        result = step_fn(value)
        if result != value:
            stats[step_name] = True
            value = result
    return value, stats
```

### Fuzzy Match via Model2Vec
```python
# Source: Existing LocaNext EmbeddingEngine + TMSearcher patterns
async def find_fuzzy_matches(
    source_texts: list[str],
    target_texts: list[str],
    threshold: float = 0.85,
) -> list[tuple[int, int, float]]:
    """Find fuzzy matches between source and target texts using Model2Vec."""
    engine = get_embedding_engine()

    # Encode all texts
    source_embeddings = engine.encode(source_texts)
    target_embeddings = engine.encode(target_texts)

    # Normalize for cosine similarity
    faiss.normalize_L2(source_embeddings)
    faiss.normalize_L2(target_embeddings)

    # Build FAISS index from target
    dim = target_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(target_embeddings)

    # Search
    scores, indices = index.search(source_embeddings, k=1)

    matches = []
    for src_idx in range(len(source_texts)):
        tgt_idx = int(indices[src_idx][0])
        score = float(scores[src_idx][0])
        if score >= threshold:
            matches.append((src_idx, tgt_idx, score))

    return matches
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single StringID lookup | 4-tier match hierarchy | QuickTranslate v2+ | Catches re-keyed and paraphrased strings |
| Edit-distance fuzzy | Model2Vec semantic similarity | Model2Vec migration (2026) | 79x faster, catches paraphrases not just typos |
| Manual br-tag handling | 3-layer automatic defense | QuickTranslate postprocess.py | Zero br-tag corruption in production |
| 7-step postprocess | 8-step postprocess | Recent QuickTranslate update | Added double-escaped entity decode (step 8) |

**Note:** QuickTranslate's postprocess has grown from 7 to 8 steps (adding `cleanup_double_escaped`). The phase description says "7-step" but the actual source has 8. Port all 8.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in pytest.ini) |
| Config file | `pytest.ini` |
| Quick run command | `python -m pytest tests/unit/ldm/test_translator_merge.py -x` |
| Full suite command | `python -m pytest tests/unit/ldm/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMERGE-01 | Exact StringID match transfers translations | unit | `python -m pytest tests/unit/ldm/test_translator_merge.py::test_strict_match -x` | Wave 0 |
| TMERGE-01 | StringID-only match transfers when source text differs | unit | `python -m pytest tests/unit/ldm/test_translator_merge.py::test_stringid_only_match -x` | Wave 0 |
| TMERGE-02 | StrOrigin match transfers when StringID differs | unit | `python -m pytest tests/unit/ldm/test_translator_merge.py::test_strorigin_match -x` | Wave 0 |
| TMERGE-03 | Fuzzy matching finds similar strings above threshold | unit | `python -m pytest tests/unit/ldm/test_translator_merge.py::test_fuzzy_match -x` | Wave 0 |
| TMERGE-04 | 8-step postprocess pipeline runs correctly | unit | `python -m pytest tests/unit/ldm/test_postprocess.py -x` | Wave 0 |
| TMERGE-04 | CJK languages skip ellipsis normalization | unit | `python -m pytest tests/unit/ldm/test_postprocess.py::test_cjk_ellipsis_skip -x` | Wave 0 |
| ALL | Skip guards prevent bad corrections | unit | `python -m pytest tests/unit/ldm/test_translator_merge.py::TestSkipGuards -x` | Wave 0 |
| ALL | br-tag round-trip preservation | unit | `python -m pytest tests/unit/ldm/test_postprocess.py::test_br_tag_roundtrip -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_translator_merge.py tests/unit/ldm/test_postprocess.py -x`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_translator_merge.py` -- covers TMERGE-01, TMERGE-02, TMERGE-03
- [ ] `tests/unit/ldm/test_postprocess.py` -- covers TMERGE-04
- [ ] `tests/unit/ldm/test_text_matching.py` -- covers normalize functions
- [ ] `tests/fixtures/xml/merge_source.xml` -- source file with corrections
- [ ] `tests/fixtures/xml/merge_target.xml` -- target file to merge into

## Open Questions

1. **Desc transfer scope**
   - What we know: QuickTranslate transfers Desc (voice direction descriptions) alongside Str when both DescOrigin match. The `_try_write_desc()` function handles this.
   - What's unclear: Does LocaNext's row model store Desc separately or as part of extra_data?
   - Recommendation: Check row schema. If Desc is in extra_data, the merge service needs to read/write it there.

2. **Match mode UI exposure**
   - What we know: QuickTranslate exposes match modes as separate buttons/tabs in the GUI (Strict, StringID-only, StrOrigin-only).
   - What's unclear: Should LocaNext expose all 4 match modes or default to strict with fuzzy fallback?
   - Recommendation: Start with a single "Merge" action that runs strict + strorigin_only + fuzzy in cascade (priority order). Advanced users can select specific modes later.

3. **Merge target: files or rows?**
   - What we know: QuickTranslate merges XML files on disk. LocaNext has rows in a database.
   - What's unclear: Does the user upload a source file and merge into an already-loaded target file? Or select two loaded files?
   - Recommendation: User selects a source file (upload or already loaded), and the merge applies to the currently open target file's rows.

## Sources

### Primary (HIGH confidence)
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py` -- merge_corrections_to_xml (strict), merge_corrections_stringid_only, _build_correction_lookups (4 modes), _convert_linebreaks_for_xml, _is_no_translation, _try_write_desc, _fast_folder_merge
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/postprocess.py` -- run_all_postprocess_on_tree (8-step), _normalize_newlines (7 variants), cleanup functions, _CJK_SKIP_LANGS
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_io.py` -- parse_corrections_from_xml (skip guards: Korean, no-translation, formula, integrity)
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/text_utils.py` -- normalize_text, normalize_for_matching, normalize_nospace
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/korean_detection.py` -- is_korean_text with full regex
- `server/tools/ldm/services/xml_parsing.py` -- XMLParsingEngine, get_attr, iter_locstr_elements, attribute constants
- `server/tools/ldm/file_handlers/xml_handler.py` -- parse_xml_file, row model (string_id, source, target, extra_data)
- `server/tools/shared/embedding_engine.py` -- EmbeddingEngine, get_embedding_engine (Model2Vec)
- `server/tools/ldm/indexing/searcher.py` -- TMSearcher, FAISS integration pattern
- `server/repositories/sqlite/row_repo.py` -- Row schema (id, file_id, row_num, string_id, source, target, status, extra_data)

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` -- Pitfalls 1, 4, 14, 15, 19 directly apply to this phase
- `.planning/research/SUMMARY.md` -- Architecture patterns and phase ordering rationale
- Project MEMORY.md -- Cross-project rules (Korean regex, br-tags, Excel libs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in production
- Architecture: HIGH -- based on direct source code analysis of both QuickTranslate and LocaNext
- Pitfalls: HIGH -- every pitfall sourced from production code and documented bugs
- Match logic: HIGH -- exact source code read, function signatures and edge cases documented
- Postprocess: HIGH -- all 8 steps read and documented with exact behavior
- Fuzzy matching: MEDIUM -- existing infrastructure confirmed, adapter pattern needs implementation

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- QuickTranslate merge logic is mature)
