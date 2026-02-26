#!/usr/bin/env python3
# coding: utf-8
"""
Script No-Voice String Extractor v1.0
======================================
Standalone GUI tool that extracts LocStr entries from languagedata XML files
that belong to SCRIPT type (Dialog/Sequencer) but do NOT have a SoundEventName
attribute. These are text-only SCRIPT strings with no associated voice/audio.

Inputs:
  - EXPORT folder (export__): Build StringID->Category map + voiced StringIDs set
  - LOC folder: languagedata_*.xml files to extract from

Output (per language, in Extraction_Output/novoice_script_{timestamp}/):
  - Excel (.xlsx): StringID, StrOrigin, Str, Correction (empty), Category
  - XML (.xml): Raw LocStr elements under <root>

Usage: python script_novoice_extractor.py
"""

import json
import re as _re
import sys
import time
import logging
import datetime as _dt
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Try lxml first (preserves attribute order, recovery mode), fallback to stdlib
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

# Try xlsxwriter for writing Excel
try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("ScriptNoVoiceExtractor")
logger.setLevel(logging.DEBUG)

# =============================================================================
# CONSTANTS
# =============================================================================

# Detect script directory (supports PyInstaller frozen exe)
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

SETTINGS_FILE = SCRIPT_DIR / "script_novoice_extractor_settings.json"
OUTPUT_DIR = SCRIPT_DIR / "Extraction_Output"

# LocStr tag and attribute variants (case-insensitive matching)
LOCSTR_TAGS = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
STRINGID_ATTRS = ('StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId')
STRORIGIN_ATTRS = ('StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN')
STR_ATTRS = ('Str', 'str', 'STR')

# SoundEventName attribute variants — found on various element types, not just LocStr
SOUNDEVENT_ATTRS = ('SoundEventName', 'soundeventname', 'Soundeventname',
                     'SOUNDEVENTNAME', 'EventName', 'eventname', 'EVENTNAME')

# Categories that qualify as SCRIPT type
SCRIPT_CATEGORIES = {"Sequencer", "Dialog"}


# =============================================================================
# SETTINGS PERSISTENCE
# =============================================================================

def _load_settings() -> dict:
    """Load persisted settings from JSON."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(settings: dict):
    """Save settings to JSON."""
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to save settings: %s", e)


# =============================================================================
# HELPERS
# =============================================================================

def get_attr(elem, attr_variants):
    """Get attribute value from element, trying multiple case variants."""
    for attr_name in attr_variants:
        val = elem.get(attr_name)
        if val is not None:
            return attr_name, val
    return None, None


def extract_language_from_filename(filename: str) -> str:
    """Extract language code from languagedata_*.xml filename."""
    m = _re.match(r'languagedata_(.+)\.xml', filename, _re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return ""


def _xml_escape_attr(value: str) -> str:
    """Escape a string for use in an XML attribute value.
    PRESERVES <br/> tags — the standard newline format in game XML data."""
    # Protect <br/> variants before escaping
    value = _re.sub(r'<br\s*/?>', '\x00BR\x00', value, flags=_re.IGNORECASE)
    value = (
        value
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
    # Restore <br/> tags
    value = value.replace('\x00BR\x00', '<br/>')
    return value


def _read_xml_raw(xml_path: Path) -> Optional[str]:
    """Read XML file with encoding fallback (latin-1 always succeeds)."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return xml_path.read_text(encoding=enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return None  # Unreachable — latin-1 decodes any byte sequence


# Fix bare & that aren't valid XML entities
_bad_amp = _re.compile(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)')
# Fix malformed self-closing tags like </>
_bad_selfclose = _re.compile(r'</>')
# Fix unescaped < inside attribute values, but PRESERVE <br/> tags
_attr_dangerous_lt = _re.compile(r'<(?![bB][rR]\s*/?>)')


def _escape_attr_lt(m):
    """Escape < inside attribute values, preserving <br/> tags."""
    content = m.group(1)
    content = _attr_dangerous_lt.sub('&lt;', content)
    return '="' + content + '"'


# Matches attribute values containing <
_attr_with_lt = _re.compile(r'="([^"]*<[^"]*)"')


