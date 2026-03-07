#!/usr/bin/env python3
# coding: utf-8
"""
DescFileFinder v1.0
====================
Reports which XML files contain ONLY LocStr elements that have a DescOrigin/Desc
attribute value that is NON-EMPTY and NON-KOREAN.

A file qualifies only if EVERY LocStr in it passes the condition.
If even one LocStr has no DescOrigin/Desc, or the value is empty/Korean, the file
is excluded from the report.

Input:
  - Data Folder: any folder containing XML files (recursive walk)

Output:
  - GUI log: list of qualifying file paths + summary counts

Usage: python desc_file_finder.py
"""

import re
import sys
import json
import logging
import datetime as _dt
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

# Try lxml first (recovery mode), fallback to stdlib
try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree
    USING_LXML = False

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("DescFileFinder")
logger.setLevel(logging.DEBUG)

# =============================================================================
# CONSTANTS
# =============================================================================

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

SETTINGS_FILE = SCRIPT_DIR / "desc_file_finder_settings.json"

LOCSTR_TAGS    = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']
DESCORIGIN_ATTRS = ('DescOrigin', 'Descorigin', 'descorigin', 'DESCORIGIN')
DESC_ATTRS       = ('Desc', 'desc', 'DESC')

KOREAN_RE = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')

# Pre-compile bad XML fixers
_bad_amp       = re.compile(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)')
_bad_selfclose = re.compile(r'</>')
_attr_with_lt  = re.compile(r'="([^"]*<[^"]*)"')
_attr_dangerous_lt = re.compile(r'<(?![bB][rR]\s*/?>)')


# =============================================================================
# SETTINGS
# =============================================================================

def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(settings: dict):
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to save settings: %s", e)


# =============================================================================
# XML PARSING HELPERS
# =============================================================================

