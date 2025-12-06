# Monolith Code Deviations - Audit Report

**Audit Date:** 2025-12-06
**Status:** Issues Identified - Fixes Required

---

## Summary

The original Python scripts (monoliths) in `RessourcesForCodingTheProject/` are **FLAWLESS** - they work perfectly. Our server implementations deviate from them in several ways that cause bugs.

**Rule:** When in doubt, copy the original monolith logic EXACTLY.

---

## XLSTransfer (95% Correct)

**Monolith:** `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/XLSTransfer0225.py`
**Implementation:** `server/tools/xlstransfer/`

### CRITICAL Issues

| Issue | Location | Status |
|-------|----------|--------|
| Simple Excel Transfer NOT IMPLEMENTED | `simple_transfer.py:16-26` | Returns error only |

### Minor Issues

| Issue | Location | Fix |
|-------|----------|-----|
| Newline counting includes escaped `\\n` | `core.py:420-424` | Should only count literal `\n` |

### Correctly Implemented
- Create Dictionary
- Load Dictionary
- Translate Excel
- Check Newlines (logic correct, counting differs)
- Combine Excel
- Newline Auto-Adapt
- Code pattern handling
- FAISS matching

---

## KR Similar (70% Correct)

**Monolith:** `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/KRSIMILAR0124.py`
**Implementation:** `server/tools/kr_similar/`

### CRITICAL Issues

| Issue | Location | Original Lines | Fix Required |
|-------|----------|----------------|--------------|
| Missing triangle marker fallback | `searcher.py:294-320` | Lines 536-576 | Add normalized structure fallback when line_changed==False |
| Custom skip-self logic differs | `searcher.py:175-176` | Lines 258-271 | Use mask-based skip with k+1 search |

### HIGH Priority Issues

| Issue | Location | Fix Required |
|-------|----------|--------------|
| Extract output format mismatch | `searcher.py:223-236` | Return 9-column TSV format |
| Missing file deduplication on 5 cols | `searcher.py:200-204` | Add dedup on first 5 fields |
| No file output in extract | `kr_similar_async.py:602` | Write results to disk |
| Missing dictionary update mode | `embeddings.py:129-192` | Add incremental update logic |

### MEDIUM Priority Issues

| Issue | Location | Fix Required |
|-------|----------|--------------|
| Progress every 100 vs 10 rows | `searcher.py:195` | Change to 10 rows |

---

## QuickSearch (80% Correct - FIXED TODAY)

**Monolith:** `RessourcesForCodingTheProject/SECONDARY PYTHON SCRIPTS/QuickSearch0818.py`
**Implementation:** `server/tools/quicksearch/`

### FIXED Today (2025-12-06)

| Issue | Location | Status |
|-------|----------|--------|
| Exception returns 4 values not 6 | `parser.py:177` | **FIXED** |
| Missing `on_bad_lines='skip'` | `parser.py:174` | **FIXED** |

### Still Needs Fix

| Issue | Location | Original Behavior | Fix Required |
|-------|----------|-------------------|--------------|
| Return format: tuple vs list | `searcher.py:213` | Returns list only | API handles correctly - OK |
| Exception crashes instead of [] | `searcher.py:59-213` | Returns [] on error | Add try/except wrapper |
| Reference search deduplicates | `searcher.py:184,201` | Original allows dups | Remove dedup check |
| File parsing early return | `parser.py:110-112` | Uses `continue` | Change to continue |

---

## Test Files (D:\TestFilesForLocaNext)

### Correct Files to Use

| Tool | File | Notes |
|------|------|-------|
| QuickSearch | `sampleofLanguageData.txt` | 16MB, 9 cols, consistent |
| XLSTransfer | `translationTEST.xlsx` | Standard test file |
| KR Similar | `lineembeddingtest.xlsx` | Embedding test |

### DO NOT USE

| File | Problem |
|------|---------|
| `SMALLTESTFILEFORQUICKSEARCH.txt` | Inconsistent column counts (6 or 9) |

---

## Priority Order for Fixes

### P1 - Critical (Blocking Features)
1. KR Similar: Triangle marker fallback
2. KR Similar: Skip-self logic
3. XLSTransfer: Simple Excel Transfer implementation

### P2 - High (Wrong Results)
4. KR Similar: Extract output format
5. KR Similar: Deduplication on 5 fields
6. QuickSearch: Exception handling

### P3 - Medium (User Experience)
7. KR Similar: Progress frequency
8. KR Similar: File output
9. QuickSearch: Remove ref search dedup

### P4 - Low (Optimization)
10. XLSTransfer: Newline counting
11. KR Similar: Dictionary update mode

---

## Key Principle

```
THE MONOLITH CODE IS FLAWLESS.

When implementing:
1. Copy logic EXACTLY from monolith
2. Only change UI-related code (tkinter → API)
3. Keep same error handling (continue, not crash)
4. Keep same return formats where possible
5. Test against same files monolith uses
```

---

*Last Updated: 2025-12-06 by Claude*
