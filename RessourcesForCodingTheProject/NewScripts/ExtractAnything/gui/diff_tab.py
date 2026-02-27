"""Diff tab – file diff, folder diff, and revert modes."""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import config
from core import diff_engine, input_parser
from core.excel_writer import write_extraction_excel
from core.validators import (
    validate_diff_excel_columns,
    validate_diff_folder_excel_columns,
    validate_diff_file,
    validate_xml_source_folder,
)
from core.xml_writer import write_locstr_xml
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class DiffTab(BaseTab):
    TAB_TITLE = "Diff"

    def _build_ui(self) -> None:
        nb = ttk.Notebook(self.frame)
        nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._build_file_tab(nb)
        self._build_folder_tab(nb)
        self._build_revert_tab(nb)

    # ------------------------------------------------------------------
    # File Diff sub-tab
    # ------------------------------------------------------------------
    def _build_file_tab(self, parent: ttk.Notebook) -> None:
        f = ttk.Frame(parent)
        parent.add(f, text="File Diff")

        # Source
        src_frame = ttk.LabelFrame(f, text="Source (before / reference)")
        src_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_file_var = tk.StringVar()
        self._make_path_row(src_frame, "File:", self._src_file_var,
                            lambda: self.browse_file(
                                self._src_file_var, "Select source file",
                                [("XML/Excel", "*.xml *.xlsx"), ("All", "*.*")],
                                on_selected=lambda p: validate_diff_file(p, label="Source", log_fn=self.log)))

        # Target
        tgt_frame = ttk.LabelFrame(f, text="Target (after / to extract from)")
        tgt_frame.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_file_var = tk.StringVar()
        self._make_path_row(tgt_frame, "File:", self._tgt_file_var,
                            lambda: self.browse_file(
                                self._tgt_file_var, "Select target file",
                                [("XML/Excel", "*.xml *.xlsx"), ("All", "*.*")],
                                on_selected=lambda p: validate_diff_file(p, label="Target", log_fn=self.log)))

        # Options
        opt = ttk.LabelFrame(f, text="Options")
        opt.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(opt, text="Compare mode:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self._file_mode_var = tk.StringVar(value=config.COMPARE_MODES[0])
        ttk.Combobox(opt, textvariable=self._file_mode_var, values=config.COMPARE_MODES,
                     state="readonly", width=30).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(opt, text="Category filter:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self._file_cat_var = tk.StringVar(value=config.CATEGORY_FILTERS[0])
        ttk.Combobox(opt, textvariable=self._file_cat_var, values=config.CATEGORY_FILTERS,
                     state="readonly", width=30).grid(row=1, column=1, padx=5, pady=2)

        # Action
        ttk.Button(f, text="Run File Diff", command=self._run_file_diff).pack(pady=10)

    # ------------------------------------------------------------------
    # Folder Diff sub-tab
    # ------------------------------------------------------------------
    def _build_folder_tab(self, parent: ttk.Notebook) -> None:
        f = ttk.Frame(parent)
        parent.add(f, text="Folder Diff")

        src_frame = ttk.LabelFrame(f, text="Source Folder (before)")
        src_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_folder_var = tk.StringVar()
        self._make_path_row(src_frame, "Folder:", self._src_folder_var,
                            lambda: self.browse_folder(
                                self._src_folder_var, "Select source folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Source", log_fn=self.log)))

        tgt_frame = ttk.LabelFrame(f, text="Target Folder (after)")
        tgt_frame.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_folder_var = tk.StringVar()
        self._make_path_row(tgt_frame, "Folder:", self._tgt_folder_var,
                            lambda: self.browse_folder(
                                self._tgt_folder_var, "Select target folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Target", log_fn=self.log)))

        opt = ttk.LabelFrame(f, text="Options")
        opt.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(opt, text="Compare mode:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self._folder_mode_var = tk.StringVar(value=config.COMPARE_MODES[0])
        ttk.Combobox(opt, textvariable=self._folder_mode_var, values=config.COMPARE_MODES,
                     state="readonly", width=30).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(opt, text="Category filter:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self._folder_cat_var = tk.StringVar(value=config.CATEGORY_FILTERS[0])
        ttk.Combobox(opt, textvariable=self._folder_cat_var, values=config.CATEGORY_FILTERS,
                     state="readonly", width=30).grid(row=1, column=1, padx=5, pady=2)

        ttk.Button(f, text="Run Folder Diff", command=self._run_folder_diff).pack(pady=10)

    # ------------------------------------------------------------------
    # Revert sub-tab
    # ------------------------------------------------------------------
    def _build_revert_tab(self, parent: ttk.Notebook) -> None:
        f = ttk.Frame(parent)
        parent.add(f, text="Revert")

        bf = ttk.LabelFrame(f, text="BEFORE file (original state)")
        bf.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._before_var = tk.StringVar()
        self._make_path_row(bf, "File:", self._before_var,
                            lambda: self.browse_file(
                                self._before_var, "Select BEFORE file",
                                [("XML", "*.xml"), ("All", "*.*")],
                                on_selected=lambda p: validate_diff_file(p, label="Before", log_fn=self.log)))

        af = ttk.LabelFrame(f, text="AFTER file (modified state)")
        af.pack(fill=tk.X, padx=5, pady=2)
        self._after_var = tk.StringVar()
        self._make_path_row(af, "File:", self._after_var,
                            lambda: self.browse_file(
                                self._after_var, "Select AFTER file",
                                [("XML", "*.xml"), ("All", "*.*")],
                                on_selected=lambda p: validate_diff_file(p, label="After", log_fn=self.log)))

        cf = ttk.LabelFrame(f, text="CURRENT file (to revert)")
        cf.pack(fill=tk.X, padx=5, pady=2)
        self._current_var = tk.StringVar()
        self._make_path_row(cf, "File:", self._current_var,
                            lambda: self.browse_file(
                                self._current_var, "Select CURRENT file",
                                [("XML", "*.xml"), ("All", "*.*")],
                                on_selected=lambda p: validate_diff_file(p, label="Current", log_fn=self.log)))

        ttk.Button(f, text="Revert Changes", command=self._run_revert).pack(pady=10)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @staticmethod
    def _diff_columns(mode: str) -> list[tuple[str, str, int]]:
        cols = [
            ("string_id", "StringID", 35),
            ("str_origin", "StrOrigin", 45),
            ("str_value", "Str", 60),
        ]
        if mode == "Full (all attributes)":
            cols.append(("_diff_type", "DiffType", 10))
        return cols

    @staticmethod
    def _diff_sort_key(mode: str):
        if mode == "Full (all attributes)":
            return lambda e: (e.get("_diff_type", ""), e["string_id"].lower())
        return lambda e: e["string_id"].lower()

    def _get_category_map(self) -> dict[str, str] | None:
        """Build/get category map if a non-All filter is selected."""
        idx = self.get_export_index(
            lambda cur, tot: self.set_progress(cur * 100 // max(tot, 1))
        )
        return idx.category_map if idx.is_built else None

    def _run_file_diff(self) -> None:
        src_path = self._src_file_var.get().strip()
        tgt_path = self._tgt_file_var.get().strip()
        if not src_path or not tgt_path:
            self.log("Source and target files are required.", "error")
            return

        mode = self._file_mode_var.get()
        cat_filter = self._file_cat_var.get()

        def work():
            self._log_header(f"File Diff: {mode} | {cat_filter}")
            self.set_progress(5)

            if self.app.path_filter_active:
                self.log(f"Path filter active: {self.app.path_filter_count} paths selected")

            # --- Column validation (BLOCKING) ---
            blocked = False
            for fpath, flabel in [(src_path, "Source"), (tgt_path, "Target")]:
                p = Path(fpath)
                if p.suffix.lower() in (".xlsx", ".xls"):
                    vr = validate_diff_excel_columns(p, mode, label=flabel, log_fn=self.log)
                    if not vr.ok:
                        blocked = True
            if blocked:
                self.log(
                    f"OPERATION BLOCKED: Excel file(s) missing columns required by mode '{mode}'.\n"
                    f"Fix the input files or choose a different compare mode.",
                    "error",
                )
                return

            self.log(f"Parsing source: {Path(src_path).name}")
            src_entries, _ = input_parser.parse_input_file(Path(src_path), log_fn=self.log)
            self.set_progress(30)

            self.log(f"Parsing target: {Path(tgt_path).name}")
            tgt_entries, _ = input_parser.parse_input_file(Path(tgt_path), log_fn=self.log)
            self.set_progress(60)

            self.log(f"Source: {len(src_entries):,} entries | Target: {len(tgt_entries):,} entries")

            cat_map = self._get_category_map() if cat_filter != "All (no filter)" else None
            self.set_progress(70)

            self.log("Comparing...")
            extracted = diff_engine.diff_file(
                src_entries, tgt_entries,
                mode=mode, category_filter=cat_filter, category_map=cat_map,
            )
            extracted = self.filter_entries_by_path(extracted)
            self.set_progress(90)

            if not extracted:
                self.log("No differences found.", "info")
                return

            self.log(f"Extracted {len(extracted):,} entries.", "success")

            # Write output
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = config.OUTPUT_DIR / f"diff_{ts}"
            tgt_stem = Path(tgt_path).stem
            sort_key = self._diff_sort_key(mode)
            columns = self._diff_columns(mode)

            xlsx_file = out_dir / f"DIFF_{tgt_stem}.xlsx"
            write_extraction_excel(
                xlsx_file, extracted,
                columns=columns, sheet_name="Diff",
                header_bg="#5B4A8A", sort_key=sort_key,
            )

            xml_file = out_dir / f"DIFF_{tgt_stem}.xml"
            write_locstr_xml(xml_file, extracted, sort_key=sort_key)
            self.log(f"Output: {out_dir}", "success")

        self.run_in_thread(work)

    def _run_folder_diff(self) -> None:
        src = self._src_folder_var.get().strip()
        tgt = self._tgt_folder_var.get().strip()
        if not src or not tgt:
            self.log("Source and target folders are required.", "error")
            return

        mode = self._folder_mode_var.get()
        cat_filter = self._folder_cat_var.get()

        def work():
            self._log_header(f"Folder Diff: {mode} | {cat_filter}")

            if self.app.path_filter_active:
                self.log(f"Path filter active: {self.app.path_filter_count} paths selected")

            # --- Column validation (BLOCKING) ---
            blocked = False
            for folder, flabel in [(Path(src), "Source"), (Path(tgt), "Target")]:
                vr = validate_diff_folder_excel_columns(folder, mode, label=flabel, log_fn=self.log)
                if not vr.ok:
                    blocked = True
            if blocked:
                self.log(
                    f"OPERATION BLOCKED: Excel file(s) missing columns required by mode '{mode}'.\n"
                    f"Fix the input files or choose a different compare mode.",
                    "error",
                )
                return

            cat_map = self._get_category_map() if cat_filter != "All (no filter)" else None

            result = diff_engine.diff_folder(
                Path(src), Path(tgt),
                mode=mode, category_filter=cat_filter, category_map=cat_map,
                log_fn=self.log,
                progress_fn=self.set_progress,
            )

            if self.app.path_filter_active:
                for lang in list(result.keys()):
                    result[lang] = self.filter_entries_by_path(result[lang])
                    if not result[lang]:
                        del result[lang]

            if not result:
                self.log("No differences found across languages.", "info")
                return

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = config.OUTPUT_DIR / f"diff_folder_{ts}"
            sort_key = self._diff_sort_key(mode)
            columns = self._diff_columns(mode)

            total = sum(len(v) for v in result.values())
            for lang, entries in sorted(result.items()):
                write_extraction_excel(
                    out_dir / f"DIFF_{lang}.xlsx", entries,
                    columns=columns, sheet_name="Diff",
                    header_bg="#5B4A8A", sort_key=sort_key,
                )
                write_locstr_xml(out_dir / f"DIFF_{lang}.xml", entries, sort_key=sort_key)

            self.log(f"Total: {total:,} entries across {len(result)} languages -> {out_dir}", "success")

        self.run_in_thread(work)

    def _run_revert(self) -> None:
        before = self._before_var.get().strip()
        after = self._after_var.get().strip()
        current = self._current_var.get().strip()
        if not all([before, after, current]):
            self.log("All three files (BEFORE, AFTER, CURRENT) are required.", "error")
            return

        if not messagebox.askyesno("Confirm Revert",
                                   f"This will modify:\n{current}\n\nProceed?"):
            return

        def work():
            self._log_header("Revert Changes")
            self.set_progress(10)

            # --- Column validation (BLOCKING) ---
            # Revert needs the same columns as Full mode
            revert_mode = "Full (all attributes)"
            blocked = False
            for fpath, flabel in [(before, "Before"), (after, "After")]:
                p = Path(fpath)
                if p.suffix.lower() in (".xlsx", ".xls"):
                    vr = validate_diff_excel_columns(p, revert_mode, label=flabel, log_fn=self.log)
                    if not vr.ok:
                        blocked = True
            if blocked:
                self.log(
                    "OPERATION BLOCKED: Excel file(s) missing columns required for revert.\n"
                    "Fix the input files or use XML files.",
                    "error",
                )
                return

            self.log(f"Parsing BEFORE: {Path(before).name}")
            before_entries, _ = input_parser.parse_input_file(Path(before), log_fn=self.log)
            self.set_progress(30)

            self.log(f"Parsing AFTER: {Path(after).name}")
            after_entries, _ = input_parser.parse_input_file(Path(after), log_fn=self.log)
            self.set_progress(60)

            self.log(f"Before: {len(before_entries):,} entries | After: {len(after_entries):,} entries")
            self.log(f"Reverting {Path(current).name}...")
            removed, restored = diff_engine.revert_entries(
                before_entries, after_entries, Path(current), log_fn=self.log,
            )
            self.log(f"Done: {removed} removed, {restored} restored.", "success")

        self.run_in_thread(work)
