#!/usr/bin/env python3
"""
gui_chinese_tools.py
-------------------------------------------------
GUI with two buttons:
1) Chinese Extraction/Injection  → original extraction logic.
2) Special Filter Output         → regex-based character list filtering.

Both show live progress in terminal and run in threads to avoid GUI freeze.
"""

from __future__ import annotations
import os
import sys
import time
import re
import threading
from pathlib import Path
from typing import List, Tuple, Sequence
import tkinter as tk
from tkinter import filedialog, messagebox

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
def choose_files(title: str, multiple=True) -> List[str]:
    """Open file dialog."""
    paths = filedialog.askopenfilenames(
        title=title,
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    ) if multiple else filedialog.askopenfilename(
        title=title,
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not paths:
        return []
    return list(paths) if multiple else [paths]

# ──────────────────────────────────────────────────────────────────────
def chinese_extraction_injection():
    """Original extraction logic wrapped for GUI."""
    input_files = choose_files("Select one or more TXT translation files")
    if not input_files:
        messagebox.showerror("Error", "No input files selected.")
        return

    out_file = Path(__file__).resolve().parent / "unique_cjk_chars.txt"
    unique_chars: set[str] = set()

    def process_file(path: Path):
        total_bytes = path.stat().st_size or 1
        start_time = time.time()
        last_report_t = start_time
        report_interval = 1.0
        lines_read = 0
        bytes_read = 0

        with path.open("rb") as fb:
            while True:
                raw = fb.readline()
                if not raw:
                    break
                bytes_read += len(raw)
                lines_read += 1
                line = raw.decode("utf-8", "ignore").rstrip("\r\n")
                cols = line.split("\t")
                if len(cols) >= 7:
                    for ch in cols[6]:
                        if is_cjk(ch):
                            unique_chars.add(ch)
                now = time.time()
                if now - last_report_t >= report_interval:
                    elapsed = now - start_time
                    percent = bytes_read / total_bytes * 100
                    speed = lines_read / elapsed if elapsed else 0.0
                    print(
                        f"\r[{path.name}] {percent:6.2f}% | "
                        f"{lines_read:>9,} rows | "
                        f"{len(unique_chars):>9,} chars | "
                        f"{speed:8.1f} rows/s",
                        end="", flush=True
                    )
                    last_report_t = now

        elapsed = max(time.time() - start_time, 1e-6)
        speed = lines_read / elapsed
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

    result_text = "".join(sorted(unique_chars))
    Path(out_file).write_text(result_text, encoding="utf-8")
    print(f"\n✅  Wrote {len(unique_chars):,} unique CJK characters → {out_file}")
    messagebox.showinfo("Done", f"Extraction complete.\nOutput: {out_file}")

# ──────────────────────────────────────────────────────────────────────
def special_filter_output():
    """Special filter logic based on regex character list."""
    char_file = choose_files("Select character list file", multiple=False)
    if not char_file:
        messagebox.showerror("Error", "No character list file selected.")
        return
    target_file = choose_files("Select target translation file", multiple=False)
    if not target_file:
        messagebox.showerror("Error", "No target translation file selected.")
        return

    # Step 1: Extract characters from char_file
    chars_set: set[str] = set()
    char_pattern = re.compile(r"'(.*?)'")
    with open(char_file[0], "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = char_pattern.search(line)
            if m:
                chars_set.add(m.group(1))
    print(f"✅ Extracted {len(chars_set)} characters from {char_file[0]}")

    # Step 2: Scan target file for matches in column index 6
    out_file = Path(__file__).resolve().parent / "special_filter_output.txt"
    total_bytes = Path(target_file[0]).stat().st_size or 1
    start_time = time.time()
    last_report_t = start_time
    report_interval = 1.0
    lines_read = 0
    bytes_read = 0

    # Dictionary: char -> set of example strings
    matches_dict: dict[str, set[str]] = {ch: set() for ch in chars_set}

    with open(target_file[0], "rb") as fb:
        while True:
            raw = fb.readline()
            if not raw:
                break
            bytes_read += len(raw)
            lines_read += 1
            line = raw.decode("utf-8", "ignore").rstrip("\r\n")
            cols = line.split("\t")
            if len(cols) >= 7:
                col6 = cols[6]
                for ch in chars_set:
                    if ch in col6 and len(matches_dict[ch]) < 3:
                        matches_dict[ch].add(col6)
            now = time.time()
            if now - last_report_t >= report_interval:
                elapsed = now - start_time
                percent = bytes_read / total_bytes * 100
                total_matches = sum(len(v) for v in matches_dict.values())
                speed = lines_read / elapsed if elapsed else 0.0
                print(
                    f"\r[{Path(target_file[0]).name}] {percent:6.2f}% | "
                    f"{lines_read:>9,} rows | "
                    f"{total_matches:>9,} matches | "
                    f"{speed:8.1f} rows/s",
                    end="", flush=True
                )
                last_report_t = now

    # Step 3: Write output with numbering
    with open(out_file, "w", encoding="utf-8") as out:
        index = 1
        for ch in sorted(matches_dict.keys()):
            examples = list(matches_dict[ch])
            if examples:
                out.write(f"{index}. {ch}\n")
                for ex in examples[:3]:
                    out.write(f"{ex}\n")
                out.write("\n")
                index += 1

    elapsed = max(time.time() - start_time, 1e-6)
    speed = lines_read / elapsed
    total_matches = sum(len(v) for v in matches_dict.values())
    print(
        f"\r[{Path(target_file[0]).name}] 100.00% | "
        f"{lines_read:>9,} rows | "
        f"{total_matches:>9,} matches | "
        f"{speed:8.1f} rows/s (done)",
        flush=True
    )
    print(f"\n✅ Wrote {index-1:,} unique characters → {out_file}")
    messagebox.showinfo("Done", f"Special filter complete.\nOutput: {out_file}")

# ──────────────────────────────────────────────────────────────────────
def run_in_thread(func):
    threading.Thread(target=func, daemon=True).start()

# ──────────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    root.title("Chinese Tools")
    root.geometry("400x200")

    btn1 = tk.Button(root, text="Chinese Extraction/Injection",
                     command=lambda: run_in_thread(chinese_extraction_injection),
                     font=("Arial", 12), width=30, height=2)
    btn1.pack(pady=20)

    btn2 = tk.Button(root, text="Special Filter Output",
                     command=lambda: run_in_thread(special_filter_output),
                     font=("Arial", 12), width=30, height=2)
    btn2.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()