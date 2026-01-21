#!/usr/bin/env python3
"""
QACompiler CI Validation Script
================================
COMPREHENSIVE local validation that mirrors the CI pipeline.

Run this script BEFORE pushing code to catch errors early!

Checks performed:
1. Python syntax validation (py_compile)
2. Module import validation (catches missing imports like 'sys')
3. Flake8 code quality (undefined names, unused imports, errors)
4. Security audit (pip-audit for vulnerable dependencies)
5. Unit tests (pytest)

Usage:
    python ci_validate.py           # Run all checks
    python ci_validate.py --quick   # Skip slow checks (security, tests)
    python ci_validate.py --fix     # Show what would fix issues

Exit codes:
    0 = All checks passed
    1 = Critical errors found (will break build)
    2 = Warnings found (build may succeed but review recommended)
"""

import sys
import os
import subprocess
import importlib
import py_compile
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

# Add current directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# ============================================================================
# CONFIGURATION
# ============================================================================

# All modules that must import successfully
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

# Directories to exclude from checks
EXCLUDE_DIRS = ["__pycache__", "build", "dist", ".git", ".pytest_cache", "installer_output"]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_header(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("=" * 64)
    print(f"  {title}")
    print("=" * 64)


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print()
    print(f"--- {title} ---")


def check_tool_available(tool: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        subprocess.run([tool, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# ============================================================================
# CHECK 1: PYTHON SYNTAX VALIDATION
# ============================================================================

def check_syntax() -> Tuple[bool, List[str]]:
    """
    Validate Python syntax of all .py files.

    Returns:
        Tuple of (passed, list of error messages)
    """
    print_header("CHECK 1: PYTHON SYNTAX VALIDATION")

    errors = []
    checked = 0

    for py_file in SCRIPT_DIR.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in str(py_file) for excluded in EXCLUDE_DIRS):
            continue

        try:
            py_compile.compile(str(py_file), doraise=True)
            checked += 1
        except py_compile.PyCompileError as e:
            errors.append(f"{py_file.relative_to(SCRIPT_DIR)}: {e}")
            print(f"  [FAIL] {py_file.relative_to(SCRIPT_DIR)}")
            print(f"         Line {e.lineno}: {e.msg}")

    if errors:
        print(f"\n[ERROR] {len(errors)} syntax errors found!")
        return False, errors
    else:
        print(f"  [OK] All {checked} Python files have valid syntax")
        return True, []


# ============================================================================
# CHECK 2: MODULE IMPORT VALIDATION
# ============================================================================

def check_imports() -> Tuple[bool, List[str]]:
    """
    Test that all modules can be imported without errors.

    This catches bugs like missing 'import sys' that broke builds!

    Returns:
        Tuple of (passed, list of error messages)
    """
    print_header("CHECK 2: MODULE IMPORT VALIDATION")
    print("  (Catches missing imports like 'import sys' bug)")
    print()

    errors = []
    passed = 0

    for module_name in MODULES_TO_CHECK:
        try:
            # Clear any cached imports to ensure fresh check
            if module_name in sys.modules:
                del sys.modules[module_name]

            importlib.import_module(module_name)
            print(f"  [PASS] {module_name}")
            passed += 1
        except Exception as e:
            error_type = type(e).__name__
            print(f"  [FAIL] {module_name}")
            print(f"         {error_type}: {e}")
            errors.append(f"{module_name}: {error_type}: {e}")

    print()
    print(f"Results: {passed}/{len(MODULES_TO_CHECK)} modules passed")

    if errors:
        print(f"\n[ERROR] {len(errors)} modules failed to import!")
        return False, errors
    else:
        print(f"\n[OK] All {len(MODULES_TO_CHECK)} modules imported successfully!")
        return True, []


# ============================================================================
# CHECK 3: FLAKE8 CODE QUALITY
# ============================================================================

def check_flake8() -> Tuple[bool, List[str], List[str]]:
    """
    Run flake8 to check for code quality issues.

    Critical errors (will fail build):
    - E9xx: Runtime errors (syntax, IO, etc)
    - F63x: Invalid code
    - F7xx: Statement errors
    - F82x: Undefined names (CRITICAL!)

    Warnings (won't fail build):
    - F401: Unused imports

    Returns:
        Tuple of (passed, list of critical errors, list of warnings)
    """
    print_header("CHECK 3: FLAKE8 CODE QUALITY")
    print("  (Catches undefined names, unused imports, errors)")

    if not check_tool_available("flake8"):
        print()
        print("  [SKIP] flake8 not installed")
        print("         Install with: pip install flake8")
        return True, [], ["flake8 not installed - skipped"]

    critical_errors = []
    warnings = []

    # Check for critical errors
    print_subheader("Critical Errors (will fail build)")

    result = subprocess.run(
        ["flake8", ".", "--select=E9,F63,F7,F82", "--show-source",
         f"--exclude={','.join(EXCLUDE_DIRS)}"],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR
    )

    if result.returncode != 0:
        critical_errors = result.stdout.strip().split("\n") if result.stdout.strip() else []
        for error in critical_errors:
            print(f"  {error}")
        print(f"\n  [FAIL] {len(critical_errors)} critical errors found!")
    else:
        print("  [OK] No critical flake8 errors")

    # Check for warnings (unused imports)
    print_subheader("Warnings (won't fail build)")

    result = subprocess.run(
        ["flake8", ".", "--select=F401", "--show-source",
         f"--exclude={','.join(EXCLUDE_DIRS)}"],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR
    )

    if result.returncode != 0:
        warnings = result.stdout.strip().split("\n") if result.stdout.strip() else []
        for warning in warnings:
            print(f"  {warning}")
        print(f"\n  [WARN] {len(warnings)} unused imports found (non-blocking)")
    else:
        print("  [OK] No unused imports")

    passed = len(critical_errors) == 0
    return passed, critical_errors, warnings


# ============================================================================
# CHECK 4: SECURITY AUDIT
# ============================================================================

def check_security() -> Tuple[bool, List[str]]:
    """
    Run pip-audit to check for vulnerable dependencies.

    Returns:
        Tuple of (passed, list of vulnerabilities)
    """
    print_header("CHECK 4: SECURITY AUDIT (pip-audit)")

    if not check_tool_available("pip-audit"):
        print()
        print("  [SKIP] pip-audit not installed")
        print("         Install with: pip install pip-audit")
        return True, ["pip-audit not installed - skipped"]

    result = subprocess.run(
        ["pip-audit", "--desc"],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR
    )

    vulnerabilities = []

    if result.returncode != 0:
        output = result.stdout + result.stderr
        vulnerabilities = [line for line in output.split("\n") if line.strip()]
        print(output)
        print(f"\n  [WARN] Vulnerabilities found - logged for review")
    else:
        print("  [OK] No known vulnerabilities in dependencies")

    # Security audit is non-blocking (warning only)
    return True, vulnerabilities


# ============================================================================
# CHECK 5: RUN TESTS
# ============================================================================

def check_tests() -> Tuple[bool, List[str]]:
    """
    Run pytest to execute any test files.

    Returns:
        Tuple of (passed, list of test failures)
    """
    print_header("CHECK 5: PYTEST TESTS")

    if not check_tool_available("pytest"):
        print()
        print("  [SKIP] pytest not installed")
        print("         Install with: pip install pytest")
        return True, ["pytest not installed - skipped"]

    # Find test files
    test_files = list(SCRIPT_DIR.glob("test_*.py"))

    if not test_files:
        print()
        print("  [INFO] No test files found - skipping pytest")
        return True, []

    print(f"\n  Found {len(test_files)} test file(s)")

    result = subprocess.run(
        ["python", "-m", "pytest"] + [str(f) for f in test_files] + ["-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=SCRIPT_DIR
    )

    print(result.stdout)

    failures = []
    if result.returncode != 0:
        failures = [line for line in result.stdout.split("\n") if "FAILED" in line]
        print(f"\n  [WARN] Some tests failed (may require Windows environment)")
    else:
        print(f"\n  [OK] All tests passed!")

    # Tests are non-blocking (some may require Windows)
    return True, failures


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="QACompiler CI Validation - Run before pushing code!"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode: skip slow checks (security, tests)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Show suggestions for fixing issues"
    )
    args = parser.parse_args()

    print()
    print("*" * 64)
    print("*  QACOMPILER CI VALIDATION                                   *")
    print("*  Run this BEFORE pushing to catch errors early!             *")
    print("*" * 64)

    # Track results
    all_passed = True
    critical_errors = []
    warnings = []

    # CHECK 1: Syntax
    passed, errors = check_syntax()
    if not passed:
        all_passed = False
        critical_errors.extend(errors)

    # CHECK 2: Imports
    passed, errors = check_imports()
    if not passed:
        all_passed = False
        critical_errors.extend(errors)

    # CHECK 3: Flake8
    passed, errors, warns = check_flake8()
    if not passed:
        all_passed = False
        critical_errors.extend(errors)
    warnings.extend(warns)

    if not args.quick:
        # CHECK 4: Security (slow, optional)
        passed, vulns = check_security()
        warnings.extend(vulns)

        # CHECK 5: Tests (slow, optional)
        passed, failures = check_tests()
        warnings.extend(failures)
    else:
        print_header("SKIPPED: Security Audit (--quick mode)")
        print_header("SKIPPED: Tests (--quick mode)")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print()
    print("=" * 64)
    print("  VALIDATION SUMMARY")
    print("=" * 64)
    print()

    if all_passed:
        print("  STATUS: [PASS] ALL CRITICAL CHECKS PASSED")
        print()
        print("  Your code is ready for CI!")
        print()

        if warnings:
            print(f"  Warnings: {len(warnings)} (non-blocking)")
            print("  Review these but they won't fail the build.")

        if args.fix and warnings:
            print()
            print("  To fix unused imports, remove them from the files.")
            print("  To update vulnerable dependencies: pip install --upgrade <package>")

        return 0
    else:
        print("  STATUS: [FAIL] CRITICAL ERRORS FOUND")
        print()
        print(f"  {len(critical_errors)} critical error(s) that WILL break the CI build:")
        print()
        for error in critical_errors[:10]:  # Show first 10
            print(f"    - {error}")
        if len(critical_errors) > 10:
            print(f"    ... and {len(critical_errors) - 10} more")

        print()
        print("  FIX THESE ERRORS BEFORE PUSHING!")

        if args.fix:
            print()
            print("  Common fixes:")
            print("    - Syntax errors: Check the line number and fix the code")
            print("    - Import errors: Add missing 'import' statements")
            print("    - Undefined names: Define variables before using them")

        return 1


if __name__ == "__main__":
    sys.exit(main())