def sanitize_xml(raw: str) -> str:
    """Fix common XML issues in game data files before parsing.
    PRESERVES <br/> tags inside attribute values."""
    raw = _bad_selfclose.sub('', raw)
    raw = _attr_with_lt.sub(_escape_attr_lt, raw)
    raw = _bad_amp.sub('&amp;', raw)
    return raw


# =============================================================================
# EXPORT INDEX (combined category + SoundEventName)
# =============================================================================

def build_export_index(
    export_folder: Path, progress_fn=None,
) -> Tuple[Dict[str, str], Set[str]]:
    """
    Single-pass scan of EXPORT folder to build:
      1. category_map: {stringid_lower: category_name} from LocStr elements
      2. voiced_sids: set of stringid_lower that have a SoundEventName attribute

    Scans *.loc.xml files in category subfolders.
    For category mapping: only LocStr elements.
    For voiced detection: ALL elements (SoundEventName can be on any element type).

    Returns:
        (category_map, voiced_sids)
    """
    category_map: Dict[str, str] = {}
    voiced_sids: Set[str] = set()

    if not export_folder.exists():
        return category_map, voiced_sids

    categories = [d for d in export_folder.iterdir() if d.is_dir()]
    total_files = 0

    for cat_folder in categories:
        cat_name = cat_folder.name
        xml_files = list(cat_folder.rglob("*.loc.xml"))
        total_files += len(xml_files)

        if progress_fn:
            progress_fn(f"  Indexing {cat_name} ({len(xml_files)} files)...")

        for xml_file in xml_files:
            try:
                root = _parse_xml_root_file(xml_file)
                if root is None:
                    continue

                # Scan ALL elements for both LocStr mapping AND SoundEventName
                for node in root.iter():
                    tag_local = node.tag if isinstance(node.tag, str) else ""

                    # Category mapping: only LocStr elements
                    if tag_local in LOCSTR_TAGS:
                        _, sid = get_attr(node, STRINGID_ATTRS)
                        if sid and sid.strip():
                            category_map[sid.strip().lower()] = cat_name

                    # Voiced detection: any element with SoundEventName + StringID
                    _, se_val = get_attr(node, SOUNDEVENT_ATTRS)
                    if se_val and se_val.strip():
                        _, sid = get_attr(node, STRINGID_ATTRS)
                        if sid and sid.strip():
                            voiced_sids.add(sid.strip().lower())

            except Exception as e:
                logger.warning("Failed to parse %s: %s", xml_file, e)
                continue

    if progress_fn:
        progress_fn(f"  Scanned {total_files} files across {len(categories)} categories")

    return category_map, voiced_sids


# =============================================================================
# XML PARSING
# =============================================================================

def _parse_xml_root_file(xml_path: Path):
    """Parse XML file, return root element. Uses lxml with XXE protection."""
    try:
        if USING_LXML:
            parser = etree.XMLParser(
                resolve_entities=False, load_dtd=False,
                no_network=True, recover=True,
            )
            tree = etree.parse(str(xml_path), parser)
        else:
            tree = etree.parse(str(xml_path))
        return tree.getroot()
    except Exception as e:
        logger.warning("XML parse error for %s: %s", xml_path, e)
        return None


def _parse_xml_root_string(raw: str):
    """Parse sanitized XML string and return root element."""
    sanitized = sanitize_xml(raw)
    try:
        if USING_LXML:
            parser = etree.XMLParser(
                recover=True, encoding="utf-8",
                resolve_entities=False, load_dtd=False, no_network=True,
            )
            return etree.fromstring(sanitized.encode("utf-8"), parser)
        else:
            return etree.fromstring(sanitized)
    except Exception as e:
        logger.error("XML parse error: %s", e)
        return None


def _iter_locstr(root) -> list:
    """Iterate all LocStr elements (case-insensitive tag matching)."""
    elements = []
    for tag in LOCSTR_TAGS:
        elements.extend(root.iter(tag))
    return elements


# =============================================================================
# EXTRACTION
# =============================================================================

