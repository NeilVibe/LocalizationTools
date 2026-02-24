#!/usr/bin/env python3
# coding: utf-8
"""
XML Diff Extractor v2.0
========================
Two modes:

Tab 1 - DIFF:
  Compare SOURCE (old) vs TARGET (new), extract ADD/EDIT LocStr elements.

Tab 2 - REVERT:
  Undo changes that occurred between BEFORE and AFTER in your CURRENT file.
  - ADDs (new in AFTER) -> REMOVED from CURRENT
  - EDITs (changed in AFTER) -> RESTORED to BEFORE version in CURRENT
  Everything else in CURRENT stays untouched.

Usage: python xml_diff_extractor.py
"""

import os
import re as _re
import sys
import logging
import datetime as _dt
from pathlib import Path
from typing import Dict, List, Tuple, Optional
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
# XML SANITIZATION
# =============================================================================

# Fix unescaped < inside attribute values (e.g., <br/> in Desc attributes)
_attr_unescaped_lt = _re.compile(r'="([^"]*<[^"]*)"')
# Fix bare & that aren't valid XML entities
_bad_amp = _re.compile(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)')
# Fix malformed self-closing tags like </>
_bad_selfclose = _re.compile(r'</>')


def sanitize_xml(raw: str) -> str:
    """
    Fix common XML issues in game data files before parsing:
    - Unescaped <br/>, <PAColor>, etc. inside attribute values
    - Bare & characters that aren't valid entities
    - Malformed </> closing tags
    """
    raw = _bad_selfclose.sub('', raw)
    raw = _attr_unescaped_lt.sub(
        lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw
    )
    raw = _bad_amp.sub('&amp;', raw)
    return raw


# =============================================================================
# XML PARSING
# =============================================================================

def _read_xml_raw(xml_path: Path) -> Optional[str]:
    """Read XML file with encoding fallback."""
    try:
        return xml_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return xml_path.read_text(encoding="utf-8-sig")
        except Exception as e:
            logger.error("Failed to read %s: %s", xml_path, e)
            return None


def _parse_root(raw: str):
    """Parse sanitized XML string and return root element."""
    sanitized = sanitize_xml(raw)
    try:
        if USING_LXML:
            parser = etree.XMLParser(recover=True, encoding="utf-8")
            return etree.fromstring(sanitized.encode("utf-8"), parser)
        else:
            return etree.fromstring(sanitized)
    except Exception as e:
        logger.error("XML parse error: %s", e)
        return None


def parse_locstr_elements(xml_path: Path) -> Tuple[Dict[str, dict], int]:
    """
    Parse an XML file and return a dict of StringId -> {attr: value}.

    Returns:
        (locstr_map, total_count)
    """
    locstr_map: Dict[str, dict] = OrderedDict()
    total = 0

    raw = _read_xml_raw(xml_path)
    if raw is None:
        return locstr_map, 0

    root = _parse_root(raw)
    if root is None:
        logger.error("Empty or invalid XML: %s", xml_path)
        return locstr_map, 0

    for elem in root.iter("LocStr"):
        total += 1
        string_id = elem.get("StringId") or elem.get("StringID") or ""
        if not string_id:
            continue
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
            added.append((string_id, target_attrs))
        else:
            source_attrs = source_map[string_id]
            if source_attrs != target_attrs:
                edited.append((string_id, source_attrs, target_attrs))

    return added, edited


# =============================================================================
# XML OUTPUT
# =============================================================================

def _xml_escape_attr(value: str) -> str:
    """Escape a string for use in an XML attribute value (double-quoted)."""
    return (
        value
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def _build_locstr_line(attrs: dict, extra_attr: str = "") -> str:
    """Build a single <LocStr .../> line preserving all original attributes."""
    parts = ['<LocStr']
    if extra_attr:
        parts.append(f' {extra_attr}')
    for key, value in attrs.items():
        safe_val = _xml_escape_attr(value)
        parts.append(f' {key}="{safe_val}"')
    parts.append(' />')
    return ''.join(parts)


def write_diff_xml(
    added: List[Tuple[str, dict]],
    edited: List[Tuple[str, dict, dict]],
    output_path: Path,
) -> int:
    """Write diff results as XML. Returns total elements written."""
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<LanguageData>',
    ]
    count = 0

    if added:
        lines.append('  <!-- ===== ADDED ===== -->')
        for string_id, attrs in added:
            line = _build_locstr_line(attrs, 'diff_type="ADD"')
            lines.append(f'  {line}')
            count += 1

    if edited:
        lines.append('  <!-- ===== EDITED ===== -->')
        for string_id, source_attrs, target_attrs in edited:
            line = _build_locstr_line(target_attrs, 'diff_type="EDIT"')
            lines.append(f'  {line}')
            count += 1

    lines.append('</LanguageData>')
    lines.append('')
    output_path.write_text('\n'.join(lines), encoding='utf-8')
    return count


