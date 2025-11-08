#!/usr/bin/env python
"""
Find and report duplicate values in column A of an Excel workbook.

Now with a small GUI file-picker:
    • If you launch the script with no command-line arguments, a native file-
      selection dialog (tkinter) will pop up so you can choose the workbook.
    • If you pass the path (and optionally the sheet name / index) on the
      command line, the script behaves exactly as before.

Usage (two options):

1) Pure GUI
   $ python find_duplicates.py
   [pick a file in the dialog]
   (uses first sheet by default)

2) Command-line
   $ python find_duplicates.py <excel_file> [<sheet_name_or_index>]

Requires:
    pandas
    openpyxl   (or xlrd if you read .xls)

Works with Python 3.8+
"""
import sys
from pathlib import Path
from collections import defaultdict
from typing import Union, Dict, List

import pandas as pd

# --- Optional tiny GUI for picking the file -------------------------------
try:
    # Import only when we might need it (keeps CLI-only usage headless-safe)
    import tkinter as _tk
    from tkinter import filedialog as _fd
except ImportError:
    _tk = None      # Running in an environment without tkinter (e.g. Linux minimal)
# ---------------------------------------------------------------------------


def read_column_a(
    excel_path: Path,
    sheet_name: Union[str, int, None] = 0
) -> pd.Series:
    """
    Load ONLY column A from the requested sheet.
    Returns a `pandas.Series` with original row indexes preserved.
    """
    df = pd.read_excel(
        excel_path,
        sheet_name=sheet_name,
        usecols=[0],        # Column A → index 0
        header=None,        # Treat every row as data (no header line)
        dtype=str           # Read everything as text
    )
    # Flatten to a Series and drop NaNs / blank strings
    ser = df.iloc[:, 0].dropna().astype(str).str.strip()
    ser = ser[ser != ""]
    return ser


def group_duplicates(values: pd.Series) -> Dict[str, List[int]]:
    """
    Return mapping of duplicated value → list of (1-based) row numbers
    where it appears.
    """
    locations: Dict[str, List[int]] = defaultdict(list)
    for idx, val in values.items():
        locations[val].append(idx + 1)       # +1 so it matches Excel's row numbers

    # Keep only those with more than one occurrence
    return {val: rows for val, rows in locations.items() if len(rows) > 1}


def print_duplicate_report(dupes: Dict[str, List[int]]) -> None:
    """
    Pretty-print the duplicates to the console.
    """
    if not dupes:
        print("No duplicates found in column A.")
        return

    print("\nDUPLICATES IN COLUMN A\n" + "=" * 30)
    for value, rows in sorted(dupes.items(), key=lambda x: (-len(x[1]), x[0])):
        print(f"\n• {value!r}  (count: {len(rows)})")
        print("  Rows:", ", ".join(map(str, rows)))
    print("\nDone.")


def pick_excel_with_gui() -> Path:
    """
    Open a native file-open dialog to choose an Excel file.
    Returns the selected Path, or exits the program if cancelled.
    """
    if _tk is None:
        sys.exit("tkinter is not available on this system; "
                 "please provide the Excel file path as a command-line argument.")

    root = _tk.Tk()
    root.withdraw()        # Hide the main empty window

    file_path = _fd.askopenfilename(
        title="Select Excel file",
        filetypes=[
            ("Excel files", "*.xlsx *.xlsm *.xls"),
            ("All files", "*.*")
        ]
    )
    root.destroy()

    if not file_path:
        sys.exit("No file selected. Exiting.")
    return Path(file_path)


def main() -> None:
    # ------------------------------------------------------------------
    # 1) Determine Excel file path & optional sheet specification
    # ------------------------------------------------------------------
    if len(sys.argv) >= 2:
        # CLI path provided
        excel_path = Path(sys.argv[1])
    else:
        # No argument → pop up GUI file picker
        excel_path = pick_excel_with_gui()

    if not excel_path.exists():
        sys.exit(f"Error: file not found -> {excel_path}")

    sheet_name: Union[str, int] = sys.argv[2] if len(sys.argv) >= 3 else 0

    # ------------------------------------------------------------------
    # 2) Read, analyse, report
    # ------------------------------------------------------------------
    try:
        col_a = read_column_a(excel_path, sheet_name)
    except Exception as exc:
        sys.exit(f"Failed to read Excel file: {exc}")

    duplicates = group_duplicates(col_a)
    print_duplicate_report(duplicates)


if __name__ == "__main__":
    main()