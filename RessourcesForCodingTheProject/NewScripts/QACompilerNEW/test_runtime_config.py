#!/usr/bin/env python3
"""
Test Runtime Configuration System
=================================
Tests that settings.json properly overrides the default F: drive.

This simulates what happens when:
1. PyInstaller bundles the app with F: hardcoded
2. Installer creates settings.json with different drive letter
3. App reads settings.json at runtime and uses correct drive

Run this test to verify the fix works before building.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# Test results
PASSED = 0
FAILED = 0


def test_result(name: str, passed: bool, details: str = ""):
    global PASSED, FAILED
    if passed:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED += 1
        print(f"  [FAIL] {name}")
        if details:
            print(f"         {details}")


def test_no_settings_file():
    """Test: Without settings.json, uses default F: drive"""
    print("\n=== TEST 1: No settings.json (default F: drive) ===")

    # Create temp directory to simulate app folder
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Copy config.py to temp dir
        config_src = Path(__file__).parent / "config.py"
        config_dst = tmpdir / "config.py"
        shutil.copy(config_src, config_dst)

        # Simulate PyInstaller environment
        old_frozen = getattr(sys, 'frozen', None)
        old_executable = sys.executable

        # DON'T set frozen - we want to test via __file__ path
        # Just import with modified path
        sys.path.insert(0, str(tmpdir))

        try:
            # Force reimport
            if 'config' in sys.modules:
                del sys.modules['config']

            import config as test_config

            # Check paths use F: drive
            resource_str = str(test_config.RESOURCE_FOLDER)
            test_result(
                "RESOURCE_FOLDER uses F: drive",
                resource_str.startswith("F:"),
                f"Got: {resource_str[:20]}..."
            )

            language_str = str(test_config.LANGUAGE_FOLDER)
            test_result(
                "LANGUAGE_FOLDER uses F: drive",
                language_str.startswith("F:"),
                f"Got: {language_str[:20]}..."
            )

        finally:
            sys.path.remove(str(tmpdir))
            if 'config' in sys.modules:
                del sys.modules['config']


def test_with_settings_d_drive():
    """Test: With settings.json specifying D: drive"""
    print("\n=== TEST 2: settings.json with D: drive ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Copy config.py to temp dir
        config_src = Path(__file__).parent / "config.py"
        config_dst = tmpdir / "config.py"
        shutil.copy(config_src, config_dst)

        # Create settings.json with D: drive
        settings_file = tmpdir / "settings.json"
        settings_file.write_text('{"drive_letter": "D", "version": "1.0"}', encoding='utf-8')

        sys.path.insert(0, str(tmpdir))

        try:
            if 'config' in sys.modules:
                del sys.modules['config']

            import config as test_config

            # Check paths use D: drive
            resource_str = str(test_config.RESOURCE_FOLDER)
            test_result(
                "RESOURCE_FOLDER uses D: drive",
                resource_str.startswith("D:"),
                f"Got: {resource_str[:20]}..."
            )

            language_str = str(test_config.LANGUAGE_FOLDER)
            test_result(
                "LANGUAGE_FOLDER uses D: drive",
                language_str.startswith("D:"),
                f"Got: {language_str[:20]}..."
            )

            export_str = str(test_config.EXPORT_FOLDER)
            test_result(
                "EXPORT_FOLDER uses D: drive",
                export_str.startswith("D:"),
                f"Got: {export_str[:20]}..."
            )

            quest_str = str(test_config.QUESTGROUPINFO_FILE)
            test_result(
                "QUESTGROUPINFO_FILE uses D: drive",
                quest_str.startswith("D:"),
                f"Got: {quest_str[:20]}..."
            )

            voice_str = str(test_config.VOICE_RECORDING_SHEET_FOLDER)
            test_result(
                "VOICE_RECORDING_SHEET_FOLDER uses D: drive",
                voice_str.startswith("D:"),
                f"Got: {voice_str[:20]}..."
            )

        finally:
            sys.path.remove(str(tmpdir))
            if 'config' in sys.modules:
                del sys.modules['config']


def test_with_settings_e_drive():
    """Test: With settings.json specifying E: drive"""
    print("\n=== TEST 3: settings.json with E: drive ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        config_src = Path(__file__).parent / "config.py"
        config_dst = tmpdir / "config.py"
        shutil.copy(config_src, config_dst)

        settings_file = tmpdir / "settings.json"
        settings_file.write_text('{"drive_letter": "E", "version": "1.0"}', encoding='utf-8')

        sys.path.insert(0, str(tmpdir))

        try:
            if 'config' in sys.modules:
                del sys.modules['config']

            import config as test_config

            resource_str = str(test_config.RESOURCE_FOLDER)
            test_result(
                "RESOURCE_FOLDER uses E: drive",
                resource_str.startswith("E:"),
                f"Got: {resource_str[:20]}..."
            )

        finally:
            sys.path.remove(str(tmpdir))
            if 'config' in sys.modules:
                del sys.modules['config']


def test_invalid_settings():
    """Test: Invalid settings.json falls back to F: drive"""
    print("\n=== TEST 4: Invalid settings.json (fallback to F:) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        config_src = Path(__file__).parent / "config.py"
        config_dst = tmpdir / "config.py"
        shutil.copy(config_src, config_dst)

        # Create invalid JSON
        settings_file = tmpdir / "settings.json"
        settings_file.write_text('{"drive_letter": invalid json}', encoding='utf-8')

        sys.path.insert(0, str(tmpdir))

        try:
            if 'config' in sys.modules:
                del sys.modules['config']

            import config as test_config

            # Should fall back to F: drive
            resource_str = str(test_config.RESOURCE_FOLDER)
            test_result(
                "Invalid JSON falls back to F: drive",
                resource_str.startswith("F:"),
                f"Got: {resource_str[:20]}..."
            )

        finally:
            sys.path.remove(str(tmpdir))
            if 'config' in sys.modules:
                del sys.modules['config']


def test_invalid_drive_letter():
    """Test: Invalid drive letter in settings.json falls back to F:"""
    print("\n=== TEST 5: Invalid drive_letter (fallback to F:) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        config_src = Path(__file__).parent / "config.py"
        config_dst = tmpdir / "config.py"
        shutil.copy(config_src, config_dst)

        # Create settings with invalid drive letter
        settings_file = tmpdir / "settings.json"
        settings_file.write_text('{"drive_letter": "XYZ", "version": "1.0"}', encoding='utf-8')

        sys.path.insert(0, str(tmpdir))

        try:
            if 'config' in sys.modules:
                del sys.modules['config']

            import config as test_config

            # Should fall back to F: drive
            resource_str = str(test_config.RESOURCE_FOLDER)
            test_result(
                "Invalid drive_letter falls back to F: drive",
                resource_str.startswith("F:"),
                f"Got: {resource_str[:20]}..."
            )

        finally:
            sys.path.remove(str(tmpdir))
            if 'config' in sys.modules:
                del sys.modules['config']


def main():
    print("=" * 60)
    print("QACompiler Runtime Configuration Test")
    print("=" * 60)
    print("\nThis test verifies that settings.json properly overrides")
    print("the default F: drive letter at runtime.")

    # Run tests
    test_no_settings_file()
    test_with_settings_d_drive()
    test_with_settings_e_drive()
    test_invalid_settings()
    test_invalid_drive_letter()

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {PASSED} passed, {FAILED} failed")
    print("=" * 60)

    if FAILED > 0:
        print("\n[!] Some tests FAILED - fix issues before building!")
        sys.exit(1)
    else:
        print("\n[+] All tests PASSED - runtime config system working!")
        sys.exit(0)


if __name__ == "__main__":
    main()