def revert_current_inplace(
    current_path: Path,
    added_sids: set,
    edit_reverts: Dict[str, dict],
) -> Tuple[int, int]:
    """
    Modify CURRENT XML file in-place:
    - REMOVE LocStr elements whose StringId was added between BEFORE/AFTER
    - REVERT Str attribute to BEFORE value for edited StringIds
    - Preserves exact file structure, formatting, root element, etc.

    Returns:
        (removed_count, reverted_count)
    """
    import os
    import stat

    # Read raw file
    raw = _read_xml_raw(current_path)
    if raw is None:
        raise RuntimeError(f"Cannot read {current_path}")

    sanitized = sanitize_xml(raw)

    # Parse into tree (NOT just root — we need tree.write() later)
    if USING_LXML:
        parser = etree.XMLParser(recover=True, encoding="utf-8")
        tree = etree.ElementTree(etree.fromstring(sanitized.encode("utf-8"), parser))
    else:
        tree = etree.ElementTree(etree.fromstring(sanitized))

    root = tree.getroot()
    if root is None:
        raise RuntimeError(f"Failed to parse {current_path}")

    removed = 0
    reverted = 0
    to_remove = []

    for elem in root.iter("LocStr"):
        string_id = elem.get("StringId") or elem.get("StringID") or ""
        if not string_id:
            continue

        # REMOVE: this StringId was added between BEFORE→AFTER
        if string_id in added_sids:
            to_remove.append(elem)
            removed += 1
            continue

        # REVERT: only overwrite Str with BEFORE value
        if string_id in edit_reverts:
            before_attrs = edit_reverts[string_id]
            if "Str" in before_attrs:
                elem.set("Str", before_attrs["Str"])
            reverted += 1

    # Remove ADD elements from tree
    for elem in to_remove:
        parent = root
        # Find parent of this element to remove it
        if USING_LXML:
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
        else:
            # stdlib: need to find parent by iterating
            _remove_element_stdlib(root, elem)

    # Make file writable if read-only
    try:
        current_mode = os.stat(current_path).st_mode
        if not current_mode & stat.S_IWRITE:
            os.chmod(current_path, current_mode | stat.S_IWRITE)
    except Exception:
        pass

    # Write back — no xml_declaration to preserve original structure
    if USING_LXML:
        tree.write(str(current_path), encoding="utf-8", xml_declaration=False, pretty_print=True)
    else:
        tree.write(str(current_path), encoding="utf-8", xml_declaration=False)

    return removed, reverted


def _remove_element_stdlib(root, target):
    """Remove an element from the tree (stdlib ElementTree has no getparent)."""
    for parent in root.iter():
        for child in list(parent):
            if child is target:
                parent.remove(child)
                return


# =============================================================================
# GUI
# =============================================================================

