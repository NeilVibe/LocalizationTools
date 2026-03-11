#!/usr/bin/env python3
# coding: utf-8
"""
MultiLookup v1.0
==================
Standalone GUI tool for Excel-to-Excel lookup transfer with multi-file
support and normalized key matching.

Build a lookup dictionary from one or more SOURCE Excel files, then write
matched values into one or more TARGET Excel files.

Features:
  - Multi-file source/target with per-file sheet + column config
  - Normalized key matching (strip, collapse spaces, remove _x000D_, case-insensitive)
  - First-wins dedup for duplicate normalized keys
  - Save as copy (default) or overwrite original

Usage: python multi_lookup.py
"""
from __future__ import annotations

import json
import re
import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Try openpyxl (required for both read and write on existing files)
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("MultiLookup")
logger.setLevel(logging.DEBUG)

# =============================================================================
# CONSTANTS
# =============================================================================

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent

SETTINGS_FILE = SCRIPT_DIR / "multi_lookup_settings.json"

SAVE_MODES = ["Save as _lookup copy", "Overwrite original"]

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
# NORMALIZATION
# =============================================================================

def normalize_key(value) -> str:
    """Normalize a cell value for key matching.

    Strip whitespace, remove _x000D_, collapse multiple spaces, lowercase.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    s = re.sub(r'_x000D_', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()


def clean_value(value) -> Optional[str]:
    """Clean a value for transfer. Strip whitespace, remove _x000D_.
    NOT lowercased — preserves original casing."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = re.sub(r'_x000D_', '', s, flags=re.IGNORECASE)
    return s


# =============================================================================
# EXCEL INTROSPECTION
# =============================================================================

def read_sheets(file_path: Path) -> List[str]:
    """Read sheet names from an Excel file."""
    try:
        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        names = wb.sheetnames
        wb.close()
        return names
    except Exception as e:
        logger.error("Failed to read sheets from %s: %s", file_path, e)
        return []


def read_headers(file_path: Path, sheet_name: str) -> List[str]:
    """Read column headers (row 1) from a specific sheet."""
    try:
        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        ws = wb[sheet_name]
        headers = []
        for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
            for cell_val in row:
                if cell_val is not None:
                    headers.append(str(cell_val).strip())
                else:
                    headers.append("")
        wb.close()
        return headers
    except Exception as e:
        logger.error("Failed to read headers from %s [%s]: %s", file_path, sheet_name, e)
        return []


# =============================================================================
# CORE LOGIC
# =============================================================================

def build_source_dict(
    entries: List[dict],
    log_fn=None,
) -> Tuple[Dict[str, str], int]:
    """Build a unified lookup dictionary from all source file entries.

    Each entry: {path, sheet, key_col, value_col, key_col_idx, value_col_idx}

    Returns:
        (lookup_dict {normalized_key: cleaned_value}, duplicate_count)
    """
    lookup: Dict[str, str] = {}
    duplicates = 0

    for entry in entries:
        file_path = Path(entry["path"])
        sheet = entry["sheet"]
        key_idx = entry["key_col_idx"]
        val_idx = entry["value_col_idx"]

        if log_fn:
            log_fn(f"  Reading: {file_path.name} [{sheet}]", "info")

        try:
            wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
            ws = wb[sheet]
        except Exception as e:
            if log_fn:
                log_fn(f"    ERROR: {e}", "error")
            continue

        row_count = 0
        added = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            row_count += 1
            if key_idx >= len(row):
                continue
            raw_key = row[key_idx]
            nk = normalize_key(raw_key)
            if not nk:
                continue

            raw_val = row[val_idx] if val_idx < len(row) else None
            cv = clean_value(raw_val)

            if nk in lookup:
                duplicates += 1
            else:
                lookup[nk] = cv if cv is not None else ""
                added += 1

        wb.close()

        if log_fn:
            log_fn(f"    {row_count} rows scanned, {added} keys added", "info")

    return lookup, duplicates


