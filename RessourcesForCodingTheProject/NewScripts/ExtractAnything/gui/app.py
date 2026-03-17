"""Main application window – PanedWindow, Notebook, shared log, settings bar."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

import config
from core.export_index import ExportIndex, build_export_index
from core.language_utils import invalidate_code_cache
from core.path_filter import precompute_path_filter, filter_entries_by_path as _filter_by_path
from core.validators import validate_loc_folder, validate_export_folder

logger = logging.getLogger(__name__)

_POLL_MS = 50


class ExtractAnythingApp:
    """Top-level application managing tabs, log, and shared state."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"ExtractAnything v{config.VERSION}")
        import sys as _sys
        _base = Path(getattr(_sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
        _icon = _base / "images" / "EAico.ico"
        if _icon.exists():
            try:
                self.root.iconbitmap(str(_icon))
            except Exception:
                pass
        self.root.geometry("1100x700")
        self.root.minsize(900, 550)

        self._msg_queue: queue.Queue = queue.Queue()
        self._busy = False
        self._export_index: ExportIndex | None = None
        self._path_selections: list[str] = config.load_path_filter_rules()
        self._path_prefixes: tuple[str, ...] = ()
        self._path_files: frozenset[str] = frozenset()
        if self._path_selections:
            self._path_prefixes, self._path_files = precompute_path_filter(self._path_selections)

        # StringVars for settings bar
        self._loc_var = tk.StringVar(value=str(config.LOC_FOLDER or ""))
        self._export_var = tk.StringVar(value=str(config.EXPORT_FOLDER or ""))

        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Main pane: left (tabs) | right (log)
        pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))

        # --- Left: Notebook ---
        left = ttk.Frame(pane)
        pane.add(left, weight=3)

        self.notebook = ttk.Notebook(left)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # --- Right: Log panel ---
        right = ttk.Frame(pane)
        pane.add(right, weight=2)

        log_label = ttk.Label(right, text="Log", font=("Segoe UI", 10, "bold"))
        log_label.pack(anchor="w", padx=5, pady=(2, 0))

        self._log_text = scrolledtext.ScrolledText(
            right, wrap=tk.WORD, font=("Consolas", 9), state="normal",
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Log tags
        self._log_text.tag_configure("info", foreground="#333333")
        self._log_text.tag_configure("success", foreground="#2E7D32")
        self._log_text.tag_configure("warning", foreground="#E65100")
        self._log_text.tag_configure("error", foreground="#C62828", font=("Consolas", 9, "bold"))
        self._log_text.tag_configure("header", foreground="#1565C0", font=("Consolas", 10, "bold"))

        # Clear log button
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(btn_frame, text="Clear Log", command=self._clear_log).pack(side=tk.RIGHT)

        # --- Bottom settings bar ---
        self._build_settings_bar()

        # --- Register tabs (deferred import to avoid circular) ---
        self._register_tabs()

    def _build_settings_bar(self) -> None:
        bar = ttk.Frame(self.root)
        bar.pack(fill=tk.X, padx=5, pady=(0, 5))

        # LOC
        ttk.Label(bar, text="LOC:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(bar, textvariable=self._loc_var, width=30).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(bar, text="...", width=3,
                   command=self._browse_loc).pack(side=tk.LEFT, padx=(0, 8))

        # EXPORT
        ttk.Label(bar, text="EXPORT:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(bar, textvariable=self._export_var, width=30).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(bar, text="...", width=3,
                   command=self._browse_export).pack(side=tk.LEFT, padx=(0, 8))

        # Save
        ttk.Button(bar, text="Save", command=self._save_settings).pack(side=tk.LEFT, padx=(0, 8))

        # Path Filter
        ttk.Button(bar, text="Path Filter...", command=self._open_path_filter_dialog).pack(side=tk.LEFT, padx=(0, 2))
        self._path_filter_label = tk.Label(bar, text="", fg="#1565C0", font=("Segoe UI", 8))
        self._path_filter_label.pack(side=tk.LEFT, padx=(0, 8))
        self._update_path_filter_label()

        # Output label
        ttk.Label(bar, text=f"Output: {config.OUTPUT_DIR}").pack(side=tk.LEFT, padx=(0, 8))

        # Progress bar
        self._progress = ttk.Progressbar(bar, mode="determinate", length=150)
        self._progress.pack(side=tk.RIGHT, padx=(8, 0))

    def _register_tabs(self) -> None:
        from .extract_tab import ExtractTab
        from .diff_tab import DiffTab
        from .long_string_tab import LongStringTab
        from .novoice_tab import NoVoiceTab
        from .blacklist_tab import BlacklistTab
        from .string_eraser_tab import StringEraserTab
        from .string_add_tab import StringAddTab
        from .file_eraser_tab import FileEraserTab
        from .xml_tools_tab import XmlToolsTab

        self.tabs = [
            ExtractTab(self.notebook, self),
            DiffTab(self.notebook, self),
            LongStringTab(self.notebook, self),
            NoVoiceTab(self.notebook, self),
            BlacklistTab(self.notebook, self),
            StringEraserTab(self.notebook, self),
            StringAddTab(self.notebook, self),
            FileEraserTab(self.notebook, self),
            XmlToolsTab(self.notebook, self),
        ]

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def _browse_loc(self) -> None:
        path = filedialog.askdirectory(title="Select LOC folder")
        if path:
            self._loc_var.set(path)
            invalidate_code_cache()
            validate_loc_folder(Path(path), log_fn=self.log_msg)

    def _browse_export(self) -> None:
        path = filedialog.askdirectory(title="Select EXPORT folder")
        if path:
            self._export_var.set(path)
            validate_export_folder(Path(path), log_fn=self.log_msg)

    def _save_settings(self) -> None:
        loc = self._loc_var.get().strip()
        exp = self._export_var.get().strip()

        kwargs = {}
        if loc:
            kwargs["loc_folder"] = loc
            # Invalidate language code cache when LOC changes
            if str(config.LOC_FOLDER) != loc:
                invalidate_code_cache()
        if exp:
            kwargs["export_folder"] = exp
            # Invalidate cached index when EXPORT changes
            if self._export_index and str(config.EXPORT_FOLDER) != exp:
                self._export_index.invalidate()
                self._export_index = None

        if kwargs:
            config.update_settings(**kwargs)
            self.log_msg("Settings saved.", "success")
        else:
            self.log_msg("Nothing to save.", "warning")

    @property
    def loc_folder(self) -> Path | None:
        val = self._loc_var.get().strip()
        return Path(val) if val else config.LOC_FOLDER

    @property
    def export_folder(self) -> Path | None:
        val = self._export_var.get().strip()
        return Path(val) if val else config.EXPORT_FOLDER

    # ------------------------------------------------------------------
    # Export index (cached)
    # ------------------------------------------------------------------
    def get_export_index(self, progress_fn=None) -> ExportIndex:
        if self._export_index and self._export_index.is_built:
            return self._export_index

        ef = self.export_folder
        if not ef or not ef.is_dir():
            self.log_msg("EXPORT folder not set or invalid.", "error")
            return ExportIndex()

        self.log_msg("Building EXPORT index (first use)...", "header")
        idx = build_export_index(ef, progress_fn=progress_fn)
        self._export_index = idx
        self.log_msg(
            f"EXPORT index ready: {len(idx.category_map)} categories, "
            f"{len(idx.voiced_sids)} voiced SIDs",
            "success",
        )
        return idx

    # ------------------------------------------------------------------
    # Path filter
    # ------------------------------------------------------------------
    @property
    def path_filter_active(self) -> bool:
        return bool(self._path_selections)

    @property
    def path_filter_count(self) -> int:
        return len(self._path_selections)

    def filter_entries_by_path(self, entries: list[dict]) -> list[dict]:
        """Apply current path filter. Returns entries unchanged if inactive."""
        if not self._path_selections:
            return entries
        idx = self._export_index
        path_map = idx.path_map if idx and idx.is_built else {}
        return _filter_by_path(entries, path_map, self._path_prefixes, self._path_files)

    def _open_path_filter_dialog(self) -> None:
        ef = self.export_folder
        if not ef or not ef.is_dir():
            self.log_msg("Set EXPORT folder first.", "warning")
            return

        from .path_filter_dialog import PathFilterDialog
        dlg = PathFilterDialog(self.root, ef, self._path_selections, mode="include")
        if dlg.result is not None:
            self._path_selections = dlg.result
            self._path_prefixes, self._path_files = precompute_path_filter(self._path_selections)
            config.save_path_filter_rules(self._path_selections)
            self._update_path_filter_label()
            if self._path_selections:
                self.log_msg(f"Path filter saved: {len(self._path_selections)} paths selected.", "success")
            else:
                self.log_msg("Path filter cleared.", "info")

    def _update_path_filter_label(self) -> None:
        n = len(self._path_selections)
        if n:
            self._path_filter_label.configure(text=f"({n} path{'s' if n != 1 else ''})")
        else:
            self._path_filter_label.configure(text="")

    # ------------------------------------------------------------------
    # Thread-safe logging
    # ------------------------------------------------------------------
    def log_msg(self, msg: str, tag: str = "info") -> None:
        self._msg_queue.put(("log", msg, tag))

    def set_progress(self, value: float) -> None:
        self._msg_queue.put(("progress", value))

    def signal_done(self) -> None:
        self._msg_queue.put(("done",))

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._msg_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    _, msg, tag = item
                    self._append_log(msg, tag)
                elif kind == "progress":
                    self._progress["value"] = item[1]
                elif kind == "done":
                    self._busy = False
                    self._progress["value"] = 100
        except queue.Empty:
            pass
        self.root.after(_POLL_MS, self._poll_queue)

    _MAX_LOG_LINES = 5000

    def _append_log(self, msg: str, tag: str) -> None:
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.insert(tk.END, f"[{ts}] {msg}\n", tag)
        # Auto-truncate to prevent memory growth
        line_count = int(self._log_text.index("end-1c").split(".")[0])
        if line_count > self._MAX_LOG_LINES:
            excess = line_count - self._MAX_LOG_LINES
            self._log_text.delete("1.0", f"{excess}.0")
        self._log_text.see(tk.END)

    def _clear_log(self) -> None:
        self._log_text.delete("1.0", tk.END)

    # ------------------------------------------------------------------
    # Threading
    # ------------------------------------------------------------------
    def run_in_thread(self, work_fn, on_done=None) -> None:
        if self._busy:
            self.log_msg("A task is already running. Please wait.", "warning")
            return
        self._busy = True
        self._progress["value"] = 0

        def _worker():
            try:
                work_fn()
            except Exception as exc:
                self.log_msg(f"ERROR: {exc}", "error")
                logger.exception("Worker thread error")
            finally:
                self.signal_done()
                if on_done:
                    on_done()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
