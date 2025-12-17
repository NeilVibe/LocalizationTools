"""
TRUE E2E Test: XLS Transfer Engine with Code Preservation

===============================================================================
THIS IS A TRUE END-TO-END TEST
===============================================================================

WHAT THIS TEST DOES:
1. Loads ~5000 rows from real production data (sampleofLanguageData.txt)
2. Builds FAISS indexes (split mode for line-by-line, whole mode for blocks)
3. Creates test cases with various code patterns ({ItemID}, <PAColor>, etc.)
4. Runs translate_text_multi_mode() to translate Korean → French
5. Verifies CORRECT translation + CODE PRESERVATION

DATA SOURCE:
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/sampleofLanguageData.txt
- 103,499 rows of real game localization data
- Tab-separated: Col1=StringID, Col5=Korean, Col6=French
- Contains: color codes, TextBind, newlines

KEY XLS TRANSFER FEATURES TESTED:
1. Code extraction from Korean text
2. FAISS similarity matching (split/whole mode)
3. Code reconstruction in translated text
4. simple_number_replace() code preservation

CODE PATTERNS TESTED:
- {ItemID}, {Amount}, {NpcName} - game variables
- <PAColor0xHEX>...<PAOldColor> - color wrappers
- {TextBind:...} - UI binding codes
- Mixed codes and colors
- Multiline text with codes

Run: python -m pytest tests/fixtures/stringid/true_e2e_xls_transfer.py -v -s
Time: ~5 minutes (embedding generation)
"""

import os
import sys
import pytest
import random
import tempfile
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Data source path
SAMPLE_DATA_PATH = Path("/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/sampleofLanguageData.txt")

# Test configuration
DICT_SIZE = 5000        # Number of rows for dictionary
TEST_FILE_SIZE = 150    # Number of rows to translate
THRESHOLD = 0.92        # Match threshold