def transfer_to_targets(
    lookup: Dict[str, str],
    entries: List[dict],
    save_mode: str,
    log_fn=None,
) -> Tuple[int, int, int]:
    """Transfer values from lookup dict into target files.

    Each entry: {path, sheet, key_col, write_col, key_col_idx, write_col_idx}

    Returns:
        (total_matches, total_rows, files_saved)
    """
    total_matches = 0
    total_rows = 0
    files_saved = 0

    for entry in entries:
        file_path = Path(entry["path"])
        sheet = entry["sheet"]
        key_idx = entry["key_col_idx"]
        write_idx = entry["write_col_idx"]

        if log_fn:
            log_fn(f"\n  Processing: {file_path.name} [{sheet}]", "info")

        try:
            wb = openpyxl.load_workbook(str(file_path))
            ws = wb[sheet]
        except PermissionError:
            if log_fn:
                log_fn(f"    ERROR: File locked — close it in Excel first", "error")
            continue
        except Exception as e:
            if log_fn:
                log_fn(f"    ERROR: {e}", "error")
            continue

        matches = 0
        rows = 0

        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            rows += 1
            if key_idx >= len(row):
                continue
            raw_key = row[key_idx].value
            nk = normalize_key(raw_key)
            if not nk:
                continue

            if nk in lookup:
                # write_idx is 0-based, but openpyxl row objects are also 0-based
                if write_idx < len(row):
                    row[write_idx].value = lookup[nk]
                else:
                    # Column beyond current range — use cell() method
                    ws.cell(row=row_idx, column=write_idx + 1, value=lookup[nk])
                matches += 1

        total_matches += matches
        total_rows += rows

        # Save
        try:
            if save_mode == SAVE_MODES[0]:
                # Save as _lookup copy
                stem = file_path.stem
                out_path = file_path.parent / f"{stem}_lookup{file_path.suffix}"
            else:
                out_path = file_path

            wb.save(str(out_path))
            wb.close()
            files_saved += 1

            if log_fn:
                log_fn(f"    {matches}/{rows} rows matched", "success")
                log_fn(f"    Saved: {out_path.name}", "success")

        except PermissionError:
            if log_fn:
                log_fn(f"    ERROR: Cannot save — file locked. Close it in Excel first.", "error")
            wb.close()
        except Exception as e:
            if log_fn:
                log_fn(f"    ERROR saving: {e}", "error")
            wb.close()

    return total_matches, total_rows, files_saved


# =============================================================================
# FILE ENTRY (data model for each file in list)
# =============================================================================

class FileEntry:
    """Stores config for one file in the source or target list."""

    __slots__ = ("path", "sheets", "headers", "sheet", "col1", "col2",
                 "col1_idx", "col2_idx")

    def __init__(self, path: str):
        self.path = path
        self.sheets: List[str] = []
        self.headers: List[str] = []
        self.sheet: str = ""
        self.col1: str = ""  # KEY column
        self.col2: str = ""  # VALUE (source) or WRITE (target) column
        self.col1_idx: int = -1
        self.col2_idx: int = -1

    @property
    def display(self) -> str:
        name = Path(self.path).name
        if self.sheet:
            return f"{name} [{self.sheet}]"
        return name

    def to_transfer_dict(self, is_source: bool) -> dict:
        d = {"path": self.path, "sheet": self.sheet}
        d["key_col_idx"] = self.col1_idx
        if is_source:
            d["value_col_idx"] = self.col2_idx
        else:
            d["write_col_idx"] = self.col2_idx
        return d


# =============================================================================
# GUI APPLICATION
# =============================================================================

