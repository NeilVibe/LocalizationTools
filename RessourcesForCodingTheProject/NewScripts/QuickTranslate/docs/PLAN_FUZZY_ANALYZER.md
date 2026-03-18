# Plan: Fuzzy Match Analyzer (Other Tools Tab)

**Status:** Reviewed by 2 agents, revised per user feedback. Ready for implementation.

## What It Does

Read-only analysis tool. Compares Source corrections against Target languagedata to answer: **"If I run fuzzy transfer, what would happen?"** — without actually transferring anything.

Classifies every StrOrigin change into 3 impact buckets: **SAFE / REVIEW / RETRANSLATE**.

---

## Where It Lives

**Other Tools tab** — new section below "Find Missing Translations."

GUI elements:
- Button: **"Analyze Fuzzy"**
- Uses the existing Source/Target paths from the Transfer tab (same pattern as Find Missing)
- Must call `_ensure_fuzzy_model()` before spawning worker thread
- Progress bar + log output in the console

---

## The 3 Buckets

| Bucket | Color | Meaning | Detection |
|--------|-------|---------|-----------|
| **SAFE** | Green | Zero impact on translation. Ship it. | After full normalize (collapse ws + strip punct + lowercase), texts are equal |
| **REVIEW** | Yellow | Might affect meaning. Quick human check. | Texts differ after normalize, but difflib ratio > 0.5 |
| **RETRANSLATE** | Red | Different text. Translation is probably wrong. | difflib ratio ≤ 0.5 |

**SAFE** catches: whitespace changes, punctuation changes, capitalization changes, and any combination of those. One normalize-and-compare, done.

---

## Analysis Pipeline

### Step 1: Load & Match by StringID

```
Source corrections (pre-parsed list of dicts from GUI)
Target languagedata (XML, one language file)

For each source StringID (case-insensitive .lower()):
  - Found in target with identical StrOrigin? → IDENTICAL (count only, not in report)
  - Found in target with different StrOrigin? → classify into SAFE / REVIEW / RETRANSLATE
  - Not found in target? → NOT FOUND sheet
```

Multi-language sources: deduplicate by StringID (StrOrigin is language-agnostic).

### Step 2: Classify & Score

For each changed pair:

1. **SAFE check**: `normalize_all(source) == normalize_all(target)` → SAFE, done
2. **difflib ratio**: `SequenceMatcher(source, target).ratio()`
   - ratio > 0.5 → REVIEW
   - ratio ≤ 0.5 → RETRANSLATE
3. **Pairwise cosine** (Model2Vec): encode both, dot product → fuzzy score
4. **Word-level diff**: `extract_differences()` from `failure_report.py`

### Step 3: FAISS Coverage Prediction

- Build LOCAL FAISS index from target StrOrigins (do NOT touch global cache)
- For each changed source StrOrigin: search index, check if top-1 = correct StringID
- Bin scores into threshold bands for coverage prediction table

---

## Output: `FuzzyAnalysis_YYMMDD_HHMM.xlsx`

Saved to `Output/` folder (same as Find Missing reports).

### Sheet 1: "Summary"

```
=== Overview ===
Total Source Entries:          500
  Skipped (empty StrOrigin):    5
Found in Target:              480
  Identical StrOrigin:        350  (not shown — safe for exact match)
  Different StrOrigin:        130
Not Found in Target:           15

=== Impact Breakdown ===
Bucket            Count    %        Avg Score
SAFE                 43   33.1%     0.972
REVIEW               68   52.3%     0.854
RETRANSLATE          19   14.6%     0.714

=== Fuzzy Coverage Prediction ===
Threshold    Would Match    Coverage
0.95+            43          33.1%
0.90-0.95        28          21.5%
0.85-0.90        24          18.5%     ← default
0.80-0.85        16          12.3%
0.75-0.80         9           6.9%
0.70-0.75         5           3.8%
Below 0.70        5           3.8%
```

Color-coded bands (same palette as Fuzzy Match Report).

### Sheet 2: "SAFE"

Green rows. These changes won't affect translation quality.

| StringID | Source StrOrigin | Target StrOrigin | Diff | Fuzzy Score |

Sorted by fuzzy score ascending. Autofilter + freeze.

### Sheet 3: "REVIEW"

Yellow rows. Human should glance at these.

| StringID | Source StrOrigin | Target StrOrigin | Diff | Fuzzy Score | Status | Comment |

Sorted by fuzzy score ascending (worst first = review priority). Status dropdown: ISSUE / NO ISSUE / FIXED.

### Sheet 4: "RETRANSLATE"

Red rows. Translation is likely wrong, needs redo.

| StringID | Source StrOrigin | Target StrOrigin | Diff | Fuzzy Score | Status | Comment |

Sorted by fuzzy score ascending. Status dropdown.

### Sheet 5: "Not Found"

Gray rows. StringIDs missing from target entirely.

| StringID | Source StrOrigin | Correction |

---

## Implementation

### Files to Change

| File | Change | ~Lines |
|------|--------|:------:|
| `core/fuzzy_analyzer.py` | **NEW** — engine + report generator (self-contained) | ~350 |
| `gui/app.py` | Button + thread in Other Tools tab | ~40 |
| `core/__init__.py` | Export `analyze_fuzzy` | ~2 |

### `core/fuzzy_analyzer.py`

```python
def analyze_fuzzy(
    corrections: List[Dict],
    target_folder: Path,
    progress_callback=None,
    log_callback=None,
) -> Dict:
    """
    Read-only fuzzy analysis: compare source corrections against target.

    Returns dict with:
      - identical_count: int
      - safe: List[Dict]
      - review: List[Dict]
      - retranslate: List[Dict]
      - not_found: List[Dict]
      - coverage: List[Dict]
    """


def _classify_change(source_str: str, target_str: str) -> str:
    """Returns 'SAFE', 'REVIEW', or 'RETRANSLATE'."""
    normalized_source = _normalize_all(source_str)
    normalized_target = _normalize_all(target_str)
    if normalized_source == normalized_target:
        return "SAFE"
    ratio = SequenceMatcher(None, source_str, target_str).ratio()
    return "REVIEW" if ratio > 0.5 else "RETRANSLATE"


def _normalize_all(text: str) -> str:
    """Collapse whitespace + strip punctuation + lowercase."""


def generate_analysis_report(results: Dict, output_path: Path) -> Path:
    """5-sheet xlsxwriter report."""
```

### Critical Rules

- **Case-insensitive StringID**: `.lower()` for all lookups
- **normalize_for_matching()**: for "identical" StrOrigin comparison
- **Local FAISS index**: build fresh, do NOT use/modify global `_cached_index`
- **Read-only**: no file writes except the output report
- **<br/> handling**: normalize before comparing

### Dependencies

All already installed: Model2Vec, FAISS, difflib (stdlib), xlsxwriter.

---

## What This Does NOT Do

- Does NOT modify any source or target files
- Does NOT replace TRANSFER or the Fuzzy Report
- Does NOT use ML for classification (rule-based: normalize + difflib ratio)

---

## Verification

1. Run on real source/target with known mismatches
2. SAFE + REVIEW + RETRANSLATE counts = total changed
3. All SAFE entries must pass: normalize_all(source) == normalize_all(target)
4. Coverage prediction matches actual fuzzy transfer results
5. Non-fuzzy mode (no Model2Vec): button disabled or graceful error
