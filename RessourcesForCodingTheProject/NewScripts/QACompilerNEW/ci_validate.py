#!/usr/bin/env python3
"""
CI Validation Script for QACompiler
====================================
Runs before PyInstaller build to catch common errors:
- Import errors (missing imports like 'sys')
- Syntax errors
- Module resolution issues

Usage in CI:
    python ci_validate.py

Exit codes:
    0 = All checks passed
    1 = Validation failed
"""

import sys
import importlib
import traceback
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

MODULES_TO_CHECK = [
    # Main entry
    "main",
    "config",

    # GUI
    "gui.app",

    # Generators (these had the missing 'sys' import bug)
    "generators",
    "generators.base",
    "generators.quest",
    "generators.item",
    "generators.skill",
    "generators.character",
    "generators.region",
    "generators.knowledge",
    "generators.help",
    "generators.gimmick",

    # Core
    "core.compiler",
    "core.discovery",
    "core.excel_ops",
    "core.matching",
    "core.populate_new",
    "core.processing",
    "core.transfer",
    "core.tracker_update",

    # Tracker
    "tracker.coverage",
    "tracker.daily",
    "tracker.total",
    "tracker.data",

    # Standalone tools
    "system_localizer",
    "drive_replacer",
]

def validate_imports():
    """Test that all modules can be imported without errors."""
    print("=" * 60)
    print("QACompiler CI Validation")
    print("=" * 60)
    print()
    print("Checking module imports...")
    print()

    errors = []
    passed = 0

    for module_name in MODULES_TO_CHECK:
        try:
            importlib.import_module(module_name)
            print(f"  [PASS] {module_name}")
            passed += 1
        except Exception as e:
            error_type = type(e).__name__
            print(f"  [FAIL] {module_name}")
            print(f"         {error_type}: {e}")
            errors.append((module_name, e))

    print()
    print("-" * 60)
    print(f"Results: {passed}/{len(MODULES_TO_CHECK)} modules passed")

    if errors:
        print()
        print("ERRORS FOUND:")
        for module_name, e in errors:
            print(f"\n  {module_name}:")
            print(f"    {type(e).__name__}: {e}")
        print()
        print("=" * 60)
        print("VALIDATION FAILED - Fix errors before building!")
        print("=" * 60)
        return False
    else:
        print()
        print("=" * 60)
        print("VALIDATION PASSED - All modules import successfully!")
        print("=" * 60)
        return True


def validate_syntax():
    """Check Python syntax of all .py files."""
    print()
    print("Checking Python syntax...")

    py_files = list(Path(__file__).parent.rglob("*.py"))
    errors = []

    for py_file in py_files:
        # Skip test files and __pycache__
        if "__pycache__" in str(py_file):
            continue
        if "test_" in py_file.name:
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                source = f.read()
            compile(source, py_file, 'exec')
        except SyntaxError as e:
            errors.append((py_file, e))
            print(f"  [FAIL] {py_file.name}: {e}")

    if not errors:
        print(f"  [PASS] All {len(py_files)} Python files have valid syntax")
        return True
    else:
        print(f"\n  {len(errors)} syntax errors found!")
        return False


def main():
    success = True

    if not validate_syntax():
        success = False

    if not validate_imports():
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
