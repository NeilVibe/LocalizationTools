"""
QuickCheck GUI

Single-window UI for LINE CHECK, TERM CHECK, LANG CHECK, and NUM CHECK across multiple languages.

Modes:
  - Auto-extract glossary: glossary is built from source files automatically
  - External glossary: separate folder with language-tagged glossary files

Settings (persisted):
  - Max term length, min occurrences, max issues per term
  - Filter sentences toggle
  - Term match mode: Isolated / Substring
"""
from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import config
from config import Settings, get_settings, save_settings, get_output_dir, MATCH_MODE_ISOLATED
from core.scanner import scan_folder_for_languages
from core.line_check import run_line_check_all_languages
from core.term_check import run_term_check_all_languages
from core.glossary_extractor import extract_glossary_all_languages
from core.lang_check import run_lang_check_all_languages
from core.number_check import run_number_check_all_languages
from core.category_mapper import load_cluster_config, build_export_indexes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour + style constants
# ---------------------------------------------------------------------------
BG_MAIN = "#2b2b2b"
BG_FRAME = "#333333"
BG_ENTRY = "#3c3f41"
FG_MAIN = "#bbbbbb"
FG_BRIGHT = "#ffffff"
FG_DIM = "#888888"
FG_OK = "#6dbf67"
FG_WARN = "#e0a050"
FG_ERR = "#e05050"
ACCENT = "#4c9be8"
BTN_BG = "#3c6ea0"
BTN_BG_HOVER = "#5580b0"
BTN_FG = "#ffffff"
FONT_MAIN = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SMALL = ("Segoe UI", 8)
FONT_MONO = ("Consolas", 9)


class QuickCheckApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"QuickCheck v{config.VERSION}")
        import sys as _sys
        _base = Path(getattr(_sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
        _icon = _base / "images" / "QCico.ico"
        if _icon.exists():
            try:
                self.iconbitmap(str(_icon))
            except Exception:
                pass
        self.configure(bg=BG_MAIN)
        self.resizable(True, True)
        self.minsize(640, 700)

        self._settings = get_settings()
        self._source_scan: Dict[str, List[Path]] = {}
        self._glossary_scan: Dict[str, List[Path]] = {}
        self._running = False
        self._last_scanned_source: str = ""
        self._suppress_save: bool = False
        self._save_after_id: Optional[str] = None
        self._lang_vars: Dict[str, tk.BooleanVar] = {}
        self._all_var: tk.BooleanVar = tk.BooleanVar(value=True)
        self._category_index: Dict[str, str] = {}
        self._filename_index: Dict[str, str] = {}

        self._build_ui()
        self._apply_settings_to_ui()

        # Load persisted EXPORT folder and build index if set
        if self._settings.export_folder:
            self._var_export.set(self._settings.export_folder)
            self._build_export_index()
        self.update_idletasks()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=BG_MAIN, padx=12, pady=10)
        outer.pack(fill=tk.BOTH, expand=True)

        # ---- Source folder ----
        self._build_folder_row(outer, "Source Folder:", self._browse_source, "_var_source")

        # ---- EXPORT folder (optional — enables Category/FileName columns) ----
        self._build_folder_row(outer, "EXPORT Folder:", self._browse_export, "_var_export")
        self._lbl_export_status = tk.Label(
            outer, text="EXPORT: (not set)", bg=BG_MAIN, fg=FG_DIM,
            font=FONT_SMALL, anchor="w",
        )
        self._lbl_export_status.pack(fill=tk.X, pady=(0, 4))

        # ---- Language selection (populated after folder scan) ----
        self._lang_check_frame = tk.Frame(outer, bg=BG_MAIN)
        self._lang_check_frame.pack(fill=tk.X, pady=(0, 6))
        self._lbl_no_langs = tk.Label(
            self._lang_check_frame,
            text="Languages: (select source folder to detect)",
            bg=BG_MAIN, fg=FG_DIM, font=FONT_SMALL, anchor="w",
        )
        self._lbl_no_langs.pack(anchor="w")

        # ---- Mode selection ----
        self._mode_frame = tk.LabelFrame(outer, text=" Glossary Mode ", bg=BG_FRAME,
                                         fg=FG_MAIN, font=FONT_BOLD, padx=8, pady=6)
        self._mode_frame.pack(fill=tk.X, pady=(0, 6))
        mode_frame = self._mode_frame

        self._var_mode = tk.StringVar(value="auto")
        tk.Radiobutton(
            mode_frame, text="Auto-extract from source files (self-check)",
            variable=self._var_mode, value="auto",
            bg=BG_FRAME, fg=FG_BRIGHT, selectcolor=BG_MAIN,
            activebackground=BG_FRAME, font=FONT_MAIN,
            command=self._on_mode_change,
        ).pack(anchor="w")
        tk.Radiobutton(
            mode_frame, text="External Glossary folder",
            variable=self._var_mode, value="external",
            bg=BG_FRAME, fg=FG_BRIGHT, selectcolor=BG_MAIN,
            activebackground=BG_FRAME, font=FONT_MAIN,
            command=self._on_mode_change,
        ).pack(anchor="w", pady=(2, 0))

        # ---- Glossary folder row (shown only in external mode) ----
        self._gloss_frame = tk.Frame(outer, bg=BG_MAIN)
        self._build_folder_row(self._gloss_frame, "Glossary Folder:", self._browse_glossary, "_var_glossary")
        self._lbl_gloss_detected = tk.Label(self._gloss_frame, text="Glossary Detected: (none)",
                                             bg=BG_MAIN, fg=FG_DIM, font=FONT_SMALL, anchor="w")
        self._lbl_gloss_detected.pack(fill=tk.X)
        # Initially hidden
        # self._gloss_frame.pack(fill=tk.X, pady=(0, 6))

        # ---- Settings section ----
        self._build_settings(outer)

        # ---- Action buttons (2 rows for clean layout) ----
        btn_frame = tk.LabelFrame(outer, text=" Checks ", bg=BG_FRAME,
                                  fg=FG_MAIN, font=FONT_BOLD, padx=8, pady=6)
        btn_frame.pack(fill=tk.X, pady=(4, 8))

        btn_row1 = tk.Frame(btn_frame, bg=BG_FRAME)
        btn_row1.pack(fill=tk.X, pady=(0, 4))
        self._btn_line = self._make_button(btn_row1, "LINE CHECK", self._run_line_check, width=18)
        self._btn_line.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_term = self._make_button(btn_row1, "TERM CHECK", self._run_term_check, width=18)
        self._btn_term.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_gloss = self._make_button(
            btn_row1, "EXTRACT GLOSSARY", self._run_extract_glossary, width=20
        )
        self._btn_gloss.pack(side=tk.LEFT)

        btn_row2 = tk.Frame(btn_frame, bg=BG_FRAME)
        btn_row2.pack(fill=tk.X)
        self._btn_lang = self._make_button(btn_row2, "LANG CHECK", self._run_lang_check, width=18)
        self._btn_lang.pack(side=tk.LEFT, padx=(0, 6))
        self._btn_num = self._make_button(btn_row2, "NUM CHECK", self._run_number_check, width=18)
        self._btn_num.pack(side=tk.LEFT)

        # ---- Progress bar ----
        self._progress_var = tk.DoubleVar(value=0)
        self._progressbar = ttk.Progressbar(outer, variable=self._progress_var,
                                            maximum=100, mode="indeterminate")
        self._progressbar.pack(fill=tk.X, pady=(0, 4))

        # ---- Status / log area ----
        log_frame = tk.Frame(outer, bg=BG_MAIN)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self._log = tk.Text(log_frame, height=10, bg=BG_ENTRY, fg=FG_MAIN,
                            font=FONT_MONO, relief=tk.FLAT, wrap=tk.WORD,
                            state=tk.DISABLED, insertbackground=FG_BRIGHT)
        scrollbar = tk.Scrollbar(log_frame, command=self._log.yview,
                                 bg=BG_FRAME, troughcolor=BG_MAIN)
        self._log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure log text tags
        self._log.tag_config("ok", foreground=FG_OK)
        self._log.tag_config("warn", foreground=FG_WARN)
        self._log.tag_config("err", foreground=FG_ERR)
        self._log.tag_config("info", foreground=ACCENT)

    def _build_folder_row(self, parent: tk.Widget, label: str,
                          command: callable, var_attr: str) -> None:
        """Build a labelled folder browser row."""
        row = tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill=tk.X, pady=(0, 2))
        tk.Label(row, text=label, bg=row.cget("bg"), fg=FG_MAIN, font=FONT_MAIN,
                 width=16, anchor="w").pack(side=tk.LEFT)
        var = tk.StringVar()
        setattr(self, var_attr, var)
        tk.Entry(row, textvariable=var, bg=BG_ENTRY, fg=FG_BRIGHT, font=FONT_MAIN,
                 relief=tk.FLAT, insertbackground=FG_BRIGHT).pack(
                     side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self._make_button(row, "Browse", command).pack(side=tk.LEFT)

    def _build_settings(self, parent: tk.Widget) -> None:
        """Build the settings section (always visible)."""
        sf = tk.LabelFrame(parent, text=" Settings ", bg=BG_FRAME, fg=FG_MAIN,
                           font=FONT_BOLD, padx=8, pady=6)
        sf.pack(fill=tk.X, pady=(0, 8))

        # Row 1: filter sentences + max term length
        r1 = tk.Frame(sf, bg=BG_FRAME)
        r1.pack(fill=tk.X, pady=(0, 4))

        self._var_filter_sentences = tk.BooleanVar(value=self._settings.filter_sentences)
        tk.Checkbutton(r1, text="Filter sentences (no phrases)",
                       variable=self._var_filter_sentences,
                       bg=BG_FRAME, fg=FG_BRIGHT, selectcolor=BG_MAIN,
                       activebackground=BG_FRAME, font=FONT_MAIN,
                       command=self._save_settings).pack(side=tk.LEFT)

        tk.Label(r1, text="Max term length:", bg=BG_FRAME, fg=FG_MAIN,
                 font=FONT_MAIN).pack(side=tk.LEFT, padx=(20, 4))
        self._var_max_len = tk.StringVar(value=str(self._settings.max_term_length))
        tk.Entry(r1, textvariable=self._var_max_len, width=5, bg=BG_ENTRY, fg=FG_BRIGHT,
                 font=FONT_MAIN, relief=tk.FLAT, insertbackground=FG_BRIGHT).pack(side=tk.LEFT)
        self._var_max_len.trace_add("write", lambda *_: self._save_settings())

        # Row 2: min occurrences + max issues per term
        r2 = tk.Frame(sf, bg=BG_FRAME)
        r2.pack(fill=tk.X, pady=(0, 4))

        tk.Label(r2, text="Min occurrences:", bg=BG_FRAME, fg=FG_MAIN,
                 font=FONT_MAIN).pack(side=tk.LEFT)
        self._var_min_occ = tk.StringVar(value=str(self._settings.min_occurrence))
        tk.Entry(r2, textvariable=self._var_min_occ, width=5, bg=BG_ENTRY, fg=FG_BRIGHT,
                 font=FONT_MAIN, relief=tk.FLAT, insertbackground=FG_BRIGHT).pack(
                     side=tk.LEFT, padx=(4, 20))
        self._var_min_occ.trace_add("write", lambda *_: self._save_settings())

        tk.Label(r2, text="Max issues per term:", bg=BG_FRAME, fg=FG_MAIN,
                 font=FONT_MAIN).pack(side=tk.LEFT)
        self._var_max_issues = tk.StringVar(value=str(self._settings.max_issues_per_term))
        tk.Entry(r2, textvariable=self._var_max_issues, width=5, bg=BG_ENTRY, fg=FG_BRIGHT,
                 font=FONT_MAIN, relief=tk.FLAT, insertbackground=FG_BRIGHT).pack(
                     side=tk.LEFT, padx=(4, 0))
        self._var_max_issues.trace_add("write", lambda *_: self._save_settings())

        # Term match mode — always Isolated (word boundary); substring hidden
        self._var_match_mode = tk.StringVar(value=MATCH_MODE_ISOLATED)

    def _make_button(self, parent: tk.Widget, text: str,
                     command: callable, width: int = 8) -> tk.Button:
        btn = tk.Button(parent, text=text, command=command, width=width,
                        bg=BTN_BG, fg=BTN_FG, font=FONT_BOLD, relief=tk.FLAT,
                        activebackground=BTN_BG_HOVER, activeforeground=BTN_FG,
                        cursor="hand2", padx=4)
        return btn

    # ------------------------------------------------------------------
    # Settings read/write
    # ------------------------------------------------------------------

    def _apply_settings_to_ui(self) -> None:
        self._suppress_save = True
        try:
            s = self._settings
            self._var_filter_sentences.set(s.filter_sentences)
            self._var_max_len.set(str(s.max_term_length))
            self._var_min_occ.set(str(s.min_occurrence))
            self._var_max_issues.set(str(s.max_issues_per_term))
        finally:
            self._suppress_save = False

    def _save_settings(self) -> None:
        """Schedule a debounced settings save (400ms after last change)."""
        if self._suppress_save:
            return
        if self._save_after_id is not None:
            try:
                self.after_cancel(self._save_after_id)
            except Exception:
                pass
        self._save_after_id = self.after(400, self._do_save_settings)

    def _do_save_settings(self) -> None:
        """Actually persist settings to disk."""
        self._save_after_id = None
        try:
            s = self._settings
            s.filter_sentences = self._var_filter_sentences.get()
            s.max_term_length = int(self._var_max_len.get() or str(config.DEFAULT_MAX_TERM_LENGTH))
            s.min_occurrence = int(self._var_min_occ.get() or str(config.DEFAULT_MIN_OCCURRENCE))
            s.max_issues_per_term = int(self._var_max_issues.get() or str(config.DEFAULT_MAX_ISSUES_PER_TERM))
            s.term_match_mode = MATCH_MODE_ISOLATED
            save_settings(s)
        except ValueError:
            pass  # Expected during partial typing
        except Exception:
            logger.warning("Settings save failed", exc_info=True)

    def _read_settings(self) -> Settings:
        """Flush any pending save and return current settings."""
        self._do_save_settings()
        return self._settings

    # ------------------------------------------------------------------
    # Browse callbacks
    # ------------------------------------------------------------------

    def _browse_source(self) -> None:
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self._var_source.set(path)
            self._scan_source(path)

    def _browse_glossary(self) -> None:
        path = filedialog.askdirectory(title="Select Glossary Folder")
        if path:
            self._var_glossary.set(path)
            self._scan_glossary(path)

    def _browse_export(self) -> None:
        if self._running:
            return
        path = filedialog.askdirectory(title="Select EXPORT Folder")
        if path:
            self._var_export.set(path)
            self._settings.export_folder = path
            save_settings(self._settings)
            self._build_export_index()

    def _build_export_index(self) -> None:
        """Scan EXPORT folder in a background thread to build category/filename indexes."""
        export_path = self._var_export.get()
        if not export_path:
            self._category_index = {}
            self._filename_index = {}
            self._lbl_export_status.configure(text="EXPORT: (not set)", fg=FG_DIM)
            return

        self._lbl_export_status.configure(text="EXPORT: Indexing...", fg=FG_WARN)
        self._set_buttons_state(tk.DISABLED)

        def worker() -> None:
            cluster_config = load_cluster_config(
                Path(config.get_base_dir()) / "category_clusters.json"
            )
            cat_idx, fn_idx = build_export_indexes(Path(export_path), cluster_config)
            self.after(0, self._on_export_index_done, cat_idx, fn_idx)

        threading.Thread(target=worker, daemon=True).start()

    def _on_export_index_done(self, cat_idx: Dict, fn_idx: Dict) -> None:
        self._category_index = cat_idx
        self._filename_index = fn_idx
        count = len(fn_idx)
        if count > 0:
            self._lbl_export_status.configure(
                text=f"EXPORT: {count} StringIDs indexed", fg=FG_OK,
            )
        else:
            self._lbl_export_status.configure(
                text="EXPORT: 0 files found \u2014 check folder path", fg=FG_WARN,
            )
        if not self._running:
            self._set_buttons_state(tk.NORMAL)

    # ------------------------------------------------------------------
    # Language scanning
    # ------------------------------------------------------------------

    def _scan_source(self, folder: str) -> None:
        result = scan_folder_for_languages(Path(folder))
        self._source_scan = result.lang_files
        self._last_scanned_source = folder
        self._rebuild_lang_checkboxes(result.get_languages())

    def _scan_glossary(self, folder: str) -> None:
        result = scan_folder_for_languages(Path(folder))
        self._glossary_scan = result.lang_files
        langs = result.get_languages()
        if langs:
            self._lbl_gloss_detected.configure(
                text=f"Glossary Detected: {' '.join(langs)} ({len(langs)} lang{'s' if len(langs) != 1 else ''})",
                fg=FG_OK
            )
        else:
            self._lbl_gloss_detected.configure(text="Glossary Detected: (none found)", fg=FG_WARN)

    def _rebuild_lang_checkboxes(self, langs: List[str]) -> None:
        """Rebuild language checkboxes after a folder scan."""
        for w in self._lang_check_frame.winfo_children():
            w.destroy()
        self._lang_vars.clear()

        if not langs:
            tk.Label(
                self._lang_check_frame,
                text="Languages: (no language-tagged files found)",
                bg=BG_MAIN, fg=FG_WARN, font=FONT_SMALL, anchor="w",
            ).pack(anchor="w")
            return

        tk.Label(
            self._lang_check_frame, text="Languages:",
            bg=BG_MAIN, fg=FG_MAIN, font=FONT_MAIN,
        ).pack(side=tk.LEFT, padx=(0, 6))

        self._all_var.set(True)
        tk.Checkbutton(
            self._lang_check_frame, text="ALL",
            variable=self._all_var,
            command=self._on_all_toggle,
            bg=BG_MAIN, fg=FG_BRIGHT, selectcolor=BG_MAIN,
            activebackground=BG_MAIN, font=FONT_BOLD,
        ).pack(side=tk.LEFT, padx=(0, 2))

        ttk.Separator(self._lang_check_frame, orient="vertical").pack(
            side=tk.LEFT, fill="y", padx=(4, 8), pady=2,
        )

        for lang in langs:
            var = tk.BooleanVar(value=True)
            self._lang_vars[lang] = var
            tk.Checkbutton(
                self._lang_check_frame, text=lang,
                variable=var,
                command=self._on_lang_toggle,
                bg=BG_MAIN, fg=FG_BRIGHT, selectcolor=BG_MAIN,
                activebackground=BG_MAIN, font=FONT_SMALL,
            ).pack(side=tk.LEFT, padx=(0, 2))

    def _on_all_toggle(self) -> None:
        state = self._all_var.get()
        for var in self._lang_vars.values():
            var.set(state)

    def _on_lang_toggle(self) -> None:
        all_checked = all(var.get() for var in self._lang_vars.values())
        self._all_var.set(all_checked)

    def _get_selected_lang_files(self) -> Dict[str, List[Path]]:
        """Return source_scan filtered to only selected language checkboxes."""
        if not self._lang_vars:
            return dict(self._source_scan)
        return {
            lang: files
            for lang, files in self._source_scan.items()
            if lang in self._lang_vars and self._lang_vars[lang].get()
        }

    def _on_mode_change(self) -> None:
        if self._var_mode.get() == "external":
            self._gloss_frame.pack(fill=tk.X, pady=(0, 6), after=self._mode_frame)
        else:
            self._gloss_frame.pack_forget()

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log_msg(self, msg: str, tag: str = "") -> None:
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, msg + "\n", tag)
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _log_clear(self) -> None:
        self._log.configure(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Pre-run validation
    # ------------------------------------------------------------------

    def _validate_run(self) -> bool:
        if self._running:
            return False
        if not self._var_source.get():
            messagebox.showwarning("QuickCheck", "Please select a source folder first.")
            return False
        # Re-scan if path changed (handles manual Entry edits, not just Browse)
        current_path = self._var_source.get()
        if not self._source_scan or current_path != self._last_scanned_source:
            self._scan_source(current_path)
        if not self._source_scan:
            messagebox.showwarning("QuickCheck",
                                   "No language-tagged files detected in source folder.\n"
                                   "Make sure subfolders/files have language code suffixes (e.g. FRE/, patch_GER.xml).")
            return False
        if not self._get_selected_lang_files():
            messagebox.showwarning("QuickCheck", "No languages selected.\nPlease check at least one language checkbox.")
            return False
        return True

    def _get_glossary_lang_files(self) -> Tuple[bool, Optional[Dict[str, list]]]:
        """
        Returns (ok, glossary_lang_files).
        ok=False means abort (validation failed).
        glossary_lang_files=None means auto-extract from source files.
        glossary_lang_files=dict means use external glossary files.
        """
        if self._var_mode.get() == "external":
            if not self._var_glossary.get():
                messagebox.showwarning("QuickCheck", "External Glossary mode selected but no glossary folder chosen.")
                return False, None
            if not self._glossary_scan:
                self._scan_glossary(self._var_glossary.get())
            if not self._glossary_scan:
                messagebox.showwarning("QuickCheck",
                                       "No language-tagged files found in glossary folder.")
                return False, None
            return True, self._glossary_scan
        # Auto-extract: None = use source files
        return True, None

    def _set_buttons_state(self, state: str) -> None:
        self._btn_line.configure(state=state)
        self._btn_term.configure(state=state)
        self._btn_gloss.configure(state=state)
        self._btn_lang.configure(state=state)
        self._btn_num.configure(state=state)

    # ------------------------------------------------------------------
    # LINE CHECK
    # ------------------------------------------------------------------

    def _run_line_check(self) -> None:
        if not self._validate_run():
            return
        self._running = True
        self._set_buttons_state(tk.DISABLED)
        self._log_clear()
        self._progressbar.configure(mode="indeterminate")
        self._progressbar.start(15)
        self._log_msg("Starting LINE CHECK...", "info")

        s = self._read_settings()
        lang_files = self._get_selected_lang_files()
        output_dir = Path(get_output_dir())

        def worker() -> None:
            try:
                results = run_line_check_all_languages(
                    lang_files=lang_files,
                    output_dir=output_dir,
                    filter_sentences=s.filter_sentences,
                    length_threshold=s.max_term_length,
                    min_occurrence=s.min_occurrence if s.min_occurrence > 1 else None,
                    progress_callback=lambda msg: self.after(0, self._log_msg, msg),
                )
                summary_parts = [f"{lang}({count})" for lang, count in sorted(results.items())]
                summary = "LINE CHECK done: " + " ".join(summary_parts)
                summary += f" — saved to {output_dir}"
                self.after(0, self._log_msg, summary, "ok")
            except Exception as exc:
                logger.exception("LINE CHECK failed")
                self.after(0, self._log_msg, f"ERROR: {exc}", "err")
            finally:
                self.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # TERM CHECK
    # ------------------------------------------------------------------

    def _run_term_check(self) -> None:
        if not self._validate_run():
            return

        ok, glossary_lang_files = self._get_glossary_lang_files()
        if not ok:
            return

        self._running = True
        self._set_buttons_state(tk.DISABLED)
        self._log_clear()
        self._progressbar.configure(mode="indeterminate")
        self._progressbar.start(15)
        mode_label = "external glossary" if glossary_lang_files else "auto-extract"
        self._log_msg(f"Starting TERM CHECK ({mode_label})...", "info")

        s = self._read_settings()
        lang_files = self._get_selected_lang_files()
        output_dir = Path(get_output_dir())
        cat_idx = self._category_index
        fn_idx = self._filename_index

        def worker() -> None:
            try:
                results = run_term_check_all_languages(
                    lang_files=lang_files,
                    output_dir=output_dir,
                    glossary_lang_files=glossary_lang_files,
                    filter_sentences=s.filter_sentences,
                    length_threshold=s.max_term_length,
                    min_occurrence=s.min_occurrence if s.min_occurrence > 1 else None,
                    max_issues_per_term=s.max_issues_per_term,
                    match_mode=s.term_match_mode,
                    progress_callback=lambda msg: self.after(0, self._log_msg, msg),
                    category_index=cat_idx,
                    filename_index=fn_idx,
                )
                summary_parts = [f"{lang}({count})" for lang, count in sorted(results.items())]
                summary = "TERM CHECK done: " + " ".join(summary_parts)
                summary += f" — saved to {output_dir}"
                self.after(0, self._log_msg, summary, "ok")
            except Exception as exc:
                logger.exception("TERM CHECK failed")
                self.after(0, self._log_msg, f"ERROR: {exc}", "err")
            finally:
                self.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # EXTRACT GLOSSARY
    # ------------------------------------------------------------------

    def _run_extract_glossary(self) -> None:
        if not self._validate_run():
            return
        self._running = True
        self._set_buttons_state(tk.DISABLED)
        self._log_clear()
        self._progressbar.configure(mode="indeterminate")
        self._progressbar.start(15)
        self._log_msg("Starting EXTRACT GLOSSARY...", "info")

        s = self._read_settings()
        lang_files = self._get_selected_lang_files()
        output_dir = Path(get_output_dir())

        def worker() -> None:
            try:
                results = extract_glossary_all_languages(
                    lang_files=lang_files,
                    output_dir=output_dir,
                    max_term_length=s.max_term_length,
                    min_occurrence=s.min_occurrence if s.min_occurrence > 0 else 2,
                    filter_sentences=s.filter_sentences,
                    progress_callback=lambda msg: self.after(0, self._log_msg, msg),
                )
                summary_parts = [f"{lang}({count})" for lang, count in sorted(results.items())]
                summary = "GLOSSARY done: " + " ".join(summary_parts)
                summary += f" — saved to {output_dir}"
                self.after(0, self._log_msg, summary, "ok")
            except Exception as exc:
                logger.exception("EXTRACT GLOSSARY failed")
                self.after(0, self._log_msg, f"ERROR: {exc}", "err")
            finally:
                self.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # LANG CHECK
    # ------------------------------------------------------------------

    def _run_lang_check(self) -> None:
        if not self._validate_run():
            return
        self._running = True
        self._set_buttons_state(tk.DISABLED)
        self._log_clear()
        self._progressbar.configure(mode="indeterminate")
        self._progressbar.start(15)
        self._log_msg("Starting LANG CHECK...", "info")

        s = self._read_settings()
        lang_files = self._get_selected_lang_files()
        output_dir = Path(get_output_dir())

        def worker() -> None:
            try:
                results = run_lang_check_all_languages(
                    lang_files=lang_files,
                    output_dir=output_dir,
                    min_text_length=s.min_lang_text_length,
                    confidence_threshold=s.lang_confidence,
                    progress_callback=lambda msg: self.after(0, self._log_msg, msg),
                )
                summary_parts = [f"{lang}({count})" for lang, count in sorted(results.items())]
                summary = "LANG CHECK done: " + " ".join(summary_parts)
                summary += f" — saved to {output_dir}"
                self.after(0, self._log_msg, summary, "ok")
            except Exception as exc:
                logger.exception("LANG CHECK failed")
                self.after(0, self._log_msg, f"ERROR: {exc}", "err")
            finally:
                self.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # NUMBER CHECK
    # ------------------------------------------------------------------

    def _run_number_check(self) -> None:
        if not self._validate_run():
            return
        self._running = True
        self._set_buttons_state(tk.DISABLED)
        self._log_clear()
        self._progressbar.configure(mode="indeterminate")
        self._progressbar.start(15)
        self._log_msg("Starting NUM CHECK...", "info")

        lang_files = self._get_selected_lang_files()
        output_dir = Path(get_output_dir())
        cat_idx = self._category_index

        def worker() -> None:
            try:
                results = run_number_check_all_languages(
                    lang_files=lang_files,
                    output_dir=output_dir,
                    progress_callback=lambda msg: self.after(0, self._log_msg, msg),
                    category_index=cat_idx,
                )
                summary_parts = [f"{lang}({count})" for lang, count in sorted(results.items())]
                summary = "NUM CHECK done: " + " ".join(summary_parts)
                summary += f" — saved to {output_dir}"
                self.after(0, self._log_msg, summary, "ok")
            except Exception as exc:
                logger.exception("NUM CHECK failed")
                self.after(0, self._log_msg, f"ERROR: {exc}", "err")
            finally:
                self.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self) -> None:
        try:
            self._progressbar.stop()
            self._progressbar.configure(mode="determinate")
            self._progress_var.set(0)
        except Exception:
            pass
        self._set_buttons_state(tk.NORMAL)
        self._running = False
