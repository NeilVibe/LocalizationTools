---
phase: 09-translator-merge
plan: 01
subsystem: text-processing
tags: [postprocess, normalization, korean, text-matching, br-tag, cjk]

requires:
  - phase: 07-xml-parsing
    provides: XMLParsingEngine singleton for centralized parsing
provides:
  - normalize_text_for_match, normalize_for_matching, normalize_nospace for merge lookup
  - is_formula_text for Excel formula/error detection
  - is_korean_text with full 3-range regex (syllables + Jamo + Compat Jamo)
  - postprocess_value for single-value 8-step cleanup
  - postprocess_rows for batch row cleanup
  - POSTPROCESS_STEPS ordered list of (name, function) tuples
affects: [09-translator-merge, 10-gamedev-merge]

tech-stack:
  added: []
  patterns: [8-step postprocess pipeline, CJK ellipsis skip, br-tag roundtrip safety]

key-files:
  created:
    - server/tools/ldm/services/text_matching.py
    - server/tools/ldm/services/korean_detection.py
    - server/tools/ldm/services/postprocess.py
    - tests/unit/ldm/test_text_matching.py
    - tests/unit/ldm/test_postprocess.py
  modified: []

key-decisions:
  - "normalize_text_for_match named differently from LocaNext display normalize_text to avoid confusion"
  - "postprocess_value source defaults to None (skip step 2) not empty string (clear target)"
  - "en-dash and em-dash NOT normalized to hyphen (only U+2010/U+2011 which are visually identical)"

patterns-established:
  - "Postprocess pipeline: ordered (name, function) tuples in POSTPROCESS_STEPS list"
  - "CJK detection: is_korean_text with 3-range regex for skip-guard decisions"
  - "Source sentinel: None = not applicable, empty string = explicitly empty"

requirements-completed: [TMERGE-04]

duration: 4min
completed: 2026-03-15
---

# Phase 09 Plan 01: Text Utilities + Postprocess Pipeline Summary

**Ported QuickTranslate's text matching (4 functions), Korean detection, and 8-step postprocess pipeline with CJK skip and br-tag roundtrip safety**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T02:35:43Z
- **Completed:** 2026-03-15T02:40:00Z
- **Tasks:** 2
- **Files created:** 5

## Accomplishments
- Text matching utilities (normalize_text_for_match, normalize_for_matching, normalize_nospace, is_formula_text) ported from QuickTranslate
- Korean detection with full 3-range Unicode regex (syllables + Jamo + Compat Jamo)
- 8-step postprocess pipeline: newlines, empty_strorigin, no_translation, apostrophes, invisible_chars, hyphens, ellipsis, double_escaped
- 87 unit tests (38 text matching + 49 postprocess), all passing, no regressions (372 total LDM tests pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Text matching utilities + Korean detection** - `8a927f6e` (feat)
2. **Task 2: 8-step postprocess pipeline** - `1b4f8c76` (feat)

## Files Created/Modified
- `server/tools/ldm/services/text_matching.py` - normalize_text_for_match, normalize_for_matching, normalize_nospace, is_formula_text
- `server/tools/ldm/services/korean_detection.py` - is_korean_text with 3-range regex
- `server/tools/ldm/services/postprocess.py` - 8-step pipeline, postprocess_value, postprocess_rows
- `tests/unit/ldm/test_text_matching.py` - 38 tests for all matching + detection functions
- `tests/unit/ldm/test_postprocess.py` - 49 tests for each step, pipeline order, CJK skip, br-tag roundtrip

## Decisions Made
- Named merge normalization `normalize_text_for_match` to distinguish from LocaNext's display `normalize_text` (different purpose: HTML unescape vs quote stripping)
- `postprocess_value(source=None)` means step 2 not applicable (skipped); `source=""` means source is empty (target cleared). This avoids accidental clearing when source is simply not provided.
- Only U+2010 (Hyphen) and U+2011 (Non-breaking Hyphen) normalized to ASCII hyphen. En-dash (U+2013) and em-dash (U+2014) are intentional typography and left untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed source default sentinel in postprocess_value**
- **Found during:** Task 2 (postprocess pipeline)
- **Issue:** Default `source=""` caused step 2 to clear all targets when source was simply not provided
- **Fix:** Changed default to `source=None` with None meaning "not applicable" (step 2 skipped)
- **Files modified:** server/tools/ldm/services/postprocess.py
- **Verification:** All 49 postprocess tests pass
- **Committed in:** 1b4f8c76 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness. Without this fix, postprocess_value would clear all values when called without source text.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Text matching utilities ready for TranslatorMergeService match lookup building (Plan 02)
- Korean detection ready for CJK skip guards in merge and postprocess
- Postprocess pipeline ready for post-merge cleanup (Plan 02)
- All 372 LDM tests pass, no regressions

---
*Phase: 09-translator-merge*
*Completed: 2026-03-15*
