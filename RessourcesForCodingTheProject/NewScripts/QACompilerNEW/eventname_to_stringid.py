#!/usr/bin/env python3
"""
EventName to StringID Converter
===============================
Reads EventName from column 1, writes StringID to column 2.

Usage:
    python eventname_to_stringid.py input.xlsx [output.xlsx]

If output not specified, creates input_with_stringid.xlsx
"""

import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent))

from openpyxl import load_workbook
from core.export_index import get_soundevent_mapping


def convert_eventnames(input_path: str, output_path: str = None) -> None:
    """Convert EventName (col 1) to StringID (col 2)."""

    input_file = Path(input_path)
    if not input_file.exists():
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)

    # Output path
    if output_path:
        output_file = Path(output_path)
    else:
        output_file = input_file.parent / f"{input_file.stem}_with_stringid.xlsx"

    print(f"Loading EXPORT mapping...")
    mapping = get_soundevent_mapping()
    print(f"  Loaded {len(mapping)} EventName entries")

    print(f"Reading: {input_file}")
    wb = load_workbook(input_file)
    ws = wb.active

    # Add header if not present
    if ws.cell(1, 2).value != "STRINGID":
        ws.cell(1, 2, "STRINGID")

    found = 0
    missing = 0

    for row in range(2, ws.max_row + 1):
        eventname = ws.cell(row, 1).value
        if not eventname:
            continue

        eventname_key = str(eventname).strip().lower()
        export_data = mapping.get(eventname_key)

        if export_data:
            stringid = export_data.get("stringid", "")
            ws.cell(row, 2, stringid)
            found += 1
        else:
            ws.cell(row, 2, "NOT_FOUND")
            missing += 1

    wb.save(output_file)
    wb.close()

    print(f"Output: {output_file}")
    print(f"  Found: {found}")
    print(f"  Missing: {missing}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    convert_eventnames(input_path, output_path)
