"""File Eraser tab – move files whose stem matches source stems to backup."""

import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ..core import file_eraser_engine
from ..core.validators import validate_generic_folder
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class FileEraserTab(BaseTab):
    TAB_TITLE = "File Erase"

    def _build_ui(self) -> None:
        # Source folder (file stems to match)
        src = ttk.LabelFrame(self.frame, text="Source Folder (files whose stems to match)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "Folder:", self._src_var,
                            lambda: self.browse_folder(
                                self._src_var, "Select source folder",
                                on_selected=lambda p: validate_generic_folder(
                                    p, label="Source", log_fn=self.log)))

        # Target folder
        tgt = ttk.LabelFrame(self.frame, text="Target Folder (files to move)")
        tgt.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_var = tk.StringVar()
        self._make_path_row(tgt, "Folder:", self._tgt_var,
                            lambda: self.browse_folder(
                                self._tgt_var, "Select target folder",
                                on_selected=lambda p: validate_generic_folder(
                                    p, label="Target", log_fn=self.log)))

        # Warning
        warn = ttk.LabelFrame(self.frame, text="Warning")
        warn.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(warn, text="Files in target whose stem matches any source file stem\n"
                             "will be MOVED to Erased_Files/ backup folder.\n"
                             "Matching is case-insensitive on file stems.",
                  wraplength=500, justify=tk.LEFT, foreground="#C62828").pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Erase Matching Files", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        tgt = self._tgt_var.get().strip()
        if not src or not tgt:
            self.log("Source and target folders are required.", "error")
            return

        # Preview
        stems = file_eraser_engine.collect_source_stems(Path(src))
        matches = file_eraser_engine.find_matches(Path(tgt), stems)

        if not matches:
            self.log("No matching files found.", "info")
            return

        self.log(f"Preview: {len(stems):,} source stems, {len(matches):,} target matches")

        if not messagebox.askyesno(
            "Confirm File Erase",
            f"Found {len(matches)} files to move.\n\n"
            f"First 5:\n" + "\n".join(f.name for f in matches[:5]) +
            ("\n..." if len(matches) > 5 else "") +
            "\n\nProceed?",
        ):
            return

        def work():
            self._log_header("File Erase Operation")
            self.set_progress(5)

            moved, backup_dir = file_eraser_engine.erase_files(
                Path(src), Path(tgt),
                log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.9),
            )

            self.log(f"Done: {moved:,} files moved -> {backup_dir}", "success")

        self.run_in_thread(work)
