#!/usr/bin/env python3
# coding: utf-8
"""
XML Diff Extractor v4.0
========================
Three tabs:

Tab 1 - DIFF:
  Compare SOURCE (old) vs TARGET (new), extract ADD/EDIT LocStr elements.

  Comparison Modes:
    - Full (all attributes): Compare all attributes by StringID key (v2.0 default)
    - StrOrigin + StringID: Composite key -- extract entries whose tuple not in SOURCE
    - StrOrigin + StringID + Str: Triple key -- extract entries whose triple not in SOURCE
    - StringID + Str: Pair key -- extract entries whose pair not in SOURCE

  Category Filter:
    - All (no filter): No filtering, extract all diffs
    - SCRIPT only: Only Dialog/Sequencer entries (requires export folder)
    - NON-SCRIPT only: Only non-Dialog/non-Sequencer entries (requires export folder)

Tab 2 - DIFF FOLDER:
  Compare SOURCE folder vs TARGET folder, auto-matching files by language suffix.
  Language suffixes validated against LOC folder (languagedata_*.xml).
  Same comparison modes and category filters as Tab 1.
  Output: auto-created DIFF_FOLDER_{timestamp}/ with one XML per language.

Tab 3 - REVERT:
  Undo changes that occurred between BEFORE and AFTER in your CURRENT file.
  - ADDs (new in AFTER) -> REMOVED from CURRENT
  - EDITs (changed in AFTER) -> RESTORED to BEFORE version in CURRENT
  Everything else in CURRENT stays untouched.

Usage: python xml_diff_extractor.py
"""

import json
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
# CONSTANTS
# =============================================================================

# LocStr tag and attribute variants (case-insensitive matching)
LOCSTR_TAGS = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
STRINGID_ATTRS = ('StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId')
STRORIGIN_ATTRS = ('StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN')
STR_ATTRS = ('Str', 'str', 'STR')

# Script categories (Dialog and Sequencer)
SCRIPT_CATEGORIES = {"Sequencer", "Dialog"}

# Comparison modes for DIFF tab
COMPARE_MODES = [
    "Full (all attributes)",
    "StrOrigin + StringID",
    "StrOrigin + StringID + Str",
    "StringID + Str",
]

# Category filters for DIFF tab
CATEGORY_FILTERS = [
    "All (no filter)",
    "SCRIPT only",
    "NON-SCRIPT only",
]

# =============================================================================
# SETTINGS PERSISTENCE
# =============================================================================

# Detect script directory (supports PyInstaller frozen exe)
if getattr(sys, 'frozen', False):
    _SCRIPT_DIR = Path(sys.executable).parent
else:
    _SCRIPT_DIR = Path(__file__).parent

_SETTINGS_FILE = _SCRIPT_DIR / "xml_diff_settings.json"


def _load_settings() -> dict:
    """Load persisted settings from JSON."""
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(settings: dict):
    """Save settings to JSON."""
    try:
        _SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to save settings: %s", e)


# =============================================================================
# LANGUAGE DETECTION (standalone — no QuickTranslate dependency)
# =============================================================================

def discover_valid_codes(loc_folder: Path) -> set:
    """
    Discover valid language codes from LOC folder by scanning languagedata_*.xml.

    Returns:
        Set of uppercase language codes (e.g. {'ENG', 'FRE', 'GER', 'ZHO-CN'})
    """
    codes = set()
    if loc_folder.exists() and loc_folder.is_dir():
        for xml_file in loc_folder.glob("languagedata_*.xml"):
            match = _re.match(r'languagedata_(.+)\.xml', xml_file.name, _re.IGNORECASE)
            if match:
                codes.add(match.group(1).upper())
    return codes


def extract_language_suffix(name: str, valid_codes: set) -> Optional[str]:
    """
    Extract language code from a folder or file name.

    Patterns (same as QuickTranslate source_scanner):
    - FRE                   -> FRE (standalone code)
    - ZHO-CN                -> ZHO-CN (standalone hyphenated)
    - name_FRE              -> FRE (underscore-prefixed)
    - name_ZHO_CN           -> ZHO-CN (underscore-separated hyphenated)
    - languagedata_ger.xml  -> GER (from stem, case-insensitive)

    NOT matched: LaLaFRElala (no substring detection).
    """
    if not name:
        return None

    # Remove extension if present
    if "." in name:
        name = Path(name).stem

    parts = name.split("_")

    # Standalone code: entire name is a valid code
    if len(parts) == 1:
        upper = name.upper()
        return upper if upper in valid_codes else None

    # Underscore-separated: check last parts for hyphenated codes (ZHO-CN)
    if len(parts) >= 2:
        hyphenated = f"{parts[-2]}-{parts[-1]}".upper()
        if hyphenated in valid_codes:
            return hyphenated

    # Single last part (FRE, GER, etc.)
    suffix = parts[-1].upper()
    return suffix if suffix in valid_codes else None


