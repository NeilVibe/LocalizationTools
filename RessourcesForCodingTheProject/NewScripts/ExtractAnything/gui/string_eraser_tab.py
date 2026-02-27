"""String Eraser tab – remove LocStr nodes from XML by key match."""

import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import config
from core import string_eraser_engine
from core.validators import validate_source_keys_folder, validate_xml_source_folder
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class StringEraserTab(BaseTab):
    TAB_TITLE = "Str Erase"

    def _build_ui(self) -> None:
        # Source keys
        src = ttk.LabelFrame(self.frame, text="Source Keys (folder with XML/Excel)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "Folder:", self._src_var,
                            lambda: self.browse_folder(
                                self._src_var, "Select source keys folder",
                                on_selected=lambda p: validate_source_keys_folder(
                                    p, label="Source Keys", log_fn=self.log)))

        # Target XMLs
        tgt = ttk.LabelFrame(self.frame, text="Target XMLs (to erase from)")
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
                             "LocStr nodes matching (StringID + StrOrigin) will be removed.\n"
                             "2-step cascade: exact normalised -> nospace normalised.",
                  wraplength=500, justify=tk.LEFT, foreground="#C62828").pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Erase Matching Strings", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        tgt = self._tgt_var.get().strip()
        if not src or not tgt:
            self.log("Source and target folders are required.", "error")
            return

        if not messagebox.askyesno(
            "Confirm String Erase",
            f"This will modify XML files in:\n{tgt}\n\n"
            "Matching LocStr nodes will be REMOVED.\nProceed?",
        ):
            return

        def work():
            self._log_header("String Erase Operation")
            self.set_progress(5)

            total_erased, report = string_eraser_engine.erase_folder(
                Path(src), Path(tgt),
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
