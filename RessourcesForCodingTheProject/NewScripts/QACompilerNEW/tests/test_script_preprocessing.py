#!/usr/bin/env python3
"""
Test Script-Type Preprocessing
==============================

Tests for preprocess_script_category() and create_filtered_script_template()
to ensure they handle edge cases and produce correct output.

Run with: python3 tests/test_script_preprocessing.py
"""

import sys
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font


class TestResult:
    """Simple test result tracker."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def pass_test(self, name: str):
        self.passed += 1
        print(f"  [PASS] {name}")

    def fail_test(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


def test_preprocess_script_category():
    """Test preprocess_script_category with mock fixture."""
    print("\n--- Testing preprocess_script_category ---")
    result = TestResult()

    # Import the function
    from core.compiler import preprocess_script_category

    fixture_path = Path(__file__).parent / "fixtures" / "mock_script_qa.xlsx"

    if not fixture_path.exists():
        print(f"  [ERROR] Fixture not found: {fixture_path}")
        print(f"  Run create_mock_fixture.py first!")
        return False

    # Create mock qa_folders structure
    qa_folders = [{
        "xlsx_path": fixture_path,
        "username": "test_user",
        "category": "Sequencer",
        "folder_path": fixture_path.parent,
        "images": [],
    }]

    try:
        # Run preprocessing
        universe = preprocess_script_category(qa_folders, is_english=True)

        # Test 1: Returns dict with expected keys
        if isinstance(universe, dict) and "rows" in universe and "row_count" in universe:
            result.pass_test("Returns dict with expected keys")
        else:
            result.fail_test("Returns dict with expected keys", f"Got: {type(universe)}, keys: {universe.keys() if isinstance(universe, dict) else 'N/A'}")

        # Test 2: Found expected number of rows with STATUS
        # Expected: 6 from Sequencer (ISSUE, NON-ISSUE, ISSUE, BLOCKED, ISSUE, NON-ISSUE)
        #         + 3 from Dialog (ISSUE, NON-ISSUE, KOREAN)
        expected_count = 9
        actual_count = universe.get("row_count", 0)
        if actual_count == expected_count:
            result.pass_test(f"Found {expected_count} rows with STATUS")
        else:
            result.fail_test(f"Found {expected_count} rows with STATUS", f"Got {actual_count}")

        # Test 3: Rows dict is properly keyed
        rows = universe.get("rows", {})
        sample_key = ("SEQ_001", "Hello there!")
        if sample_key in rows:
            result.pass_test("Rows keyed by (eventname, text)")
        else:
            result.fail_test("Rows keyed by (eventname, text)", f"Key {sample_key} not found")

        # Test 4: Source tracking works
        if sample_key in rows:
            sources = rows[sample_key].get("sources", [])
            if sources and len(sources) > 0:
                result.pass_test("Source tracking works")
            else:
                result.fail_test("Source tracking works", f"No sources found for {sample_key}")
        else:
            result.fail_test("Source tracking works", "Sample key not found")

        # Test 5: Empty STATUS rows are skipped
        empty_key = ("SEQ_003", "Skip me")
        if empty_key not in rows:
            result.pass_test("Empty STATUS rows are skipped")
        else:
            result.fail_test("Empty STATUS rows are skipped", f"Key {empty_key} was not skipped")

        # Test 6: Sparse rows are found (row 50 and row 100)
        sparse_key_50 = ("SEQ_050", "Sparse issue at row 50")
        sparse_key_100 = ("SEQ_100", "Sparse non-issue at row 100")
        if sparse_key_50 in rows and sparse_key_100 in rows:
            result.pass_test("Sparse rows at row 50 and 100 found")
        else:
            missing = []
            if sparse_key_50 not in rows:
                missing.append("row 50")
            if sparse_key_100 not in rows:
                missing.append("row 100")
            result.fail_test("Sparse rows at row 50 and 100 found", f"Missing: {missing}")

        # Test 7: Errors list is included
        if "errors" in universe:
            result.pass_test("Errors list included in result")
        else:
            result.fail_test("Errors list included in result", "No errors key")

    except Exception as e:
        print(f"  [ERROR] Exception during test: {e}")
        traceback.print_exc()
        result.fail_test("No exceptions", str(e))

    return result.summary()


def test_create_filtered_script_template():
    """Test create_filtered_script_template with mock fixture."""
    print("\n--- Testing create_filtered_script_template ---")
    result = TestResult()

    # Import the functions
    from core.compiler import preprocess_script_category, create_filtered_script_template

    fixture_path = Path(__file__).parent / "fixtures" / "mock_script_qa.xlsx"

    if not fixture_path.exists():
        print(f"  [ERROR] Fixture not found: {fixture_path}")
        return False

    # Create mock qa_folders structure
    qa_folders = [{
        "xlsx_path": fixture_path,
        "username": "test_user",
        "category": "Sequencer",
        "folder_path": fixture_path.parent,
        "images": [],
    }]

    try:
        # First, run preprocessing
        universe = preprocess_script_category(qa_folders, is_english=True)

        # Test 1: create_filtered_script_template doesn't crash
        output_path = None
        try:
            output_path = create_filtered_script_template(fixture_path, universe)
            result.pass_test("create_filtered_script_template completes without error")
        except Exception as e:
            result.fail_test("create_filtered_script_template completes without error", str(e))
            traceback.print_exc()
            return result.summary()

        # Test 2: Output file exists
        if output_path and output_path.exists():
            result.pass_test("Output file created")
        else:
            result.fail_test("Output file created", f"Path: {output_path}, exists: {output_path.exists() if output_path else 'N/A'}")
            return result.summary()

        # Test 3: Output file is valid Excel
        try:
            wb = load_workbook(output_path)
            result.pass_test("Output file is valid Excel")
        except Exception as e:
            result.fail_test("Output file is valid Excel", str(e))
            return result.summary()

        # Test 4: Contains expected sheets
        if "Sequencer" in wb.sheetnames:
            result.pass_test("Contains Sequencer sheet")
        else:
            result.fail_test("Contains Sequencer sheet", f"Sheets: {wb.sheetnames}")

        if "Dialog" in wb.sheetnames:
            result.pass_test("Contains Dialog sheet")
        else:
            result.fail_test("Contains Dialog sheet", f"Sheets: {wb.sheetnames}")

        # Test 5: Sequencer sheet has correct row count (header + data rows)
        ws_seq = wb["Sequencer"]
        expected_seq_rows = 6 + 1  # 6 with STATUS + 1 header
        actual_seq_rows = ws_seq.max_row
        if actual_seq_rows == expected_seq_rows:
            result.pass_test(f"Sequencer has {expected_seq_rows} rows (6 data + header)")
        else:
            result.fail_test(f"Sequencer has {expected_seq_rows} rows", f"Got {actual_seq_rows}")

        # Test 6: Dialog sheet has correct row count
        ws_dialog = wb["Dialog"]
        expected_dialog_rows = 3 + 1  # 3 with STATUS + 1 header
        actual_dialog_rows = ws_dialog.max_row
        if actual_dialog_rows == expected_dialog_rows:
            result.pass_test(f"Dialog has {expected_dialog_rows} rows (3 data + header)")
        else:
            result.fail_test(f"Dialog has {expected_dialog_rows} rows", f"Got {actual_dialog_rows}")

        # Test 7: Headers are preserved
        headers = [ws_seq.cell(1, col).value for col in range(1, 6)]
        expected_headers = ["EventName", "Text", "Translation", "STATUS", "MEMO"]
        if headers == expected_headers:
            result.pass_test("Headers preserved correctly")
        else:
            result.fail_test("Headers preserved correctly", f"Got: {headers}")

        # Cleanup
        wb.close()
        try:
            output_path.unlink()
            print(f"  Cleaned up: {output_path}")
        except:
            pass

    except Exception as e:
        print(f"  [ERROR] Exception during test: {e}")
        traceback.print_exc()
        result.fail_test("No exceptions", str(e))

    return result.summary()


def test_edge_cases():
    """Test edge cases like empty files, missing columns, etc."""
    print("\n--- Testing Edge Cases ---")
    result = TestResult()

    from core.compiler import preprocess_script_category, create_filtered_script_template
    import tempfile
    import os

    # Test 1: Empty qa_folders list
    try:
        universe = preprocess_script_category([], is_english=True)
        if universe["row_count"] == 0 and "errors" in universe:
            result.pass_test("Empty qa_folders handled gracefully")
        else:
            result.fail_test("Empty qa_folders handled gracefully", f"Got: {universe}")
    except Exception as e:
        result.fail_test("Empty qa_folders handled gracefully", str(e))

    # Test 2: Missing xlsx_path
    try:
        qa_folders = [{"username": "test", "category": "Test"}]  # Missing xlsx_path
        universe = preprocess_script_category(qa_folders, is_english=True)
        if universe["row_count"] == 0:
            result.pass_test("Missing xlsx_path handled gracefully")
        else:
            result.fail_test("Missing xlsx_path handled gracefully", f"Got row_count: {universe['row_count']}")
    except Exception as e:
        result.fail_test("Missing xlsx_path handled gracefully", str(e))

    # Test 3: Non-existent file
    try:
        qa_folders = [{
            "xlsx_path": Path("/nonexistent/file.xlsx"),
            "username": "test",
        }]
        universe = preprocess_script_category(qa_folders, is_english=True)
        if universe["row_count"] == 0:
            result.pass_test("Non-existent file handled gracefully")
        else:
            result.fail_test("Non-existent file handled gracefully", f"Got row_count: {universe['row_count']}")
    except Exception as e:
        result.fail_test("Non-existent file handled gracefully", str(e))

    # Test 4: Empty workbook (no sheets)
    try:
        # Create temp empty workbook
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        temp_path = Path(temp_path)

        wb = Workbook()
        # Remove default sheet
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]
        # Create empty sheet
        wb.create_sheet("EmptySheet")
        wb.save(temp_path)
        wb.close()

        qa_folders = [{"xlsx_path": temp_path, "username": "test"}]
        universe = preprocess_script_category(qa_folders, is_english=True)

        if universe["row_count"] == 0:
            result.pass_test("Empty workbook handled gracefully")
        else:
            result.fail_test("Empty workbook handled gracefully", f"Got row_count: {universe['row_count']}")

        temp_path.unlink()

    except Exception as e:
        result.fail_test("Empty workbook handled gracefully", str(e))
        traceback.print_exc()

    # Test 5: Workbook with missing required columns
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        temp_path = Path(temp_path)

        wb = Workbook()
        ws = wb.active
        ws.title = "Sequencer"
        # Only add some columns, not all required ones
        ws.cell(1, 1, "SomeColumn")
        ws.cell(1, 2, "AnotherColumn")
        ws.cell(2, 1, "Value1")
        ws.cell(2, 2, "Value2")
        wb.save(temp_path)
        wb.close()

        qa_folders = [{"xlsx_path": temp_path, "username": "test"}]
        universe = preprocess_script_category(qa_folders, is_english=True)

        if universe["row_count"] == 0:
            result.pass_test("Missing columns handled gracefully")
        else:
            result.fail_test("Missing columns handled gracefully", f"Got row_count: {universe['row_count']}")

        temp_path.unlink()

    except Exception as e:
        result.fail_test("Missing columns handled gracefully", str(e))
        traceback.print_exc()

    return result.summary()


def test_color_handling():
    """Test that style copying handles various color types without crashing."""
    print("\n--- Testing Color Handling ---")
    result = TestResult()

    from core.compiler import _safe_get_color_rgb

    # Test 1: None color object
    try:
        rgb = _safe_get_color_rgb(None)
        if rgb == "FFFFFF":
            result.pass_test("None color returns white")
        else:
            result.fail_test("None color returns white", f"Got: {rgb}")
    except Exception as e:
        result.fail_test("None color returns white", str(e))

    # Test 2: Create a mock color with integer rgb (indexed color)
    class MockColorInt:
        rgb = 0  # Indexed color

    try:
        rgb = _safe_get_color_rgb(MockColorInt())
        if rgb == "FFFFFF":
            result.pass_test("Indexed color (int) returns white")
        else:
            result.fail_test("Indexed color (int) returns white", f"Got: {rgb}")
    except Exception as e:
        result.fail_test("Indexed color (int) returns white", str(e))

    # Test 3: Valid RGB string
    class MockColorValid:
        rgb = "FF5500"

    try:
        rgb = _safe_get_color_rgb(MockColorValid())
        if rgb == "FF5500":
            result.pass_test("Valid RGB string preserved")
        else:
            result.fail_test("Valid RGB string preserved", f"Got: {rgb}")
    except Exception as e:
        result.fail_test("Valid RGB string preserved", str(e))

    # Test 4: RGB with alpha channel (8 chars)
    class MockColorAlpha:
        rgb = "FFFF5500"  # Alpha + RGB

    try:
        rgb = _safe_get_color_rgb(MockColorAlpha())
        if rgb == "FF5500":
            result.pass_test("Alpha channel stripped correctly")
        else:
            result.fail_test("Alpha channel stripped correctly", f"Got: {rgb}")
    except Exception as e:
        result.fail_test("Alpha channel stripped correctly", str(e))

    # Test 5: Color with no rgb attribute
    class MockColorNoRgb:
        pass

    try:
        rgb = _safe_get_color_rgb(MockColorNoRgb())
        if rgb == "FFFFFF":
            result.pass_test("Missing rgb attribute returns white")
        else:
            result.fail_test("Missing rgb attribute returns white", f"Got: {rgb}")
    except Exception as e:
        result.fail_test("Missing rgb attribute returns white", str(e))

    return result.summary()


def main():
    """Run all tests."""
    print("=" * 60)
    print("QACompiler Script Preprocessing Tests")
    print("=" * 60)

    all_passed = True

    # Run each test suite
    all_passed &= test_color_handling()
    all_passed &= test_preprocess_script_category()
    all_passed &= test_create_filtered_script_template()
    all_passed &= test_edge_cases()

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - see above for details")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