def _read_xml_raw(xml_path: Path):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return xml_path.read_text(encoding=enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return None


def _escape_attr_lt(m):
    content = _attr_dangerous_lt.sub('&lt;', m.group(1))
    return '="' + content + '"'


def _sanitize_xml(raw: str) -> str:
    raw = _bad_selfclose.sub('', raw)
    raw = _attr_with_lt.sub(_escape_attr_lt, raw)
    raw = _bad_amp.sub('&amp;', raw)
    return raw


def _parse_root(raw: str):
    sanitized = _sanitize_xml(raw)
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
        logger.debug("Parse error in file: %s", e)
        return None


def _get_attr(attrib: dict, variants: tuple) -> str:
    for name in variants:
        val = attrib.get(name)
        if val is not None:
            return val
    return ""


def _iter_locstr(root):
    elements = []
    for tag in LOCSTR_TAGS:
        elements.extend(root.iter(tag))
    return elements


# =============================================================================
# CORE LOGIC
# =============================================================================

def _is_korean(text: str) -> bool:
    return bool(KOREAN_RE.search(text))


def _locstr_passes(attrib: dict) -> bool:
    """
    A LocStr passes if it has at least one of DescOrigin/Desc with a value
    that is non-empty AND non-Korean.
    """
    for variants in (DESCORIGIN_ATTRS, DESC_ATTRS):
        val = _get_attr(attrib, variants).strip()
        if val and not _is_korean(val):
            return True
    return False


def check_file(xml_path: Path):
    """
    Check a single XML file.

    Returns:
        (qualifies: bool, total_locstr: int, fail_count: int, parse_error: bool)
    """
    raw = _read_xml_raw(xml_path)
    if raw is None:
        return False, 0, 0, True

    root = _parse_root(raw)
    if root is None:
        return False, 0, 0, True

    elements = _iter_locstr(root)
    if not elements:
        return False, 0, 0, False  # No LocStr = does not qualify

    fail_count = 0
    for elem in elements:
        attrib = dict(elem.attrib)
        if not _locstr_passes(attrib):
            fail_count += 1

    qualifies = (fail_count == 0)
    return qualifies, len(elements), fail_count, False


def scan_folder(folder: Path, progress_fn=None):
    """
    Walk folder recursively, check all XML files.

    Returns:
        (qualifying_files: list[Path], stats: dict)
    """
    xml_files = sorted(folder.rglob("*.xml"))
    total_files = len(xml_files)

    qualifying = []
    stats = {
        "total_files": total_files,
        "parse_errors": 0,
        "empty_files": 0,   # XML files with no LocStr at all
        "checked": 0,
        "qualifying": 0,
    }

    for idx, xml_path in enumerate(xml_files, 1):
        if progress_fn and idx % 50 == 0:
            progress_fn(f"  Scanning... {idx}/{total_files} files")

        qualifies, total_locstr, fail_count, parse_err = check_file(xml_path)

        if parse_err:
            stats["parse_errors"] += 1
            continue

        if total_locstr == 0:
            stats["empty_files"] += 1
            continue

        stats["checked"] += 1

        if qualifies:
            qualifying.append(xml_path)
            stats["qualifying"] += 1

    return qualifying, stats


# =============================================================================
# GUI
# =============================================================================

class DescFileFinderApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DescFileFinder v1.0")
        self.root.geometry("900x680")
        self.root.resizable(True, True)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)
        pad = {"padx": 8, "pady": 4}

        ttk.Label(
            main, text="DescFileFinder",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 2))
        ttk.Label(
            main,
            text=(
                "Reports files where ALL LocStr have a DescOrigin/Desc attribute "
                "that is non-empty and non-Korean"
            ),
            font=("Segoe UI", 9),
        ).pack(pady=(0, 10))

        # Folder input
        self.folder_var = tk.StringVar()
        f_folder = ttk.LabelFrame(main, text="Data Folder (recursive walk)", padding=5)
        f_folder.pack(fill="x", **pad)
        folder_row = ttk.Frame(f_folder)
        folder_row.pack(fill="x")
        ttk.Entry(folder_row, textvariable=self.folder_var, width=70).pack(
            side="left", fill="x", expand=True, padx=(0, 5),
        )
        ttk.Button(
            folder_row, text="Browse...",
            command=self._browse_folder,
        ).pack(side="right", padx=(0, 3))
        ttk.Button(folder_row, text="Save", command=self._save_setting).pack(side="right")

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=10)
        self.run_btn = ttk.Button(
            btn_frame, text="FIND QUALIFYING FILES", width=30,
            command=self._run,
        )
        self.run_btn.pack(side="left", padx=5)
        ttk.Button(
            btn_frame, text="Clear Log", width=12,
            command=lambda: self.log.delete("1.0", "end"),
        ).pack(side="left", padx=5)

        # Log
        f_log = ttk.LabelFrame(main, text="Report", padding=5)
        f_log.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(
            f_log, height=25, font=("Consolas", 9), wrap="none",
        )
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("header",  foreground="#003080", font=("Consolas", 9, "bold"))
        self.log.tag_config("success", foreground="#007000")
        self.log.tag_config("info",    foreground="black")
        self.log.tag_config("warning", foreground="#B05000")
        self.log.tag_config("error",   foreground="#C00000")

    def _log(self, msg: str, tag: str = "info"):
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.root.update_idletasks()

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select Data Folder")
        if path:
            self.folder_var.set(path)

    def _save_setting(self):
        folder = self.folder_var.get().strip()
        if folder:
            _save_settings({"folder": folder})
            self._log(f"Folder saved: {folder}", "info")

    def _load_settings(self):
        s = _load_settings()
        folder = s.get("folder", "")
        if folder:
            self.folder_var.set(folder)

    def _run(self):
        self.log.delete("1.0", "end")
        folder = self.folder_var.get().strip()

        if not folder:
            self._log("ERROR: Please select a data folder.", "error")
            return

        folder_path = Path(folder)
        if not folder_path.is_dir():
            self._log(f"ERROR: Folder not found:\n  {folder_path}", "error")
            return

        self.run_btn.config(state="disabled")
        try:
            self._execute(folder_path)
        except Exception as e:
            self._log(f"\nERROR: {e}", "error")
            logger.exception("DescFileFinder failed")
        finally:
            self.run_btn.config(state="normal")

    def _execute(self, folder_path: Path):
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log("=" * 70, "header")
        self._log("  DESCFILEFINDER v1.0", "header")
        self._log(f"  {now}", "header")
        self._log("=" * 70, "header")
        self._log(f"\nFolder: {folder_path}", "info")
        self._log(
            "\nCondition: ALL LocStr must have DescOrigin or Desc that is\n"
            "           non-empty AND non-Korean.\n",
            "info",
        )
        self._log("Scanning...", "info")

        qualifying, stats = scan_folder(
            folder_path,
            progress_fn=lambda msg: self._log(msg, "info"),
        )

        self._log(f"\n{'─' * 70}", "info")
        self._log(f"  QUALIFYING FILES ({len(qualifying)})", "header")
        self._log(f"{'─' * 70}", "info")

        if qualifying:
            for p in qualifying:
                try:
                    rel = p.relative_to(folder_path)
                except ValueError:
                    rel = p
                self._log(f"  {rel}", "success")
        else:
            self._log("  (none)", "warning")

        self._log(f"\n{'=' * 70}", "header")
        self._log("  SUMMARY", "header")
        self._log(f"{'=' * 70}", "header")
        self._log(f"  XML files found:     {stats['total_files']}", "info")
        self._log(f"  Parse errors:        {stats['parse_errors']}", "warning" if stats['parse_errors'] else "info")
        self._log(f"  No-LocStr files:     {stats['empty_files']}", "info")
        self._log(f"  Files checked:       {stats['checked']}", "info")
        self._log(f"  Qualifying files:    {stats['qualifying']}", "success" if stats['qualifying'] else "info")
        self._log("", "info")

    def run(self):
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    app = DescFileFinderApp()
    app.run()


if __name__ == "__main__":
    main()
