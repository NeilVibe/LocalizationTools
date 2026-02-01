#!/usr/bin/env python3
"""
extract_chinese_chars.py
-------------------------------------------------
• Read one or more BDO/BDM TXT-translation files (tab-delimited:
  Korean in column-5, translation in column-6 ... 0-based),
• collect EVERY unique Chinese character used in the translation column
  (Simplified + Traditional, no distinction) and
• write them to an output text file – all characters in ONE SINGLE LINE
  (no separators, no newline between them).

WHAT’S NEW?
-----------
1) Automatic output file
   If the “-o ...” option is NOT supplied, the script now writes the result
   to a file named “unique_cjk_chars.txt” in THE SAME FOLDER AS THE SCRIPT.

2) Characters listed “nicely”
   The collected characters are sorted alphabetically before being written
   to the file (but they appear in a single continuous string).

3) Everything else (GUI fallback, live progress, etc.) is unchanged.

USAGE
-----
   # CLI
   python extract_chinese_chars.py  in1.txt [in2.txt ...]       # → auto file
   python extract_chinese_chars.py  in1.txt -o my_chars.txt     # → custom file

   # GUI file-dialog
   python extract_chinese_chars.py                              # choose files

Written for standard Python – no third-party dependencies.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple, Sequence

# ──────────────────────────────────────────────────────────────────────
# Optional file-dialog via Tkinter (only imported if needed)
def choose_input_files() -> List[str]:
    """Ask the user to select one or more TXT files via GUI; return list."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # hide main window
    paths: Tuple[str, ...] = filedialog.askopenfilenames(
        title="Select one or more TXT translation files",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    root.destroy()
    return list(paths)

# ──────────────────────────────────────────────────────────────────────
# Helper: “is this code-point a CJK ideograph?”
_CJK_RANGES: Sequence[Tuple[int, int]] = [
    (0x3400, 0x4DBF),   # CJK Ext-A
    (0x4E00, 0x9FFF),   # CJK Unified
    (0xF900, 0xFAFF),   # CJK Compatibility
    (0x20000, 0x2A6DF), # CJK Ext-B
    (0x2A700, 0x2B73F), # CJK Ext-C
    (0x2B740, 0x2B81F), # CJK Ext-D
    (0x2B820, 0x2CEAF), # CJK Ext-E
    (0x2CEB0, 0x2EBEF), # CJK Ext-F
    (0x30000, 0x3134F), # CJK Ext-G
]
def is_cjk(char: str) -> bool:
    cp = ord(char)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)

# ──────────────────────────────────────────────────────────────────────
# Command-line parsing
out_file: str | None = None
input_files: List[str] = []

args = iter(sys.argv[1:])
for tok in args:
    if tok == "-o":
        try:
            out_file = next(args)
        except StopIteration:
            sys.exit("❌  “-o” needs a filename")
    else:
        input_files.append(tok)

# No CLI input files? → open GUI
if not input_files:
    input_files = choose_input_files()

if not input_files:
    print("❌  No input files provided (nothing chosen)")
    sys.exit(0)

# ──────────────────────────────────────────────────────────────────────
# Processing
unique_chars: set[str] = set()

def process_file(path: Path) -> None:
    """
    Scan a file, update global `unique_chars`,
    and show live progress on the console.
    """
    total_bytes = path.stat().st_size or 1
    start_time      = time.time()
    last_report_t   = start_time
    report_interval = 1.0  # seconds
    lines_read      = 0
    bytes_read      = 0

    with path.open("rb") as fb:
        while True:
            raw = fb.readline()
            if not raw:
                break
            bytes_read += len(raw)
            lines_read += 1

            # decode and grab column-6 (index 6)
            line = raw.decode("utf-8", "ignore").rstrip("\r\n")
            cols = line.split("\t")
            if len(cols) >= 7:
                for ch in cols[6]:
                    if is_cjk(ch):
                        unique_chars.add(ch)

            # periodic progress update
            now = time.time()
            if now - last_report_t >= report_interval:
                elapsed = now - start_time
                percent = bytes_read / total_bytes * 100
                speed   = lines_read / elapsed if elapsed else 0.0
                print(
                    f"\r[{path.name}] "
                    f"{percent:6.2f}% | "
                    f"{lines_read:>9,} rows | "
                    f"{len(unique_chars):>9,} chars | "
                    f"{speed:8.1f} rows/s",
                    end="", flush=True
                )
                last_report_t = now

    # final summary line (overwrite previous line, then newline)
    elapsed = max(time.time() - start_time, 1e-6)
    speed   = lines_read / elapsed
    print(
        f"\r[{path.name}] 100.00% | "
        f"{lines_read:>9,} rows | "
        f"{len(unique_chars):>9,} chars | "
        f"{speed:8.1f} rows/s (done)",
        flush=True
    )

for fname in input_files:
    p = Path(fname)
    if not p.is_file():
        print(f"⚠️  Skipped (not found): {p}")
        continue
    process_file(p)

# ──────────────────────────────────────────────────────────────────────
# Output
if out_file is None:
    # Default output file in the same directory as this script
    script_dir = Path(sys.argv[0]).resolve().parent
    out_file = str(script_dir / "unique_cjk_chars.txt")

# All characters in one single line (sorted)
result_text = "".join(sorted(unique_chars))

Path(out_file).write_text(result_text, encoding="utf-8")
print(f"✅  Wrote {len(unique_chars):,} unique CJK characters → {out_file}")