def extract_novoice_script(
    xml_path: Path,
    ci_category: Dict[str, str],
    voiced_sids: Set[str],
    progress_fn=None,
) -> Tuple[List[Dict], int]:
    """
    Extract LocStr entries from a languagedata XML file that are:
      1. In a SCRIPT category (Dialog/Sequencer)
      2. NOT in the voiced_sids set

    Args:
        xml_path: Path to languagedata_*.xml
        ci_category: {stringid_lower: category_name}
        voiced_sids: set of stringid_lower with SoundEventName
        progress_fn: optional callback for progress messages

    Returns:
        (results_list, orphan_count) where orphan_count = entries not in EXPORT index
    """
    t0 = time.time()

    raw = _read_xml_raw(xml_path)
    if raw is None:
        return [], 0

    root = _parse_xml_root_string(raw)
    if root is None:
        logger.error("Empty or invalid XML: %s", xml_path)
        return [], 0

    results = []
    orphans = 0
    elements = _iter_locstr(root)
    total = len(elements)

    if progress_fn:
        progress_fn(f"    Parsing done — {total:,} entries to scan...")

    # Dynamic progress interval: ~20 updates per language, min 1000
    progress_interval = max(1000, total // 20)

    for idx, elem in enumerate(elements):
        attrs = dict(elem.attrib)
        _, sid = get_attr(elem, STRINGID_ATTRS)
        _, so = get_attr(elem, STRORIGIN_ATTRS)
        _, sv = get_attr(elem, STR_ATTRS)

        sid = (sid or "").strip()
        so = (so or "").strip()
        sv = (sv or "").strip()

        if not sid:
            continue

        sid_lower = sid.lower()

        # Check if StringID exists in EXPORT index
        category = ci_category.get(sid_lower)
        if category is None:
            orphans += 1
            continue

        # Must be SCRIPT category
        if category not in SCRIPT_CATEGORIES:
            continue

        # Must NOT be voiced
        if sid_lower in voiced_sids:
            continue

        results.append({
            "string_id": sid,
            "str_origin": so,
            "str_value": sv,
            "category": category,
            "raw_attribs": attrs,
        })

        if progress_fn and idx > 0 and idx % progress_interval == 0:
            elapsed = time.time() - t0
            pct = (idx / total) * 100
            progress_fn(f"    {pct:5.1f}% ({idx:,}/{total:,}) — {len(results):,} hits [{elapsed:.1f}s]")

    return results, orphans


# =============================================================================
# REPORT GENERATION
# =============================================================================

def write_excel_report(entries: List[Dict], output_path: Path) -> bool:
    """Write extraction results to Excel.
    Columns: StringID, StrOrigin, Str, Correction (empty), Category."""
    if not HAS_XLSXWRITER:
        logger.warning("xlsxwriter not available — skipping Excel output")
        return False

    if not entries:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = xlsxwriter.Workbook(str(output_path))
    ws = wb.add_worksheet("No-Voice Script Strings")

    # Formats
    header_fmt = wb.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#4A6741',
        'border': 1, 'text_wrap': True,
    })
    cell_fmt = wb.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})
    correction_fmt = wb.add_format({
        'border': 1, 'text_wrap': True, 'valign': 'top',
        'bg_color': '#FFF9C4',  # Light yellow for user input
    })
    cat_fmt = wb.add_format({
        'border': 1, 'valign': 'top', 'align': 'center',
    })

    headers = ["StringID", "StrOrigin", "Str", "Correction", "Category"]
    for col, h in enumerate(headers):
        ws.write(0, col, h, header_fmt)

    # Sort by StringID ascending
    entries_sorted = sorted(entries, key=lambda e: e["string_id"].lower())

    for row, e in enumerate(entries_sorted, 1):
        ws.write(row, 0, e["string_id"], cell_fmt)
        ws.write(row, 1, e["str_origin"], cell_fmt)
        ws.write(row, 2, e["str_value"], cell_fmt)
        ws.write(row, 3, "", correction_fmt)  # Empty for user to fill in
        ws.write(row, 4, e["category"], cat_fmt)

    # Column widths
    ws.set_column(0, 0, 35)   # StringID
    ws.set_column(1, 1, 45)   # StrOrigin
    ws.set_column(2, 2, 60)   # Str
    ws.set_column(3, 3, 40)   # Correction
    ws.set_column(4, 4, 14)   # Category

    ws.autofilter(0, 0, len(entries_sorted), len(headers) - 1)
    ws.freeze_panes(1, 0)

    wb.close()
    return True