def scan_folder_for_language_xmls(
    folder: Path, valid_codes: set,
) -> Dict[str, Path]:
    """
    Scan a folder for XML files with language suffixes.

    Detects language from:
    - languagedata_ENG.xml pattern
    - Language-suffixed filenames (hotfix_FRE.xml, GER.xml)
    - Language-named subfolders containing XML files

    Returns:
        {lang_code: Path} — one file per language (first match wins)
    """
    result: Dict[str, Path] = {}

    if not folder.exists() or not folder.is_dir():
        return result

    for child in sorted(folder.iterdir()):
        if child.is_file() and child.suffix.lower() == ".xml":
            lang = extract_language_suffix(child.stem, valid_codes)

            # Also handle standard languagedata_XXX.xml pattern
            if not lang and child.stem.lower().startswith("languagedata_"):
                suffix_part = child.stem[13:]  # After "languagedata_"
                upper = suffix_part.upper()
                if upper in valid_codes:
                    lang = upper

            if lang and lang not in result:
                result[lang] = child

        elif child.is_dir():
            # Language-named folder: scan for XML inside
            lang = extract_language_suffix(child.name, valid_codes)
            if lang and lang not in result:
                # Pick first XML file inside
                xml_files = sorted(child.glob("*.xml"))
                if xml_files:
                    result[lang] = xml_files[0]

    return result


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
# HELPERS
# =============================================================================

def get_attr_value(attrs: dict, attr_variants: tuple) -> str:
    """Get attribute value from dict, trying multiple case variants."""
    for attr_name in attr_variants:
        if attr_name in attrs:
            return attrs[attr_name]
    return ""


def _passes_category_filter(
    string_id: str,
    ci_category: Dict[str, str],
    filter_mode: str,
) -> bool:
    """Check if a StringID passes the category filter."""
    if filter_mode == CATEGORY_FILTERS[0]:  # All (no filter)
        return True
    category = ci_category.get(string_id.lower(), "")
    if filter_mode == CATEGORY_FILTERS[1]:  # SCRIPT only
        return category in SCRIPT_CATEGORIES
    if filter_mode == CATEGORY_FILTERS[2]:  # NON-SCRIPT only
        return bool(category) and category not in SCRIPT_CATEGORIES
    return True


def filter_entries_by_category(
    entries: List[dict],
    ci_category: Dict[str, str],
    filter_mode: str,
) -> List[dict]:
    """Filter a list of LocStr attr dicts by category."""
    if filter_mode == CATEGORY_FILTERS[0]:  # All
        return entries
    return [
        attrs for attrs in entries
        if _passes_category_filter(
            get_attr_value(attrs, STRINGID_ATTRS), ci_category, filter_mode,
        )
    ]


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


def parse_locstr_entry_list(xml_path: Path) -> Tuple[List[dict], int]:
    """
    Parse an XML file and return a list of all LocStr attribute dicts.
    Unlike parse_locstr_elements, preserves duplicates (multiple entries
    with the same StringID but different StrOrigin).

    Returns:
        (entries, total_count) where entries is [{attr: value}, ...]
    """
    entries: List[dict] = []
    total = 0

    raw = _read_xml_raw(xml_path)
    if raw is None:
        return entries, 0

    root = _parse_root(raw)
    if root is None:
        logger.error("Empty or invalid XML: %s", xml_path)
        return entries, 0

    for elem in root.iter("LocStr"):
        total += 1
        attrs = dict(elem.attrib)
        sid = get_attr_value(attrs, STRINGID_ATTRS)
        if not sid:
            continue
        entries.append(attrs)

    return entries, total


# =============================================================================
# COMPARISON
# =============================================================================

