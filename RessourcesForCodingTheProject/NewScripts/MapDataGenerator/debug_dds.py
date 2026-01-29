"""
DEBUG SCRIPT: Test DDS file scanning and lookup
Run this directly to diagnose image loading issues.

Usage: python debug_dds.py
"""

import os
import sys
from pathlib import Path

# Default paths (adjust if needed)
TEXTURE_FOLDER = r"F:\perforce\common\mainline\commonresource\ui\texture\image"
TEST_TEXTURE_NAME = "cd_knowledgeimage_Node_Dem_DemenissCastle"

def main():
    print("=" * 60)
    print("MapDataGenerator DDS Debug Script")
    print("=" * 60)

    texture_folder = Path(TEXTURE_FOLDER)

    # Check if folder exists
    print(f"\n1. Checking texture folder: {texture_folder}")
    if not texture_folder.exists():
        print(f"   ERROR: Folder does not exist!")
        print(f"   Please edit this script and set TEXTURE_FOLDER to your actual path.")
        return
    print(f"   OK: Folder exists")

    # Scan for DDS files
    print(f"\n2. Scanning for .dds files recursively...")
    dds_files = {}
    count = 0
    for dds_path in texture_folder.rglob("*.dds"):
        name_lower = dds_path.stem.lower()
        dds_files[name_lower] = dds_path
        count += 1
        if count % 1000 == 0:
            print(f"   Scanned {count} files...")

    print(f"   Total DDS files found: {count}")

    # Check subfolders
    print(f"\n3. Checking subfolders:")
    subfolders = set()
    for dds_path in texture_folder.rglob("*.dds"):
        rel_path = dds_path.relative_to(texture_folder)
        if len(rel_path.parts) > 1:
            subfolders.add(rel_path.parts[0])
    print(f"   Subfolders with DDS files: {sorted(subfolders)}")

    # Check for specific file
    print(f"\n4. Looking for test texture: {TEST_TEXTURE_NAME}")
    test_key = TEST_TEXTURE_NAME.lower()
    if test_key in dds_files:
        print(f"   FOUND: {dds_files[test_key]}")
    else:
        print(f"   NOT FOUND!")
        # Try to find similar names
        similar = [k for k in dds_files.keys() if "demeniss" in k.lower()]
        if similar:
            print(f"   Similar names found:")
            for s in similar[:10]:
                print(f"     - {s}")

    # Check if Knowledgeimage folder is scanned
    print(f"\n5. Checking Knowledgeimage subfolder:")
    ki_path = texture_folder / "Knowledgeimage"
    if ki_path.exists():
        ki_count = len(list(ki_path.glob("*.dds")))
        print(f"   Path exists: {ki_path}")
        print(f"   DDS files directly in Knowledgeimage: {ki_count}")
    else:
        print(f"   WARNING: Knowledgeimage subfolder not found at {ki_path}")
        # Check case variations
        for item in texture_folder.iterdir():
            if item.is_dir() and "knowledge" in item.name.lower():
                print(f"   Found similar folder: {item}")

    # Sample some indexed keys
    print(f"\n6. Sample indexed texture names (first 10):")
    for i, key in enumerate(list(dds_files.keys())[:10]):
        print(f"   {key}")

    print("\n" + "=" * 60)
    print("Debug complete. Check results above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
