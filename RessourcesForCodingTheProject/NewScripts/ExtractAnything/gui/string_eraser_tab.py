"""String Eraser tab – remove LocStr nodes from XML folder by key match against source file."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import config
from core import string_eraser_engine
from core.validators import validate_xml_source_folder
from .base_tab import BaseTab

logger = logging.getLogger(__name__)

_XML_FILETYPES = [("XML files", "*.xml"), ("All files", "*.*")]


class StringEraserTab(BaseTab):
    TAB_TITLE = "Str Erase"

    def _build_ui(self) -> None:
        # Source file (keys to erase)
        src = ttk.LabelFrame(self.frame, text="Source XML (entries to erase)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "File:", self._src_var,
                            lambda: self.browse_file(
                                self._src_var, "Select source XML file",
                                filetypes=_XML_FILETYPES))

        # Target folder
        tgt = ttk.LabelFrame(self.frame, text="Target XMLs folder (to erase from)")
        tgt.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_var = tk.StringVar()
        self._make_path_row(tgt, "Folder:", self._tgt_var,
                            lambda: self.browse_folder(
                                self._tgt_var, "Select target XML folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Target", log_fn=self.log)))

        # Warning
        warn = ttk.LabelFrame(self.frame, text="Warning")
        warn.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(warn, text="DESTRUCTIVE: This modifies target XMLs in-place!\n"
                             "LocStr nodes matching (StringID + StrOrigin) from source file\n"
                             "will be removed from ALL XMLs in target folder.",
                  wraplength=500, justify=tk.LEFT, foreground="#C62828").pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Erase Matching Strings", command=self._run).pack(pady=10)

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
            "Confirm String Erase",
            f"Source: {src_path.name}\n\n"
            f"This will scan {xml_count} XML files in:\n{tgt_path}\n\n"
            "Matching LocStr nodes will be REMOVED.\nProceed?",
        ):
            return

        def work():
            self._log_header("String Erase Operation")
            self.set_progress(5)

            total_erased, report = string_eraser_engine.erase_folder_from_file(
                src_path, tgt_path,
                log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.85),
            )

            self.set_progress(92)

            if report:
                report_path = string_eraser_engine.write_erase_report(
                    report, config.OUTPUT_DIR / "erase_reports",
                )
                self.log(f"Report: {report_path}")

            self.log(f"Done: {total_erased:,} entries erased.", "success")

        self.run_in_thread(work)
