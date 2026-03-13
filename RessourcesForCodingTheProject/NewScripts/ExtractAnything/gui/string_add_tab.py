"""String Add tab – add missing LocStr nodes from source file to target folder."""

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

        # Target folder
        tgt = ttk.LabelFrame(self.frame, text="Target XMLs folder (to add entries into)")
        tgt.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_var = tk.StringVar()
        self._make_path_row(tgt, "Folder:", self._tgt_var,
                            lambda: self.browse_folder(
                                self._tgt_var, "Select target XML folder"))

        # Info
        info = ttk.LabelFrame(self.frame, text="Info")
        info.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(info, text="MODIFIES TARGETS: Adds LocStr entries from source file\n"
                             "to ALL XML files in the target folder (recursive).\n"
                             "Key = StringID + StrOrigin (2-step cascade: exact → nospace).",
                  wraplength=500, justify=tk.LEFT, foreground="#1565C0").pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Add Missing Strings", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        tgt = self._tgt_var.get().strip()
        if not src or not tgt:
            self.log("Source file and target folder are required.", "error")
            return

        src_path = Path(src)
        tgt_path = Path(tgt)

        if not src_path.is_file():
            self.log(f"Source file not found: {src_path.name}", "error")
            return
        if not tgt_path.is_dir():
            self.log(f"Target folder not found: {tgt_path}", "error")
            return

        xml_count = len(list(tgt_path.rglob("*.xml")))
        if not messagebox.askyesno(
            "Confirm String Add",
            f"Source: {src_path.name}\n\n"
            f"This will scan {xml_count} XML files in:\n{tgt_path}\n\n"
            f"Missing entries will be ADDED.\nProceed?",
        ):
            return

        def work():
            self._log_header("String Add Operation")
            self.set_progress(5)

            total_added, report = string_add_engine.add_missing_folder(
                src_path, tgt_path,
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
