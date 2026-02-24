#!/usr/bin/env python3
# coding: utf-8
"""
XML Diff Extractor v1.0
========================
Simple WinMerge-style diff for XML language data files.
Compares SOURCE (old) vs TARGET (new) and extracts ADD/EDIT LocStr elements.

- ADD:  StringId exists in TARGET but not in SOURCE
- EDIT: StringId exists in both but any attribute value changed

Output: XML file with <LanguageData> root containing only changed LocStr elements,
        each tagged with diff_type="ADD" or diff_type="EDIT".

Usage: python xml_diff_extractor.py
"""

import os
import sys
import logging
import datetime as _dt
from pathlib import Path
from typing import Dict, List, Tuple
from collections import OrderedDict

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Try lxml first (preserves attribute order), fallback to stdlib
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("XMLDiffExtractor")
logger.setLevel(logging.DEBUG)

# =============================================================================
# XML PARSING
# =============================================================================

def parse_locstr_elements(xml_path: Path) -> Tuple[Dict[str, dict], int]:
    """
    Parse an XML file and return a dict of StringId -> {attr: value}.

    Returns:
        (locstr_map, total_count)
    """
    locstr_map: Dict[str, dict] = OrderedDict()
    total = 0

    try:
        if USING_LXML:
            parser = etree.XMLParser(recover=True, encoding="utf-8")
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        else:
            tree = etree.parse(str(xml_path))
            root = tree.getroot()
    except Exception as e:
        logger.error("Failed to parse %s: %s", xml_path, e)
        return locstr_map, 0

    for elem in root.iter("LocStr"):
        total += 1
        string_id = elem.get("StringId") or elem.get("StringID") or ""
        if not string_id:
            continue

        # Capture all attributes
        attrs = dict(elem.attrib)
        locstr_map[string_id] = attrs

    return locstr_map, total


def compare_xml(
    source_map: Dict[str, dict],
    target_map: Dict[str, dict],
) -> Tuple[List[Tuple[str, dict]], List[Tuple[str, dict, dict]]]:
    """
    Compare source and target LocStr maps.

    Returns:
        (added, edited)
        - added:  [(string_id, target_attrs), ...]
        - edited: [(string_id, source_attrs, target_attrs), ...]
    """
    added = []
    edited = []

    for string_id, target_attrs in target_map.items():
        if string_id not in source_map:
            # ADD: exists in target but not source
            added.append((string_id, target_attrs))
        else:
            # Check if any attribute changed
            source_attrs = source_map[string_id]
            if source_attrs != target_attrs:
                edited.append((string_id, source_attrs, target_attrs))

    return added, edited


def write_diff_xml(
    added: List[Tuple[str, dict]],
    edited: List[Tuple[str, dict, dict]],
    output_path: Path,
) -> int:
    """
    Write diff results as XML with LocStr elements under <LanguageData>.
    Each element gets a diff_type attribute ("ADD" or "EDIT").

    Returns total elements written.
    """
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<LanguageData>',
    ]

    count = 0

    # ADDs first
    if added:
        lines.append('  <!-- ===== ADDED ===== -->')
        for string_id, attrs in added:
            line = _build_locstr_line(attrs, "ADD")
            lines.append(f"  {line}")
            count += 1

    # EDITs
    if edited:
        lines.append('  <!-- ===== EDITED ===== -->')
        for string_id, source_attrs, target_attrs in edited:
            line = _build_locstr_line(target_attrs, "EDIT")
            lines.append(f"  {line}")
            count += 1

    lines.append('</LanguageData>')
    lines.append('')

    output_path.write_text('\n'.join(lines), encoding='utf-8')
    return count


def _build_locstr_line(attrs: dict, diff_type: str) -> str:
    """Build a single <LocStr .../> line preserving all original attributes."""
    parts = [f'<LocStr diff_type="{diff_type}"']
    for key, value in attrs.items():
        # XML-escape attribute values
        safe_val = _xml_escape_attr(value)
        parts.append(f' {key}="{safe_val}"')
    parts.append(' />')
    return ''.join(parts)


