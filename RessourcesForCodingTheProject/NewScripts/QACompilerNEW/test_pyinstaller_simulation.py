#!/usr/bin/env python3
"""
PyInstaller Simulation Test
===========================
This test simulates what happens when:
1. PyInstaller bundles the app with F: hardcoded (at compile time)
2. Installer creates settings.json with different drive letter
3. App reads settings.json at runtime

This PROVES the fix will work in production.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

def test_pyinstaller_simulation():
    """
    Simulate PyInstaller + Installer flow:

    1. Create a mock "installed" folder structure
    2. Copy config.py (simulating PyInstaller bundle - F: is the default)
    3. Create settings.json with D: (simulating Inno Setup post-install)
    4. Import config and verify D: is used (not F:)
    """
    print("=" * 60)
    print("PyInstaller + Installer Simulation Test")
    print("=" * 60)
    print()
    print("Simulating:")
    print("  1. PyInstaller bundles app with F: as default")
    print("  2. User installs and selects D: drive")
    print("  3. Installer creates settings.json with D:")
    print("  4. App starts and reads settings.json at runtime")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Step 1: Copy config.py (simulates PyInstaller bundle)
        # The source has F: hardcoded - just like the compiled exe would
        config_src = Path(__file__).parent / "config.py"
        config_dst = tmpdir / "config.py"
        shutil.copy(config_src, config_dst)
        print(f"[1] Copied config.py to simulated install folder")
        print(f"    (F: paths are hardcoded in the source)")

        # Step 2: Create settings.json (simulates Inno Setup post-install)
        settings_file = tmpdir / "settings.json"
        settings_content = {"drive_letter": "D", "version": "1.0"}
        settings_file.write_text(json.dumps(settings_content), encoding='utf-8')
        print(f"[2] Created settings.json with drive_letter: D")
        print(f"    (Simulating what Inno Setup does)")

        # Step 3: Import config (simulates app startup)
        sys.path.insert(0, str(tmpdir))

        try:
            # Clear any cached imports
            if 'config' in sys.modules:
                del sys.modules['config']

            print(f"[3] Importing config module...")
            import config as test_config

            # Step 4: Verify D: is used
            print()
            print("Results:")
            print("-" * 40)

            paths_to_check = [
                ("RESOURCE_FOLDER", test_config.RESOURCE_FOLDER),
                ("LANGUAGE_FOLDER", test_config.LANGUAGE_FOLDER),
                ("EXPORT_FOLDER", test_config.EXPORT_FOLDER),
                ("QUESTGROUPINFO_FILE", test_config.QUESTGROUPINFO_FILE),
                ("VOICE_RECORDING_SHEET_FOLDER", test_config.VOICE_RECORDING_SHEET_FOLDER),
            ]

            all_passed = True
            for name, path in paths_to_check:
                path_str = str(path)
                uses_d = path_str.startswith("D:")
                status = "PASS" if uses_d else "FAIL"
                if not uses_d:
                    all_passed = False
                print(f"  {status}: {name}")
                print(f"        → {path_str[:50]}...")

            print()
            print("=" * 60)
            if all_passed:
                print("SUCCESS! Runtime config override works correctly.")
                print()
                print("This proves that:")
                print("  - F: hardcoded in config.py (compile time)")
                print("  - D: in settings.json (install time)")
                print("  - App uses D: at runtime ✓")
                print()
                print("Your friend's installation will work after this fix!")
                return True
            else:
                print("FAILURE! Some paths still use F: drive.")
                return False

        finally:
            sys.path.remove(str(tmpdir))
            if 'config' in sys.modules:
                del sys.modules['config']


def main():
    success = test_pyinstaller_simulation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
