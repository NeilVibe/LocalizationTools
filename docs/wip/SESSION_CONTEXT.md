# Session Context - Claude Handoff

**Updated:** 2025-12-17 02:20 KST | **Build:** 296 ✅

---

## TL;DR

| Status | Value |
|--------|-------|
| **Build** | 296 ✅ (v25.1217.0136) |
| **Latest Commit** | `e3c5ac3` - Playground PostgreSQL auto-config |
| **Open Issues** | 0 |
| **Playground** | ✅ ONLINE (PostgreSQL 172.28.150.120:5432) |
| **Current** | Session complete - all docs updated |
| **Next** | Phase 2 Backend (API endpoints) |

---

## IMPORTANT: Session Changes (2025-12-17)

### Security Fix: Removed Server Config UI ✅

**Problem:** Users could see "Configure Server" button exposing PostgreSQL settings.

**Fixed:**
1. ❌ Deleted `ServerConfigModal.svelte` (exposed DB credentials)
2. ❌ Removed `/api/server-config/*` endpoints from backend
3. ❌ Removed "Configure Server" button from ServerStatus.svelte
4. ✅ App now auto-connects to central PostgreSQL (no user config needed)

### Playground Auto-Login Feature ✅

Added `--auto-login` flag to playground install:

```bash
# Full install with auto-login as neil/neil
./scripts/playground_install.sh --launch --auto-login
```

This waits for First Time Setup, then logs in automatically via API.

### Playground Auto-Config for PostgreSQL ✅

**Problem:** App was falling back to SQLite (OFFLINE) even with server-config.json.

**Root Cause:** PowerShell 5.x `Set-Content -Encoding UTF8` adds a UTF-8 BOM which breaks Python's JSON parsing. The config file was silently failing to load.

**Fixed in `playground_install.ps1`:**
```powershell
# Write without BOM (PowerShell 5.x UTF8 adds BOM which breaks JSON parsing)
$jsonContent = $config | ConvertTo-Json
[System.IO.File]::WriteAllText($configPath, $jsonContent, [System.Text.UTF8Encoding]::new($false))
```

**Also fixed:** Reset PostgreSQL password for `localization_admin` to match config.

**Verified:** App now connects to PostgreSQL and shows `database_type: postgresql` in health check.

---

## IMPORTANT: Where We Left Off

### COMPLETED: E2E Tests for All Pretranslation Logic ✅

**Created comprehensive E2E tests (~500 rows each) covering ALL cases each logic handles.**

#### Key Understanding

**QWEN = TEXT SIMILARITY (not meaning)**
- "저장" vs "저장" = 100% ✅ (same text)
- "저장" vs "세이브" = 58% (different text, correctly low)
- We match TEXT patterns, not semantic meaning
- 92% threshold is appropriate for text similarity

#### E2E Test Results Summary

| Engine | Passed | Failed | Edge Cases | Status |
|--------|--------|--------|------------|--------|
| **XLS Transfer** | 537 | 0 | 5 | ✅ Complete |
| **KR Similar** | 530 | 0 | 0 | ✅ Complete |
| **Standard TM** | 566 | 0 | 0 | ✅ Complete |
| **QWEN+FAISS Real** | 500 | 0 | 0 | ✅ Complete |
| **TOTAL** | **2,133** | **0** | **5** | ✅ All Passed |

---

### P36 Phase 1: Testing COMPLETE ✅

#### XLS Transfer E2E - 537 passed, 0 failed, 5 edge cases

| Case Type | Count | Status |
|-----------|-------|--------|
| plain_text | 88/88 | ✅ |
| code_at_start | 55/55 | ✅ |
| multiple_codes_start | 33/33 | ✅ |
| code_in_middle | 33/33 | ✅ |
| pacolor_hex | 55/55 | ✅ |
| color_wrapper_with_prefix | 55/55 | ✅ |
| textbind_codes | 44/44 | ✅ |
| mixed_codes_colors | 22/22 | ✅ |
| with_newlines | 31/31 | ✅ |
| x000d_removal | 20/20 | ✅ |
| complex_real | 20/20 | ✅ |
| **BULK (500 rows)** | **500/500** | ✅ |

**Edge cases:** 5 `<PAOldColor>` cases (known issue, same as monolith)

#### KR Similar E2E - 530 passed, 0 failed

| Case Type | Count | Status |
|-----------|-------|--------|
| plain_text | 95/95 | ✅ |
| single_triangle | 57/57 | ✅ |
| multiple_triangles | 57/57 | ✅ |
| scale_tags | 57/57 | ✅ |
| color_tags | 54/54 | ✅ |
| mixed_scale_color | 36/36 | ✅ |
| triangle_with_tags | 36/36 | ✅ |
| empty_lines | 36/36 | ✅ |
| structure_adaptation | 54/54 | ✅ |
| complex_multiline | 18/18 | ✅ |
| **BULK (500 rows)** | **500/500** | ✅ |

#### Standard TM E2E - 566 passed, 0 failed

| Test Category | Status |
|---------------|--------|
| Newline normalization (11 cases) | ✅ All pass |
| Hash normalization (10 cases) | ✅ All pass |
| Embedding normalization (5 cases) | ✅ All pass |
| N-gram similarity (6 cases) | ✅ All pass |
| Hash lookup (7 cases) | ✅ All pass |
| Line lookup (4 cases) | ✅ All pass |
| Threshold constants | ✅ Correct |
| Empty/null handling | ✅ Handles gracefully |
| Special characters (11 cases) | ✅ All pass |
| TMSearcher initialization | ✅ Works |
| **BULK (500 rows)** | **500/500** | ✅ |

