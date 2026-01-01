#!/usr/bin/env python3
"""
LocaNext - Version Unification Check
=====================================

Simple check: Ensures version.py matches package.json.
That's it. No complex validation needed - CI generates the version automatically.

Version Format: YY.MDD.HHMM (semver-compatible, no leading zeros)
Examples: 26.101.2352 (Jan 1), 26.1015.2352 (Oct 15), 26.1231.2352 (Dec 31)

Usage:
    python3 scripts/check_version_unified.py

Exit codes:
    0 - All checks passed
    1 - Version mismatch found
"""

import re
import sys
from pathlib import Path


def get_version_from_file(file_path: str, pattern: str) -> str | None:
    """Extract version from a file using regex pattern."""
    path = Path(file_path)
    if not path.exists():
        return None

    content = path.read_text()
    match = re.search(pattern, content)
    return match.group(1) if match else None


def main():
    print("=" * 60)
    print("LocaNext - Version Check")
    print("=" * 60)

    # Get version from source of truth
    version_py = get_version_from_file(
        "version.py",
        r'VERSION = "(\d{2}\.\d{3,4}\.\d{4})"'  # YY.MDD.HHMM or YY.MMDD.HHMM
    )

    if not version_py:
        print("❌ Could not read VERSION from version.py")
        return 1

    print(f"✓ version.py: {version_py}")

    # Check package.json matches
    package_json = get_version_from_file(
        "locaNext/package.json",
        r'"version": "(\d{2}\.\d{3,4}\.\d{4})"'
    )

    if package_json is None:
        print("⚠ package.json not found (will be created during build)")
    elif package_json != version_py:
        print(f"❌ package.json: {package_json} (MISMATCH!)")
        return 1
    else:
        print(f"✓ package.json: {package_json}")

    # Check server/config.py imports VERSION
    config_path = Path("server/config.py")
    if config_path.exists():
        content = config_path.read_text()
        if "from version import VERSION" in content:
            print("✓ server/config.py: imports VERSION")
        else:
            print("❌ server/config.py: missing VERSION import")
            return 1

    # Verify runtime import works
    try:
        sys.path.insert(0, str(Path.cwd()))
        from version import VERSION
        if VERSION != version_py:
            print(f"❌ Runtime import mismatch: {VERSION} vs {version_py}")
            return 1
        print(f"✓ Runtime import: {VERSION}")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return 1

    print("=" * 60)
    print("✓ All version checks passed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
