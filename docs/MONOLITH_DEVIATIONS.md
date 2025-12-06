# Monolith Code Deviations - Audit Report

**Audit Date:** 2025-12-06
**Status:** Issues Identified - Fixes Required

---

## Summary

The original Python scripts (monoliths) in `RessourcesForCodingTheProject/` are **FLAWLESS** - they work perfectly. Our server implementations deviate from them in several ways that cause bugs.

**Rule:** When in doubt, copy the original monolith logic EXACTLY.

---

## XLSTransfer (100% Correct - FIXED 2025-12-06)

**Monolith:** `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/XLSTransfer0225.py`
**Implementation:** `server/tools/xlstransfer/`

### CRITICAL Issues - ALL FIXED ✅

| Issue | Location | Status |
|-------|----------|--------|
| Simple Excel Transfer | `simple_transfer.py` | **FIXED** - Full implementation with API endpoints |

### Minor Issues (Backlog)

| Issue | Location | Fix |
|-------|----------|-----|
| Newline counting includes escaped `\\n` | `core.py:420-424` | Should only count literal `\n` |

### Correctly Implemented
- Create Dictionary ✅
- Load Dictionary ✅
- Translate Excel ✅
- Check Newlines (logic correct, counting differs)
- Combine Excel ✅
- Newline Auto-Adapt ✅
- Code pattern handling ✅
- FAISS matching ✅
- **Simple Excel Transfer** ✅ (NEW: analyze + execute endpoints)

---

## KR Similar (95% Correct - FIXED 2025-12-06)

**Monolith:** `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/KRSIMILAR0124.py`
**Implementation:** `server/tools/kr_similar/`

### CRITICAL Issues - ALL FIXED ✅

| Issue | Location | Status |
|-------|----------|--------|
| Missing triangle marker fallback | `searcher.py:321-365` | **FIXED** - Added normalized structure fallback |
| Custom skip-self logic differs | `searcher.py:167-172` | **FIXED** - Using mask-based skip with k+1 search |

### HIGH Priority Issues

| Issue | Location | Status |
|-------|----------|--------|
| Extract output format mismatch | `searcher.py:228-272` | **FIXED** - Returns 9-column TSV format |
| Missing file deduplication on 5 cols | `searcher.py:245-253` | **FIXED** - Dedup on first 5 fields |
| No file output in extract | `kr_similar_async.py` | API returns data, caller handles file |
| Missing dictionary update mode | `embeddings.py:129-192` | Backlog - incremental update |

### MEDIUM Priority Issues - FIXED ✅

| Issue | Location | Status |
|-------|----------|--------|
| Progress every 100 vs 10 rows | `searcher.py:200` | **FIXED** - Now every 10 rows |

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

### P1 - Critical (Blocking Features) - ALL COMPLETE ✅
1. ~~KR Similar: Triangle marker fallback~~ ✅ FIXED
2. ~~KR Similar: Skip-self logic~~ ✅ FIXED
3. ~~XLSTransfer: Simple Excel Transfer implementation~~ ✅ FIXED

### P2 - High (Wrong Results)
4. ~~KR Similar: Extract output format~~ ✅ FIXED
5. ~~KR Similar: Deduplication on 5 fields~~ ✅ FIXED
6. QuickSearch: Exception handling

### P3 - Medium (User Experience)
7. ~~KR Similar: Progress frequency~~ ✅ FIXED
8. KR Similar: File output (API handles differently)
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