class XMLDiffApp:
    """Tabbed GUI: Diff mode + Revert mode."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XML Diff Extractor v2.0")
        self.root.geometry("720x600")
        self.root.resizable(True, True)

        self._build_ui()

    def _build_ui(self):
        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 1: Diff
        self._build_diff_tab()

        # Tab 2: Revert
        self._build_revert_tab()

    # -----------------------------------------------------------------
    # TAB 1: DIFF
    # -----------------------------------------------------------------

    def _build_diff_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  DIFF  ")
        pad = {"padx": 8, "pady": 4}

        ttk.Label(
            tab, text="Compare two XML files and extract ADD/EDIT LocStr",
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(10, 5))

        # Source
        self.diff_source = tk.StringVar()
        f1 = ttk.LabelFrame(tab, text="SOURCE (old / before)", padding=5)
        f1.pack(fill="x", **pad)
        ttk.Entry(f1, textvariable=self.diff_source, width=70).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f1, text="Browse...", command=lambda: self._browse(self.diff_source, "SOURCE XML")).pack(side="right")

        # Target
        self.diff_target = tk.StringVar()
        f2 = ttk.LabelFrame(tab, text="TARGET (new / after)", padding=5)
        f2.pack(fill="x", **pad)
        ttk.Entry(f2, textvariable=self.diff_target, width=70).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f2, text="Browse...", command=lambda: self._browse(self.diff_target, "TARGET XML")).pack(side="right")

        # Run
        ttk.Button(tab, text="Run Diff", command=self._run_diff).pack(pady=10)

        # Log
        f_log = ttk.LabelFrame(tab, text="Output", padding=5)
        f_log.pack(fill="both", expand=True, **pad)
        self.diff_log = scrolledtext.ScrolledText(f_log, height=14, font=("Consolas", 9), wrap="word")
        self.diff_log.pack(fill="both", expand=True)

    # -----------------------------------------------------------------
    # TAB 2: REVERT
    # -----------------------------------------------------------------

    def _build_revert_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  REVERT  ")
        pad = {"padx": 8, "pady": 4}

        ttk.Label(
            tab, text="Revert changes that occurred between BEFORE/AFTER in CURRENT",
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(10, 2))

        ttk.Label(
            tab,
            text="ADDs (new in AFTER) are REMOVED.  EDITs: Str value RESTORED to BEFORE version.",
            font=("Segoe UI", 8),
        ).pack(pady=(0, 8))

        # Before
        self.rev_before = tk.StringVar()
        f1 = ttk.LabelFrame(tab, text="BEFORE (old version - the good one)", padding=5)
        f1.pack(fill="x", **pad)
        ttk.Entry(f1, textvariable=self.rev_before, width=70).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f1, text="Browse...", command=lambda: self._browse(self.rev_before, "BEFORE XML")).pack(side="right")

        # After
        self.rev_after = tk.StringVar()
        f2 = ttk.LabelFrame(tab, text="AFTER (new version - has unwanted changes)", padding=5)
        f2.pack(fill="x", **pad)
        ttk.Entry(f2, textvariable=self.rev_after, width=70).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f2, text="Browse...", command=lambda: self._browse(self.rev_after, "AFTER XML")).pack(side="right")

        # Current
        self.rev_current = tk.StringVar()
        f3 = ttk.LabelFrame(tab, text="CURRENT (your working file to fix)", padding=5)
        f3.pack(fill="x", **pad)
        ttk.Entry(f3, textvariable=self.rev_current, width=70).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f3, text="Browse...", command=lambda: self._browse(self.rev_current, "CURRENT XML")).pack(side="right")

        # Run
        ttk.Button(tab, text="Run Revert", command=self._run_revert).pack(pady=10)

        # Log
        f_log = ttk.LabelFrame(tab, text="Output", padding=5)
        f_log.pack(fill="both", expand=True, **pad)
        self.revert_log = scrolledtext.ScrolledText(f_log, height=10, font=("Consolas", 9), wrap="word")
        self.revert_log.pack(fill="both", expand=True)

    # -----------------------------------------------------------------
    # SHARED HELPERS
    # -----------------------------------------------------------------

    def _browse(self, var: tk.StringVar, title: str):
        path = filedialog.askopenfilename(
            title=f"Select {title}",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            var.set(path)

    def _log_to(self, widget, msg: str):
        widget.insert("end", msg + "\n")
        widget.see("end")
        self.root.update_idletasks()

    # -----------------------------------------------------------------
    # DIFF LOGIC
    # -----------------------------------------------------------------

    def _run_diff(self):
        log = self.diff_log
        log.delete("1.0", "end")
        _log = lambda msg: self._log_to(log, msg)

        src = self.diff_source.get().strip()
        tgt = self.diff_target.get().strip()

        if not src or not tgt:
            messagebox.showerror("Error", "Please select both SOURCE and TARGET XML files.")
            return

        src_path, tgt_path = Path(src), Path(tgt)
        if not src_path.exists():
            messagebox.showerror("Error", f"SOURCE not found:\n{src_path}")
            return
        if not tgt_path.exists():
            messagebox.showerror("Error", f"TARGET not found:\n{tgt_path}")
            return

        _log(f"SOURCE: {src_path.name}")
        _log(f"TARGET: {tgt_path.name}")
        _log("")

        _log("Parsing SOURCE...")
        source_map, source_total = parse_locstr_elements(src_path)
        _log(f"  {source_total} LocStr ({len(source_map)} unique StringIds)")

        _log("Parsing TARGET...")
        target_map, target_total = parse_locstr_elements(tgt_path)
        _log(f"  {target_total} LocStr ({len(target_map)} unique StringIds)")
        _log("")

        _log("Comparing...")
        added, edited = compare_xml(source_map, target_map)
        deleted_count = sum(1 for sid in source_map if sid not in target_map)

        _log(f"  ADD:    {len(added)}")
        _log(f"  EDIT:   {len(edited)}")
        _log(f"  DELETE: {deleted_count} (not extracted)")
        _log("")

        if not added and not edited:
            _log("No ADD/EDIT differences found.")
            return

        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = tgt_path.parent / f"DIFF_{tgt_path.stem}_{timestamp}.xml"
        count = write_diff_xml(added, edited, output_path)

        _log(f"Output: {output_path.name}")
        _log(f"  {count} LocStr ({len(added)} ADD + {len(edited)} EDIT)")
        _log(f"Saved to: {output_path}")
        _log("")
        _log("Done!")

    # -----------------------------------------------------------------
    # REVERT LOGIC
    # -----------------------------------------------------------------

    def _run_revert(self):
        log = self.revert_log
        log.delete("1.0", "end")
        _log = lambda msg: self._log_to(log, msg)

        before = self.rev_before.get().strip()
        after = self.rev_after.get().strip()
        current = self.rev_current.get().strip()

        if not before or not after or not current:
            messagebox.showerror("Error", "Please select all three XML files.")
            return

        before_path, after_path, current_path = Path(before), Path(after), Path(current)
        for label, p in [("BEFORE", before_path), ("AFTER", after_path), ("CURRENT", current_path)]:
            if not p.exists():
                messagebox.showerror("Error", f"{label} not found:\n{p}")
                return

        _log(f"BEFORE:  {before_path.name}")
        _log(f"AFTER:   {after_path.name}")
        _log(f"CURRENT: {current_path.name}")
        _log("")

        # Step 1: Parse all three
        _log("[1/4] Parsing BEFORE...")
        before_map, before_total = parse_locstr_elements(before_path)
        _log(f"  {before_total} LocStr ({len(before_map)} unique StringIds)")

        _log("[2/4] Parsing AFTER...")
        after_map, after_total = parse_locstr_elements(after_path)
        _log(f"  {after_total} LocStr ({len(after_map)} unique StringIds)")

        _log("[3/4] Parsing CURRENT...")
        current_map, current_total = parse_locstr_elements(current_path)
        _log(f"  {current_total} LocStr ({len(current_map)} unique StringIds)")
        _log("")

        # Step 2: Diff BEFORE vs AFTER
        _log("Analyzing changes BEFORE -> AFTER...")
        added, edited = compare_xml(before_map, after_map)

        # ADDs: StringIds that appeared in AFTER but not BEFORE -> REMOVE from CURRENT
        added_sids = {sid for sid, _ in added}

        # EDITs: StringIds that changed between BEFORE/AFTER -> RESTORE to BEFORE version
        edit_reverts: Dict[str, dict] = {}
        for sid, before_attrs, after_attrs in edited:
            edit_reverts[sid] = before_attrs

        # Count how many actually exist in CURRENT (some may not)
        adds_in_current = sum(1 for sid in added_sids if sid in current_map)
        edits_in_current = sum(1 for sid in edit_reverts if sid in current_map)

        _log(f"  Changes found: {len(added)} ADDs, {len(edited)} EDITs")
        _log(f"  Applicable to CURRENT: {adds_in_current} removals, {edits_in_current} reverts")
        _log("")

        if adds_in_current == 0 and edits_in_current == 0:
            _log("Nothing to revert! CURRENT has none of the BEFORE->AFTER changes.")
            return

        # Step 3: Apply reverts IN-PLACE
        _log("[4/4] Reverting CURRENT in-place...")

        try:
            removed, reverted = revert_current_inplace(
                current_path, added_sids, edit_reverts,
            )
        except Exception as exc:
            _log(f"  ERROR: {exc}")
            messagebox.showerror("Error", f"Failed to revert:\n{exc}")
            return

        _log(f"  Removed (undid ADDs): {removed}")
        _log(f"  Reverted Str (undid EDITs): {reverted}")
        _log("")
        _log(f"CURRENT file updated: {current_path.name}")
        _log("")
        _log("Done! CURRENT file has been modified in-place.")

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
