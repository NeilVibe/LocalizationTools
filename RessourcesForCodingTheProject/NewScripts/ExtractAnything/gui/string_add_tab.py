"""String Add tab – add missing LocStr nodes from source to target by key diff."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import config
from core import string_add_engine
from core.validators import validate_source_keys_folder, validate_xml_source_folder
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class StringAddTab(BaseTab):
    TAB_TITLE = "Str Add"

    def _build_ui(self) -> None:
        # Source folder
        src = ttk.LabelFrame(self.frame, text="Source (folder with entries to add)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "Folder:", self._src_var,
                            lambda: self.browse_folder(
                                self._src_var, "Select source folder",
                                on_selected=lambda p: validate_source_keys_folder(
                                    p, label="Source", log_fn=self.log)))

        # Target folder
        tgt = ttk.LabelFrame(self.frame, text="Target XMLs (to add entries into)")
        tgt.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_var = tk.StringVar()
        self._make_path_row(tgt, "Folder:", self._tgt_var,
                            lambda: self.browse_folder(
                                self._tgt_var, "Select target XML folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Target", log_fn=self.log)))

        # Info
        info = ttk.LabelFrame(self.frame, text="Info")
        info.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(info, text="MODIFIES TARGET: Adds LocStr entries that exist in source but not in target.\n"
                             "Matched by filename (case-insensitive). Key = StringID + StrOrigin.\n"
                             "2-step cascade match: exact normalised → nospace normalised.\n"
                             "Original LocStr format is preserved exactly (raw attributes).",
                  wraplength=500, justify=tk.LEFT, foreground="#1565C0").pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Add Missing Strings", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        tgt = self._tgt_var.get().strip()
        if not src or not tgt:
            self.log("Source and target folders are required.", "error")
            return

        if not messagebox.askyesno(
            "Confirm String Add",
            f"This will modify XML files in:\n{tgt}\n\n"
            "Missing LocStr entries from source will be ADDED.\nProceed?",
        ):
            return

        def work():
            self._log_header("String Add Operation")
            self.set_progress(5)

            total_added, report = string_add_engine.add_folder(
                Path(src), Path(tgt),
                log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.85),
            )

            self.set_progress(92)

            if report:
                report_path = string_add_engine.write_add_report(
                    report, config.OUTPUT_DIR / "add_reports",
                )
                self.log(f"Report: {report_path}")

            self.log(f"Done: {total_added:,} entries added.", "success")

        self.run_in_thread(work)