def compare_xml(
    source_map: Dict[str, dict],
    target_map: Dict[str, dict],
) -> Tuple[List[Tuple[str, dict]], List[Tuple[str, dict, dict]]]:
    """
    Compare source and target LocStr maps (Full mode — by StringID key).

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


def _build_key(attrs: dict, mode: str) -> tuple:
    """Build a comparison key tuple based on the comparison mode."""
    sid = get_attr_value(attrs, STRINGID_ATTRS)
    if mode == COMPARE_MODES[1]:  # StrOrigin + StringID
        so = get_attr_value(attrs, STRORIGIN_ATTRS)
        return (so, sid)
    elif mode == COMPARE_MODES[2]:  # StrOrigin + StringID + Str
        so = get_attr_value(attrs, STRORIGIN_ATTRS)
        sv = get_attr_value(attrs, STR_ATTRS)
        return (so, sid, sv)
    elif mode == COMPARE_MODES[3]:  # StringID + Str
        sv = get_attr_value(attrs, STR_ATTRS)
        return (sid, sv)
    return (sid,)  # fallback


def compare_xml_by_keyset(
    source_entries: List[dict],
    target_entries: List[dict],
    mode: str,
) -> Tuple[List[Tuple[str, dict]], List[Tuple[str, dict, dict]]]:
    """
    Compare SOURCE and TARGET using composite key tuples.

    Returns same format as compare_xml() for compatibility:
        (added, edited)
        - added:  [(string_id, target_attrs), ...] -- StringID not in SOURCE
        - edited: [(string_id, source_attrs, target_attrs), ...] -- StringID exists but key differs
    """
    # Build source key set and StringID lookup
    source_keys: set = set()
    source_sids: set = set()
    source_sid_attrs: Dict[str, dict] = {}  # sid -> attrs (last wins)

    for attrs in source_entries:
        key = _build_key(attrs, mode)
        source_keys.add(key)
        sid = get_attr_value(attrs, STRINGID_ATTRS)
        source_sids.add(sid)
        source_sid_attrs[sid] = attrs

    added: List[Tuple[str, dict]] = []
    edited: List[Tuple[str, dict, dict]] = []
    seen_keys: set = set()

    for attrs in target_entries:
        key = _build_key(attrs, mode)
        if key in source_keys:
            continue
        # Deduplicate: skip if we already extracted this exact key
        if key in seen_keys:
            continue
        seen_keys.add(key)

        sid = get_attr_value(attrs, STRINGID_ATTRS)
        if sid in source_sids:
            edited.append((sid, source_sid_attrs.get(sid, {}), attrs))
        else:
            added.append((sid, attrs))

    return added, edited


# =============================================================================
# CATEGORY MAPPING (from export folder)
# =============================================================================

def build_stringid_to_category(
    export_folder: Path,
    progress_fn=None,
) -> Dict[str, str]:
    """
    Build StringID -> Category mapping from an export__ folder.

    The export folder contains category subfolders (Dialog, Sequencer, Item, etc.),
    each with .loc.xml files containing LocStr elements.

    Returns:
        {stringid: category_name}
    """
    category_map: Dict[str, str] = {}
    if not export_folder.exists():
        return category_map

    categories = [d for d in export_folder.iterdir() if d.is_dir()]

    for cat_folder in categories:
        cat_name = cat_folder.name
        xml_files = list(cat_folder.rglob("*.loc.xml"))

        if progress_fn:
            progress_fn(f"  Indexing {cat_name} ({len(xml_files)} files)...")

        for xml_file in xml_files:
            try:
                raw = _read_xml_raw(xml_file)
                if raw is None:
                    continue
                root = _parse_root(raw)
                if root is None:
                    continue
                for tag in LOCSTR_TAGS:
                    for elem in root.iter(tag):
                        sid = get_attr_value(dict(elem.attrib), STRINGID_ATTRS)
                        if sid and sid.strip():
                            category_map[sid.strip()] = cat_name
            except Exception as e:
                logger.warning("Failed to parse %s: %s", xml_file, e)
                continue

    return category_map


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
    """Write diff results as XML. Returns total elements written.

    Output is raw LocStr elements under <LanguageData> root -- no XML
    declaration, no extra attributes, no comments.  Mirrors the structure
    of the original game XML files.
    """
    lines = ['<root>']
    count = 0

    for _string_id, attrs in added:
        lines.append(f'  {_build_locstr_line(attrs)}')
        count += 1

    for _string_id, _source_attrs, target_attrs in edited:
        lines.append(f'  {_build_locstr_line(target_attrs)}')
        count += 1

    lines.append('</root>')
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

    # Parse into tree (NOT just root -- we need tree.write() later)
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

        # REMOVE: this StringId was added between BEFORE->AFTER
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

    # Write back -- no xml_declaration to preserve original structure
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
        self.root.title("XML Diff Extractor v4.0")
        self.root.geometry("760x680")
        self.root.resizable(True, True)

        self._build_ui()

    def _build_ui(self):
        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 1: Diff (file)
        self._build_diff_tab()

        # Tab 2: Diff Folder
        self._build_diff_folder_tab()

        # Tab 3: Revert
        self._build_revert_tab()

        # Load persisted settings
        self._load_persisted_settings()

    # -----------------------------------------------------------------
    # TAB 1: DIFF
    # -----------------------------------------------------------------

    def _build_diff_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  DIFF (file)  ")
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

        # Options frame (Comparison Mode + Category Filter)
        opts = ttk.LabelFrame(tab, text="Options", padding=5)
        opts.pack(fill="x", **pad)

        # Comparison Mode
        mode_row = ttk.Frame(opts)
        mode_row.pack(fill="x", pady=2)
        ttk.Label(mode_row, text="Comparison Mode:", width=18, anchor="w").pack(side="left")
        self.compare_mode = tk.StringVar(value=COMPARE_MODES[0])
        mode_cb = ttk.Combobox(
            mode_row, textvariable=self.compare_mode,
            values=COMPARE_MODES, state="readonly", width=35,
        )
        mode_cb.pack(side="left", padx=(5, 0))

        # Category Filter
        cat_row = ttk.Frame(opts)
        cat_row.pack(fill="x", pady=2)
        ttk.Label(cat_row, text="Category Filter:", width=18, anchor="w").pack(side="left")
        self.cat_filter = tk.StringVar(value=CATEGORY_FILTERS[0])
        cat_cb = ttk.Combobox(
            cat_row, textvariable=self.cat_filter,
            values=CATEGORY_FILTERS, state="readonly", width=35,
        )
        cat_cb.pack(side="left", padx=(5, 0))
        cat_cb.bind("<<ComboboxSelected>>", self._on_cat_filter_change)

        # Export Folder (hidden by default, shown when category filter != All)
        self.diff_export = tk.StringVar()
        self.diff_export_frame = ttk.LabelFrame(
            tab, text="Export Folder (export__ -- for SCRIPT category detection)", padding=5,
        )
        # NOT packed initially -- shown by _on_cat_filter_change
        exp_row = ttk.Frame(self.diff_export_frame)
        exp_row.pack(fill="x")
        ttk.Entry(exp_row, textvariable=self.diff_export, width=70).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            exp_row, text="Browse...",
            command=lambda: self._browse_folder(self.diff_export, "Export Folder (export__)"),
        ).pack(side="right")

        # Run button (save reference for pack ordering)
        self.diff_run_btn = ttk.Button(tab, text="Run Diff", command=self._run_diff)
        self.diff_run_btn.pack(pady=10)

        # Log
        f_log = ttk.LabelFrame(tab, text="Output", padding=5)
        f_log.pack(fill="both", expand=True, **pad)
        self.diff_log = scrolledtext.ScrolledText(f_log, height=14, font=("Consolas", 9), wrap="word")
        self.diff_log.pack(fill="both", expand=True)

    def _on_cat_filter_change(self, _event=None):
        """Show/hide the export folder field based on category filter selection."""
        if self.cat_filter.get() == CATEGORY_FILTERS[0]:  # All (no filter)
            self.diff_export_frame.pack_forget()
        else:
            # Pack the export frame just before the Run button
            self.diff_export_frame.pack(fill="x", padx=8, pady=4, before=self.diff_run_btn)

    # -----------------------------------------------------------------
    # TAB 2: DIFF FOLDER
    # -----------------------------------------------------------------

    def _build_diff_folder_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  DIFF FOLDER  ")
        pad = {"padx": 8, "pady": 4}

        ttk.Label(
            tab,
            text="Compare SOURCE folder vs TARGET folder (auto-match by language)",
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(10, 5))

        # LOC folder (for language suffix validation)
        self.folder_loc = tk.StringVar()
        f_loc = ttk.LabelFrame(tab, text="LOC Folder (languagedata_*.xml — for language detection)", padding=5)
        f_loc.pack(fill="x", **pad)
        loc_row = ttk.Frame(f_loc)
        loc_row.pack(fill="x")
        ttk.Entry(loc_row, textvariable=self.folder_loc, width=60).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            loc_row, text="Browse...",
            command=lambda: self._browse_folder(self.folder_loc, "LOC Folder"),
        ).pack(side="right", padx=(0, 3))
        ttk.Button(
            loc_row, text="Save",
            command=self._save_loc_setting,
        ).pack(side="right")

        # SOURCE folder
        self.folder_source = tk.StringVar()
        f_src = ttk.LabelFrame(tab, text="SOURCE folder (old / before)", padding=5)
        f_src.pack(fill="x", **pad)
        ttk.Entry(f_src, textvariable=self.folder_source, width=70).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            f_src, text="Browse...",
            command=lambda: self._browse_folder(self.folder_source, "SOURCE Folder"),
        ).pack(side="right")

        # TARGET folder
        self.folder_target = tk.StringVar()
        f_tgt = ttk.LabelFrame(tab, text="TARGET folder (new / after)", padding=5)
        f_tgt.pack(fill="x", **pad)
        ttk.Entry(f_tgt, textvariable=self.folder_target, width=70).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            f_tgt, text="Browse...",
            command=lambda: self._browse_folder(self.folder_target, "TARGET Folder"),
        ).pack(side="right")

        # Options (Comparison Mode + Category Filter)
        opts = ttk.LabelFrame(tab, text="Options", padding=5)
        opts.pack(fill="x", **pad)

        mode_row = ttk.Frame(opts)
        mode_row.pack(fill="x", pady=2)
        ttk.Label(mode_row, text="Comparison Mode:", width=18, anchor="w").pack(side="left")
        self.folder_compare_mode = tk.StringVar(value=COMPARE_MODES[0])
        ttk.Combobox(
            mode_row, textvariable=self.folder_compare_mode,
            values=COMPARE_MODES, state="readonly", width=35,
        ).pack(side="left", padx=(5, 0))

        cat_row = ttk.Frame(opts)
        cat_row.pack(fill="x", pady=2)
        ttk.Label(cat_row, text="Category Filter:", width=18, anchor="w").pack(side="left")
        self.folder_cat_filter = tk.StringVar(value=CATEGORY_FILTERS[0])
        folder_cat_cb = ttk.Combobox(
            cat_row, textvariable=self.folder_cat_filter,
            values=CATEGORY_FILTERS, state="readonly", width=35,
        )
        folder_cat_cb.pack(side="left", padx=(5, 0))
        folder_cat_cb.bind("<<ComboboxSelected>>", self._on_folder_cat_filter_change)

        # Export Folder (hidden by default)
        self.folder_export = tk.StringVar()
        self.folder_export_frame = ttk.LabelFrame(
            tab, text="Export Folder (export__ — for SCRIPT category detection)", padding=5,
        )
        exp_row = ttk.Frame(self.folder_export_frame)
        exp_row.pack(fill="x")
        ttk.Entry(exp_row, textvariable=self.folder_export, width=70).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            exp_row, text="Browse...",
            command=lambda: self._browse_folder(self.folder_export, "Export Folder (export__)"),
        ).pack(side="right")

        # Run button
        self.folder_run_btn = ttk.Button(tab, text="Run Folder Diff", command=self._run_diff_folder)
        self.folder_run_btn.pack(pady=10)

        # Log
        f_log = ttk.LabelFrame(tab, text="Output", padding=5)
        f_log.pack(fill="both", expand=True, **pad)
        self.folder_log = scrolledtext.ScrolledText(
            f_log, height=14, font=("Consolas", 9), wrap="word",
        )
        self.folder_log.pack(fill="both", expand=True)

    def _on_folder_cat_filter_change(self, _event=None):
        """Show/hide export folder field for folder diff tab."""
        if self.folder_cat_filter.get() == CATEGORY_FILTERS[0]:
            self.folder_export_frame.pack_forget()
        else:
            self.folder_export_frame.pack(
                fill="x", padx=8, pady=4, before=self.folder_run_btn,
            )

    def _save_loc_setting(self):
        """Persist LOC folder path to settings."""
        loc = self.folder_loc.get().strip()
        if not loc:
            return
        settings = _load_settings()
        settings["loc_folder"] = loc
        _save_settings(settings)
        messagebox.showinfo("Saved", f"LOC folder saved:\n{loc}")

    def _load_persisted_settings(self):
        """Load persisted settings into GUI fields."""
        settings = _load_settings()
        loc = settings.get("loc_folder", "")
        if loc:
            self.folder_loc.set(loc)

    # -----------------------------------------------------------------
    # TAB 3: REVERT
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

    def _browse_folder(self, var: tk.StringVar, title: str):
        path = filedialog.askdirectory(title=f"Select {title}")
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

        mode = self.compare_mode.get()
        cat_filter = self.cat_filter.get()

        _log(f"SOURCE: {src_path.name}")
        _log(f"TARGET: {tgt_path.name}")
        _log(f"Mode:   {mode}")
        _log(f"Filter: {cat_filter}")
        _log("")

        # --- Category mapping (if needed) ---
        ci_category: Dict[str, str] = {}
        if cat_filter != CATEGORY_FILTERS[0]:  # Not "All"
            export_path = self.diff_export.get().strip()
            if not export_path:
                messagebox.showerror(
                    "Error",
                    "Export folder is required for category filtering.\n"
                    "Please select the export__ folder.",
                )
                return
            export_folder = Path(export_path)
            if not export_folder.is_dir():
                messagebox.showerror("Error", f"Export folder not found:\n{export_folder}")
                return

            _log("Building category mapping from export folder...")
            raw_map = build_stringid_to_category(export_folder, progress_fn=_log)
            ci_category = {k.lower(): v for k, v in raw_map.items()}
            script_count = sum(1 for v in raw_map.values() if v in SCRIPT_CATEGORIES)
            _log(f"  {len(raw_map)} StringIDs indexed ({script_count} SCRIPT)")
            _log("")

        # --- Parse & compare based on mode ---
        if mode == COMPARE_MODES[0]:  # Full (all attributes)
            _log("Parsing SOURCE...")
            source_map, source_total = parse_locstr_elements(src_path)
            _log(f"  {source_total} LocStr ({len(source_map)} unique StringIds)")

            _log("Parsing TARGET...")
            target_map, target_total = parse_locstr_elements(tgt_path)
            _log(f"  {target_total} LocStr ({len(target_map)} unique StringIds)")

            # Apply category filter to maps
            if ci_category:
                source_before = len(source_map)
                target_before = len(target_map)
                source_map = {
                    sid: attrs for sid, attrs in source_map.items()
                    if _passes_category_filter(sid, ci_category, cat_filter)
                }
                target_map = {
                    sid: attrs for sid, attrs in target_map.items()
                    if _passes_category_filter(sid, ci_category, cat_filter)
                }
                _log(f"  After filter: SOURCE {source_before}->{len(source_map)}, TARGET {target_before}->{len(target_map)}")

            _log("")
            _log("Comparing...")
            added, edited = compare_xml(source_map, target_map)
            deleted_count = sum(1 for sid in source_map if sid not in target_map)

        else:  # Keyset modes
            _log("Parsing SOURCE...")
            source_entries, source_total = parse_locstr_entry_list(src_path)
            _log(f"  {source_total} LocStr ({len(source_entries)} with StringID)")

            _log("Parsing TARGET...")
            target_entries, target_total = parse_locstr_entry_list(tgt_path)
            _log(f"  {target_total} LocStr ({len(target_entries)} with StringID)")

            # Apply category filter
            if ci_category:
                src_before = len(source_entries)
                tgt_before = len(target_entries)
                source_entries = filter_entries_by_category(source_entries, ci_category, cat_filter)
                target_entries = filter_entries_by_category(target_entries, ci_category, cat_filter)
                _log(f"  After filter: SOURCE {src_before}->{len(source_entries)}, TARGET {tgt_before}->{len(target_entries)}")

            _log("")
            _log(f"Comparing [{mode}]...")
            added, edited = compare_xml_by_keyset(source_entries, target_entries, mode)
            deleted_count = 0  # Not applicable for keyset modes

        _log(f"  ADD:    {len(added)}")
        _log(f"  EDIT:   {len(edited)}")
        if deleted_count:
            _log(f"  DELETE: {deleted_count} (not extracted)")
        _log("")

        if not added and not edited:
            _log("No ADD/EDIT differences found.")
            return

        # --- Build output filename ---
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = ["DIFF"]
        if mode != COMPARE_MODES[0]:
            mode_short = {
                COMPARE_MODES[1]: "SO-SID",
                COMPARE_MODES[2]: "SO-SID-STR",
                COMPARE_MODES[3]: "SID-STR",
            }.get(mode, "")
            if mode_short:
                parts.append(mode_short)
        if cat_filter != CATEGORY_FILTERS[0]:
            filter_short = {
                CATEGORY_FILTERS[1]: "SCRIPT",
                CATEGORY_FILTERS[2]: "NONSCRIPT",
            }.get(cat_filter, "")
            if filter_short:
                parts.append(filter_short)
        parts.append(tgt_path.stem)
        parts.append(timestamp)
        output_name = "_".join(parts) + ".xml"
        output_path = tgt_path.parent / output_name

        count = write_diff_xml(added, edited, output_path)

        _log(f"Output: {output_name}")
        _log(f"  {count} LocStr ({len(added)} ADD + {len(edited)} EDIT)")
        _log(f"Saved to: {output_path}")
        _log("")
        _log("Done!")

    # -----------------------------------------------------------------
    # DIFF FOLDER LOGIC
    # -----------------------------------------------------------------

    def _run_diff_folder(self):
        log = self.folder_log
        log.delete("1.0", "end")
        _log = lambda msg: self._log_to(log, msg)

        loc = self.folder_loc.get().strip()
        src = self.folder_source.get().strip()
        tgt = self.folder_target.get().strip()

        # --- Validate inputs ---
        if not loc:
            messagebox.showerror("Error", "Please select the LOC folder (for language detection).")
            return
        loc_path = Path(loc)
        if not loc_path.is_dir():
            messagebox.showerror("Error", f"LOC folder not found:\n{loc_path}")
            return

        if not src or not tgt:
            messagebox.showerror("Error", "Please select both SOURCE and TARGET folders.")
            return
        src_path, tgt_path = Path(src), Path(tgt)
        if not src_path.is_dir():
            messagebox.showerror("Error", f"SOURCE folder not found:\n{src_path}")
            return
        if not tgt_path.is_dir():
            messagebox.showerror("Error", f"TARGET folder not found:\n{tgt_path}")
            return

        mode = self.folder_compare_mode.get()
        cat_filter = self.folder_cat_filter.get()

        _log(f"LOC:    {loc_path}")
        _log(f"SOURCE: {src_path}")
        _log(f"TARGET: {tgt_path}")
        _log(f"Mode:   {mode}")
        _log(f"Filter: {cat_filter}")
        _log("")

        # --- Discover languages from LOC ---
        _log("Discovering languages from LOC folder...")
        valid_codes = discover_valid_codes(loc_path)
        if not valid_codes:
            messagebox.showerror(
                "Error",
                "No languagedata_*.xml files found in LOC folder.\n"
                "Cannot determine valid language suffixes.",
            )
            return
        _log(f"  {len(valid_codes)} languages found: {', '.join(sorted(valid_codes))}")
        _log("")

        # --- Scan SOURCE and TARGET for language-suffixed files ---
        _log("Scanning SOURCE folder...")
        source_langs = scan_folder_for_language_xmls(src_path, valid_codes)
        if not source_langs:
            messagebox.showerror("Error", "No language-recognizable XML files found in SOURCE folder.")
            return
        for lang, path in sorted(source_langs.items()):
            _log(f"  {lang}: {path.name}")

        _log("")
        _log("Scanning TARGET folder...")
        target_langs = scan_folder_for_language_xmls(tgt_path, valid_codes)
        if not target_langs:
            messagebox.showerror("Error", "No language-recognizable XML files found in TARGET folder.")
            return
        for lang, path in sorted(target_langs.items()):
            _log(f"  {lang}: {path.name}")

        # --- Match languages ---
        matched = sorted(set(source_langs.keys()) & set(target_langs.keys()))
        source_only = sorted(set(source_langs.keys()) - set(target_langs.keys()))
        target_only = sorted(set(target_langs.keys()) - set(source_langs.keys()))

        _log("")
        _log(f"Matched languages: {len(matched)}")
        if source_only:
            _log(f"  SOURCE only (skipped): {', '.join(source_only)}")
        if target_only:
            _log(f"  TARGET only (skipped): {', '.join(target_only)}")

        if not matched:
            messagebox.showerror("Error", "No matching languages between SOURCE and TARGET.")
            return

        # --- Category mapping (if needed) ---
        ci_category: Dict[str, str] = {}
        if cat_filter != CATEGORY_FILTERS[0]:
            export_path = self.folder_export.get().strip()
            if not export_path:
                messagebox.showerror(
                    "Error",
                    "Export folder is required for category filtering.\n"
                    "Please select the export__ folder.",
                )
                return
            export_folder = Path(export_path)
            if not export_folder.is_dir():
                messagebox.showerror("Error", f"Export folder not found:\n{export_folder}")
                return

            _log("")
            _log("Building category mapping from export folder...")
            raw_map = build_stringid_to_category(export_folder, progress_fn=_log)
            ci_category = {k.lower(): v for k, v in raw_map.items()}
            script_count = sum(1 for v in raw_map.values() if v in SCRIPT_CATEGORIES)
            _log(f"  {len(raw_map)} StringIDs indexed ({script_count} SCRIPT)")

        # --- Create output folder ---
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_short = {
            COMPARE_MODES[0]: "FULL",
            COMPARE_MODES[1]: "SO-SID",
            COMPARE_MODES[2]: "SO-SID-STR",
            COMPARE_MODES[3]: "SID-STR",
        }.get(mode, "FULL")
        filter_short = {
            CATEGORY_FILTERS[0]: "",
            CATEGORY_FILTERS[1]: "_SCRIPT",
            CATEGORY_FILTERS[2]: "_NONSCRIPT",
        }.get(cat_filter, "")

        output_dir = _SCRIPT_DIR / f"DIFF_FOLDER_{mode_short}{filter_short}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        _log("")
        _log(f"Output folder: {output_dir.name}/")
        _log("")

        # --- Run diff for each matched language ---
        total_add = 0
        total_edit = 0
        langs_with_diffs = 0

        for lang in matched:
            s_path = source_langs[lang]
            t_path = target_langs[lang]

            _log(f"[{lang}] {s_path.name} vs {t_path.name}")

            if mode == COMPARE_MODES[0]:  # Full (all attributes)
                source_map, source_total = parse_locstr_elements(s_path)
                target_map, target_total = parse_locstr_elements(t_path)

                if ci_category:
                    source_map = {
                        sid: attrs for sid, attrs in source_map.items()
                        if _passes_category_filter(sid, ci_category, cat_filter)
                    }
                    target_map = {
                        sid: attrs for sid, attrs in target_map.items()
                        if _passes_category_filter(sid, ci_category, cat_filter)
                    }

                added, edited = compare_xml(source_map, target_map)

            else:  # Keyset modes
                source_entries, _ = parse_locstr_entry_list(s_path)
                target_entries, _ = parse_locstr_entry_list(t_path)

                if ci_category:
                    source_entries = filter_entries_by_category(source_entries, ci_category, cat_filter)
                    target_entries = filter_entries_by_category(target_entries, ci_category, cat_filter)

                added, edited = compare_xml_by_keyset(source_entries, target_entries, mode)

            n_add = len(added)
            n_edit = len(edited)

            if n_add == 0 and n_edit == 0:
                _log(f"  No differences.")
            else:
                out_name = f"DIFF_{lang}.xml"
                out_path = output_dir / out_name
                count = write_diff_xml(added, edited, out_path)
                _log(f"  ADD: {n_add}  EDIT: {n_edit}  → {out_name}")
                total_add += n_add
                total_edit += n_edit
                langs_with_diffs += 1

        # --- Summary ---
        _log("")
        _log("=" * 50)
        _log(f"SUMMARY: {langs_with_diffs}/{len(matched)} languages had differences")
        _log(f"  Total ADD:  {total_add}")
        _log(f"  Total EDIT: {total_edit}")
        _log(f"  Output: {output_dir}")

        if langs_with_diffs == 0:
            _log("")
            _log("No differences found — removing empty output folder.")
            try:
                output_dir.rmdir()
            except OSError:
                pass
        else:
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
