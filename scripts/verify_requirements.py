#!/usr/bin/env python3
"""
Verify all packages from requirements.txt are properly installed.

This script prevents build failures caused by missing packages.
Run after pip install -r requirements.txt to catch issues early.

Usage:
    python scripts/verify_requirements.py
    python scripts/verify_requirements.py --critical-only  # Only check CRITICAL packages

Exit codes:
    0 = All packages verified
    1 = Critical package missing (FATAL)
    2 = Optional package missing (WARNING only)
"""

import sys
import importlib
import re
from pathlib import Path

# Package name to import name mapping
# (pip package name != Python import name for some packages)
PACKAGE_TO_IMPORT = {
    # ML/NLP
    "sentence-transformers": "sentence_transformers",
    "faiss-cpu": "faiss",
    "faiss-gpu": "faiss",
    "model2vec": "model2vec",
    # Web
    "python-multipart": "multipart",
    "python-socketio": "socketio",
    "uvicorn[standard]": "uvicorn",
    # Database
    "psycopg2-binary": "psycopg2",
    # Auth
    "python-jose[cryptography]": "jose",
    "passlib[bcrypt]": "passlib",
    "python-dotenv": "dotenv",
    # Utils
    "python-dateutil": "dateutil",
    "pyyaml": "yaml",
    # Dev
    "pytest-asyncio": "pytest_asyncio",
    "pytest-cov": "pytest_cov",
    "pytest-xdist": "xdist",
}

# CRITICAL packages - app CRASHES without these
# NOTE: Include both with and without extras for matching
CRITICAL_PACKAGES = {
    "fastapi",
    "uvicorn",
    "uvicorn[standard]",
    "sqlalchemy",
    "asyncpg",         # Added after Build 421 crash!
    "psycopg2-binary",
    "pydantic",
    "python-jose",
    "python-jose[cryptography]",
    "passlib",
    "passlib[bcrypt]",
    "loguru",
}

# OPTIONAL packages - app works without these (graceful degradation)
OPTIONAL_PACKAGES = {
    "torch",
    "transformers",
    "sentence-transformers",
    "faiss-cpu",
    "model2vec",
    "plotly",
    "matplotlib",
    "seaborn",
    "pip-audit",
    "black",
    "flake8",
    "mypy",
    "isort",
    "pyinstaller",
}


def parse_requirements(req_file: Path) -> list[tuple[str, str]]:
    """Parse requirements.txt and return list of (package_name, version_spec)."""
    packages = []

    with open(req_file) as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Extract package name (before ==, >=, etc.)
            match = re.match(r"^([a-zA-Z0-9_\-\[\]]+)", line)
            if match:
                pkg_name = match.group(1)
                packages.append((pkg_name, line))

    return packages


def get_import_name(pkg_name: str) -> str:
    """Get the Python import name for a package."""
    # Check mapping first
    if pkg_name in PACKAGE_TO_IMPORT:
        return PACKAGE_TO_IMPORT[pkg_name]

    # Default: replace - with _ and remove extras like [standard]
    clean_name = re.sub(r"\[.*\]", "", pkg_name)
    return clean_name.replace("-", "_")


def verify_package(pkg_name: str) -> tuple[bool, str]:
    """Try to import a package. Returns (success, message)."""
    import_name = get_import_name(pkg_name)

    try:
        importlib.import_module(import_name)
        return True, f"OK: {pkg_name} -> {import_name}"
    except ImportError as e:
        return False, f"MISSING: {pkg_name} (import {import_name}): {e}"
    except Exception as e:
        return False, f"ERROR: {pkg_name}: {e}"


def main():
    critical_only = "--critical-only" in sys.argv

    # Find requirements.txt
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    req_file = project_root / "requirements.txt"

    if not req_file.exists():
        print(f"ERROR: requirements.txt not found at {req_file}")
        sys.exit(1)

    print("=" * 60)
    print("PACKAGE VERIFICATION - requirements.txt")
    print("=" * 60)

    packages = parse_requirements(req_file)
    print(f"Found {len(packages)} packages in requirements.txt\n")

    critical_failures = []
    optional_failures = []
    successes = []

    for pkg_name, full_spec in packages:
        # Skip if critical-only mode and package is optional
        if critical_only and pkg_name not in CRITICAL_PACKAGES:
            continue

        success, message = verify_package(pkg_name)

        if success:
            successes.append(message)
        else:
            if pkg_name in CRITICAL_PACKAGES:
                critical_failures.append(message)
            elif pkg_name in OPTIONAL_PACKAGES:
                optional_failures.append(message)
            else:
                # Unknown = treat as critical
                critical_failures.append(message)

    # Report results
    print(f"PASSED: {len(successes)} packages")
    for msg in successes:
        print(f"  {msg}")

    if optional_failures:
        print(f"\nWARNING: {len(optional_failures)} optional packages missing (non-fatal)")
        for msg in optional_failures:
            print(f"  {msg}")

    if critical_failures:
        print(f"\nFATAL: {len(critical_failures)} CRITICAL packages missing!")
        for msg in critical_failures:
            print(f"  {msg}")
        print("\n" + "=" * 60)
        print("BUILD WILL FAIL - Install missing critical packages!")
        print("=" * 60)
        sys.exit(1)

    print("\n" + "=" * 60)
    if optional_failures:
        print("RESULT: PASS (with warnings)")
    else:
        print("RESULT: ALL PACKAGES VERIFIED")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
