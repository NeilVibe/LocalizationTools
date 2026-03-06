"""String Add tab – add missing LocStr nodes from source file to target file."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import config
from core import string_add_engine
from .base_tab import BaseTab

logger = logging.getLogger(__name__)

_XML_FILETYPES = [("XML files", "*.xml"), ("All files", "*.*")]


class StringAddTab(BaseTab):
    TAB_TITLE = "Str Add"

    def _build_ui(self) -> None:
        # Source file
        src = ttk.LabelFrame(self.frame, text="Source XML (entries to add)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "File:", self._src_var,
                            lambda: self.browse_file(
                                self._src_var, "Select source XML file",
                                filetypes=_XML_FILETYPES))

        # Target file
        tgt = ttk.LabelFrame(self.frame, text="Target XML (to add entries into)")
        tgt.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_var = tk.StringVar()
        self._make_path_row(tgt, "File:", self._tgt_var,
                            lambda: self.browse_file(
                                self._tgt_var, "Select target XML file",
                                filetypes=_XML_FILETYPES))

        # Info
        info = ttk.LabelFrame(self.frame, text="Info")
        info.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(info, text="MODIFIES TARGET: Adds LocStr entries that exist in source but not in target.\n"
                             "Key = StringID + StrOrigin (2-step cascade: exact → nospace).\n"
                             "Original LocStr format is preserved exactly (raw attributes).\n"
                             "A .bak backup is created before writing.",
                  wraplength=500, justify=tk.LEFT, foreground="#1565C0").pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Add Missing Strings", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        tgt = self._tgt_var.get().strip()
        if not src or not tgt:
            self.log("Source and target files are required.", "error")
            return

        src_path = Path(src)
        tgt_path = Path(tgt)

        if not src_path.is_file():
            self.log(f"Source file not found: {src_path.name}", "error")
            return
        if not tgt_path.is_file():
            self.log(f"Target file not found: {tgt_path.name}", "error")
            return

        if not messagebox.askyesno(
            "Confirm String Add",
            f"This will modify:\n{tgt_path.name}\n\n"
            f"Missing entries from {src_path.name} will be ADDED.\nProceed?",
        ):
            return

        def work():
            self._log_header("String Add Operation")
            self.set_progress(10)

            total_added, report = string_add_engine.add_missing(
                src_path, tgt_path, log_fn=self.log,
            )

            self.set_progress(90)

            if report:
                report_path = string_add_engine.write_add_report(
                    report, config.OUTPUT_DIR / "add_reports",
                )
                self.log(f"Report: {report_path}")

            self.log(f"Done: {total_added:,} entries added.", "success")

        self.run_in_thread(work)