def _xml_escape_attr(value: str) -> str:
    """Escape a string for use in an XML attribute value (double-quoted)."""
    return (
        value
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


# =============================================================================
# GUI
# =============================================================================

class XMLDiffApp:
    """Simple tkinter GUI for XML diff extraction."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XML Diff Extractor v1.0")
        self.root.geometry("700x520")
        self.root.resizable(True, True)

        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # Title
        ttk.Label(
            self.root, text="XML Diff Extractor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(10, 5))

        ttk.Label(
            self.root,
            text="Compare two XML files and extract ADD/EDIT LocStr elements",
            font=("Segoe UI", 9),
        ).pack(pady=(0, 10))

        # Source file
        frame_src = ttk.LabelFrame(self.root, text="SOURCE (old / before)", padding=5)
        frame_src.pack(fill="x", **pad)

        entry_src = ttk.Entry(frame_src, textvariable=self.source_path, width=70)
        entry_src.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_src, text="Browse...", command=self._browse_source).pack(side="right")

        # Target file
        frame_tgt = ttk.LabelFrame(self.root, text="TARGET (new / after)", padding=5)
        frame_tgt.pack(fill="x", **pad)

        entry_tgt = ttk.Entry(frame_tgt, textvariable=self.target_path, width=70)
        entry_tgt.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(frame_tgt, text="Browse...", command=self._browse_target).pack(side="right")

        # Run button
        ttk.Button(
            self.root, text="Run Diff", command=self._run_diff,
        ).pack(pady=10)

        # Log output
        frame_log = ttk.LabelFrame(self.root, text="Output", padding=5)
        frame_log.pack(fill="both", expand=True, **pad)

        self.log_text = scrolledtext.ScrolledText(
            frame_log, height=14, font=("Consolas", 9), wrap="word",
        )
        self.log_text.pack(fill="both", expand=True)

    def _browse_source(self):
        path = filedialog.askopenfilename(
            title="Select SOURCE XML (old / before)",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self.source_path.set(path)

    def _browse_target(self):
        path = filedialog.askopenfilename(
            title="Select TARGET XML (new / after)",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self.target_path.set(path)

    def _log(self, msg: str):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def _run_diff(self):
        self.log_text.delete("1.0", "end")

        src = self.source_path.get().strip()
        tgt = self.target_path.get().strip()

        if not src or not tgt:
            messagebox.showerror("Error", "Please select both SOURCE and TARGET XML files.")
            return

        src_path = Path(src)
        tgt_path = Path(tgt)

        if not src_path.exists():
            messagebox.showerror("Error", f"SOURCE file not found:\n{src_path}")
            return
        if not tgt_path.exists():
            messagebox.showerror("Error", f"TARGET file not found:\n{tgt_path}")
            return

        self._log(f"SOURCE: {src_path.name}")
        self._log(f"TARGET: {tgt_path.name}")
        self._log("")

        # Parse both files
        self._log("Parsing SOURCE...")
        source_map, source_total = parse_locstr_elements(src_path)
        self._log(f"  {source_total} LocStr elements ({len(source_map)} unique StringIds)")

        self._log("Parsing TARGET...")
        target_map, target_total = parse_locstr_elements(tgt_path)
        self._log(f"  {target_total} LocStr elements ({len(target_map)} unique StringIds)")
        self._log("")

        # Compare
        self._log("Comparing...")
        added, edited = compare_xml(source_map, target_map)

        # Also count DELETEs (informational only, not extracted)
        deleted_count = sum(1 for sid in source_map if sid not in target_map)

        self._log(f"  ADD:    {len(added)} (new StringIds in TARGET)")
        self._log(f"  EDIT:   {len(edited)} (changed attributes)")
        self._log(f"  DELETE: {deleted_count} (in SOURCE but not TARGET, not extracted)")
        self._log("")

        if not added and not edited:
            self._log("No differences found (ADD/EDIT). Files are identical for LocStr content.")
            return

        # Output path: next to TARGET file
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"DIFF_{tgt_path.stem}_{timestamp}.xml"
        output_path = tgt_path.parent / output_name

        count = write_diff_xml(added, edited, output_path)
        self._log(f"Output: {output_path.name}")
        self._log(f"  {count} LocStr elements written ({len(added)} ADD + {len(edited)} EDIT)")
        self._log("")
        self._log(f"Saved to: {output_path}")
        self._log("")
        self._log("Done!")

    def run(self):
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    app = XMLDiffApp()
    app.run()


if __name__ == "__main__":
    main()