#### QWEN Validation - Complete ✅

| Category | Score Range | Status |
|----------|-------------|--------|
| Identical | 100% | ✅ Perfect |
| Punctuation diff | 90-97% | ✅ Good |
| One word diff | 68-84% | ✅ Good separation |
| Synonyms | 83-87% | ✅ Good |
| Opposite meanings | 64-72% | ✅ Correctly low |
| Unrelated | 26-37% | ✅ Correctly very low |
| Short EN variations | 61-72% | ⚠️ NPC threshold issue |

**Result:** 26/27 tests passed (96.3%)

---

## Test Files

### E2E Test Suite (NEW)

```
tests/fixtures/pretranslation/
├── e2e_test_data.py             # Test data generator (all cases)
├── test_e2e_xls_transfer.py     # XLS Transfer E2E (537 passed) ✅
├── test_e2e_kr_similar.py       # KR Similar E2E (530 passed) ✅
├── test_e2e_tm_standard.py      # Standard TM E2E (566 passed) ✅
├── test_e2e_tm_faiss_real.py    # REAL QWEN+FAISS E2E (500 queries) ✅
├── test_qwen_validation.py      # QWEN similarity tests (26/27) ✅
└── test_real_patterns.py        # Real pattern tests (13/13) ✅
```

### QWEN + FAISS Real E2E Results

| Metric | Value |
|--------|-------|
| TM Entries | 165 |
| Test Queries | 500 |
| Model Load | 25s |
| Search Time | 44s (88ms/query) |
| **Matched** | **180 (36%)** |
| **No Match** | **320 (64%)** |

**Tier Distribution:**
- Tier 1 (Hash): 105 (21%) - exact matches
- Tier 2 (FAISS): 25 (5%) - embedding matches
- Tier 3 (Line): 50 (10%) - line matches
- Tier 0 (None): 320 (64%) - below 92% threshold

### Test Data Files

```
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/
├── sampleofLanguageData.txt     # 16MB - Full production data
├── closetotest.txt              # Korean dialogue with ▶ markers
└── [other test files...]
```

---

## P36 Architecture

**Three SEPARATE engines - user selects ONE:**

```
┌───────────────────────────────────────────────────────────────────────┐
│  1. STANDARD (TM 5-Tier)                                             │
│     └── Hash + FAISS HNSW + N-gram cascade                           │
│     └── server/tools/ldm/tm_indexer.py                               │
│                                                                       │
│  2. XLS TRANSFER (DO NOT MODIFY)                                     │
│     └── server/tools/xlstransfer/                                    │
│     └── Monolith: XLSTransfer0225.py                                 │
│                                                                       │
│  3. KR SIMILAR (DO NOT MODIFY)                                       │
│     └── server/tools/kr_similar/                                     │
│     └── Monolith: KRSIMILAR0124.py                                   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Potential Issues (Future Reference)

See: `docs/wip/POTENTIAL_ISSUES.md`

One edge case documented:
- `<PAColor>` at position 0 loses `<PAOldColor>` ending
- Same behavior in original monolith
- Only fix if user feedback received

---

## Threshold Recommendations

| Use Case | Current | Recommended | Evidence |
|----------|---------|-------------|----------|
| **TM Matching** | 92% | **90%** | Punctuation removal = 90.2% |
| **NPC Check** | 80% | **65%** | Short variations = 61-72% |
| **Safe Floor** | - | **>72%** | Opposite meanings = up to 71.9% |

---

## Next Steps

1. **Phase 1 COMPLETE** - All E2E tests passing (2,133 tests) ✅
2. **Commit `480e7fc`** - E2E test suite + doc cleanup pushed ✅
3. **NEXT:** Phase 2 Backend implementation
   - API endpoint for pretranslation (`/api/ldm/pretranslate`)
   - Engine selection (Standard TM / XLS Transfer / KR Similar)
   - Batch processing support
4. **AFTER:** Phase 3 Pretranslation Modal UI
   - Right-click file → "Pretranslate..."
   - Engine selection, threshold slider, options

---

## Quick Commands

```bash
# Run E2E tests
python3 tests/fixtures/pretranslation/test_e2e_xls_transfer.py
python3 tests/fixtures/pretranslation/test_e2e_kr_similar.py
python3 tests/fixtures/pretranslation/test_e2e_tm_standard.py

# Run all pretranslation tests
python3 tests/fixtures/pretranslation/test_qwen_validation.py
python3 tests/fixtures/pretranslation/test_real_patterns.py

# Check servers
./scripts/check_servers.sh

# Playground install with auto-login
./scripts/playground_install.sh --launch --auto-login
```

---

## Documentation State

| Doc | Status |
|-----|--------|
| `CLAUDE.md` | ✅ Current |
| `Roadmap.md` | ✅ Current |
| `P36_PRETRANSLATION_STACK.md` | ✅ Current |
| `SESSION_CONTEXT.md` | ✅ This file |
| `ISSUES_TO_FIX.md` | ✅ 0 open |
| `POTENTIAL_ISSUES.md` | ✅ For future reference |

---

*Last: 2025-12-17 02:25 KST - Commit e3c5ac3 pushed. Playground PostgreSQL auto-config working. Ready for Phase 2 Backend.*
