"""
LocaNext - vgmstream Binary Bundler

Copies vgmstream-cli.exe and all required DLLs from MapDataGenerator/tools/
to bin/vgmstream/ for Electron packaging.

Usage:
    python tools/bundle_vgmstream.py
    python tools/bundle_vgmstream.py --source /custom/source --output /custom/dest
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# vgmstream-cli.exe + 11 required DLLs (all must be co-located)
VGMSTREAM_FILES = [
    "vgmstream-cli.exe",
    "avcodec-vgmstream-59.dll",
    "avformat-vgmstream-59.dll",
    "avutil-vgmstream-57.dll",
    "swresample-vgmstream-4.dll",
    "libvorbis.dll",
    "libmpg123-0.dll",
    "libg719_decode.dll",
    "libatrac9.dll",
    "libcelt-0061.dll",
    "libcelt-0110.dll",
    "libspeex-1.dll",
]


def main() -> int:
    project_root = Path(__file__).parent.parent
    default_source = project_root / "RessourcesForCodingTheProject" / "NewScripts" / "MapDataGenerator" / "tools"
    default_output = project_root / "bin" / "vgmstream"

    parser = argparse.ArgumentParser(description="Bundle vgmstream binaries for Electron packaging")
    parser.add_argument(
        "--source",
        type=str,
        default=str(default_source),
        help="Source directory containing vgmstream files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(default_output),
        help="Output directory (default: bin/vgmstream)",
    )
    args = parser.parse_args()

    source_dir = Path(args.source)
    output_dir = Path(args.output)

    if not source_dir.exists():
        print(f"[ERROR] Source directory not found: {source_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing = []

    for filename in VGMSTREAM_FILES:
        src = source_dir / filename
        if not src.exists():
            missing.append(filename)
            continue

        shutil.copy2(str(src), str(output_dir / filename))
        copied += 1

    if missing:
        print(f"[WARNING] Missing files: {', '.join(missing)}")

    print(f"Copied {copied} files to {output_dir}/")

    if copied != len(VGMSTREAM_FILES):
        print(f"[ERROR] Expected {len(VGMSTREAM_FILES)} files, copied {copied}")
        return 1

    print(f"[SUCCESS] vgmstream binaries bundled ({copied} files: 1 exe + {copied - 1} DLLs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