class MultiLookupApp:
    """GUI for Excel-to-Excel lookup transfer."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MultiLookup v1.0")
        self.root.geometry("850x780")
        self.root.resizable(True, True)

        self.source_entries: List[FileEntry] = []
        self.target_entries: List[FileEntry] = []

        self._build_ui()
        self._load_persisted_settings()
        self._check_openpyxl()

    def _check_openpyxl(self):
        if not HAS_OPENPYXL:
            self._log("ERROR: openpyxl is required. Install with: pip install openpyxl", "error")
            self.transfer_btn.config(state="disabled")

    # -----------------------------------------------------------------
    # UI BUILDING
    # -----------------------------------------------------------------

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            main, text="MultiLookup v1.0",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 2))
        ttk.Label(
            main,
            text="Excel-to-Excel lookup transfer with normalized key matching",
            font=("Segoe UI", 9),
        ).pack(pady=(0, 10))

        # SOURCE section
        self._build_file_section(
            main, "SOURCE Files (lookup dictionary)",
            is_source=True,
        )

        # TARGET section
        self._build_file_section(
            main, "TARGET Files (write into)",
            is_source=False,
        )

        # Transfer + Clear Log buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=8)
        self.transfer_btn = ttk.Button(
            btn_frame, text="===== TRANSFER =====", width=30,
            command=self._run_transfer,
        )
        self.transfer_btn.pack(side="left", padx=5)
        ttk.Button(
            btn_frame, text="Clear Log", width=12,
            command=lambda: self.log.delete("1.0", "end"),
        ).pack(side="left", padx=5)

        # Log
        f_log = ttk.LabelFrame(main, text="Log", padding=5)
        f_log.pack(fill="both", expand=True, padx=8, pady=4)
        self.log = scrolledtext.ScrolledText(
            f_log, height=12, font=("Consolas", 9), wrap="word",
        )
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("info", foreground="black")
        self.log.tag_config("success", foreground="green")
        self.log.tag_config("warning", foreground="orange")
        self.log.tag_config("error", foreground="red")
        self.log.tag_config("header", foreground="blue", font=("Consolas", 9, "bold"))

    def _build_file_section(self, parent, title: str, is_source: bool):
        """Build a SOURCE or TARGET file section with listbox + config."""
        pad = {"padx": 8, "pady": 4}
        lf = ttk.LabelFrame(parent, text=title, padding=5)
        lf.pack(fill="x", **pad)

        # Buttons row
        btn_row = ttk.Frame(lf)
        btn_row.pack(fill="x", pady=(0, 4))

        ttk.Button(
            btn_row, text="Add Files...",
            command=lambda: self._add_files(is_source),
        ).pack(side="left", padx=(0, 3))
        ttk.Button(
            btn_row, text="Remove",
            command=lambda: self._remove_selected(is_source),
        ).pack(side="left", padx=(0, 3))
        ttk.Button(
            btn_row, text="Clear All",
            command=lambda: self._clear_files(is_source),
        ).pack(side="left", padx=(0, 3))

        # Status label (right side)
        status_var = tk.StringVar(value="No files")
        ttk.Label(btn_row, textvariable=status_var, font=("Segoe UI", 8)).pack(
            side="right", padx=5,
        )

        # Listbox
        lb_frame = ttk.Frame(lf)
        lb_frame.pack(fill="x", pady=(0, 4))
        lb = tk.Listbox(lb_frame, height=4, font=("Consolas", 9))
        lb.pack(fill="x", side="left", expand=True)
        sb = ttk.Scrollbar(lb_frame, orient="vertical", command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.config(yscrollcommand=sb.set)

        # Config frame (updates on listbox selection)
        cfg = ttk.Frame(lf)
        cfg.pack(fill="x", pady=(0, 4))

        ttk.Label(cfg, text="Sheet:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        sheet_cb = ttk.Combobox(cfg, state="readonly", width=30)
        sheet_cb.grid(row=0, column=1, sticky="w", padx=(0, 15))

        ttk.Label(cfg, text="KEY Column:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        key_cb = ttk.Combobox(cfg, state="readonly", width=25)
        key_cb.grid(row=0, column=3, sticky="w", padx=(0, 15))

        col2_label = "VALUE Column:" if is_source else "WRITE Column:"
        ttk.Label(cfg, text=col2_label).grid(row=0, column=4, sticky="w", padx=(0, 5))
        val_cb = ttk.Combobox(cfg, state="readonly", width=25)
        val_cb.grid(row=0, column=5, sticky="w")

        # Save mode (target only)
        save_cb = None
        if not is_source:
            save_frame = ttk.Frame(lf)
            save_frame.pack(fill="x", pady=(0, 2))
            ttk.Label(save_frame, text="Save Mode:").pack(side="left", padx=(0, 5))
            save_cb = ttk.Combobox(
                save_frame, state="readonly", values=SAVE_MODES, width=30,
            )
            save_cb.set(SAVE_MODES[0])
            save_cb.pack(side="left")

        # Store references
        if is_source:
            self.src_lb = lb
            self.src_sheet_cb = sheet_cb
            self.src_key_cb = key_cb
            self.src_val_cb = val_cb
            self.src_status = status_var
        else:
            self.tgt_lb = lb
            self.tgt_sheet_cb = sheet_cb
            self.tgt_key_cb = key_cb
            self.tgt_val_cb = val_cb
            self.tgt_status = status_var
            self.save_mode_cb = save_cb

        # Bind events
        lb.bind("<<ListboxSelect>>", lambda e: self._on_listbox_select(is_source))
        sheet_cb.bind("<<ComboboxSelected>>", lambda e: self._on_sheet_select(is_source))
        key_cb.bind("<<ComboboxSelected>>", lambda e: self._on_col_select(is_source, is_key=True))
        val_cb.bind("<<ComboboxSelected>>", lambda e: self._on_col_select(is_source, is_key=False))

    # -----------------------------------------------------------------
    # FILE MANAGEMENT
    # -----------------------------------------------------------------

    def _get_entries(self, is_source: bool) -> List[FileEntry]:
        return self.source_entries if is_source else self.target_entries

    def _get_listbox(self, is_source: bool) -> tk.Listbox:
        return self.src_lb if is_source else self.tgt_lb

    def _get_status(self, is_source: bool) -> tk.StringVar:
        return self.src_status if is_source else self.tgt_status

    def _update_listbox(self, is_source: bool):
        """Refresh listbox display from entries."""
        lb = self._get_listbox(is_source)
        lb.delete(0, "end")
        entries = self._get_entries(is_source)
        for entry in entries:
            lb.insert("end", entry.display)
        self._update_status(is_source)

    def _update_status(self, is_source: bool):
        entries = self._get_entries(is_source)
        status = self._get_status(is_source)
        n = len(entries)
        configured = sum(1 for e in entries if e.col1_idx >= 0 and e.col2_idx >= 0)
        if n == 0:
            status.set("No files")
        else:
            status.set(f"{n} file(s), {configured} configured")

    def _add_files(self, is_source: bool):
        paths = filedialog.askopenfilenames(
            title="Select Excel files",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if not paths:
            return

        entries = self._get_entries(is_source)
        existing_paths = {e.path for e in entries}

        for p in paths:
            if p in existing_paths:
                continue
            entry = FileEntry(p)
            entry.sheets = read_sheets(Path(p))
            if entry.sheets:
                entry.sheet = entry.sheets[0]
                entry.headers = read_headers(Path(p), entry.sheet)
            entries.append(entry)

        self._update_listbox(is_source)

        # Auto-select last added
        lb = self._get_listbox(is_source)
        if entries:
            lb.selection_clear(0, "end")
            lb.selection_set(len(entries) - 1)
            self._on_listbox_select(is_source)

    def _remove_selected(self, is_source: bool):
        lb = self._get_listbox(is_source)
        sel = lb.curselection()
        if not sel:
            return
        entries = self._get_entries(is_source)
        idx = sel[0]
        entries.pop(idx)
        self._update_listbox(is_source)
        self._clear_config(is_source)

    def _clear_files(self, is_source: bool):
        entries = self._get_entries(is_source)
        entries.clear()
        self._update_listbox(is_source)
        self._clear_config(is_source)

    def _clear_config(self, is_source: bool):
        """Clear the config comboboxes."""
        if is_source:
            self.src_sheet_cb.set("")
            self.src_sheet_cb["values"] = []
            self.src_key_cb.set("")
            self.src_key_cb["values"] = []
            self.src_val_cb.set("")
            self.src_val_cb["values"] = []
        else:
            self.tgt_sheet_cb.set("")
            self.tgt_sheet_cb["values"] = []
            self.tgt_key_cb.set("")
            self.tgt_key_cb["values"] = []
            self.tgt_val_cb.set("")
            self.tgt_val_cb["values"] = []

    # -----------------------------------------------------------------
    # SELECTION EVENTS
    # -----------------------------------------------------------------

    def _get_selected_entry(self, is_source: bool) -> Optional[FileEntry]:
        lb = self._get_listbox(is_source)
        sel = lb.curselection()
        if not sel:
            return None
        entries = self._get_entries(is_source)
        idx = sel[0]
        if idx < len(entries):
            return entries[idx]
        return None

    def _on_listbox_select(self, is_source: bool):
        entry = self._get_selected_entry(is_source)
        if not entry:
            return

        if is_source:
            sheet_cb = self.src_sheet_cb
            key_cb = self.src_key_cb
            val_cb = self.src_val_cb
        else:
            sheet_cb = self.tgt_sheet_cb
            key_cb = self.tgt_key_cb
            val_cb = self.tgt_val_cb

        # Populate sheet combobox
        sheet_cb["values"] = entry.sheets
        if entry.sheet:
            sheet_cb.set(entry.sheet)
        elif entry.sheets:
            sheet_cb.set(entry.sheets[0])

        # Populate column comboboxes from headers
        col_display = [f"{i}: {h}" for i, h in enumerate(entry.headers)] if entry.headers else []
        key_cb["values"] = col_display
        val_cb["values"] = col_display

        # Restore saved selections
        if entry.col1 and entry.col1 in col_display:
            key_cb.set(entry.col1)
        else:
            key_cb.set("")

        if entry.col2 and entry.col2 in col_display:
            val_cb.set(entry.col2)
        else:
            val_cb.set("")

    def _on_sheet_select(self, is_source: bool):
        entry = self._get_selected_entry(is_source)
        if not entry:
            return

        if is_source:
            sheet_cb = self.src_sheet_cb
            key_cb = self.src_key_cb
            val_cb = self.src_val_cb
        else:
            sheet_cb = self.tgt_sheet_cb
            key_cb = self.tgt_key_cb
            val_cb = self.tgt_val_cb

        new_sheet = sheet_cb.get()
        if new_sheet == entry.sheet:
            return

        entry.sheet = new_sheet
        entry.headers = read_headers(Path(entry.path), new_sheet)
        entry.col1 = ""
        entry.col1_idx = -1
        entry.col2 = ""
        entry.col2_idx = -1

        col_display = [f"{i}: {h}" for i, h in enumerate(entry.headers)] if entry.headers else []
        key_cb["values"] = col_display
        key_cb.set("")
        val_cb["values"] = col_display
        val_cb.set("")

        # Update listbox display
        self._update_listbox(is_source)

    def _on_col_select(self, is_source: bool, is_key: bool):
        entry = self._get_selected_entry(is_source)
        if not entry:
            return

        if is_source:
            cb = self.src_key_cb if is_key else self.src_val_cb
        else:
            cb = self.tgt_key_cb if is_key else self.tgt_val_cb

        val = cb.get()
        if not val:
            return

        # Extract index from "N: header" format
        try:
            col_idx = int(val.split(":")[0])
        except (ValueError, IndexError):
            return

        if is_key:
            entry.col1 = val
            entry.col1_idx = col_idx
        else:
            entry.col2 = val
            entry.col2_idx = col_idx

        self._update_status(is_source)

    # -----------------------------------------------------------------
    # LOGGING
    # -----------------------------------------------------------------

    def _log(self, msg: str, tag: str = "info"):
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.root.update_idletasks()

    # -----------------------------------------------------------------
    # TRANSFER LOGIC
    # -----------------------------------------------------------------

    def _run_transfer(self):
        self.log.delete("1.0", "end")

        # Validate source entries
        if not self.source_entries:
            messagebox.showerror("Error", "No SOURCE files added.")
            return

        unconfigured_src = [
            e for e in self.source_entries if e.col1_idx < 0 or e.col2_idx < 0
        ]
        if unconfigured_src:
            names = ", ".join(Path(e.path).name for e in unconfigured_src)
            messagebox.showerror(
                "Error",
                f"Source files not fully configured (select Sheet + KEY + VALUE):\n{names}",
            )
            return

        # Validate target entries
        if not self.target_entries:
            messagebox.showerror("Error", "No TARGET files added.")
            return

        unconfigured_tgt = [
            e for e in self.target_entries if e.col1_idx < 0 or e.col2_idx < 0
        ]
        if unconfigured_tgt:
            names = ", ".join(Path(e.path).name for e in unconfigured_tgt)
            messagebox.showerror(
                "Error",
                f"Target files not fully configured (select Sheet + KEY + WRITE):\n{names}",
            )
            return

        save_mode = self.save_mode_cb.get() if self.save_mode_cb else SAVE_MODES[0]

        self.transfer_btn.config(state="disabled")

        try:
            self._execute_transfer(save_mode)
        except Exception as e:
            self._log(f"\nERROR: {e}", "error")
            logger.exception("MultiLookup transfer failed")
        finally:
            self.transfer_btn.config(state="normal")
            self._persist_settings()

    def _execute_transfer(self, save_mode: str):
        t0 = time.time()

        self._log("=" * 60, "header")
        self._log("  MULTILOOKUP TRANSFER v1.0", "header")
        self._log("=" * 60, "header")

        # Step 1: Build source dictionary
        self._log(f"\n{'─' * 60}", "info")
        self._log("BUILDING SOURCE DICTIONARY...", "header")
        self._log(f"{'─' * 60}", "info")

        src_dicts = [e.to_transfer_dict(is_source=True) for e in self.source_entries]
        lookup, dup_count = build_source_dict(src_dicts, log_fn=self._log)

        if not lookup:
            self._log("\nERROR: Source dictionary is empty — nothing to transfer.", "error")
            return

        self._log(f"\n  Dictionary: {len(lookup):,} unique keys", "success")
        if dup_count > 0:
            self._log(
                f"  WARNING: {dup_count:,} duplicate keys (first value wins)",
                "warning",
            )

        # Step 2: Transfer to targets
        self._log(f"\n{'─' * 60}", "info")
        self._log(f"TRANSFERRING TO TARGETS ({save_mode})...", "header")
        self._log(f"{'─' * 60}", "info")

        tgt_dicts = [e.to_transfer_dict(is_source=False) for e in self.target_entries]
        total_matches, total_rows, files_saved = transfer_to_targets(
            lookup, tgt_dicts, save_mode, log_fn=self._log,
        )

        # Step 3: Summary
        elapsed = time.time() - t0
        self._log(f"\n{'=' * 60}", "header")
        self._log("  DONE", "header")
        self._log(f"{'=' * 60}", "header")
        self._log(f"  Source: {len(lookup):,} keys from {len(self.source_entries)} file(s)", "info")
        self._log(f"  Target: {total_matches:,}/{total_rows:,} rows matched across {len(self.target_entries)} file(s)", "info")
        self._log(f"  Files saved: {files_saved}", "success")
        self._log(f"  Time: {elapsed:.1f}s", "info")

        if total_matches == 0:
            self._log(
                "\n  WARNING: 0 matches — check that KEY columns contain matching data.",
                "warning",
            )

    # -----------------------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------------------

    def _persist_settings(self):
        """Save current file paths and column selections."""
        settings = _load_settings()

        def serialize_entries(entries: List[FileEntry]) -> List[dict]:
            return [
                {
                    "path": e.path,
                    "sheet": e.sheet,
                    "col1": e.col1,
                    "col2": e.col2,
                }
                for e in entries
            ]

        settings["source_entries"] = serialize_entries(self.source_entries)
        settings["target_entries"] = serialize_entries(self.target_entries)
        if self.save_mode_cb:
            settings["save_mode"] = self.save_mode_cb.get()

        _save_settings(settings)

    def _load_persisted_settings(self):
        """Restore file entries from saved settings."""
        settings = _load_settings()

        if self.save_mode_cb and "save_mode" in settings:
            mode = settings["save_mode"]
            if mode in SAVE_MODES:
                self.save_mode_cb.set(mode)

        for key, is_source in [("source_entries", True), ("target_entries", False)]:
            saved = settings.get(key, [])
            entries = self._get_entries(is_source)

            for item in saved:
                p = item.get("path", "")
                if not p or not Path(p).exists():
                    continue
                entry = FileEntry(p)
                entry.sheets = read_sheets(Path(p))

                sheet = item.get("sheet", "")
                if sheet and sheet in entry.sheets:
                    entry.sheet = sheet
                elif entry.sheets:
                    entry.sheet = entry.sheets[0]

                if entry.sheet:
                    entry.headers = read_headers(Path(p), entry.sheet)

                col1 = item.get("col1", "")
                col2 = item.get("col2", "")

                col_display = [f"{i}: {h}" for i, h in enumerate(entry.headers)]

                if col1 and col1 in col_display:
                    entry.col1 = col1
                    try:
                        entry.col1_idx = int(col1.split(":")[0])
                    except (ValueError, IndexError):
                        pass

                if col2 and col2 in col_display:
                    entry.col2 = col2
                    try:
                        entry.col2_idx = int(col2.split(":")[0])
                    except (ValueError, IndexError):
                        pass

                entries.append(entry)

            self._update_listbox(is_source)

    def run(self):
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    app = MultiLookupApp()
    app.run()


if __name__ == "__main__":
    main()
