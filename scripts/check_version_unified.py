#!/usr/bin/env python3
"""
LocaNext - Version Unification Check
=====================================

Ensures all files have matching version numbers from single source of truth: version.py

CURRENT CHECKS:
1. Timestamp Validation - Version (KST) must be within 1 hour of build time
2. Version consistency across code, docs, and build configurations

FUTURE EXTENSIBILITY:
Can be expanded to monitor:
- Build artifact sizes
- Model file integrity
- Security policy compliance
- Documentation coverage

Usage:
    python3 scripts/check_version_unified.py

Exit codes:
    0 - All checks passed ✅
    1 - One or more checks failed ❌
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Source of truth
VERSION_FILE = "version.py"


def check_version_timestamp(version, max_hours_diff=1):
    """
    Check if version timestamp is within acceptable range of current time.

    UNIFIED VERSION FORMAT: YY.MMDD.HHMM (e.g., "25.1213.1540")
    - Valid semver (X.Y.Z)
    - Human readable (Dec 13, 2025, 15:40 KST)
    Script converts version from KST to UTC for comparison on GitHub Actions.

    Args:
        version: Version string (e.g., "25.1213.1540") in KST
        max_hours_diff: Maximum allowed difference in hours (default: 1)

    Returns:
        tuple: (is_valid, message)
    """
    # Parse YY.MMDD.HHMM format
    parts = version.split('.')
    if len(parts) != 3:
        return False, f"Invalid version format: {version} (expected YY.MMDD.HHMM, e.g., 25.1213.1540)"

    try:
        yy, mmdd, hhmm = parts
        version_year = int("20" + yy)  # YY -> 20YY
        version_month = int(mmdd[:2])
        version_day = int(mmdd[2:])
        version_hour = int(hhmm[:2])
        version_minute = int(hhmm[2:])

        # Get current time in UTC
        now_utc = datetime.now(timezone.utc)

        # Build version datetime in KST (UTC+9), then convert to UTC
        kst = timezone(timedelta(hours=9))
        try:
            version_dt_kst = datetime(version_year, version_month, version_day,
                                       version_hour, version_minute, tzinfo=kst)
            version_dt_utc = version_dt_kst.astimezone(timezone.utc)
        except ValueError as e:
            return False, f"Invalid datetime in version: {version} ({e})"

        # Calculate difference in hours (both in UTC now)
        diff = abs((now_utc - version_dt_utc).total_seconds() / 3600)

        if diff <= max_hours_diff:
            return True, f"Version timestamp OK: {version} (KST) = {version_dt_utc.strftime('%Y-%m-%d %H:%M')} UTC, within {diff:.1f}h of now"
        else:
            return False, f"Version timestamp TOO FAR: {version} (KST) is {diff:.1f}h away from now. Max: {max_hours_diff}h"
    except ValueError as e:
        return False, f"Could not parse version timestamp: {version} ({e})"

# UNIFIED VERSION FORMAT: YY.MMDD.HHMM (e.g., 25.1213.1540)
# This format is BOTH valid semver AND human-readable datetime!
# Capture group pattern for version extraction
VER = r'(\d{2}\.\d{4}\.\d{4})'  # Matches and captures YY.MMDD.HHMM

# All files that must have matching version
VERSION_FILES = {
    "version.py": [
        r'VERSION = "' + VER + r'"',
    ],
    "server/config.py": [
        r'from version import VERSION',  # Verify import exists (no version string here)
    ],
    "README.md": [
        r'\*\*Version:\*\* ' + VER,
        r'ver\. ' + VER,
    ],
    "CLAUDE.md": [
        r'\*\*Current Version:\*\* ' + VER,
        r'v' + VER,
    ],
    "Roadmap.md": [
        r'## Current Status.*v' + VER,
        r'Version ' + VER,
    ],
    # Optional files (may not exist yet)
    "locaNext/package.json": [
        r'"version": "' + VER + r'"',  # Same unified format!
    ],
    "installer/locanext_electron.iss": [
        r'#define MyAppVersion "' + VER + r'"',
    ],
    "installer/locanext_light.iss": [
        r'#define MyAppVersion "' + VER + r'"',
    ],
}


def get_source_version():
    """Get the source of truth version from version.py"""
    version_path = Path(VERSION_FILE)
    if not version_path.exists():
        print(f"❌ Error: {VERSION_FILE} not found!")
        sys.exit(1)

    content = version_path.read_text()
    # Match unified format: YY.MMDD.HHMM (e.g., 25.1213.1540)
    match = re.search(r'VERSION = "(\d{2}\.\d{4}\.\d{4})"', content)
    if not match:
        print(f"❌ Error: Could not find VERSION in unified format (YY.MMDD.HHMM) in {VERSION_FILE}")
        sys.exit(1)

    return match.group(1)


def get_semantic_version():
    """Get semantic version from version.py - now same as VERSION (unified format)"""
    # With unified format, SEMANTIC_VERSION = VERSION
    # Both are now YY.MMDD.HHMM which is valid semver
    return get_source_version()


def check_file_versions(file_path, patterns, source_version, semantic_version=None):
    """Check all version patterns in a file"""
    mismatches = []

    path = Path(file_path)
    if not path.exists():
        # Optional files (Electron config, installer) may not exist yet
        if "locaNext/package.json" in file_path or "installer/" in file_path:
            return []  # Skip silently
        return [(0, f"⚠️  File not found: {file_path} (will be created later)")]

    content = path.read_text()
    lines = content.split('\n')

    # Special handling for package.json - check semantic version
    if "package.json" in file_path and semantic_version:
        for line_num, line in enumerate(lines, 1):
            match = re.search(r'"version": "(\d+\.\d+\.\d+)"', line)
            if match:
                found_version = match.group(1)
                if found_version != semantic_version:
                    mismatches.append((line_num, f"Expected semantic '{semantic_version}', found '{found_version}'"))
        return mismatches

    # Special handling for Roadmap.md - ignore Version History section
    in_history_section = False
    if "Roadmap.md" in file_path:
        for line_num, line in enumerate(lines, 1):
            if "## Version History" in line or "## Build History" in line:
                in_history_section = True

            # Only check lines before history sections
            if not in_history_section:
                for pattern in patterns:
                    if "import" in pattern:
                        # Just check if import exists
                        if re.search(pattern, content):
                            continue  # Import found, good
                    else:
                        match = re.search(pattern, line)
                        if match:
                            found_version = match.group(1)
                            if found_version != source_version:
                                mismatches.append((line_num, f"Expected '{source_version}', found '{found_version}'"))
    else:
        # Normal checking for all other files
        for pattern in patterns:
            # Check for import statements (presence check only)
            if "import" in pattern:
                if not re.search(pattern, content):
                    mismatches.append((0, f"Missing import statement"))
                continue

            # Check version numbers
            for line_num, line in enumerate(lines, 1):
                match = re.search(pattern, line)
                if match:
                    found_version = match.group(1)
                    if found_version != source_version:
                        mismatches.append((line_num, f"Expected '{source_version}', found '{found_version}'"))

    return mismatches


def main():
    print("=" * 70)
    print("LocaNext - Version Unification Check")
    print("=" * 70)
    print()

    # Get source of truth
    source_version = get_source_version()
    semantic_version = get_semantic_version()

    print(f"✓ Source of truth: {VERSION_FILE}")
    print(f"✓ DateTime version: {source_version}")
    if semantic_version:
        print(f"✓ Semantic version: {semantic_version}")
    print()

    # TIMESTAMP VALIDATION - Version must be within 1 hour of current time
    print("Checking version timestamp...")
    timestamp_valid, timestamp_msg = check_version_timestamp(source_version, max_hours_diff=1)
    if timestamp_valid:
        print(f"✓ {timestamp_msg}")
    else:
        print(f"❌ {timestamp_msg}")
        print()
        print("=" * 70)
        print("❌ BUILD BLOCKED: Version timestamp too far from current time!")
        print("   Update version to current timestamp before building.")
        # Generate suggested version in KST using UNIFIED FORMAT: YY.MMDD.HHMM
        from datetime import datetime, timezone, timedelta
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        suggested = f"{now_kst.strftime('%y')}.{now_kst.strftime('%m%d')}.{now_kst.strftime('%H%M')}"
        print(f"   Suggested version: {suggested}")
        print("   Format: YY.MMDD.HHMM (valid semver + human-readable)")
        print("=" * 70)
        return 1
    print()

    # Test runtime import
    print("Testing runtime imports...")
    try:
        sys.path.insert(0, str(Path.cwd()))
        from version import VERSION, SEMANTIC_VERSION, VERSION_FOOTER

        if VERSION != source_version:
            print(f"❌ Runtime import VERSION mismatch!")
            print(f"   Expected: {source_version}")
            print(f"   Got: {VERSION}")
            return 1

        print(f"✓ Runtime import: VERSION = {VERSION}")
        print(f"✓ Runtime import: SEMANTIC_VERSION = {SEMANTIC_VERSION}")
        print(f"✓ Runtime import: VERSION_FOOTER = {VERSION_FOOTER[:50]}...")
        print()
    except ImportError as e:
        print(f"❌ Failed to import VERSION from version.py: {e}")
        return 1

    # Check all files
    all_good = True
    files_checked = 0
    files_skipped = 0

    for file_path, patterns in VERSION_FILES.items():
        mismatches = check_file_versions(file_path, patterns, source_version, semantic_version)

        if not Path(file_path).exists():
            if "locaNext/package.json" in file_path or "installer/" in file_path:
                files_skipped += 1
                continue  # Skip optional files silently

        files_checked += 1

        if mismatches:
            all_good = False
            print(f"❌ {file_path}")
            for line_num, error in mismatches:
                if line_num > 0:
                    print(f"   Line {line_num}: {error}")
                else:
                    print(f"   {error}")
            print()
        else:
            print(f"✓ {file_path}")

    print()
    print("=" * 70)

    if all_good:
        print(f"🎉 SUCCESS! All {files_checked} files have unified version: {source_version}")
        print(f"🎉 Runtime imports verified!")
        if files_skipped > 0:
            print(f"ℹ️  Skipped {files_skipped} optional files (not created yet)")
        print()
        print("COVERAGE SUMMARY:")
        print("  ✓ Timestamp Validation: Version (KST) within 1 hour of build time")
        print("  ✓ Source of Truth: version.py (VERSION, SEMANTIC_VERSION)")
        print("  ✓ Backend: server/config.py (imports VERSION)")
        print("  ✓ Documentation: README.md, CLAUDE.md, Roadmap.md")
        print("  ✓ Runtime Imports: Verified successful")
        if files_skipped == 0:
            print("  ✓ Build System: Electron package.json, installer scripts")
        print()
        print("All version references unified and consistent!")
        print("=" * 70)
        return 0
    else:
        print(f"⚠️  MISMATCH DETECTED! Fix version inconsistencies above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