def write_xml_report(entries: List[Dict], output_path: Path) -> int:
    """Write raw LocStr elements under <root> to XML file.
    Sorted by StringID ascending. Preserves <br/> tags.
    Returns number of entries written."""
    if not entries:
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ['<?xml version="1.0" encoding="utf-8"?>', '<root>']

    for e in sorted(entries, key=lambda x: x["string_id"].lower()):
        attribs = e.get("raw_attribs", {})
        if not attribs:
            attribs = {"StringID": e["string_id"], "StrOrigin": e["str_origin"], "Str": e["str_value"]}

        attr_parts = []
        for k, v in attribs.items():
            escaped = _xml_escape_attr(str(v))
            attr_parts.append(f'{k}="{escaped}"')

        lines.append(f'  <LocStr {" ".join(attr_parts)} />')

    lines.append('</root>')
    lines.append('')

    output_path.write_text('\n'.join(lines), encoding='utf-8')
    return len(entries)


# =============================================================================
# GUI APPLICATION
# =============================================================================

class ScriptNoVoiceExtractorApp:
    """GUI for extracting SCRIPT-type LocStr entries without SoundEventName."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Script No-Voice Extractor v1.0")
        self.root.geometry("820x720")
        self.root.resizable(True, True)

        self._build_ui()
        self._load_persisted_settings()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)
        pad = {"padx": 8, "pady": 4}

        # Title
        ttk.Label(
            main, text="Script No-Voice Extractor",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 2))
        ttk.Label(
            main,
            text="Extract SCRIPT-type (Dialog/Sequencer) entries WITHOUT voice (no SoundEventName)",
            font=("Segoe UI", 9),
        ).pack(pady=(0, 10))

        # EXPORT folder
        self.export_var = tk.StringVar()
        f_export = ttk.LabelFrame(main, text="EXPORT Folder (export__ — for category + voice detection)", padding=5)
        f_export.pack(fill="x", **pad)
        exp_row = ttk.Frame(f_export)
        exp_row.pack(fill="x")
        ttk.Entry(exp_row, textvariable=self.export_var, width=60).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            exp_row, text="Browse...",
            command=lambda: self._browse_folder(self.export_var, "EXPORT Folder (export__)"),
        ).pack(side="right", padx=(0, 3))
        ttk.Button(exp_row, text="Save", command=self._save_export_setting).pack(side="right")

        # LOC folder
        self.loc_var = tk.StringVar()
        f_loc = ttk.LabelFrame(main, text="LOC Folder (languagedata_*.xml — source files to extract from)", padding=5)
        f_loc.pack(fill="x", **pad)
        loc_row = ttk.Frame(f_loc)
        loc_row.pack(fill="x")
        ttk.Entry(loc_row, textvariable=self.loc_var, width=60).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            loc_row, text="Browse...",
            command=lambda: self._browse_folder(self.loc_var, "LOC Folder"),
        ).pack(side="right", padx=(0, 3))
        ttk.Button(loc_row, text="Save", command=self._save_loc_setting).pack(side="right")

        # Output info
        out_frame = ttk.LabelFrame(main, text="Output", padding=5)
        out_frame.pack(fill="x", **pad)
        ttk.Label(out_frame, text=f"Output directory: {OUTPUT_DIR}", font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Label(out_frame, text="Per language: NOVOICE_{LANG}.xlsx + NOVOICE_{LANG}.xml", font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Label(out_frame, text="Excel includes empty Correction column for QuickTranslate feedback", font=("Segoe UI", 8)).pack(anchor="w")

        # Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=10)
        self.run_btn = ttk.Button(
            btn_frame, text="EXTRACT NO-VOICE SCRIPT STRINGS", width=40,
            command=self._run,
        )
        self.run_btn.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Log", width=12, command=self._clear_all).pack(side="left", padx=5)

        # Log
        f_log = ttk.LabelFrame(main, text="Log", padding=5)
        f_log.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(f_log, height=18, font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("info", foreground="black")
        self.log.tag_config("success", foreground="green")
        self.log.tag_config("warning", foreground="orange")
        self.log.tag_config("error", foreground="red")
        self.log.tag_config("header", foreground="blue", font=("Consolas", 9, "bold"))

    # -----------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------

    def _log(self, msg: str, tag: str = "info"):
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.root.update_idletasks()

    def _browse_folder(self, var: tk.StringVar, title: str):
        path = filedialog.askdirectory(title=f"Select {title}")
        if path:
            var.set(path)

    def _clear_all(self):
        self.log.delete("1.0", "end")

    def _save_export_setting(self):
        export = self.export_var.get().strip()
        if not export:
            return
        settings = _load_settings()
        settings["export_folder"] = export
        _save_settings(settings)
        messagebox.showinfo("Saved", f"EXPORT folder saved:\n{export}")

    def _save_loc_setting(self):
        loc = self.loc_var.get().strip()
        if not loc:
            return
        settings = _load_settings()
        settings["loc_folder"] = loc
        _save_settings(settings)
        messagebox.showinfo("Saved", f"LOC folder saved:\n{loc}")

    def _load_persisted_settings(self):
        settings = _load_settings()
        export = settings.get("export_folder", "")
        if export:
            self.export_var.set(export)
        loc = settings.get("loc_folder", "")
        if loc:
            self.loc_var.set(loc)

    # -----------------------------------------------------------------
    # MAIN LOGIC
    # -----------------------------------------------------------------

    def _run(self):
        self.log.delete("1.0", "end")

        export = self.export_var.get().strip()
        loc = self.loc_var.get().strip()

        # --- Validate inputs ---
        if not export:
            messagebox.showerror("Error", "Please select the EXPORT folder (export__).")
            return
        export_path = Path(export)
        if not export_path.is_dir():
            messagebox.showerror("Error", f"EXPORT folder not found:\n{export_path}")
            return

        if not loc:
            messagebox.showerror("Error", "Please select the LOC folder (languagedata_*.xml).")
            return
        loc_path = Path(loc)
        if not loc_path.is_dir():
            messagebox.showerror("Error", f"LOC folder not found:\n{loc_path}")
            return

        if not HAS_XLSXWRITER:
            messagebox.showerror("Error", "xlsxwriter is required for Excel output.\npip install xlsxwriter")
            return

        self.run_btn.config(state="disabled")

        try:
            self._execute(export_path, loc_path)
        except Exception as e:
            self._log(f"\nERROR: {e}", "error")
            logger.exception("ScriptNoVoiceExtractor failed")
        finally:
            self.run_btn.config(state="normal")

    def _execute(self, export_path: Path, loc_path: Path):
        self._log("=" * 60, "header")
        self._log("  SCRIPT NO-VOICE EXTRACTOR v1.0", "header")
        self._log("=" * 60, "header")

        # ── Step 1: Build EXPORT index ─────────────────────────────
        self._log(f"\nEXPORT folder: {export_path}", "info")
        self._log("Building category map + voiced StringID set (single pass)...", "info")

        t0 = time.time()
        category_map, voiced_sids = build_export_index(
            export_path, progress_fn=self._log,
        )
        index_elapsed = time.time() - t0

        total_indexed = len(category_map)
        script_count = sum(1 for v in category_map.values() if v in SCRIPT_CATEGORIES)
        voiced_count = len(voiced_sids)
        # Count SCRIPT entries that are NOT voiced
        script_novoice_candidates = sum(
            1 for sid, cat in category_map.items()
            if cat in SCRIPT_CATEGORIES and sid not in voiced_sids
        )

        self._log(f"\n{'─' * 60}", "info")
        self._log("EXPORT INDEX", "header")
        self._log(f"{'─' * 60}", "info")
        self._log(f"  Total StringIDs indexed: {total_indexed:,}", "info")
        self._log(f"  SCRIPT StringIDs (Dialog/Sequencer): {script_count:,}", "info")
        self._log(f"  Voiced StringIDs (with SoundEventName): {voiced_count:,}", "info")
        self._log(f"  -> SCRIPT + No Voice candidates: {script_novoice_candidates:,}", "success")
        self._log(f"  Index time: {index_elapsed:.1f}s", "info")

        if script_novoice_candidates == 0:
            self._log("\nNo SCRIPT entries without voice found. Nothing to extract.", "warning")
            return

        # ── Step 2: Find languagedata files ────────────────────────
        self._log(f"\nLOC folder: {loc_path}", "info")
        lang_files = sorted(loc_path.glob("languagedata_*.xml"))

        if not lang_files:
            self._log("No languagedata_*.xml files found in LOC folder.", "error")
            return

        self._log(f"  Found {len(lang_files)} language file(s):", "info")
        for f in lang_files:
            lang_code = extract_language_from_filename(f.name)
            self._log(f"    {f.name} [{lang_code}]", "info")

        # ── Step 3: Extract per language ───────────────────────────
        self._log(f"\n{'─' * 60}", "info")
        self._log("EXTRACTION", "header")
        self._log(f"{'─' * 60}", "info")

        all_results: Dict[str, List[Dict]] = {}  # {lang: [entries]}
        total_orphans = 0
        num_langs = len(lang_files)

        for lang_idx, xml_file in enumerate(lang_files, 1):
            lang_code = extract_language_from_filename(xml_file.name) or "UNKNOWN"
            self._log(f"\n  [{lang_idx}/{num_langs}] {lang_code} — {xml_file.name}", "info")

            entries, orphans = extract_novoice_script(
                xml_file, category_map, voiced_sids,
                progress_fn=lambda msg: self._log(msg, "info"),
            )
            total_orphans += orphans

            if entries:
                all_results[lang_code] = entries
                self._log(
                    f"  [{lang_code}] {len(entries):,} no-voice SCRIPT entries extracted",
                    "success",
                )
            else:
                self._log(f"  [{lang_code}] No entries matched", "info")

            if orphans > 0:
                self._log(f"  [{lang_code}] {orphans:,} orphaned (in LOC, not in EXPORT) — skipped", "warning")

        # ── Step 4: Summary ────────────────────────────────────────
        self._log(f"\n{'=' * 60}", "header")
        self._log("  SUMMARY", "header")
        self._log(f"{'=' * 60}", "header")

        total_entries = sum(len(v) for v in all_results.values())
        self._log(f"  Total no-voice SCRIPT entries: {total_entries:,}", "success" if total_entries else "info")
        if total_orphans:
            self._log(f"  Orphaned (in LOC, not in EXPORT): {total_orphans:,} — skipped", "warning")

        if not all_results:
            self._log("\nNo no-voice SCRIPT entries found in any language.", "info")
            return

        for lang in sorted(all_results.keys()):
            entries = all_results[lang]
            cat_counts: Dict[str, int] = {}
            for e in entries:
                cat_counts[e["category"]] = cat_counts.get(e["category"], 0) + 1
            cat_str = ", ".join(f"{c}: {n:,}" for c, n in sorted(cat_counts.items()))
            self._log(f"  {lang}: {len(entries):,} entries ({cat_str})", "info")

        # ── Step 5: Write reports ──────────────────────────────────
        self._log(f"\n{'─' * 60}", "info")
        self._log("WRITING OUTPUT...", "header")
        self._log(f"{'─' * 60}", "info")

        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_DIR / f"novoice_script_{timestamp}"

        total_xlsx = 0
        total_xml = 0

        for lang in sorted(all_results.keys()):
            entries = all_results[lang]

            # Excel output
            xlsx_path = output_dir / f"NOVOICE_{lang}.xlsx"
            if write_excel_report(entries, xlsx_path):
                total_xlsx += 1
                self._log(f"  {xlsx_path.name}: {len(entries):,} entries", "success")

            # XML output
            xml_path = output_dir / f"NOVOICE_{lang}.xml"
            xml_count = write_xml_report(entries, xml_path)
            if xml_count:
                total_xml += 1
                self._log(f"  {xml_path.name}: {xml_count:,} entries", "success")

        self._log(f"\n{'=' * 60}", "header")
        self._log("  DONE", "header")
        self._log(f"{'=' * 60}", "header")
        self._log(f"  Output: {output_dir}", "success")
        self._log(f"  Excel files: {total_xlsx}", "info")
        self._log(f"  XML files:   {total_xml}", "info")
        self._log(f"  Total entries: {total_entries:,} across {len(all_results)} language(s)", "info")

    def run(self):
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    app = ScriptNoVoiceExtractorApp()
    app.run()


if __name__ == "__main__":
    main()