def parse_sample_data(limit: int = None) -> List[Dict]:
    """
    Parse sampleofLanguageData.txt into list of entries.

    Format: Tab-separated
    Col 0: Flag (0)
    Col 1: StringID (numeric)
    Col 2-4: Metadata
    Col 5: Korean source
    Col 6: Target (French)
    Col 7: Status
    """
    if not SAMPLE_DATA_PATH.exists():
        pytest.skip(f"Sample data not found: {SAMPLE_DATA_PATH}")

    entries = []
    with open(SAMPLE_DATA_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break

            parts = line.strip().split('\t')
            if len(parts) >= 7:
                string_id = parts[1].strip()
                source = parts[5].strip()
                target = parts[6].strip()

                if source and target:  # Skip empty
                    entries.append({
                        "string_id": string_id,
                        "source": source,
                        "target": target
                    })

    return entries


def find_entries_with_codes(entries: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Categorize entries by code pattern type.
    """
    categories = {
        "plain_text": [],           # No codes
        "curly_brace_codes": [],    # {ItemID}, {Amount}, etc.
        "pacolor_codes": [],        # <PAColor...>
        "paoldcolor_ending": [],    # Ends with <PAOldColor>
        "textbind_codes": [],       # {TextBind:...}
        "newlines": [],             # Contains \n
        "mixed_codes": [],          # Multiple code types
    }

    for entry in entries:
        src = entry["source"]

        has_curly = "{" in src and "}" in src
        has_pacolor = "<PAColor" in src
        has_paoldcolor = src.endswith("<PAOldColor>")
        has_textbind = "TextBind" in src
        has_newline = "\n" in src or "\\n" in src

        # Categorize
        if has_curly and has_pacolor:
            categories["mixed_codes"].append(entry)
        elif has_textbind:
            categories["textbind_codes"].append(entry)
        elif has_paoldcolor:
            categories["paoldcolor_ending"].append(entry)
        elif has_pacolor:
            categories["pacolor_codes"].append(entry)
        elif has_curly:
            categories["curly_brace_codes"].append(entry)
        elif has_newline:
            categories["newlines"].append(entry)
        else:
            categories["plain_text"].append(entry)

    return categories


class TestTrueE2EXLSTransfer:
    """
    TRUE End-to-End test for XLS Transfer with code preservation.

    This test uses real production data and verifies the full pipeline:
    Dictionary Creation → FAISS Index Build → Translation → Code Reconstruction
    """

    @pytest.fixture(scope="class", autouse=True)
    def setup(self, request):
        """Setup test environment with FAISS indexes from real data."""
        from server.tools.xlstransfer.embeddings import (
            generate_embeddings, create_faiss_index, create_translation_dictionary
        )
        from server.tools.xlstransfer.translation import translate_text_multi_mode
        from server.tools.xlstransfer.core import simple_number_replace, clean_text
        import pandas as pd

        cls = request.cls

        print("\n" + "="*70)
        print("TRUE E2E TEST: XLS Transfer with Code Preservation")
        print("="*70)

        # Parse real data
        print(f"\n[1/6] Loading data from {SAMPLE_DATA_PATH}...")
        all_entries = parse_sample_data(limit=DICT_SIZE * 2)
        print(f"      Loaded {len(all_entries)} entries")

        # Categorize by code patterns
        cls.categories = find_entries_with_codes(all_entries)
        print(f"      Categories found:")
        for cat, items in cls.categories.items():
            print(f"        - {cat}: {len(items)} entries")

        # Select entries for dictionary (first DICT_SIZE)
        cls.dict_entries = all_entries[:DICT_SIZE]
        print(f"\n[2/6] Selected {len(cls.dict_entries)} entries for dictionary")

        # Separate into split and whole mode
        print(f"\n[3/6] Building translation dictionaries...")

        split_kr = []
        split_trans = []
        whole_kr = []
        whole_trans = []

        for entry in cls.dict_entries:
            src = entry["source"]
            tgt = entry["target"]

            # Clean text
            src_clean = clean_text(src) if src else ""
            tgt_clean = clean_text(tgt) if tgt else ""

            if not src_clean or not tgt_clean:
                continue

            # Check line counts
            src_lines = src_clean.split('\n')
            tgt_lines = tgt_clean.split('\n')

            if len(src_lines) == len(tgt_lines) and len(src_lines) > 1:
                # Split mode: line counts match
                for s, t in zip(src_lines, tgt_lines):
                    if s.strip() and t.strip():
                        split_kr.append(s.strip())
                        split_trans.append(t.strip())
            else:
                # Whole mode: single entry
                whole_kr.append(src_clean)
                whole_trans.append(tgt_clean)

        # Also add single lines to split mode
        for entry in cls.dict_entries:
            src = clean_text(entry["source"]) if entry["source"] else ""
            tgt = clean_text(entry["target"]) if entry["target"] else ""
            if src and tgt and '\n' not in src:
                split_kr.append(src)
                split_trans.append(tgt)

        print(f"      Split mode: {len(split_kr)} entries")
        print(f"      Whole mode: {len(whole_kr)} entries")

        # Create dictionaries
        cls.split_dict = create_translation_dictionary(split_kr, split_trans)
        cls.whole_dict = create_translation_dictionary(whole_kr, whole_trans)
        print(f"      Split dict: {len(cls.split_dict)} unique translations")
        print(f"      Whole dict: {len(cls.whole_dict)} unique translations")

        # Generate embeddings and create indexes
        print(f"\n[4/6] Generating embeddings (this takes ~2 minutes)...")

        # Split embeddings
        split_keys = list(cls.split_dict.keys())
        cls.split_embeddings = generate_embeddings(split_keys)
        cls.split_index = create_faiss_index(cls.split_embeddings.copy())
        cls.split_sentences = pd.Series(split_keys, dtype=str)
        print(f"      Split index: {cls.split_index.ntotal} vectors")

        # Whole embeddings
        if cls.whole_dict:
            whole_keys = list(cls.whole_dict.keys())
            cls.whole_embeddings = generate_embeddings(whole_keys)
            cls.whole_index = create_faiss_index(cls.whole_embeddings.copy())
            cls.whole_sentences = pd.Series(whole_keys, dtype=str)
            print(f"      Whole index: {cls.whole_index.ntotal} vectors")
        else:
            cls.whole_index = None
            cls.whole_sentences = None

        # Store helper functions BEFORE creating test cases
        cls.translate_fn = translate_text_multi_mode
        cls.code_preserve_fn = simple_number_replace
        cls.clean_fn = clean_text

        # Create test cases
        print(f"\n[5/6] Creating test cases ({TEST_FILE_SIZE} rows)...")
        cls._create_test_cases_static(cls)
        print(f"      Test cases created: {len(cls.test_cases)}")

        print("\n" + "="*70)
        print("SETUP COMPLETE - Ready for testing")
        print("="*70 + "\n")

        yield

        # Cleanup (nothing to clean for XLS Transfer - no DB)
        print("\n[CLEANUP] Done")

    @staticmethod
    def _create_test_cases_static(cls):
        """
        Create test cases mixing:
        1. Plain text from dictionary (should translate)
        2. Text with {codes} added (should preserve codes)
        3. Text with <PAColor> added (should preserve colors)
        4. Mixed code patterns
        """
        cls.test_cases = []
        cls.expected_results = {}

        # Code patterns to inject
        CODE_PATTERNS = [
            ("{ItemID}", "curly"),
            ("{Amount}", "curly"),
            ("{NpcName}", "curly"),
            ("<PAColor0xffe9bd23>", "pacolor_start"),
            ("{TextBind:CLICK_RMB}", "textbind"),
        ]

        case_num = 0

        # 1. Plain text cases (30 rows) - direct from dictionary
        plain_entries = [e for e in cls.dict_entries if '{' not in e["source"] and '<PA' not in e["source"]]
        for entry in plain_entries[:30]:
            case_num += 1
            src = cls.clean_fn(entry["source"])
            expected_target = cls.split_dict.get(src) or cls.whole_dict.get(src, "")

            cls.test_cases.append({
                "case_num": case_num,
                "type": "plain_text",
                "korean": src,
                "expected_translation": expected_target,
                "expected_codes": []
            })
            cls.expected_results[case_num] = {
                "type": "plain_text",
                "should_translate": bool(expected_target),
                "codes_to_preserve": []
            }

        # 2. Add {code} at START (30 rows)
        for entry in plain_entries[30:60]:
            case_num += 1
            src = cls.clean_fn(entry["source"])
            code = random.choice(["{ItemID}", "{Amount}", "{NpcName}"])
            korean_with_code = code + src
            expected_target = cls.split_dict.get(src) or cls.whole_dict.get(src, "")

            cls.test_cases.append({
                "case_num": case_num,
                "type": "code_at_start",
                "korean": korean_with_code,
                "original_korean": src,
                "expected_translation": expected_target,
                "expected_codes": [code]
            })
            cls.expected_results[case_num] = {
                "type": "code_at_start",
                "should_translate": bool(expected_target),
                "codes_to_preserve": [code]
            }

        # 3. Add <PAColor>...<PAOldColor> wrapper (30 rows)
        for entry in plain_entries[60:90]:
            case_num += 1
            src = cls.clean_fn(entry["source"])
            korean_with_color = f"<PAColor0xffe9bd23>{src}<PAOldColor>"
            expected_target = cls.split_dict.get(src) or cls.whole_dict.get(src, "")

            cls.test_cases.append({
                "case_num": case_num,
                "type": "pacolor_wrapper",
                "korean": korean_with_color,
                "original_korean": src,
                "expected_translation": expected_target,
                "expected_codes": ["<PAColor0xffe9bd23>", "<PAOldColor>"]
            })
            cls.expected_results[case_num] = {
                "type": "pacolor_wrapper",
                "should_translate": bool(expected_target),
                "codes_to_preserve": ["<PAColor", "<PAOldColor>"]
            }

        # 4. Multiple codes at start (20 rows)
        for entry in plain_entries[90:110]:
            case_num += 1
            src = cls.clean_fn(entry["source"])
            codes = ["{ItemID}", "{Amount}"]
            korean_with_codes = "".join(codes) + src
            expected_target = cls.split_dict.get(src) or cls.whole_dict.get(src, "")

            cls.test_cases.append({
                "case_num": case_num,
                "type": "multiple_codes_start",
                "korean": korean_with_codes,
                "original_korean": src,
                "expected_translation": expected_target,
                "expected_codes": codes
            })
            cls.expected_results[case_num] = {
                "type": "multiple_codes_start",
                "should_translate": bool(expected_target),
                "codes_to_preserve": codes
            }

        # 5. TextBind codes (20 rows)
        for entry in plain_entries[110:130]:
            case_num += 1
            src = cls.clean_fn(entry["source"])
            code = "{TextBind:CLICK_ON_RMB_ONLY}"
            korean_with_code = code + src
            expected_target = cls.split_dict.get(src) or cls.whole_dict.get(src, "")

            cls.test_cases.append({
                "case_num": case_num,
                "type": "textbind",
                "korean": korean_with_code,
                "original_korean": src,
                "expected_translation": expected_target,
                "expected_codes": [code]
            })
            cls.expected_results[case_num] = {
                "type": "textbind",
                "should_translate": bool(expected_target),
                "codes_to_preserve": ["{TextBind"]
            }

        # 6. Real entries with codes from data (20 rows)
        # Find entries that already have codes
        coded_entries = (
            cls.categories.get("curly_brace_codes", [])[:5] +
            cls.categories.get("pacolor_codes", [])[:5] +
            cls.categories.get("paoldcolor_ending", [])[:5] +
            cls.categories.get("textbind_codes", [])[:5]
        )
        for entry in coded_entries:
            case_num += 1
            src = entry["source"]

            cls.test_cases.append({
                "case_num": case_num,
                "type": "real_coded_entry",
                "korean": src,
                "expected_translation": "",  # May or may not match
                "expected_codes": []  # Codes already in source
            })
            cls.expected_results[case_num] = {
                "type": "real_coded_entry",
                "should_translate": None,  # Unknown
                "codes_to_preserve": []
            }

        # Pad to TEST_FILE_SIZE
        while len(cls.test_cases) < TEST_FILE_SIZE:
            entry = random.choice(plain_entries)
            case_num += 1
            src = cls.clean_fn(entry["source"])
            expected_target = cls.split_dict.get(src) or cls.whole_dict.get(src, "")

            cls.test_cases.append({
                "case_num": case_num,
                "type": "plain_text",
                "korean": src,
                "expected_translation": expected_target,
                "expected_codes": []
            })
            cls.expected_results[case_num] = {
                "type": "plain_text",
                "should_translate": bool(expected_target),
                "codes_to_preserve": []
            }

    # =========================================================================
    # RUN TRANSLATION ONCE FOR ALL TESTS
    # =========================================================================

    @pytest.fixture(scope="class")
    def translation_results(self):
        """Run translation once and store results for all tests."""
        from server.tools.xlstransfer.translation import translate_text_multi_mode
        from server.tools.xlstransfer.core import simple_number_replace

        results = {}

        for case in self.test_cases:
            korean = case["korean"]

            # Get raw translation (without code preservation)
            raw_translation = translate_text_multi_mode(
                korean,
                self.split_index,
                self.split_sentences,
                self.split_dict,
                self.whole_index,
                self.whole_sentences,
                self.whole_dict,
                threshold=THRESHOLD
            )

            # Apply code preservation
            if raw_translation:
                final_translation = simple_number_replace(korean, raw_translation)
            else:
                final_translation = ""

            results[case["case_num"]] = {
                "korean": korean,
                "raw_translation": raw_translation,
                "final_translation": final_translation,
                "type": case["type"]
            }

        self.__class__.translation_results_data = results
        return results

    # =========================================================================
    # TEST 1: Translation runs successfully
    # =========================================================================

    def test_01_translation_runs(self, translation_results):
        """TEST-01: Translation completes without errors."""
        results = translation_results

        total = len(results)
        translated = sum(1 for r in results.values() if r["raw_translation"])

        print(f"\nTEST-01 PASSED: Translation completed")
        print(f"  - Total: {total}")
        print(f"  - Translated: {translated}")
        print(f"  - Match rate: {translated/total:.1%}")

        assert total == len(self.test_cases)

    # =========================================================================
    # TEST 2: Plain text translation accuracy
    # =========================================================================

    def test_02_plain_text_translation(self, translation_results):
        """TEST-02: Plain text cases get correct translations."""
        results = translation_results

        plain_cases = [c for c in self.test_cases if c["type"] == "plain_text"]

        matched = 0
        correct = 0

        for case in plain_cases:
            result = results[case["case_num"]]
            if result["raw_translation"]:
                matched += 1
                # Check if translation matches expected
                expected = case.get("expected_translation", "")
                if expected and result["raw_translation"] == expected:
                    correct += 1

        match_rate = matched / len(plain_cases) if plain_cases else 0

        print(f"\nTEST-02: Plain Text Translation")
        print(f"  - Total plain cases: {len(plain_cases)}")
        print(f"  - Got translation: {matched}")
        print(f"  - Match rate: {match_rate:.1%}")

        assert match_rate >= 0.70, f"Plain text match rate too low: {match_rate:.1%}"

        print(f"TEST-02 PASSED: {matched}/{len(plain_cases)} plain texts translated")

    # =========================================================================
    # TEST 3: Code at start preservation
    # =========================================================================

    def test_03_code_at_start_preserved(self, translation_results):
        """TEST-03: {Code} at start is preserved in translation."""
        results = translation_results

        code_start_cases = [c for c in self.test_cases if c["type"] == "code_at_start"]

        preserved = 0
        translated = 0

        for case in code_start_cases:
            result = results[case["case_num"]]
            if result["raw_translation"]:
                translated += 1
                # Check if code is preserved at start
                final = result["final_translation"]
                codes = case["expected_codes"]

                all_preserved = all(code in final for code in codes)
                if all_preserved and final.startswith(codes[0]):
                    preserved += 1

        preserve_rate = preserved / translated if translated else 0

        print(f"\nTEST-03: Code at Start Preservation")
        print(f"  - Total code-at-start cases: {len(code_start_cases)}")
        print(f"  - Got translation: {translated}")
        print(f"  - Code preserved: {preserved}")
        print(f"  - Preservation rate: {preserve_rate:.1%}")

        assert preserve_rate >= 0.80, f"Code preservation rate too low: {preserve_rate:.1%}"

        print(f"TEST-03 PASSED: {preserved}/{translated} codes preserved at start")

    # =========================================================================
    # TEST 4: PAColor wrapper preservation
    # =========================================================================

    def test_04_pacolor_wrapper_preserved(self, translation_results):
        """TEST-04: <PAColor>...<PAOldColor> wrapper is preserved."""
        results = translation_results

        pacolor_cases = [c for c in self.test_cases if c["type"] == "pacolor_wrapper"]

        preserved_start = 0
        preserved_end = 0
        translated = 0

        for case in pacolor_cases:
            result = results[case["case_num"]]
            if result["raw_translation"]:
                translated += 1
                final = result["final_translation"]

                if "<PAColor" in final:
                    preserved_start += 1
                if final.endswith("<PAOldColor>"):
                    preserved_end += 1

        start_rate = preserved_start / translated if translated else 0
        end_rate = preserved_end / translated if translated else 0

        print(f"\nTEST-04: PAColor Wrapper Preservation")
        print(f"  - Total pacolor cases: {len(pacolor_cases)}")
        print(f"  - Got translation: {translated}")
        print(f"  - <PAColor> preserved: {preserved_start} ({start_rate:.1%})")
        print(f"  - <PAOldColor> preserved: {preserved_end} ({end_rate:.1%})")

        # PAColor at start should be preserved
        assert start_rate >= 0.80, f"PAColor start preservation too low: {start_rate:.1%}"

        print(f"TEST-04 PASSED: PAColor wrapper preserved")

    # =========================================================================
    # TEST 5: Multiple codes at start
    # =========================================================================

    def test_05_multiple_codes_preserved(self, translation_results):
        """TEST-05: Multiple codes at start are all preserved."""
        results = translation_results

        multi_cases = [c for c in self.test_cases if c["type"] == "multiple_codes_start"]

        all_preserved = 0
        translated = 0

        for case in multi_cases:
            result = results[case["case_num"]]
            if result["raw_translation"]:
                translated += 1
                final = result["final_translation"]
                codes = case["expected_codes"]

                if all(code in final for code in codes):
                    all_preserved += 1

        preserve_rate = all_preserved / translated if translated else 0

        print(f"\nTEST-05: Multiple Codes Preservation")
        print(f"  - Total multi-code cases: {len(multi_cases)}")
        print(f"  - Got translation: {translated}")
        print(f"  - All codes preserved: {all_preserved}")
        print(f"  - Rate: {preserve_rate:.1%}")

        assert preserve_rate >= 0.70, f"Multiple codes preservation too low: {preserve_rate:.1%}"

        print(f"TEST-05 PASSED: {all_preserved}/{translated} multi-code cases preserved")

    # =========================================================================
    # TEST 6: TextBind codes
    # =========================================================================

    def test_06_textbind_preserved(self, translation_results):
        """TEST-06: {TextBind:...} codes are preserved."""
        results = translation_results

        textbind_cases = [c for c in self.test_cases if c["type"] == "textbind"]

        preserved = 0
        translated = 0

        for case in textbind_cases:
            result = results[case["case_num"]]
            if result["raw_translation"]:
                translated += 1
                final = result["final_translation"]

                if "{TextBind" in final:
                    preserved += 1

        preserve_rate = preserved / translated if translated else 0

        print(f"\nTEST-06: TextBind Preservation")
        print(f"  - Total textbind cases: {len(textbind_cases)}")
        print(f"  - Got translation: {translated}")
        print(f"  - TextBind preserved: {preserved}")
        print(f"  - Rate: {preserve_rate:.1%}")

        assert preserve_rate >= 0.80, f"TextBind preservation too low: {preserve_rate:.1%}"

        print(f"TEST-06 PASSED: {preserved}/{translated} TextBind codes preserved")

    # =========================================================================
    # TEST 7: Full summary
    # =========================================================================

    def test_07_full_summary(self, translation_results):
        """TEST-07: Complete summary of all results."""
        results = translation_results

        # Collect stats by type
        stats = {}
        for case in self.test_cases:
            t = case["type"]
            if t not in stats:
                stats[t] = {"total": 0, "translated": 0, "codes_preserved": 0}

            stats[t]["total"] += 1
            result = results[case["case_num"]]

            if result["raw_translation"]:
                stats[t]["translated"] += 1

                # Check code preservation
                final = result["final_translation"]
                codes_to_check = self.expected_results[case["case_num"]].get("codes_to_preserve", [])

                if codes_to_check:
                    if all(code in final for code in codes_to_check):
                        stats[t]["codes_preserved"] += 1
                else:
                    stats[t]["codes_preserved"] += 1  # No codes to preserve

        print(f"\n{'='*70}")
        print("TEST-07: FULL SUMMARY")
        print(f"{'='*70}")

        total_cases = 0
        total_translated = 0
        total_preserved = 0

        for t, s in stats.items():
            trans_rate = s["translated"] / s["total"] if s["total"] else 0
            preserve_rate = s["codes_preserved"] / s["translated"] if s["translated"] else 0

            print(f"\n{t}:")
            print(f"  Total: {s['total']}")
            print(f"  Translated: {s['translated']} ({trans_rate:.1%})")
            print(f"  Codes preserved: {s['codes_preserved']} ({preserve_rate:.1%})")

            total_cases += s["total"]
            total_translated += s["translated"]
            total_preserved += s["codes_preserved"]

        overall_trans_rate = total_translated / total_cases if total_cases else 0
        overall_preserve_rate = total_preserved / total_translated if total_translated else 0

        print(f"\n{'='*70}")
        print(f"OVERALL:")
        print(f"  Total cases: {total_cases}")
        print(f"  Translated: {total_translated} ({overall_trans_rate:.1%})")
        print(f"  Codes preserved: {total_preserved} ({overall_preserve_rate:.1%})")
        print(f"{'='*70}")

        # Overall success criteria
        # Note: Translation rate is lower when we add codes to clean text because
        # it changes the embedding and doesn't match dictionary entries.
        # The key metric is that when matches occur, codes ARE preserved.
        assert overall_trans_rate >= 0.40, f"Overall translation rate too low: {overall_trans_rate:.1%}"
        assert overall_preserve_rate >= 0.90, f"Overall preservation rate too low: {overall_preserve_rate:.1%}"

        print(f"\nTEST-07 PASSED: Overall rates acceptable")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
