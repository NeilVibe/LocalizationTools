"""Abstract base class for all ExtractAnything tabs."""

from __future__ import annotations

import logging
import tkinter as tk
from abc import ABC, abstractmethod
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable

logger = logging.getLogger(__name__)


class BaseTab(ABC):
    """Common interface and helpers for every tab."""

    TAB_TITLE: str = "Tab"

    def __init__(self, parent: ttk.Notebook, app) -> None:
        self.app = app
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text=self.TAB_TITLE)
        self._build_ui()

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------
    @abstractmethod
    def _build_ui(self) -> None:
        """Create all widgets inside ``self.frame``."""

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def log(self, msg: str, tag: str = "info") -> None:
        self.app.log_msg(msg, tag)

    def set_progress(self, value: float) -> None:
        self.app.set_progress(value)

    def browse_file(self, var: tk.StringVar, title: str = "Select file",
                    filetypes: list | None = None,
                    on_selected: Callable[[Path], None] | None = None) -> None:
        ft = filetypes or [("All files", "*.*")]
        path = filedialog.askopenfilename(title=title, filetypes=ft)
        if path:
            var.set(path)
            if on_selected:
                on_selected(Path(path))

    def browse_folder(self, var: tk.StringVar, title: str = "Select folder",
                      on_selected: Callable[[Path], None] | None = None) -> None:
        path = filedialog.askdirectory(title=title)
        if path:
            var.set(path)
            if on_selected:
                on_selected(Path(path))

    def get_export_index(self, progress_fn=None):
        """Return the cached :class:`ExportIndex` (builds on first call)."""
        return self.app.get_export_index(progress_fn)

    def filter_entries_by_path(self, entries: list[dict]) -> list[dict]:
        """Apply path filter. Pass-through if no filter active."""
        return self.app.filter_entries_by_path(entries)

    def run_in_thread(self, work_fn, on_done=None) -> None:
        """Run *work_fn* in a daemon thread via the app's thread manager."""
        self.app.run_in_thread(work_fn, on_done)

    def _make_path_row(self, parent, label_text: str, var: tk.StringVar,
                       browse_cmd, *, row: int = 0) -> None:
        """Helper: create a Label + Entry + Browse button row in a grid."""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=(5, 2), pady=2)
        ttk.Entry(parent, textvariable=var, width=60).grid(row=row, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(parent, text="Browse", command=browse_cmd).grid(row=row, column=2, padx=(2, 5), pady=2)
        parent.columnconfigure(1, weight=1)

    def _log_header(self, title: str) -> None:
        """Log an operation header with separator."""
        sep = "\u2500" * 50  # ─
        self.log(sep, "header")
        self.log(f"  {title}", "header")
        self.log(sep, "header")
