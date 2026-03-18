"""
QuickTranslate GUI Application.

Tkinter-based GUI with folder-only source mode (auto-detects XML + Excel):
- Match Type Selection: StringID-only / Strict / StrOrigin Only
- Tabbed layout: Transfer (main workflow) + Other Tools (Find Missing)
- Pre-submission checks with Empty Str detection
- Settings panel for path configuration
- Detailed logging and reporting
"""

import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import threading
import queue

import os
import subprocess
import sys

import config

logger = logging.getLogger(__name__)


class _GUILogHandler(logging.Handler):
    """Bridges Python logging → GUI log panel.

    Every logger.info/warning/error call from ANY module automatically
    appears in both the terminal (StreamHandler) AND the GUI ScrolledText.
    Thread-safe: uses the app's task queue for cross-thread delivery.
    """

    _LEVEL_TO_TAG = {
        logging.DEBUG: 'info',
        logging.INFO: 'info',
        logging.WARNING: 'warning',
        logging.ERROR: 'error',
        logging.CRITICAL: 'error',
    }

    def __init__(self, app: 'QuickTranslateApp'):
        super().__init__()
        self._app = app

    def emit(self, record: logging.LogRecord):
        try:
            # Skip if app window is destroyed
            if not self._app.root.winfo_exists():
                return
            msg = self.format(record)
            tag = self._LEVEL_TO_TAG.get(record.levelno, 'info')
            # Multi-line messages (e.g. tree tables): log each line
            for line in msg.split('\n'):
                if line.strip():
                    self._app._log(line, tag)
        except (tk.TclError, RuntimeError):
            pass  # App shutting down
        except Exception:
            self.handleError(record)


from core import (
    build_sequencer_strorigin_index,
    discover_language_files,
    build_translation_lookup,
    detect_excel_columns,
    read_corrections_from_excel,
    parse_corrections_from_xml,
    # TRANSFER functions
    transfer_folder_to_folder,
    format_transfer_report,
    # Source scanner (auto-recursive language detection)
    scan_source_for_languages,
    # Target scanner (flexible target detection)
    scan_target_for_languages,
    TargetScanResult,
    # Transfer plan (full tree table)
    generate_transfer_plan,
    format_transfer_plan,
    # Failure reports (XML + Excel)
    generate_failed_merge_xml_per_language,
    extract_failed_from_folder_results,
    extract_mismatch_target_entries,
    generate_failure_report_excel,
    generate_fuzzy_report_excel,
    check_xlsxwriter_available,
)
from core.missing_translation_finder import find_missing_with_options
from core.checker import run_korean_check, run_pattern_check, check_broken_xml_in_file, check_formula_text_in_file, check_text_integrity_in_file
from core.quality_checker import run_quality_check
from gui.missing_params_dialog import MissingParamsDialog
from gui.exclude_dialog import ExcludeDialog
from core.fuzzy_matching import (
    check_model_available,
    load_model,
    build_faiss_index,
    build_index_from_folder,
    get_cached_index_info,
    clear_cache as clear_fuzzy_cache,
)
from core.language_loader import build_stringid_to_category, build_stringid_to_subfolder, build_stringid_to_filepath


class QuickTranslateApp:
    """Main GUI application for QuickTranslate."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"QuickTranslate v{config.VERSION}")
        _base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
        _icon = _base / "images" / "QTico.ico"
        if _icon.exists():
            try:
                self.root.iconbitmap(str(_icon))
            except Exception:
                pass
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = max(1400, int(screen_w * 0.8))
        win_h = max(900, int(screen_h * 0.8))
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.resizable(True, True)
        self.root.minsize(1200, 700)
        self.root.configure(bg='#f0f0f0')

        # Variables
        self.match_type = tk.StringVar(value="strict")  # stringid_only, strict, strorigin_only

        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()

        # Fuzzy matching variables
        self.fuzzy_threshold = tk.DoubleVar(value=config.FUZZY_THRESHOLD_DEFAULT)
        self.fuzzy_model_status = tk.StringVar(value="Not loaded")

        # Shared match precision: "perfect" (exact) or "fuzzy" (Model2Vec)
        # Used by Strict and StrOrigin Only modes
        self.match_precision = tk.StringVar(value="perfect")

        # Source column availability (set by _validate_source_files_async)
        self._source_columns = {
            "has_stringid": False,
            "has_strorigin": False,
            "has_correction": False,
            "has_eventname": False,
            "has_dialogvoice": False,
            "has_desc": False,
            "has_descorigin": False,
            "has_xml": False,  # XML source files always provide all fields
        }
        self._match_type_radios = {}  # value -> Radiobutton widget

        # Transfer scope: "all" = overwrite always, "untranslated" = only if target has Korean
        self.transfer_scope = tk.StringVar(value="all")

        # Unique-only filtering for StrOrigin-Only mode (skip duplicate StrOrigin)
        self.unique_only_strorigin = tk.IntVar(value=0)

        # Non-Script Only for Strict mode (skip Dialog/Sequencer)
        _presub = config.load_presubmission_settings()
        self._strict_non_script_var = tk.BooleanVar(
            value=_presub.get("strict_non_script_only", False)
        )

        # StringID-Only: ALL categories override (default OFF = SCRIPT only)
        self._stringid_all_var = tk.BooleanVar(value=False)

        # Settings variables
        self.settings_loc_path = tk.StringVar()
        self.settings_export_path = tk.StringVar()

        self.status_text = tk.StringVar(value="Ready")
        self.progress_value = tk.DoubleVar(value=0)

        # Cached data
        self.strorigin_index: Optional[Dict[str, str]] = None
        self.translation_lookup: Optional[Dict[str, Dict[str, str]]] = None
        self.stringid_to_category: Optional[Dict[str, str]] = None
        self.stringid_to_subfolder: Optional[Dict[str, str]] = None
        self.stringid_to_filepath: Optional[Dict[str, str]] = None
        self.available_langs: Optional[List[str]] = None
        self.cached_paths: Optional[tuple] = None  # (loc_path, export_path)

        # Fuzzy matching cache
        self._fuzzy_model = None
        self._fuzzy_index = None
        self._fuzzy_index_path = None  # Track which target folder was indexed
        self._fuzzy_index_filter = None  # Track stringid_filter used for cached index
        self._fuzzy_index_untranslated = None  # Track only_untranslated used for cached index
        self._fuzzy_texts = None
        self._fuzzy_entries = None

        # Exclude rules for Missing Translations
        self._exclude_paths: List[str] = config.load_exclude_rules()

        # Threading infrastructure
        self._task_queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._worker_thread = None
        self._validation_thread = None  # Separate thread for source validation

        # Load current settings into variables
        self._load_settings_to_vars()

        # Ensure default Source folder exists and pre-populate if empty
        config.ensure_source_folder()
        if not self.source_path.get():
            self.source_path.set(str(config.SOURCE_FOLDER))

        self._create_ui()

        # Bridge Python logging → GUI log panel.
        # Every logger.info/warning/error from ANY module now shows in GUI.
        self._gui_log_handler = _GUILogHandler(self)
        self._gui_log_handler.setFormatter(
            logging.Formatter('%(name)s - %(message)s')
        )
        logging.getLogger().addHandler(self._gui_log_handler)

        # Clean up logging handler on window close to prevent leaks
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Clean up resources on window close."""
        logging.getLogger().removeHandler(self._gui_log_handler)
        self._cancel_event.set()
        self.root.destroy()

    def _load_settings_to_vars(self):
        """Load current config settings into StringVars."""
        settings = config.get_settings()
        self.settings_loc_path.set(settings.get("loc_folder", ""))
        self.settings_export_path.set(settings.get("export_folder", ""))

    def _create_ui(self):
        """Create the main UI layout."""
        # Main container with padding
        main = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        # === TOP BAR: Title + Action Buttons ===
        top_bar = tk.Frame(main, bg='#f0f0f0')
        top_bar.pack(fill=tk.X, pady=(0, 10))

        # Title on the left
        title = tk.Label(top_bar, text="QuickTranslate", font=('Segoe UI', 18, 'bold'),
                        bg='#f0f0f0', fg='#333')
        title.pack(side=tk.LEFT)

        # Action buttons on the right (immediately visible!)
        btn_container = tk.Frame(top_bar, bg='#f0f0f0')
        btn_container.pack(side=tk.RIGHT)

        tk.Button(btn_container, text="Exit", command=self._on_close,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=15, pady=4, cursor='hand2').pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(btn_container, text="Clear All", command=self._clear_fields,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=12, pady=4, cursor='hand2').pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(btn_container, text="Clear Log", command=self._clear_log,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=12, pady=4, cursor='hand2').pack(side=tk.RIGHT, padx=(5, 0))

        self.preprocess_btn = tk.Button(btn_container, text="PRE-PROCESS",
                                        command=self._preprocess,
                                        font=('Segoe UI', 10), bg='#8fbc8f', fg='white',
                                        relief='solid', bd=1,
                                        padx=12, pady=4, cursor='hand2')
        self.preprocess_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.transfer_btn = tk.Button(btn_container, text="TRANSFER", command=self._transfer,
                                      font=('Segoe UI', 11, 'bold'), bg='#d9534f', fg='white',
                                      relief='flat', padx=20, pady=4, cursor='hand2')
        self.transfer_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # === Horizontal Split: Controls (left) | Log (right) ===
        ttk.Separator(main, orient='horizontal').pack(fill=tk.X, pady=(0, 8))

        self._paned = tk.PanedWindow(main, orient=tk.HORIZONTAL, sashwidth=6,
                                     bg='#cccccc', sashrelief='raised')
        self._paned.pack(fill=tk.BOTH, expand=True)

        # --- Left pane: tabbed controls ---
        left_outer = tk.Frame(self._paned, bg='#f0f0f0')

        self._notebook = ttk.Notebook(left_outer)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # --- Tab 1: Transfer ---
        tab1_frame = tk.Frame(self._notebook, bg='#f0f0f0')
        self._notebook.add(tab1_frame, text="Transfer")

        self._tab1_canvas = tk.Canvas(tab1_frame, bg='#f0f0f0', highlightthickness=0)
        tab1_scrollbar = ttk.Scrollbar(tab1_frame, orient='vertical',
                                        command=self._tab1_canvas.yview)
        self._tab1_inner = tk.Frame(self._tab1_canvas, bg='#f0f0f0', padx=10)

        tab1_cw = self._tab1_canvas.create_window((0, 0), window=self._tab1_inner,
                                                    anchor='nw')
        self._tab1_inner.bind('<Configure>', lambda e: self._tab1_canvas.configure(
            scrollregion=self._tab1_canvas.bbox('all')))
        self._tab1_canvas.bind('<Configure>', lambda e: self._tab1_canvas.itemconfigure(
            tab1_cw, width=e.width))

        tab1_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._tab1_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._tab1_canvas.configure(yscrollcommand=tab1_scrollbar.set)

        # --- Tab 2: Other Tools ---
        tab2_frame = tk.Frame(self._notebook, bg='#f0f0f0')
        self._notebook.add(tab2_frame, text="Other Tools")

        self._tab2_canvas = tk.Canvas(tab2_frame, bg='#f0f0f0', highlightthickness=0)
        tab2_scrollbar = ttk.Scrollbar(tab2_frame, orient='vertical',
                                        command=self._tab2_canvas.yview)
        self._tab2_inner = tk.Frame(self._tab2_canvas, bg='#f0f0f0', padx=10)

        tab2_cw = self._tab2_canvas.create_window((0, 0), window=self._tab2_inner,
                                                    anchor='nw')
        self._tab2_inner.bind('<Configure>', lambda e: self._tab2_canvas.configure(
            scrollregion=self._tab2_canvas.bbox('all')))
        self._tab2_canvas.bind('<Configure>', lambda e: self._tab2_canvas.itemconfigure(
            tab2_cw, width=e.width))

        tab2_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._tab2_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._tab2_canvas.configure(yscrollcommand=tab2_scrollbar.set)

        # --- Right pane: log + progress ---
        self._right_pane = tk.Frame(self._paned, bg='#f0f0f0', padx=10)

        self._paned.add(left_outer, minsize=400)
        self._paned.add(self._right_pane, minsize=200)

        # Set initial sash position after layout
        self.root.after(200, self._set_initial_sash)

        # === Match Type Selection (Tab 1) ===
        match_frame = tk.LabelFrame(self._tab1_inner, text="Match Type", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=8)
        match_frame.pack(fill=tk.X, pady=(0, 8))

        match_types = [
            ("stringid_only", "StringID-Only (SCRIPT)", "SCRIPT categories only - match by StringID"),
            ("strict", "StringID + StrOrigin (STRICT)", "Requires BOTH to match exactly"),
            ("strorigin_only", "StrOrigin Only", "Match by StrOrigin text only - skips Dialog/Sequencer"),
            ("strorigin_descorigin", "StrOrigin + DescOrigin", "Requires BOTH StrOrigin AND DescOrigin to match"),
            ("strorigin_filename", "StrOrigin + FileName (2-pass)", "Match by StrOrigin + export filepath (precise)"),
        ]

        for value, label, desc in match_types:
            row = tk.Frame(match_frame, bg='#f0f0f0')
            row.pack(fill=tk.X, pady=2)
            rb = tk.Radiobutton(row, text=label, variable=self.match_type, value=value,
                          font=('Segoe UI', 10), bg='#f0f0f0', activebackground='#f0f0f0',
                          cursor='hand2', width=35, anchor='w',
                          command=self._on_match_type_changed)
            rb.pack(side=tk.LEFT)
            desc_lbl = tk.Label(row, text=desc, font=('Segoe UI', 9), bg='#f0f0f0', fg='#888')
            desc_lbl.pack(side=tk.LEFT)
            self._match_type_radios[value] = (rb, desc_lbl)

        # === Precision Options Sub-frame (visible for strict and strorigin_only) ===
        self.precision_options_frame = tk.Frame(match_frame, bg='#e8f4e8', padx=15, pady=8,
                                              relief='groove', bd=1)
        # Don't pack yet - shown/hidden by _on_match_type_changed

        # Match Precision radio buttons
        precision_label_row = tk.Frame(self.precision_options_frame, bg='#e8f4e8')
        precision_label_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(precision_label_row, text="Match Precision:", font=('Segoe UI', 9, 'bold'),
                bg='#e8f4e8', fg='#333').pack(side=tk.LEFT)

        precision_row = tk.Frame(self.precision_options_frame, bg='#e8f4e8')
        precision_row.pack(fill=tk.X, pady=(0, 4))
        tk.Radiobutton(precision_row, text="Perfect Match (exact text comparison)",
                       variable=self.match_precision, value="perfect",
                       font=('Segoe UI', 9), bg='#e8f4e8', activebackground='#e8f4e8',
                       cursor='hand2', command=self._on_precision_changed).pack(
                       side=tk.LEFT, padx=(10, 0))

        precision_row2 = tk.Frame(self.precision_options_frame, bg='#e8f4e8')
        precision_row2.pack(fill=tk.X, pady=(0, 4))
        tk.Radiobutton(precision_row2, text="Fuzzy Match (Model2Vec semantic similarity)",
                       variable=self.match_precision, value="fuzzy",
                       font=('Segoe UI', 9), bg='#e8f4e8', activebackground='#e8f4e8',
                       cursor='hand2', command=self._on_precision_changed).pack(
                       side=tk.LEFT, padx=(10, 0))

        # Fuzzy threshold sub-frame (shown only when fuzzy precision selected)
        self.fuzzy_sub_frame = tk.Frame(self.precision_options_frame, bg='#e8f4e8')
        # Don't pack yet - shown/hidden by _on_precision_changed

        fuzzy_thresh_row = tk.Frame(self.fuzzy_sub_frame, bg='#e8f4e8')
        fuzzy_thresh_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(fuzzy_thresh_row, text="Threshold:", font=('Segoe UI', 9), bg='#e8f4e8',
                width=10, anchor='w').pack(side=tk.LEFT)

        self.threshold_slider = ttk.Scale(
            fuzzy_thresh_row, from_=config.FUZZY_THRESHOLD_MIN, to=config.FUZZY_THRESHOLD_MAX,
            variable=self.fuzzy_threshold, orient=tk.HORIZONTAL,
            command=self._on_threshold_changed,
        )
        self.threshold_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.threshold_label = tk.Label(fuzzy_thresh_row,
                                        text=f"{config.FUZZY_THRESHOLD_DEFAULT:.2f}",
                                        font=('Segoe UI', 10, 'bold'), bg='#e8f4e8',
                                        fg='#333', width=5)
        self.threshold_label.pack(side=tk.LEFT)

        # Fuzzy model status
        fuzzy_status_row = tk.Frame(self.fuzzy_sub_frame, bg='#e8f4e8')
        fuzzy_status_row.pack(fill=tk.X)
        tk.Label(fuzzy_status_row, text="Model:", font=('Segoe UI', 9), bg='#e8f4e8',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.model_status_label = tk.Label(fuzzy_status_row,
                                           textvariable=self.fuzzy_model_status,
                                           font=('Segoe UI', 9), bg='#e8f4e8', fg='#666')
        self.model_status_label.pack(side=tk.LEFT)

        # === Transfer Scope Toggle (inside Match Type section) ===
        self.transfer_scope_frame = tk.Frame(match_frame, bg='#fef3e2', padx=10, pady=4,
                                             relief='groove', bd=1)
        # Don't pack yet - shown/hidden by _on_match_type_changed

        scope_label = tk.Label(self.transfer_scope_frame, text="Transfer Scope:",
                               font=('Segoe UI', 9, 'bold'), bg='#fef3e2', fg='#333')
        scope_label.pack(side=tk.LEFT, padx=(0, 10))

        tk.Radiobutton(self.transfer_scope_frame, text="Transfer ALL (overwrite always)",
                        variable=self.transfer_scope, value="all",
                        command=self._on_transfer_scope_changed,
                        font=('Segoe UI', 9), bg='#fef3e2',
                        activebackground='#fef3e2').pack(side=tk.LEFT, padx=(0, 15))
        tk.Radiobutton(self.transfer_scope_frame, text="Only untranslated (Korean only)",
                        variable=self.transfer_scope, value="untranslated",
                        font=('Segoe UI', 9), bg='#fef3e2',
                        activebackground='#fef3e2').pack(side=tk.LEFT)

        # === Unique-Only StrOrigin sub-frame (visible only for strorigin_only) ===
        self.unique_only_frame = tk.Frame(match_frame, bg='#e8f0fe', padx=10, pady=4,
                                           relief='groove', bd=1)
        # Don't pack yet - shown/hidden by _on_match_type_changed

        unique_row = tk.Frame(self.unique_only_frame, bg='#e8f0fe')
        unique_row.pack(fill=tk.X)
        tk.Checkbutton(unique_row, text="Unique strings only (skip duplicates)",
                       variable=self.unique_only_strorigin,
                       font=('Segoe UI', 9, 'bold'), bg='#e8f0fe',
                       activebackground='#e8f0fe', cursor='hand2').pack(side=tk.LEFT)

        tk.Label(self.unique_only_frame,
            text="Safe mode: only merges StrOrigin that appears once. Duplicates exported to Excel.",
            font=('Segoe UI', 8), bg='#e8f0fe', fg='#666', wraplength=350, justify='left'
        ).pack(fill=tk.X, pady=(2, 0))

        # === Non-Script Only frame (STRICT mode only) ===
        self.strict_non_script_frame = tk.Frame(match_frame, bg='#fde8e8', padx=10, pady=4,
                                                 relief='groove', bd=1)
        # Don't pack yet - shown/hidden by _on_match_type_changed

        ns_row = tk.Frame(self.strict_non_script_frame, bg='#fde8e8')
        ns_row.pack(fill=tk.X)
        tk.Checkbutton(ns_row, text="Non-Script only (skip Dialog/Sequencer)",
                       variable=self._strict_non_script_var,
                       command=self._on_presub_setting_changed,
                       font=('Segoe UI', 9, 'bold'), bg='#fde8e8',
                       activebackground='#fde8e8', cursor='hand2').pack(side=tk.LEFT)
        tk.Label(self.strict_non_script_frame,
            text="Skips SCRIPT categories (Dialog/Sequencer). Only processes game-data entries.",
            font=('Segoe UI', 8), bg='#fde8e8', fg='#666', wraplength=350, justify='left'
        ).pack(fill=tk.X, pady=(2, 0))

        # === StringID ALL Categories frame (StringID-Only mode) ===
        self.stringid_all_frame = tk.Frame(match_frame, bg='#ffe0e0', padx=10, pady=4,
                                           relief='groove', bd=1)
        # Don't pack yet - shown/hidden by _on_match_type_changed

        sid_all_row = tk.Frame(self.stringid_all_frame, bg='#ffe0e0')
        sid_all_row.pack(fill=tk.X)
        tk.Checkbutton(sid_all_row, text="ALL Categories (not just SCRIPT)",
                       variable=self._stringid_all_var,
                       font=('Segoe UI', 9, 'bold'), bg='#ffe0e0', fg='#cc0000',
                       activebackground='#ffe0e0', cursor='hand2').pack(side=tk.LEFT)
        tk.Label(self.stringid_all_frame,
            text="WARNING: Matches ALL StringIDs regardless of category. Use only for exceptional cases.",
            font=('Segoe UI', 8, 'bold'), bg='#ffe0e0', fg='#cc0000', wraplength=350, justify='left'
        ).pack(fill=tk.X, pady=(2, 0))

        # === Files Section ===
        files_frame = tk.LabelFrame(self._tab1_inner, text="Files", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=8)
        files_frame.pack(fill=tk.X, pady=(0, 8))

        # Source folder
        source_row = tk.Frame(files_frame, bg='#f0f0f0')
        source_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(source_row, text="Source:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=8, anchor='w').pack(side=tk.LEFT)
        self.source_entry = tk.Entry(source_row, textvariable=self.source_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(source_row, text="Browse", command=self._browse_source,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Target folder (for strict mode)
        target_row = tk.Frame(files_frame, bg='#f0f0f0')
        target_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(target_row, text="Target:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=8, anchor='w').pack(side=tk.LEFT)
        self.target_entry = tk.Entry(target_row, textvariable=self.target_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(target_row, text="Browse", command=self._browse_target,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # === Pre-Submission Checks Section ===
        checks_frame = tk.LabelFrame(self._tab1_inner, text="Pre-Submission Checks",
                                      font=('Segoe UI', 10, 'bold'),
                                      bg='#f0f0f0', fg='#555', padx=15, pady=8)
        checks_frame.pack(fill=tk.X, pady=(0, 8))

        checks_btn_row = tk.Frame(checks_frame, bg='#f0f0f0')
        checks_btn_row.pack(fill=tk.X, pady=(0, 4))

        self.check_korean_btn = tk.Button(
            checks_btn_row, text="Check Korean", command=self._check_korean,
            font=('Segoe UI', 9, 'bold'), bg='#e67e22', fg='white',
            relief='flat', padx=14, cursor='hand2')
        self.check_korean_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.check_patterns_btn = tk.Button(
            checks_btn_row, text="Check Patterns", command=self._check_patterns,
            font=('Segoe UI', 9, 'bold'), bg='#e67e22', fg='white',
            relief='flat', padx=14, cursor='hand2')
        self.check_patterns_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.check_quality_btn = tk.Button(
            checks_btn_row, text="Check Quality", command=self._check_quality,
            font=('Segoe UI', 9, 'bold'), bg='#e67e22', fg='white',
            relief='flat', padx=14, cursor='hand2')
        self.check_quality_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.check_all_btn = tk.Button(
            checks_btn_row, text="Check ALL", command=self._check_all,
            font=('Segoe UI', 9, 'bold'), bg='#c0392b', fg='white',
            relief='flat', padx=14, cursor='hand2')
        self.check_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_results_btn = tk.Button(
            checks_btn_row, text="Open Results Folder",
            command=self._open_check_results_folder,
            font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
            padx=10, cursor='hand2', state='disabled')
        self.open_results_btn.pack(side=tk.RIGHT)

        checks_status_row = tk.Frame(checks_frame, bg='#f0f0f0')
        checks_status_row.pack(fill=tk.X)
        self.checks_status_text = tk.StringVar(value="Ready")
        tk.Label(checks_status_row, textvariable=self.checks_status_text,
                 font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
                 anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

        # === Settings Section ===
        settings_frame = tk.LabelFrame(self._tab1_inner, text="Settings", font=('Segoe UI', 10, 'bold'),
                                       bg='#f0f0f0', fg='#555', padx=15, pady=8)
        settings_frame.pack(fill=tk.X, pady=(0, 8))

        # LOC Path
        loc_row = tk.Frame(settings_frame, bg='#f0f0f0')
        loc_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(loc_row, text="LOC Path:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.loc_entry = tk.Entry(loc_row, textvariable=self.settings_loc_path,
                                  font=('Segoe UI', 9), relief='solid', bd=1)
        self.loc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(loc_row, text="Browse", command=self._browse_loc_path,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Export Path
        export_row = tk.Frame(settings_frame, bg='#f0f0f0')
        export_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(export_row, text="Export Path:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.export_entry = tk.Entry(export_row, textvariable=self.settings_export_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.export_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(export_row, text="Browse", command=self._browse_export_path,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Save Settings button
        save_row = tk.Frame(settings_frame, bg='#f0f0f0')
        save_row.pack(fill=tk.X)
        tk.Button(save_row, text="Save Settings", command=self._save_settings,
                 font=('Segoe UI', 9, 'bold'), bg='#5bc0de', fg='white',
                 relief='flat', padx=14, cursor='hand2').pack(side=tk.RIGHT)
        tk.Label(save_row, text="Paths are saved to settings.json", font=('Segoe UI', 8),
                bg='#f0f0f0', fg='#888').pack(side=tk.LEFT)

        # === Tab 2: Other Tools ===
        missing_frame = tk.LabelFrame(self._tab2_inner, text="Find Missing Translations",
                                       font=('Segoe UI', 10, 'bold'),
                                       bg='#f0f0f0', fg='#555', padx=15, pady=8)
        missing_frame.pack(fill=tk.X, pady=(8, 8))

        tk.Label(missing_frame,
                 text="Find Korean entries in Target that are MISSING from Source.",
                 font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
                 justify='left', anchor='w').pack(fill=tk.X, pady=(0, 4))

        # Show current Source/Target paths (auto-updates via textvariable)
        path_info = tk.Frame(missing_frame, bg='#e8e8e8', padx=8, pady=6,
                             relief='groove', bd=1)
        path_info.pack(fill=tk.X, pady=(0, 8))

        src_info = tk.Frame(path_info, bg='#e8e8e8')
        src_info.pack(fill=tk.X, pady=(0, 2))
        tk.Label(src_info, text="Source:", font=('Segoe UI', 9, 'bold'),
                 bg='#e8e8e8', width=8, anchor='w').pack(side=tk.LEFT)
        tk.Label(src_info, textvariable=self.source_path,
                 font=('Segoe UI', 9), bg='#e8e8e8', fg='#333',
                 anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

        tgt_info = tk.Frame(path_info, bg='#e8e8e8')
        tgt_info.pack(fill=tk.X)
        tk.Label(tgt_info, text="Target:", font=('Segoe UI', 9, 'bold'),
                 bg='#e8e8e8', width=8, anchor='w').pack(side=tk.LEFT)
        tk.Label(tgt_info, textvariable=self.target_path,
                 font=('Segoe UI', 9), bg='#e8e8e8', fg='#333',
                 anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(path_info, text="(Set paths on the Transfer tab)",
                 font=('Segoe UI', 8), bg='#e8e8e8', fg='#888').pack(anchor='w')

        missing_btn_row = tk.Frame(missing_frame, bg='#f0f0f0')
        missing_btn_row.pack(fill=tk.X)

        self.missing_trans_btn = tk.Button(
            missing_btn_row, text="Find Missing Translations",
            command=self._find_missing_translations,
            font=('Segoe UI', 9, 'bold'), bg='#9b59b6', fg='white',
            relief='flat', padx=10, cursor='hand2')
        self.missing_trans_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.exclude_btn = tk.Button(
            missing_btn_row, text="Exclude...",
            command=self._open_exclude_dialog,
            font=('Segoe UI', 9, 'bold'), bg='#e67e22', fg='white',
            relief='flat', padx=10, cursor='hand2')
        self.exclude_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._exclude_count_label = tk.Label(
            missing_btn_row, text="",
            font=('Segoe UI', 8, 'bold'), bg='#f0f0f0', fg='#e67e22')
        self._exclude_count_label.pack(side=tk.LEFT)

        self._update_exclude_count_label()

        # === Log Section (right pane) ===
        log_frame = tk.LabelFrame(self._right_pane, text="Log", font=('Segoe UI', 10, 'bold'),
                                  bg='#f0f0f0', fg='#555', padx=10, pady=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.log_area = scrolledtext.ScrolledText(
            log_frame, font=('Consolas', 9), relief='solid', bd=1,
            wrap=tk.WORD, state='disabled'
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Configure log tags for colors
        self.log_area.tag_config('info', foreground='#333')
        self.log_area.tag_config('success', foreground='#008000')
        self.log_area.tag_config('warning', foreground='#FF8C00')
        self.log_area.tag_config('error', foreground='#FF0000')
        self.log_area.tag_config('header', foreground='#4a90d9', font=('Consolas', 9, 'bold'))

        # === Progress Section (right pane) ===
        progress_frame = tk.Frame(self._right_pane, bg='#f0f0f0')
        progress_frame.pack(fill=tk.X, pady=(0, 8))

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_value,
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        status_cancel_row = tk.Frame(progress_frame, bg='#f0f0f0')
        status_cancel_row.pack(fill=tk.X)

        status_label = tk.Label(status_cancel_row, textvariable=self.status_text,
                               font=('Segoe UI', 9), bg='#f0f0f0', fg='#666', anchor='w')
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.cancel_btn = tk.Button(status_cancel_row, text="Cancel", command=self._request_cancel,
                                    font=('Segoe UI', 9, 'bold'), bg='#d9534f', fg='white',
                                    relief='flat', padx=14, pady=2, cursor='hand2')
        # Hidden by default — shown during operations

        # Apply initial match type state
        self._on_match_type_changed()

        # Bind mousewheel scrolling per tab
        self._bind_mousewheel_to_canvas(self._tab1_canvas, self._tab1_canvas)
        self._bind_mousewheel_to_canvas(self._tab1_inner, self._tab1_canvas)
        self._bind_mousewheel_to_canvas(self._tab2_canvas, self._tab2_canvas)
        self._bind_mousewheel_to_canvas(self._tab2_inner, self._tab2_canvas)

    def _set_initial_sash(self):
        """Set PanedWindow sash to ~65% left / 35% right split."""
        total_width = self._paned.winfo_width()
        if total_width > 1:
            self._paned.sash_place(0, int(total_width * 0.65), 0)

    def _bind_mousewheel_to_canvas(self, widget, canvas):
        """Bind mousewheel scrolling to widget targeting a specific canvas."""
        def on_mousewheel(event):
            if event.delta:  # Windows
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:  # Linux scroll up
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux scroll down
                canvas.yview_scroll(1, "units")
        widget.bind('<MouseWheel>', on_mousewheel)
        widget.bind('<Button-4>', on_mousewheel)
        widget.bind('<Button-5>', on_mousewheel)
        for child in widget.winfo_children():
            self._bind_mousewheel_to_canvas(child, canvas)

    def _bind_mousewheel_recursive(self, widget):
        """Bind mousewheel scrolling to widget (delegates to tab1 canvas)."""
        self._bind_mousewheel_to_canvas(widget, self._tab1_canvas)

    def _log(self, message: str, tag: str = 'info'):
        """Add message to log area (thread-safe).

        If called from the main thread with no active worker, inserts directly.
        Otherwise queues for main-thread processing via _poll_queue.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        if threading.current_thread() is threading.main_thread() and (
            self._worker_thread is None or not self._worker_thread.is_alive()
        ):
            self._log_on_main(timestamp, message, tag)
        else:
            self._task_queue.put(('log', timestamp, message, tag))

    _MAX_LOG_LINES = 5000

    def _log_on_main(self, timestamp: str, message: str, tag: str):
        """Insert log message into widget (must run on main thread)."""
        try:
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            # Auto-truncate: keep last _MAX_LOG_LINES lines to prevent memory growth
            line_count = int(self.log_area.index('end-1c').split('.')[0])
            if line_count > self._MAX_LOG_LINES:
                excess = line_count - self._MAX_LOG_LINES
                self.log_area.delete('1.0', f'{excess}.0')
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        except tk.TclError:
            pass  # Widget destroyed during shutdown

    def _clear_log(self):
        """Clear the log area."""
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

    def _progress_log_callback(self, message: str):
        """Progress callback that logs to GUI log area."""
        self._log(message, 'info')

    def _analyze_folder(self, folder_path: str, role: str) -> None:
        """Analyze a folder and log detailed info to terminal and GUI.

        Uses Smart Auto-Recursive Source Scanner for SOURCE folders to detect
        language codes from folder/file suffixes (e.g., Corrections_FRE/, patch_GER.xml).

        Args:
            folder_path: Path to the folder to analyze
            role: "SOURCE" or "TARGET" for display purposes
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            logger.error("[%s] Path does not exist or is not a directory: %s", role, folder_path)
            self._log(f"{role} folder invalid: {folder_path}", 'error')
            return

        try:
            all_files = list(folder.iterdir())
        except OSError as e:
            logger.error("[%s] Cannot read folder: %s", role, e)
            self._log(f"{role} folder unreadable: {e}", 'error')
            return

        xml_files = [f for f in all_files if f.suffix.lower() == ".xml" and f.is_file()]
        xlsx_files = [f for f in all_files if f.suffix.lower() in (".xlsx", ".xls") and f.is_file()]
        categorized = set(xml_files) | set(xlsx_files)
        other_files = [f for f in all_files if f.is_file() and f not in categorized]
        subdirs = [f for f in all_files if f.is_dir()]

        # Identify languagedata files and extract language codes
        lang_files = []
        non_lang_xml = []
        for f in xml_files:
            name = f.stem.lower()
            if name.startswith("languagedata_"):
                lang_code = f.stem[13:]  # Preserve original case
                try:
                    size_kb = f.stat().st_size / 1024
                except OSError:
                    size_kb = 0
                lang_files.append((f.name, lang_code, size_kb))
            else:
                non_lang_xml.append(f.name)

        # Terminal output
        separator = "=" * 60
        logger.info("\n%s", separator)
        logger.info("  %s FOLDER ANALYSIS", role)
        logger.info("%s", separator)
        logger.info("  Path: %s", folder_path)
        logger.info("  Total items: %d (%d XML, %d Excel, %d other, %d subdirs)",
                     len(all_files), len(xml_files), len(xlsx_files), len(other_files), len(subdirs))
        logger.info("%s", "-" * 60)

        if lang_files:
            logger.info("\n  LANGUAGEDATA FILES (%d found):", len(lang_files))
            logger.info("  %-4s %-35s %-8s %-10s", "#", "Filename", "Lang", "Size")
            logger.info("  %s %s %s %s", "-"*4, "-"*35, "-"*8, "-"*10)
            total_size = 0
            for idx, (fname, lang, size) in enumerate(sorted(lang_files, key=lambda x: x[1]), 1):
                total_size += size
                if size >= 1024:
                    size_str = f"{size/1024:.1f} MB"
                else:
                    size_str = f"{size:.0f} KB"
                logger.info("  %-4d %-35s %-8s %-10s", idx, fname, lang, size_str)
            if total_size >= 1024:
                total_str = f"{total_size/1024:.1f} MB"
            else:
                total_str = f"{total_size:.0f} KB"
            logger.info("  %s %s %s %s", "-"*4, "-"*35, "-"*8, "-"*10)
            logger.info("  %-4s %-35s %-8s %-10s", "", "TOTAL", "", total_str)
        else:
            # Only warn if this is TARGET or if smart scan also finds nothing
            if role == "TARGET":
                logger.info("  No languagedata_*.xml files found (checking smart scanner...)")

        # === Smart Auto-Recursive Scanner (for BOTH SOURCE and TARGET) ===
        # Scan once and reuse result (avoid duplicate scanning)
        scan_result = None
        target_scan_result = None
        has_smart_scan = False
        if role == "SOURCE":
            scan_result = scan_source_for_languages(folder)
            has_smart_scan = bool(scan_result.lang_files)
            # Show skipped files with unsupported extensions (CRITICAL — user needs to know!)
            if scan_result.skipped_files:
                logger.warning("\n  [!!] SKIPPED FILES (%d) — unsupported file type:", len(scan_result.skipped_files))
                for reason in scan_result.skipped_files[:10]:
                    logger.warning("    - %s", reason)
                if len(scan_result.skipped_files) > 10:
                    logger.warning("    ... and %d more", len(scan_result.skipped_files) - 10)
                logger.warning("  Only .xml, .xlsx, .xls files are accepted as source files.")
            if scan_result.unrecognized:
                logger.info("\n  UNRECOGNIZED ITEMS (%d) — no language suffix detected:", len(scan_result.unrecognized))
                for item in scan_result.unrecognized[:10]:
                    item_type = "folder" if item.is_dir() else "file"
                    logger.info("    - %s (%s)", item.name, item_type)
                if len(scan_result.unrecognized) > 10:
                    logger.info("    ... and %d more", len(scan_result.unrecognized) - 10)
        elif role == "TARGET":
            target_scan_result = scan_target_for_languages(folder)
            has_smart_scan = bool(target_scan_result.lang_files)
            if has_smart_scan:
                logger.info("\n  TARGET LANGUAGE DETECTION (Flexible Scanner):")
                logger.info("  %-10s %-8s %-6s %-6s %s", "Language", "Files", "XML", "Excel", "Source")
                logger.info("  %s %s %s %s %s", "-"*10, "-"*8, "-"*6, "-"*6, "-"*30)
                for lang in target_scan_result.get_languages():
                    files = target_scan_result.lang_files[lang]
                    xml_c = sum(1 for f in files if f.suffix.lower() == ".xml")
                    xls_c = sum(1 for f in files if f.suffix.lower() in (".xlsx", ".xls"))
                    if len(files) <= 2:
                        sources = ", ".join(f.name for f in files)
                    else:
                        sources = f"{files[0].name}, ... ({len(files)} total)"
                    logger.info("  %-10s %-8d %-6d %-6d %s", lang, len(files), xml_c, xls_c, sources)
                logger.info("\n  Total: %d files in %d languages (%d XML, %d Excel)",
                            target_scan_result.total_files, target_scan_result.language_count,
                            target_scan_result.xml_count, target_scan_result.excel_count)

            elif not lang_files:
                logger.warning("  No language files detected (no languagedata_*.xml, no language-suffixed files/folders)")

            # Show unrecognized + skipped OUTSIDE has_smart_scan guard — must display even when no valid files found
            if target_scan_result.unrecognized:
                logger.warning("\n  [!!] UNRECOGNIZED ITEMS (%d) — no valid language suffix:", len(target_scan_result.unrecognized))
                for item in target_scan_result.unrecognized[:10]:
                    item_type = "folder" if item.is_dir() else "file"
                    logger.warning("    - %s (%s)", item.name, item_type)
                if len(target_scan_result.unrecognized) > 10:
                    logger.warning("    ... and %d more", len(target_scan_result.unrecognized) - 10)
            if target_scan_result.skipped_files:
                logger.warning("\n  [!!] SKIPPED FILES (%d) — unsupported file type:", len(target_scan_result.skipped_files))
                for reason in target_scan_result.skipped_files[:10]:
                    logger.warning("    - %s", reason)
                if len(target_scan_result.skipped_files) > 10:
                    logger.warning("    ... and %d more", len(target_scan_result.skipped_files) - 10)
                logger.warning("  Only .xml, .xlsx, .xls files are accepted as target files.")

        if non_lang_xml:
            if has_smart_scan:
                # Split into files actually detected by scanner vs unrecognized
                active_scan = scan_result if role == "SOURCE" else target_scan_result
                scanner_detected_names = set()
                for file_list in active_scan.lang_files.values():
                    for fp in file_list:
                        scanner_detected_names.add(fp.name)
                detected = [f for f in non_lang_xml if f in scanner_detected_names]
                undetected = [f for f in non_lang_xml if f not in scanner_detected_names]
                if detected:
                    logger.info("\n  DETECTED XML FILES (%d) — included via smart scanner:", len(detected))
                    for f in detected:
                        logger.info("    - %s", f)
                if undetected:
                    logger.info("\n  OTHER XML FILES (%d) — no language suffix detected:", len(undetected))
                    for f in undetected:
                        logger.info("    - %s", f)
            else:
                logger.info("\n  OTHER XML FILES (%d):", len(non_lang_xml))
                for f in non_lang_xml:
                    logger.info("    - %s", f)

        if xlsx_files:
            logger.info("\n  EXCEL FILES (%d):", len(xlsx_files))
            for f in xlsx_files:
                try:
                    size_kb = f.stat().st_size / 1024
                    logger.info("    - %s (%.0f KB)", f.name, size_kb)
                except OSError:
                    logger.info("    - %s (size unknown)", f.name)

        if subdirs:
            logger.info("\n  SUBDIRECTORIES (%d):", len(subdirs))
            for d in subdirs:
                logger.info("    - %s/", d.name)

        # Validation - show WORKING FOR / NOT WORKING FOR
        logger.info("\n  VALIDATION:")
        is_eligible = len(lang_files) > 0
        lang_codes = sorted([lc for _, lc, _ in lang_files]) if lang_files else []

        # Smart scan makes folders eligible even without languagedata_ files
        if has_smart_scan and not is_eligible:
            is_eligible = True

        # Build combined language list from both sources
        if has_smart_scan:
            if role == "SOURCE" and scan_result:
                all_langs = sorted(set(lang_codes) | set(scan_result.get_languages()))
            elif role == "TARGET" and target_scan_result:
                all_langs = sorted(set(lang_codes) | set(target_scan_result.get_languages()))
            else:
                all_langs = lang_codes
        else:
            all_langs = lang_codes

        # Determine what features work with this structure
        working_for = []
        not_working_for = []

        if is_eligible:
            if has_smart_scan:
                if role == "SOURCE" and scan_result:
                    file_count = scan_result.total_files
                elif role == "TARGET" and target_scan_result:
                    file_count = target_scan_result.total_files
                else:
                    file_count = len(lang_files)
            elif lang_files:
                file_count = len(lang_files)
            else:
                file_count = 0
            working_for.append(f"TRANSFER ({file_count} language files)")
            working_for.append("Find Missing Translations")
            if role == "SOURCE":
                working_for.append("Pre-Submission Checks (Korean + Pattern + Quality)")
            if all_langs:
                working_for.append(f"Languages: {', '.join(all_langs)}")
        else:
            not_working_for.append("TRANSFER - no parseable language files found")
            not_working_for.append("Find Missing Translations - needs LOC folder structure")
            if role == "SOURCE":
                not_working_for.append("Pre-Submission Checks - no language files found")

        if working_for:
            logger.info("  WORKING FOR:")
            for item in working_for:
                logger.info("    + %s", item)

        if not_working_for:
            logger.info("  NOT WORKING FOR:")
            for item in not_working_for:
                logger.info("    x %s", item)

        if non_lang_xml and role == "TARGET" and not has_smart_scan:
            logger.info("  [!!] %d non-languagedata XML files will be IGNORED", len(non_lang_xml))
        if subdirs and role == "TARGET" and not has_smart_scan:
            logger.info("  [!!] %d subdirectories will be IGNORED (flat scan only)", len(subdirs))

        logger.info("%s\n", separator)

        # Broken XML detection for TARGET xml files (background thread)
        if role == "TARGET" and xml_files:
            self._validate_target_xml_async(list(xml_files))

        # Log to GUI
        if is_eligible:
            self._log(f"{role}: ELIGIBLE for TRANSFER + Find Missing Translations", 'success')
            if has_smart_scan and scan_result:
                self._log(f"  Smart scan: {scan_result.total_files} files in {scan_result.language_count} languages", 'info')
            elif has_smart_scan and target_scan_result:
                xml_info = f"{target_scan_result.xml_count} XML" if target_scan_result.xml_count else ""
                xls_info = f"{target_scan_result.excel_count} Excel" if target_scan_result.excel_count else ""
                type_info = " + ".join(filter(None, [xml_info, xls_info]))
                self._log(f"  Flexible target: {target_scan_result.total_files} files in {target_scan_result.language_count} languages ({type_info})", 'info')
            if all_langs:
                self._log(f"  Languages: {', '.join(all_langs)}", 'info')
        else:
            self._log(f"{role}: Limited features available (no parseable language files)", 'warning')

        # Run enhanced source validation (dry-run parse) in background thread
        if role == "SOURCE" and scan_result:
            self._validate_source_files_async(folder, scan_result)

    def _validate_target_xml_async(self, xml_files: list) -> None:
        """Run broken XML + formula text detection on TARGET files in a background thread.

        Prevents GUI freeze when scanning large XML files for broken LocStr nodes
        and formula-like garbage text in Str/Desc attributes.
        Uses the same validation thread pattern as source validation.
        """
        def target_validation_work():
            from core.xml_parser import validate_xml_load

            total_broken = 0
            total_formula = 0
            total_integrity = 0
            total_load_fail = 0
            total_load_recovered = 0
            total = len(xml_files)

            for i, xf in enumerate(xml_files):
                # Abort if a real worker started (user clicked Transfer, etc.)
                if self._worker_thread is not None and self._worker_thread.is_alive():
                    self._log("Target validation interrupted (operation started)", 'info')
                    return

                progress_pct = ((i + 1) / total) * 100
                self._task_queue.put(('status', f'Checking target XML... ({i + 1}/{total}) {xf.name}', progress_pct))

                # XML Load Test — first check, before anything else
                load_result = validate_xml_load(xf)
                if not load_result["ok"]:
                    total_load_fail += 1
                    self._log(f"CRITICAL: {xf.name} — XML LOAD FAILED at {load_result['stage']}: {load_result['error']}", 'error')
                    continue  # Skip all other checks — file is broken
                if load_result.get("recovery_parse_ok") and not load_result.get("strict_parse_ok"):
                    total_load_recovered += 1
                    self._log(f"WARNING: {xf.name} — XML loaded with recovery mode (has structural issues)", 'warning')

                broken = check_broken_xml_in_file(xf)
                if broken:
                    total_broken += len(broken)
                    self._log(f"WARNING: {xf.name} has {len(broken)} broken LocStr node(s)!", 'warning')
                    for sid, _fragment, _fname in broken:
                        self._log(f"  Broken LocStr: StringID={sid}", 'error')

                formula = check_formula_text_in_file(xf)
                if formula:
                    total_formula += len(formula)
                    self._log(f"WARNING: {xf.name} has {len(formula)} formula-like text entry(ies)!", 'warning')
                    for elem in formula[:10]:
                        sid = elem.attrib.get('StringId', elem.attrib.get('stringid', '(unknown)'))
                        self._log(f"  Formula text: StringID={sid}", 'error')
                    if len(formula) > 10:
                        self._log(f"  ...and {len(formula) - 10} more.", 'error')

                integrity = check_text_integrity_in_file(xf)
                if integrity:
                    total_integrity += len(integrity)
                    self._log(f"WARNING: {xf.name} has {len(integrity)} text integrity issue(s)!", 'warning')
                    for elem in integrity[:10]:
                        sid = elem.attrib.get('StringId', elem.attrib.get('stringid', '(unknown)'))
                        self._log(f"  Integrity issue: StringID={sid}", 'error')
                    if len(integrity) > 10:
                        self._log(f"  ...and {len(integrity) - 10} more.", 'error')

            # XML Load Test summary
            if total_load_fail == 0 and total_load_recovered == 0:
                self._log(f"XML LOAD: All {total} files loaded successfully", 'success')
            elif total_load_fail == 0:
                self._log(f"XML LOAD: All {total} files loadable ({total_load_recovered} with recovery mode)", 'warning')
            else:
                self._log(f"XML LOAD: {total_load_fail} file(s) FAILED to load out of {total}", 'error')

            issues = total_load_fail + total_broken + total_formula + total_integrity
            if issues:
                parts = []
                if total_load_fail:
                    parts.append(f"{total_load_fail} XML LOAD FAILED")
                if total_load_recovered:
                    parts.append(f"{total_load_recovered} recovered")
                if total_broken:
                    parts.append(f"{total_broken} broken LocStr")
                if total_formula:
                    parts.append(f"{total_formula} formula text")
                if total_integrity:
                    parts.append(f"{total_integrity} integrity issues")
                logger.warning("TARGET issues: %s found", ', '.join(parts))
                self._log(f"TARGET: {', '.join(parts)} found across {total} files", 'warning')
            else:
                if total_load_recovered:
                    self._log(f"TARGET: All {total} XML files loadable ({total_load_recovered} with recovery), no other issues", 'warning')
                else:
                    self._log(f"TARGET: All {total} XML files passed checks", 'success')

            self._task_queue.put(('status', '', 0))

        self._validation_thread = threading.Thread(
            target=target_validation_work, daemon=True
        )
        self._validation_thread.start()
        self._start_validation_poll()

    def _validate_source_files_async(self, folder: Path, scan_result) -> None:
        """Launch source file validation in a background thread.

        Uses lightweight XML parsing (just count LocStr elements, no full
        correction extraction) to avoid blocking the GUI on large files.
        """
        from core.xml_parser import parse_xml_file, iter_locstr_elements, get_attr, DESCORIGIN_ATTRS, DESC_ATTRS

        # Collect all files to validate
        files_to_check = []
        for lang, file_list in scan_result.lang_files.items():
            for f in file_list:
                files_to_check.append((f, lang))

        for item in scan_result.unrecognized:
            if item.is_file() and item.suffix.lower() in (".xml", ".xlsx", ".xls"):
                files_to_check.append((item, "???"))

        if not files_to_check:
            logger.info("  No source files to validate.")
            return

        self._task_queue.put(('status', 'Validating source files...', 0))

        def validation_work():
            from core.xml_parser import validate_xml_load

            results = []
            all_formula_warnings = []  # Collect for end-of-log summary
            all_integrity_warnings = []  # Collect for end-of-log summary
            all_no_translation_warnings = []  # Collect for end-of-log summary
            # NOTE: ellipsis warnings removed — auto-fixed by postprocess
            total = len(files_to_check)
            total_xml_files = 0
            total_load_fail = 0
            total_load_recovered = 0

            for i, (filepath, lang) in enumerate(files_to_check):
                # Abort if a real worker started (user clicked Transfer, etc.)
                if self._worker_thread is not None and self._worker_thread.is_alive():
                    self._log("Validation interrupted (operation started)", 'info')
                    return

                suffix = filepath.suffix.lower()
                file_type = "XML" if suffix == ".xml" else "Excel"

                # XML Load Test — first check for XML source files
                if suffix == ".xml":
                    total_xml_files += 1
                    load_result = validate_xml_load(filepath)
                    if not load_result["ok"]:
                        total_load_fail += 1
                        self._log(f"CRITICAL: {filepath.name} — XML LOAD FAILED: {load_result['error']}", 'error')
                        results.append((filepath.name, file_type, lang, 0, "LOAD FAILED", load_result['error']))
                        continue  # Skip all other checks
                    if load_result.get("recovery_parse_ok") and not load_result.get("strict_parse_ok"):
                        total_load_recovered += 1
                        self._log(f"WARNING: {filepath.name} — loaded with recovery mode", 'warning')

                progress_pct = ((i + 1) / total) * 100
                self._task_queue.put(('status', f'Validating... ({i + 1}/{total}) {filepath.name}', progress_pct))

                try:
                    if suffix == ".xml":
                        # Parse + count + formula + integrity detection
                        from core.xml_io import parse_corrections_from_xml
                        xml_formula_report = []
                        xml_integrity_report = []
                        xml_no_translation_report = []
                        entries = parse_corrections_from_xml(
                            filepath, formula_report=xml_formula_report, integrity_report=xml_integrity_report,
                            no_translation_report=xml_no_translation_report)
                        count = len(entries) if entries else 0

                        # Also count raw LocStr elements for broken XML check
                        root = parse_xml_file(filepath)

                        # Check for broken XML nodes (raw-text detection)
                        broken = check_broken_xml_in_file(filepath)
                        if broken:
                            self._log(f"WARNING: {filepath.name} has {len(broken)} broken LocStr node(s)!", 'warning')
                            for sid, _fragment, _fname in broken:
                                self._log(f"  Broken LocStr: StringID={sid}", 'error')

                        # Report formula-like text in XML
                        if xml_formula_report:
                            xml_formula_count = len(xml_formula_report)
                            self._log(
                                f"WARNING: {xml_formula_count} entry(ies) in {filepath.name} "
                                f"contain formula-like text (skipped/neutralized).",
                                'error'
                            )
                            for r in xml_formula_report[:10]:
                                sid = r['string_id'] or '(empty)'
                                self._log(
                                    f"  [{r['column']}] StringID={sid}: {r['reason']}",
                                    'error'
                                )
                            if xml_formula_count > 10:
                                self._log(f"  ...and {xml_formula_count - 10} more.", 'error')
                            for r in xml_formula_report:
                                all_formula_warnings.append((filepath.name, r.get('string_id', ''), r.get('column', ''), r.get('reason', '')))
                        # Report integrity issues in XML
                        if xml_integrity_report:
                            xml_integrity_count = len(xml_integrity_report)
                            self._log(
                                f"WARNING: {xml_integrity_count} entry(ies) in {filepath.name} "
                                f"have text integrity issues (skipped/neutralized).",
                                'error'
                            )
                            for r in xml_integrity_report[:10]:
                                sid = r['string_id'] or '(empty)'
                                self._log(
                                    f"  [{r['column']}] StringID={sid}: {r['reason']}",
                                    'error'
                                )
                            if xml_integrity_count > 10:
                                self._log(f"  ...and {xml_integrity_count - 10} more.", 'error')
                            for r in xml_integrity_report:
                                all_integrity_warnings.append((filepath.name, r.get('string_id', ''), r.get('column', ''), r.get('reason', '')))
                        if xml_no_translation_report:
                            for r in xml_no_translation_report:
                                all_no_translation_warnings.append((filepath.name, r.get('string_id', '')))
                    elif suffix in (".xlsx", ".xls"):
                        formula_report = []
                        integrity_report_xl = []
                        xl_no_translation_report = []
                        entries = read_corrections_from_excel(
                            filepath, formula_report=formula_report, integrity_report=integrity_report_xl,
                            no_translation_report=xl_no_translation_report)
                        count = len(entries) if entries else 0

                        if formula_report:
                            formula_count = len(formula_report)
                            self._log(
                                f"WARNING: {formula_count} cell(s) skipped in {filepath.name} "
                                f"(Excel formulas/errors detected). "
                                f"Fix: re-save Excel with Paste Values (Ctrl+Shift+V).",
                                'error'
                            )
                            for r in formula_report[:10]:
                                sid = r['string_id'] or '(empty)'
                                self._log(
                                    f"  Row {r['row']} [{r['column']}] StringID={sid}: {r['reason']}",
                                    'error'
                                )
                            if formula_count > 10:
                                self._log(f"  ...and {formula_count - 10} more.", 'error')
                            for r in formula_report:
                                all_formula_warnings.append((filepath.name, r.get('string_id', ''), r.get('column', ''), r.get('reason', '')))
                        if integrity_report_xl:
                            integrity_count_xl = len(integrity_report_xl)
                            self._log(
                                f"WARNING: {integrity_count_xl} cell(s) in {filepath.name} "
                                f"have text integrity issues (skipped/neutralized).",
                                'error'
                            )
                            for r in integrity_report_xl[:10]:
                                sid = r['string_id'] or '(empty)'
                                self._log(
                                    f"  Row {r['row']} [{r['column']}] StringID={sid}: {r['reason']}",
                                    'error'
                                )
                            if integrity_count_xl > 10:
                                self._log(f"  ...and {integrity_count_xl - 10} more.", 'error')
                            for r in integrity_report_xl:
                                all_integrity_warnings.append((filepath.name, r.get('string_id', ''), r.get('column', ''), r.get('reason', '')))
                        if xl_no_translation_report:
                            for r in xl_no_translation_report:
                                all_no_translation_warnings.append((filepath.name, r.get('string_id', '')))
                        if count == 0 and (formula_report or integrity_report_xl):
                            skip_parts = []
                            if formula_report:
                                skip_parts.append(f"{len(formula_report)} formula")
                            if integrity_report_xl:
                                skip_parts.append(f"{len(integrity_report_xl)} integrity")
                            results.append((filepath.name, file_type, lang, 0, "SKIPPED",
                                            f"All rows filtered: {' + '.join(skip_parts)} issues"))
                            continue
                    else:
                        results.append((filepath.name, file_type, lang, 0, "SKIPPED", "Unsupported format"))
                        continue

                    if count > 0:
                        results.append((filepath.name, file_type, lang, count, "OK", ""))
                    else:
                        results.append((filepath.name, file_type, lang, 0, "EMPTY", "No entries parsed"))
                except ValueError as e:
                    results.append((filepath.name, file_type, lang, 0, "COLUMN ERROR", str(e)))
                except Exception as e:
                    results.append((filepath.name, file_type, lang, 0, "FAILED", str(e)))

            # XML Load Test summary (source files)
            if total_xml_files > 0:
                if total_load_fail == 0 and total_load_recovered == 0:
                    self._log(f"XML LOAD: All {total_xml_files} XML file(s) loaded successfully", 'success')
                elif total_load_fail == 0:
                    self._log(f"XML LOAD: All {total_xml_files} XML file(s) loadable ({total_load_recovered} with recovery mode)", 'warning')
                else:
                    self._log(f"XML LOAD: {total_load_fail} XML file(s) FAILED to load out of {total_xml_files}", 'error')

            # Build terminal report
            separator = "-" * 60
            logger.info("\n%s", separator)
            logger.info("  SOURCE FILE VALIDATION (Dry-Run Parse)")
            logger.info("%s", separator)
            logger.info("  %-4s %-30s %-6s %-8s %-8s %s", "#", "Filename", "Type", "Lang", "Entries", "Status")
            logger.info("  %s %s %s %s %s %s", "-"*4, "-"*30, "-"*6, "-"*8, "-"*8, "-"*10)

            for idx, (fname, ftype, lang, count, status, err) in enumerate(results, 1):
                count_str = f"{count:,}" if count > 0 else "0"
                status_str = status if not err or status == "OK" else f"{status} ({err[:40]})"
                row_line = "  %-4d %-30s %-6s %-8s %8s  %s"
                row_args = (idx, fname[:30], ftype, lang, count_str, status_str)
                if lang == "???":
                    logger.warning(row_line, *row_args)
                else:
                    logger.info(row_line, *row_args)

            # Compute summary stats
            xml_good = sum(1 for r in results if r[1] == "XML" and r[4] == "OK")
            excel_good = sum(1 for r in results if r[1] == "Excel" and r[4] == "OK")
            xml_fail = sum(1 for r in results if r[1] == "XML" and r[4] in ("FAILED", "EMPTY", "COLUMN ERROR", "LOAD FAILED"))
            excel_fail = sum(1 for r in results if r[1] == "Excel" and r[4] in ("FAILED", "EMPTY", "COLUMN ERROR"))
            total_entries = sum(r[3] for r in results)
            errors = [(r[0], r[4], r[5]) for r in results if r[4] in ("FAILED", "COLUMN ERROR", "EMPTY", "SKIPPED", "LOAD FAILED")]

            lang_entries = {}
            for _, _, lang, count, status, _ in results:
                if status == "OK" and count > 0:
                    lang_entries[lang] = lang_entries.get(lang, 0) + count

            logger.info("%s", separator)
            summary_parts = []
            if xml_good:
                summary_parts.append(f"{xml_good} XML good")
            if excel_good:
                summary_parts.append(f"{excel_good} Excel good")
            if xml_fail:
                summary_parts.append(f"{xml_fail} XML failed")
            if excel_fail:
                summary_parts.append(f"{excel_fail} Excel failed")
            logger.info("  SUMMARY: %s", ", ".join(summary_parts) if summary_parts else "No files")
            logger.info("  Total entries parsed: %s", f"{total_entries:,}")

            if lang_entries:
                has_unknown = "???" in lang_entries
                lang_str = "  ".join(f"{lang}: {count:,}" for lang, count in sorted(lang_entries.items()))
                if has_unknown:
                    logger.warning("  Per-language: %s", lang_str)
                else:
                    logger.info("  Per-language: %s", lang_str)

            if errors:
                logger.warning("  PROBLEMS (%d):", len(errors))
                for fname, status, err_msg in errors:
                    logger.warning("    %s: %s%s", fname, status, f" ({err_msg})" if err_msg else "")

            logger.info("%s", separator)

            # Log summary to GUI
            if errors:
                gui_summary = ", ".join(summary_parts) if summary_parts else "No files"
                self._log(f"Source validation: {gui_summary}, {total_entries:,} entries total", 'warning')
                for fname, status, err_msg in errors:
                    detail = f": {err_msg}" if err_msg else ""
                    self._log(f"  {fname} — {status}{detail}", 'error')
            else:
                self._log(f"Source validation: {', '.join(summary_parts)}, {total_entries:,} entries total", 'success')

            if lang_entries:
                has_unknown = "???" in lang_entries
                lang_str = ", ".join(f"{lang}:{count:,}" for lang, count in sorted(lang_entries.items()))
                self._log(f"  Per-language: {lang_str}", 'warning' if has_unknown else 'info')

            # Split integrity warnings into critical (broken linebreaks) vs secondary
            critical_integrity = [w for w in all_integrity_warnings if w[3].startswith('Broken') or w[3].startswith('Truncated')]
            secondary_integrity = [w for w in all_integrity_warnings if not (w[3].startswith('Broken') or w[3].startswith('Truncated'))]

            # End-of-log CRITICAL warning summary (formulas + broken linebreaks)
            if all_formula_warnings or critical_integrity:
                critical_total = len(all_formula_warnings) + len(critical_integrity)
                self._log("", 'info')
                self._log(f"=== CRITICAL WARNING ({critical_total} entries) ===", 'error')
                self._log("The following entries will be SKIPPED during transfer:", 'error')
                shown = 0
                if all_formula_warnings:
                    self._log("  Formula/error text:", 'error')
                    for fname, sid, col, reason in all_formula_warnings[:20]:
                        self._log(f"    {fname} | [{col}] StringID={sid or '(empty)'} | {reason}", 'error')
                    if len(all_formula_warnings) > 20:
                        self._log(f"    ...and {len(all_formula_warnings) - 20} more.", 'error')
                    shown = min(len(all_formula_warnings), 20)
                if critical_integrity:
                    self._log("  Broken linebreak tags:", 'error')
                    remaining = max(20 - shown, 5)
                    for fname, sid, col, reason in critical_integrity[:remaining]:
                        self._log(f"    {fname} | [{col}] StringID={sid or '(empty)'} | {reason}", 'error')
                    if len(critical_integrity) > remaining:
                        self._log(f"    ...and {len(critical_integrity) - remaining} more.", 'error')
                self._log("Fix: re-save Excel with Paste Values (Ctrl+Shift+V) or fix broken <br/> tags in the source.", 'error')

            # End-of-log SECONDARY warning summary (invisible chars, encoding, control chars)
            if secondary_integrity:
                self._log("", 'info')
                self._log(f"=== SECONDARY WARNING ({len(secondary_integrity)} entries) ===", 'error')
                self._log("The following entries have encoding artifacts or invisible characters and will be SKIPPED during transfer:", 'error')
                for fname, sid, col, reason in secondary_integrity[:20]:
                    self._log(f"  {fname} | [{col}] StringID={sid or '(empty)'} | {reason}", 'error')
                if len(secondary_integrity) > 20:
                    self._log(f"  ...and {len(secondary_integrity) - 20} more.", 'error')
                self._log("Fix: correct the broken text in the source file before re-transferring.", 'error')

            # End-of-log OTHER WARNINGS ("no translation" skips)
            other_total = len(all_no_translation_warnings)
            if other_total > 0:
                self._log("", 'info')
                self._log(f"=== OTHER WARNINGS ({other_total} entries) ===", 'warning')
                if all_no_translation_warnings:
                    self._log("'no translation' entries will be skipped to preserve existing translations:", 'warning')
                    for fname, sid in all_no_translation_warnings[:20]:
                        self._log(f"  {fname} | StringID={sid or '(empty)'}", 'warning')
                    if len(all_no_translation_warnings) > 20:
                        self._log(f"  ...and {len(all_no_translation_warnings) - 20} more.", 'warning')
                # NOTE: Ellipsis warning removed — postprocess auto-fixes Unicode
                # ellipsis (…) to three dots for non-CJK languages.

            # ── Column detection: scan Excel headers to determine available match types ──
            combined_columns = {
                "has_stringid": False,
                "has_strorigin": False,
                "has_correction": False,
                "has_eventname": False,
                "has_dialogvoice": False,
                "has_desc": False,
                "has_descorigin": False,
                "has_xml": False,
            }

            # XML source files always provide StringID + StrOrigin + Correction (Str)
            has_any_xml = any(r[1] == "XML" and r[4] == "OK" for r in results)
            if has_any_xml:
                combined_columns["has_xml"] = True
                combined_columns["has_stringid"] = True
                combined_columns["has_strorigin"] = True
                combined_columns["has_correction"] = True

                # Check for Desc/DescOrigin in XML files (lightweight: break on first find)
                xml_has_descorigin = False
                xml_has_desc = False
                for filepath, _ in files_to_check:
                    if filepath.suffix.lower() != ".xml":
                        continue
                    if xml_has_descorigin and xml_has_desc:
                        break
                    try:
                        root = parse_xml_file(filepath)
                        for elem in iter_locstr_elements(root):
                            if not xml_has_descorigin and get_attr(elem, DESCORIGIN_ATTRS):
                                xml_has_descorigin = True
                            if not xml_has_desc and get_attr(elem, DESC_ATTRS):
                                xml_has_desc = True
                            if xml_has_descorigin and xml_has_desc:
                                break
                    except Exception:
                        continue
                if xml_has_descorigin:
                    combined_columns["has_descorigin"] = True
                if xml_has_desc:
                    combined_columns["has_desc"] = True

            # Detect columns from each Excel file (union of all)
            excel_files_to_scan = [
                filepath for filepath, _ in files_to_check
                if filepath.suffix.lower() in (".xlsx", ".xls")
            ]
            for ef in excel_files_to_scan:
                try:
                    cols = detect_excel_columns(ef)
                    for key in cols:
                        if cols[key]:
                            combined_columns[key] = True
                    # Per-file column summary
                    found = [k.replace("has_", "").replace("_", " ").title()
                             for k, v in cols.items() if v]
                    has_id = cols["has_stringid"] or cols["has_eventname"]
                    has_corr = cols["has_correction"]
                    if found:
                        if has_id and has_corr:
                            self._log(f"  {ef.name}: {', '.join(found)}", 'info')
                        elif not has_id:
                            self._log(f"  {ef.name}: {', '.join(found)} \u2014 no StringID/EventName, cannot match", 'warning')
                        elif not has_corr:
                            self._log(f"  {ef.name}: {', '.join(found)} \u2014 no Correction column", 'warning')
                    else:
                        self._log(f"  {ef.name}: no recognized columns", 'warning')
                except Exception:
                    continue

            # Store and update match types on main thread
            self._source_columns = combined_columns
            self._task_queue.put(('update_match_types',))

            # Log column detection
            col_info = []
            if combined_columns["has_stringid"]:
                col_info.append("StringID")
            if combined_columns["has_eventname"]:
                col_info.append("EventName")
            if combined_columns["has_dialogvoice"]:
                col_info.append("DialogVoice")
            if combined_columns["has_strorigin"]:
                col_info.append("StrOrigin")
            if combined_columns["has_correction"]:
                col_info.append("Correction")
            if combined_columns["has_descorigin"]:
                col_info.append("DescOrigin")
            if combined_columns["has_desc"]:
                col_info.append("Desc")
            if combined_columns["has_xml"]:
                col_info.append("XML")
            logger.info("  Source columns detected: %s", ", ".join(col_info) if col_info else "NONE")

            # Desc availability info/warning
            has_do = combined_columns["has_descorigin"]
            has_d = combined_columns["has_desc"]
            if not has_do and not has_d:
                self._log("No Desc/DescOrigin found in source \u2014 Desc transfer will be skipped", 'warning')
            elif has_do and not has_d:
                self._log("DescOrigin found (Desc column will be auto-created during transfer)", 'info')
            elif has_d and not has_do:
                self._log("Desc found but DescOrigin missing \u2014 Desc may not match correctly", 'warning')
            else:
                self._log("Desc data available \u2014 voice direction descriptions will be transferred", 'info')

            self._task_queue.put(('status', 'Ready', 0))

        # Use a SEPARATE validation thread — NOT _run_in_thread.
        # This prevents overlapping worker issues: validation does NOT send
        # ('done',) and does NOT interfere with _worker_thread tracking.
        self._validation_thread = threading.Thread(
            target=validation_work, daemon=True
        )
        self._validation_thread.start()
        self._start_validation_poll()

    def _start_validation_poll(self):
        """Poll queue for validation thread messages only.

        Unlike _poll_queue, this does NOT handle ('done',) and stops
        automatically when the validation thread finishes. Uses the
        shared _dispatch_queue_msg for consistent message handling.
        """
        try:
            while True:
                msg = self._task_queue.get_nowait()
                if self._dispatch_queue_msg(msg):
                    # A real worker sent ('done',) — shouldn't happen during
                    # validation-only, but handle gracefully
                    self._enable_buttons()
                    return
        except queue.Empty:
            pass

        # Keep polling while validation thread is alive AND no worker took over
        if (self._validation_thread is not None
                and self._validation_thread.is_alive()
                and (self._worker_thread is None or not self._worker_thread.is_alive())):
            self.root.after(50, self._start_validation_poll)

    def _browse_source(self):
        """Browse for source folder."""
        initial_dir = self.source_path.get() or str(config.SOURCE_FOLDER)
        path = filedialog.askdirectory(
            title="Select Source Folder",
            initialdir=initial_dir if Path(initial_dir).is_dir() else None,
        )
        if path:
            self.source_path.set(path)
            self._analyze_folder(path, "SOURCE")

    def _browse_target(self):
        """Browse for target folder."""
        path = filedialog.askdirectory(title="Select Target Folder")
        if path:
            self.target_path.set(path)
            self._analyze_folder(path, "TARGET")

    def _browse_loc_path(self):
        """Browse for LOC folder path."""
        path = filedialog.askdirectory(title="Select LOC Folder (languagedata_*.xml files)")
        if path:
            self.settings_loc_path.set(path)

    def _browse_export_path(self):
        """Browse for Export folder path."""
        path = filedialog.askdirectory(title="Select Export Folder (categorized .loc.xml files)")
        if path:
            self.settings_export_path.set(path)

    def _on_match_type_changed(self):
        """Show/hide options sub-frames based on selected match type."""
        match_type = self.match_type.get()

        # Hide stringid_all_frame for non-stringid modes
        if match_type != "stringid_only":
            self.stringid_all_frame.pack_forget()

        if match_type == "strorigin_filename":
            # strorigin_filename: no fuzzy, no unique-only, no non-script — just scope + transfer
            self.precision_options_frame.pack_forget()
            self.unique_only_frame.pack_forget()
            self.strict_non_script_frame.pack_forget()
            self.transfer_btn.config(state='normal')
            self.transfer_scope_frame.pack(fill=tk.X, pady=(4, 0))
            self._bind_mousewheel_recursive(self.transfer_scope_frame)
        elif match_type in ("strict", "strorigin_only", "strorigin_descorigin"):
            self.precision_options_frame.pack(fill=tk.X, pady=(4, 0))
            # Show/hide the fuzzy sub-frame based on current precision
            self._on_precision_changed()
            # Enable TRANSFER button + show transfer scope toggle
            self.transfer_btn.config(state='normal')
            self.transfer_scope_frame.pack(fill=tk.X, pady=(4, 0))
            # SAFETY: StrOrigin Only defaults to untranslated-only (no StringID verification)
            if match_type == "strorigin_only":
                self.transfer_scope.set("untranslated")
                # Show unique-only checkbox (StrOrigin Only specific)
                self.unique_only_frame.pack(fill=tk.X, pady=(4, 0))
                self._bind_mousewheel_recursive(self.unique_only_frame)
                self.strict_non_script_frame.pack_forget()
            else:
                # strict or strorigin_descorigin — both have StringID for category filtering
                self.unique_only_frame.pack_forget()
                self.strict_non_script_frame.pack(fill=tk.X, pady=(4, 0))
                self._bind_mousewheel_recursive(self.strict_non_script_frame)
            # Rebind mousewheel on newly shown frames
            self._bind_mousewheel_recursive(self.precision_options_frame)
            self._bind_mousewheel_recursive(self.transfer_scope_frame)
        else:
            # stringid_only
            self.precision_options_frame.pack_forget()
            # Enable TRANSFER button + show transfer scope toggle
            self.transfer_btn.config(state='normal')
            self.transfer_scope_frame.pack(fill=tk.X, pady=(4, 0))
            self.unique_only_frame.pack_forget()
            self.strict_non_script_frame.pack_forget()
            # Show ALL categories checkbox
            self.stringid_all_frame.pack(fill=tk.X, pady=(4, 0))
            self._bind_mousewheel_recursive(self.stringid_all_frame)
            # Rebind mousewheel on newly shown frame
            self._bind_mousewheel_recursive(self.transfer_scope_frame)

    def _update_match_type_availability(self):
        """Enable/disable match type radio buttons based on detected source columns.

        Rules:
        - stringid_only: Needs (StringID OR EventName) AND Correction
        - strict: Needs (StringID OR EventName) AND StrOrigin AND Correction
        - strorigin_only: Needs StrOrigin AND Correction

        XML source files always have all fields (StringID, StrOrigin, Correction).
        """
        cols = self._source_columns
        has_id = cols["has_stringid"] or cols["has_eventname"] or cols["has_xml"]
        has_strorigin = cols["has_strorigin"] or cols["has_xml"]
        has_correction = cols["has_correction"] or cols["has_xml"]
        has_descorigin = cols.get("has_descorigin", False)

        # Determine which match types are valid
        valid = {
            "stringid_only": has_id and has_correction,
            "strict": has_id and has_strorigin and has_correction,
            "strorigin_only": has_strorigin and has_correction,
            "strorigin_descorigin": has_strorigin and has_descorigin and has_correction,
            "strorigin_filename": has_strorigin and has_correction,
        }

        reasons = {
            "stringid_only": "Needs StringID/EventName + Correction columns",
            "strict": "Needs StringID/EventName + StrOrigin + Correction columns",
            "strorigin_only": "Needs StrOrigin + Correction columns",
            "strorigin_descorigin": "Needs StrOrigin + DescOrigin + Correction columns",
            "strorigin_filename": "Needs StrOrigin + Correction columns + EXPORT folder",
        }

        for value, (rb, desc_lbl) in self._match_type_radios.items():
            if valid.get(value, True):
                rb.config(state='normal', fg='black')
                # Restore original description
                orig_descs = {
                    "stringid_only": "SCRIPT categories only - match by StringID",
                    "strict": "Requires BOTH to match exactly",
                    "strorigin_only": "Match by StrOrigin text only - skips Dialog/Sequencer",
                    "strorigin_descorigin": "Requires BOTH StrOrigin AND DescOrigin to match",
                    "strorigin_filename": "Match by StrOrigin + export filepath (precise, 2-pass)",
                }
                desc_lbl.config(text=orig_descs.get(value, ""), fg='#888')
            else:
                rb.config(state='disabled', fg='#999')
                desc_lbl.config(text=reasons.get(value, "Missing columns"), fg='#cc0000')

        # If current selection is now disabled, fall back to first valid mode
        current = self.match_type.get()
        if not valid.get(current, True):
            for fb in ("strict", "strorigin_only", "strorigin_descorigin", "stringid_only"):
                if valid.get(fb, False):
                    self.match_type.set(fb)
                    self._on_match_type_changed()
                    break

        # Log to GUI
        available_modes = [k for k, v in valid.items() if v]
        if available_modes:
            self._log(f"Available match types: {', '.join(m.replace('_', ' ').title() for m in available_modes)}", 'info')
        else:
            self._log("No match types available — source lacks required columns", 'warning')

    def _on_transfer_scope_changed(self):
        """Warn user when switching to 'ALL' on StrOrigin Only (no StringID safety)."""
        match_type = self.match_type.get()
        scope = self.transfer_scope.get()

        if scope == "all" and match_type == "strorigin_only":
            confirm = messagebox.askokcancel(
                "Warning: Overwrite Risk",
                "StrOrigin Only matches by source text ONLY — there is no StringID "
                "verification.\n\n"
                "Switching to 'Transfer ALL' may OVERWRITE previously correct "
                "translations with wrong values if different entries share the "
                "same source text.\n\n"
                "Are you sure you want to allow overwriting?",
                icon='warning',
            )
            if not confirm:
                self.transfer_scope.set("untranslated")

    def _update_fuzzy_model_status(self):
        """Update the fuzzy model status display."""
        available, msg = check_model_available()
        if available:
            if self._fuzzy_model is not None:
                info = get_cached_index_info()
                if info:
                    self.fuzzy_model_status.set(f"Model2Vec: Ready ({info['ntotal']} vectors)")
                else:
                    self.fuzzy_model_status.set(f"Model2Vec: Loaded, no index yet")
            else:
                self.fuzzy_model_status.set(f"Model2Vec: Not loaded (will load on first use)")
        else:
            self.fuzzy_model_status.set(f"Model2Vec: Not available - model folder missing")

    def _on_precision_changed(self):
        """Show/hide fuzzy threshold slider within precision options."""
        if self.match_precision.get() == "fuzzy":
            self.fuzzy_sub_frame.pack(fill=tk.X, pady=(4, 0))
            self._update_fuzzy_model_status()
            self._bind_mousewheel_recursive(self.fuzzy_sub_frame)
        else:
            self.fuzzy_sub_frame.pack_forget()

    def _on_threshold_changed(self, value):
        """Update threshold display labels when slider moves."""
        # Round to nearest step
        val = round(float(value) / config.FUZZY_THRESHOLD_STEP) * config.FUZZY_THRESHOLD_STEP
        self.fuzzy_threshold.set(val)
        self.threshold_label.config(text=f"{val:.2f}")

    def _ensure_fuzzy_model(self) -> bool:
        """Load Model2Vec model if needed. Returns True if model is ready.

        Thread-safe: uses queue for UI updates instead of direct widget access.
        """
        if self._fuzzy_model is not None:
            return True

        available, msg = check_model_available()
        if not available:
            self._task_queue.put(('messagebox', 'showerror', 'Model2Vec Not Found', msg))
            return False

        try:
            self._task_queue.put(('fuzzy_status', 'Model2Vec: Loading...'))
            self._fuzzy_model = load_model(self._update_status)
            self._task_queue.put(('fuzzy_status', 'Model2Vec: Model loaded'))
            self._log("Model2Vec model loaded successfully", 'success')
            return True
        except Exception as e:
            self._task_queue.put(('fuzzy_status', 'Model2Vec: Load failed'))
            self._task_queue.put(('messagebox', 'showerror', 'Model Load Error', f'Failed to load Model2Vec model:\n{e}'))
            self._log(f"Model load error: {e}", 'error')
            return False

    def _ensure_fuzzy_entries(
        self,
        target_path: str,
        stringid_filter: set = None,
        only_untranslated: bool = False,
    ) -> bool:
        """Load target entries for fuzzy matching (no FAISS index needed).

        Used by find_matches_strict_fuzzy which builds per-StringID mini-indexes.
        Much faster than _ensure_fuzzy_index since it skips full FAISS build.

        Args:
            target_path: Path to target folder
            stringid_filter: Set of StringIDs to include. CRITICAL for performance!
                            Only entries with these StringIDs are loaded.
            only_untranslated: If True, only load entries where Str has Korean.
        """
        # Cache check — reuse if same target, same filter, same scope
        if (self._fuzzy_entries is not None
                and self._fuzzy_index_path == target_path
                and self._fuzzy_texts
                and self._fuzzy_index_filter == stringid_filter
                and self._fuzzy_index_untranslated == only_untranslated):
            return True

        if not target_path:
            self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'Fuzzy mode requires a Target folder.'))
            return False

        target = Path(target_path)
        if not target.exists():
            self._task_queue.put(('messagebox', 'showerror', 'Error', f'Target folder not found:\n{target}'))
            return False

        try:
            filter_desc = ""
            if stringid_filter:
                filter_desc = f" (filtering to {len(stringid_filter):,} StringIDs)"
            self._log(f"Loading target entries{filter_desc}: {target}", 'info')

            texts, entries = build_index_from_folder(
                target, self._update_status,
                stringid_filter=stringid_filter,
                only_untranslated=only_untranslated,
            )

            if not texts:
                self._task_queue.put(('messagebox', 'showerror', 'Error', f'No matching entries found in target folder:\n{target}'))
                return False

            # Store entries but skip expensive FAISS index build
            self._fuzzy_index_path = target_path
            self._fuzzy_index_filter = stringid_filter
            self._fuzzy_index_untranslated = only_untranslated
            self._fuzzy_texts = texts
            self._fuzzy_entries = entries
            self._fuzzy_index = None  # Invalidate stale FAISS index

            self._task_queue.put(('fuzzy_status', f"Ready ({len(entries):,} entries)"))
            self._log(f"Target entries loaded: {len(entries):,} entries", 'success')
            return True

        except Exception as e:
            self._task_queue.put(('messagebox', 'showerror', 'Load Error', f'Failed to load target entries:\n{e}'))
            self._log(f"Load error: {e}", 'error')
            return False

    def _ensure_fuzzy_index(
        self,
        target_path: str,
        stringid_filter: set = None,
        only_untranslated: bool = False,
    ) -> bool:
        """Build FAISS index for target folder if needed. Returns True if index is ready.

        Args:
            target_path: Path to target folder
            stringid_filter: Optional set of StringIDs to include. CRITICAL for performance!
            only_untranslated: If True, only include entries where Str has Korean.
        """
        # Reuse cache if same target, same filter, same scope
        if (self._fuzzy_index is not None
                and self._fuzzy_index_path == target_path
                and self._fuzzy_texts
                and self._fuzzy_index_filter == stringid_filter
                and self._fuzzy_index_untranslated == only_untranslated):
            return True

        if not target_path:
            self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'Fuzzy mode requires a Target folder for indexing.'))
            return False

        target = Path(target_path)
        if not target.exists():
            self._task_queue.put(('messagebox', 'showerror', 'Error', f'Target folder not found:\n{target}'))
            return False

        try:
            filter_info = f" (filtering to {len(stringid_filter):,} StringIDs)" if stringid_filter else " (FULL - no filter!)"
            self._log(f"Building FAISS index for: {target}{filter_info}", 'info')
            texts, entries = build_index_from_folder(
                target, self._update_status,
                stringid_filter=stringid_filter,
                only_untranslated=only_untranslated,
            )

            if not texts:
                self._task_queue.put(('messagebox', 'showerror', 'Error', f'No StrOrigin values found in target folder:\n{target}'))
                return False

            self._fuzzy_index = build_faiss_index(
                texts, entries, self._fuzzy_model, self._update_status
            )
            self._fuzzy_index_path = target_path
            self._fuzzy_index_filter = stringid_filter
            self._fuzzy_index_untranslated = only_untranslated
            self._fuzzy_texts = texts
            self._fuzzy_entries = entries

            info = get_cached_index_info()
            vec_count = info['ntotal'] if info else len(texts)
            self._task_queue.put(('fuzzy_status', f"Ready ({vec_count} vectors)"))
            self._log(f"FAISS index built: {vec_count} vectors", 'success')
            return True

        except Exception as e:
            self._task_queue.put(('messagebox', 'showerror', 'Index Build Error', f'Failed to build FAISS index:\n{e}'))
            self._log(f"Index build error: {e}", 'error')
            return False

    def _extract_stringids_from_source(self, source: Path) -> set:
        """Extract unique StringIDs from source folder.

        Used to filter FAISS index build - only include entries matching source StringIDs.
        Handles both XML and Excel source files.
        """
        from core.xml_parser import parse_xml_file, iter_locstr_elements, get_attr, STRINGID_ATTRS
        from core.excel_io import read_corrections_from_excel

        stringids = set()

        if source.is_file():
            # Handle single file - XML or Excel
            if source.suffix.lower() == '.xml':
                xml_files = [source]
                excel_files = []
            elif source.suffix.lower() in ('.xlsx', '.xls'):
                xml_files = []
                excel_files = [source]
            else:
                return stringids
        else:
            # Handle folder - find all XML and Excel files
            xml_files = list(source.rglob("*.xml"))
            excel_files = list(source.rglob("*.xlsx")) + list(source.rglob("*.xls"))

        # Extract from XML files (lowercase for case-insensitive filtering)
        for xml_file in xml_files:
            try:
                root = parse_xml_file(xml_file)
                for elem in iter_locstr_elements(root):
                    sid = get_attr(elem, STRINGID_ATTRS).strip()
                    if sid:
                        stringids.add(sid.lower())
            except Exception:
                continue

        # Extract from Excel files (lowercase for case-insensitive filtering)
        for excel_file in excel_files:
            try:
                corrections = read_corrections_from_excel(excel_file)
                for c in corrections:
                    sid = c.get("string_id", "")
                    if sid:
                        stringids.add(sid.lower())
            except Exception:
                continue

        return stringids

    def _save_settings(self):
        """Save current settings to config file."""
        loc_path = self.settings_loc_path.get().strip()
        export_path = self.settings_export_path.get().strip()

        if not loc_path and not export_path:
            messagebox.showwarning("Warning", "Please enter at least one path to save.")
            return

        # Validate paths exist
        if loc_path and not Path(loc_path).exists():
            if not messagebox.askyesno("Warning", f"LOC path does not exist:\n{loc_path}\n\nSave anyway?"):
                return

        if export_path and not Path(export_path).exists():
            if not messagebox.askyesno("Warning", f"Export path does not exist:\n{export_path}\n\nSave anyway?"):
                return

        # Save settings
        config.update_settings(
            loc_folder=loc_path if loc_path else None,
            export_folder=export_path if export_path else None
        )

        # Clear cached data since paths changed
        self.cached_paths = None
        self.strorigin_index = None
        self.translation_lookup = None
        self.stringid_to_category = None
        self.stringid_to_subfolder = None
        self.stringid_to_filepath = None

        # Clear fuzzy cache too
        self._fuzzy_model = None
        self._fuzzy_index = None
        self._fuzzy_index_path = None
        self._fuzzy_index_filter = None
        self._fuzzy_index_untranslated = None
        self._fuzzy_texts = None
        self._fuzzy_entries = None
        clear_fuzzy_cache()

        # Clear language code cache (valid codes depend on LOC folder)
        from core.source_scanner import clear_language_code_cache
        clear_language_code_cache()

        self._log("Settings saved to settings.json", 'success')
        messagebox.showinfo("Success", "Settings saved successfully!")

    def _update_status(self, text: str, progress: float = None):
        """Update status text and optionally progress bar (thread-safe via queue).

        Also checks cancel event — raises InterruptedError if cancelled.
        """
        if self._cancel_event.is_set():
            raise InterruptedError("Operation cancelled by user")
        self._task_queue.put(('status', text, progress))

    def _update_status_on_main(self, text: str, progress: float = None):
        """Apply status update on main thread."""
        self.status_text.set(text)
        if progress is not None:
            self.progress_value.set(progress)

    def _dispatch_queue_msg(self, msg) -> bool:
        """Process a single queue message. Returns True if ('done',) received."""
        try:
            kind = msg[0]
            if kind == 'log':
                _, ts, text, tag = msg
                self._log_on_main(ts, text, tag)
            elif kind == 'status':
                _, text, progress = msg
                self._update_status_on_main(text, progress)
            elif kind == 'progress':
                _, value = msg
                self.progress_value.set(value)
            elif kind == 'fuzzy_status':
                _, text = msg
                self.fuzzy_model_status.set(text)
            elif kind == 'messagebox':
                _, func_name, title, message = msg
                func = getattr(messagebox, func_name)
                func(title, message)
            elif kind == 'checks_status':
                _, text = msg
                self.checks_status_text.set(text)
            elif kind == 'enable_results_btn':
                self.open_results_btn.config(state='normal')
            elif kind == 'update_match_types':
                self._update_match_type_availability()
            elif kind == 'done':
                return True
        except tk.TclError:
            pass  # Widget destroyed during shutdown
        return False

    def _poll_queue(self):
        """Drain the task queue on the main thread. Scheduled via root.after."""
        try:
            while True:
                msg = self._task_queue.get_nowait()
                if self._dispatch_queue_msg(msg):
                    self._enable_buttons()
                    return  # Stop polling
        except queue.Empty:
            pass

        # Continue polling if worker thread is alive
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self.root.after(50, self._poll_queue)
        elif self._worker_thread is not None:
            # Thread ended but no 'done' message yet — drain remaining
            try:
                while True:
                    msg = self._task_queue.get_nowait()
                    if self._dispatch_queue_msg(msg):
                        break
            except queue.Empty:
                pass
            self._enable_buttons()

    def _request_cancel(self):
        """Handle cancel button click."""
        self._cancel_event.set()
        self._log("Cancelling operation...", 'warning')

    def _run_in_thread(self, work_fn):
        """Run work_fn in a daemon thread with error handling.

        The work function should use self._log and self._update_status
        (both thread-safe). On completion, sends ('done',) to queue.
        Drains any leftover validation messages before starting.
        """
        # Drain leftover validation queue messages to keep logs clean
        self._drain_stale_queue()

        def _wrapper():
            try:
                work_fn()
            except InterruptedError:
                self._log("Operation cancelled.", 'warning')
                self._task_queue.put(('status', 'Cancelled', None))
            except Exception as e:
                self._task_queue.put(('messagebox', 'showerror', 'Error', f'Operation failed:\n{e}'))
                self._log(f"ERROR: {e}", 'error')
                self._task_queue.put(('status', f'Error: {e}', None))
                logger.exception("Worker thread error")
            finally:
                self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=_wrapper, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)

    def _drain_stale_queue(self):
        """Process any leftover queue messages (e.g. from finished validation)."""
        try:
            while True:
                msg = self._task_queue.get_nowait()
                self._dispatch_queue_msg(msg)
        except queue.Empty:
            pass

    def _load_data_if_needed(self, need_sequencer: bool = True) -> bool:
        """Load data if not cached or paths changed."""
        loc_folder = config.LOC_FOLDER
        export_folder = config.EXPORT_FOLDER
        current_paths = (str(loc_folder), str(export_folder))

        if self.cached_paths == current_paths and self.translation_lookup is not None:
            if not need_sequencer or self.strorigin_index is not None:
                return True

        sequencer_folder = export_folder / "Sequencer"

        if not loc_folder.exists():
            self._task_queue.put(('messagebox', 'showerror', 'Error', f'LOC folder not found:\n{loc_folder}\n\nPlease configure in Settings.'))
            return False

        if need_sequencer:
            if not sequencer_folder.exists():
                self._task_queue.put(('messagebox', 'showerror', 'Error', f'Sequencer folder not found:\n{sequencer_folder}\n\nPlease check Export path in Settings.'))
                return False

            self._log(f"Loading Sequencer data...", 'info')
            self.strorigin_index = build_sequencer_strorigin_index(
                sequencer_folder, self._update_status
            )

            if not self.strorigin_index:
                self._task_queue.put(('messagebox', 'showerror', 'Error', 'No Sequencer data found.'))
                return False

            self._log(f"Loaded {len(self.strorigin_index)} Sequencer entries", 'success')

            # Also build category mapping for StringID-only mode
            self._update_status("Building category index...")
            self._log("Building category index...", 'info')
            self.stringid_to_category = build_stringid_to_category(export_folder, self._update_status)
            self._log(f"Indexed {len(self.stringid_to_category)} StringIDs to categories", 'success')

            # Build subfolder mapping for exclusion filtering
            self._update_status("Building subfolder index...")
            self._log("Building subfolder index...", 'info')
            self.stringid_to_subfolder = build_stringid_to_subfolder(export_folder, self._update_status)
            self._log(f"Indexed {len(self.stringid_to_subfolder)} StringIDs to subfolders", 'success')

            # Build filepath mapping for strorigin_filename mode
            self._update_status("Building filepath index...")
            self._log("Building filepath index...", 'info')
            self.stringid_to_filepath = build_stringid_to_filepath(export_folder, self._update_status)
            self._log(f"Indexed {len(self.stringid_to_filepath)} StringIDs to filepaths", 'success')

        # Load language files
        self._log("Discovering language files...", 'info')
        lang_files = discover_language_files(loc_folder)
        if not lang_files:
            self._task_queue.put(('messagebox', 'showerror', 'Error', 'No language files found.'))
            return False

        self._log(f"Found {len(lang_files)} languages: {', '.join(lang_files.keys())}", 'success')

        self.translation_lookup = build_translation_lookup(lang_files, self._update_status)
        self.available_langs = list(lang_files.keys())
        self.cached_paths = current_paths

        return True

    def _clear_fields(self):
        """Clear all input fields."""
        self.source_path.set(str(config.SOURCE_FOLDER))
        self.target_path.set("")
        self.progress_value.set(0)
        self.status_text.set("Ready")
        self._clear_log()

    def _disable_buttons(self):
        """Disable all action buttons during processing."""
        self._cancel_event.clear()
        self.transfer_btn.config(state='disabled')
        self.preprocess_btn.config(state='disabled')
        self.missing_trans_btn.config(state='disabled')
        self.exclude_btn.config(state='disabled')
        self.check_korean_btn.config(state='disabled')
        self.check_patterns_btn.config(state='disabled')
        self.check_quality_btn.config(state='disabled')
        self.check_all_btn.config(state='disabled')
        self.open_results_btn.config(state='disabled')
        self.cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

    def _enable_buttons(self):
        """Re-enable all action buttons."""
        self.transfer_btn.config(state='normal')
        self.preprocess_btn.config(state='normal')
        self.missing_trans_btn.config(state='normal')
        self.exclude_btn.config(state='normal')
        self.check_korean_btn.config(state='normal')
        self.check_patterns_btn.config(state='normal')
        self.check_quality_btn.config(state='normal')
        self.check_all_btn.config(state='normal')
        self.cancel_btn.pack_forget()
        self._worker_thread = None

    def _quick_detect_columns(self, source_folder: Path):
        """Quick synchronous column detection for when path was pasted, not browsed."""
        try:
            from core.excel_io import detect_excel_columns
            from core.xml_parser import parse_xml_file, iter_locstr_elements, get_attr, DESC_ATTRS, DESCORIGIN_ATTRS
            cols = self._source_columns.copy()
            for xlsx in source_folder.rglob("*.xlsx"):
                if xlsx.name.startswith("~$"):
                    continue
                detected = detect_excel_columns(xlsx)
                cols["has_stringid"] = detected["has_stringid"]
                cols["has_strorigin"] = detected["has_strorigin"]
                cols["has_correction"] = detected["has_correction"]
                cols["has_eventname"] = detected["has_eventname"]
                cols["has_descorigin"] = detected.get("has_descorigin", False)
                cols["has_desc"] = detected.get("has_desc", False)
                break  # Only check first Excel file
            for xml in source_folder.rglob("*.xml"):
                cols["has_xml"] = True
                # Scan first XML for DescOrigin/Desc (same as threaded scan)
                try:
                    root = parse_xml_file(xml)
                    for elem in iter_locstr_elements(root):
                        if not cols["has_descorigin"] and get_attr(elem, DESCORIGIN_ATTRS):
                            cols["has_descorigin"] = True
                        if not cols["has_desc"] and get_attr(elem, DESC_ATTRS):
                            cols["has_desc"] = True
                        if cols["has_descorigin"] and cols["has_desc"]:
                            break
                except Exception:
                    pass
                break
            self._source_columns = cols
        except Exception:
            pass  # Keep existing column state

    def _validate_columns_for_mode(self, cols: dict) -> bool:
        """Validate that source columns are compatible with the selected match type.
        Returns True if valid, False if not (shows error dialog)."""
        mt = self.match_type.get()
        has_id = cols["has_stringid"] or cols["has_eventname"] or cols["has_xml"]
        has_strorigin = cols["has_strorigin"] or cols["has_xml"]
        has_correction = cols["has_correction"] or cols["has_xml"]

        if mt == "stringid_only" and not (has_id and has_correction):
            messagebox.showerror("Error", "StringID-Only mode requires StringID (or EventName) + Correction columns.\n\n"
                                 "Your source files don't have these columns.")
            return False
        if mt == "strict" and not (has_id and has_strorigin and has_correction):
            messagebox.showerror("Error", "Strict mode requires StringID (or EventName) + StrOrigin + Correction columns.\n\n"
                                 "Your source files don't have all required columns.")
            return False
        if mt == "strorigin_only" and not (has_strorigin and has_correction):
            messagebox.showerror("Error", "StrOrigin Only mode requires StrOrigin + Correction columns.\n\n"
                                 "Your source files don't have these columns.")
            return False
        if mt == "strorigin_descorigin" and not (has_strorigin and cols.get("has_descorigin", False) and has_correction):
            messagebox.showerror("Error", "StrOrigin + DescOrigin mode requires StrOrigin + DescOrigin + Correction columns.\n\n"
                                 "Your source files don't have all required columns.")
            return False
        if mt == "strorigin_filename" and not (has_strorigin and has_correction):
            messagebox.showerror("Error", "StrOrigin + FileName mode requires StrOrigin + Correction columns.\n\n"
                                 "Your source files don't have these columns.")
            return False
        return True

    def _open_exclude_dialog(self):
        """Open the EXPORT tree browser to configure exclusion rules."""
        export_path = config.EXPORT_FOLDER
        if not export_path.exists():
            messagebox.showwarning(
                "Warning",
                f"EXPORT folder not found:\n{export_path}\n\n"
                "Please configure the EXPORT path in Settings first."
            )
            return

        dialog = ExcludeDialog(self.root, export_path, self._exclude_paths)
        if dialog.result is not None:
            self._exclude_paths = dialog.result
            config.save_exclude_rules(self._exclude_paths)
            self._update_exclude_count_label()

    def _update_exclude_count_label(self):
        """Update the exclude count label next to the Exclude button."""
        count = len(self._exclude_paths)
        if count > 0:
            self._exclude_count_label.configure(text=f"({count} excluded)")
        else:
            self._exclude_count_label.configure(text="")

    def _find_missing_translations(self):
        """
        Find Korean strings in Target that are MISSING from Source.
        Opens parameter dialog first, then runs with selected options.
        """
        # Validate source folder — all on main thread
        source_path = self.source_path.get().strip()
        if not source_path:
            messagebox.showwarning("Warning", "Please select a Source folder (the reference data).")
            return

        source = Path(source_path)
        if not source.exists():
            messagebox.showerror("Error", f"Source not found:\n{source}")
            return

        # Validate target (folder with languagedata_*.xml files)
        target_path_str = self.target_path.get().strip()
        if not target_path_str:
            messagebox.showwarning("Warning",
                "Please set a Target folder on the Transfer tab.\n\n"
                "Target should be the LOC folder containing languagedata_*.xml files.")
            return

        target = Path(target_path_str)
        if not target.exists():
            messagebox.showerror("Error", f"Target not found:\n{target}")
            return

        if not target.is_dir():
            messagebox.showwarning("Warning",
                "Target must be a folder containing language files.\n\n"
                "Example: LOC folder with languagedata_FRE.xml, custom_GER.xml, etc.")
            return

        # Use flexible target scanner (supports any XML with LocStr elements)
        _target_scan = scan_target_for_languages(target)
        lang_files = []
        for lang_code, files in _target_scan.lang_files.items():
            # Missing translations only works with XML targets for now
            for f in files:
                if f.suffix.lower() == ".xml":
                    lang_files.append(f)

        if not lang_files:
            messagebox.showwarning("Warning",
                f"No parseable language XML files found in:\n{target}\n\n"
                "Files need LocStr elements with StringId + StrOrigin + Str attributes.\n"
                "Example: languagedata_FRE.xml, custom_GER.xml, etc.")
            return

        # Open parameter dialog
        dialog = MissingParamsDialog(self.root)
        params = dialog.result
        if params is None:
            return  # User cancelled

        # Ask user for output directory (must be on main thread — file dialog)
        output_dir = filedialog.askdirectory(
            title="Select Output Directory for Missing Translation Reports",
            initialdir=str(Path(__file__).parent.parent / "MissingTranslationReports")
        )

        if not output_dir:
            return  # User cancelled

        self._run_missing_translations(
            source=source,
            target=target,
            lang_files=lang_files,
            output_dir=output_dir,
            match_mode=params["match_mode"],
            threshold=params["threshold"],
        )

    def _run_missing_translations(self, source, target, lang_files, output_dir, match_mode, threshold):
        """Run Find Missing Translations with the given parameters."""
        self._disable_buttons()
        self.progress_value.set(0)
        self._clear_log()

        mode_labels = {
            "stringid_kr_strict": "StringID + KR (Strict)",
            "stringid_kr_fuzzy": "StringID + KR (Fuzzy)",
            "kr_strict": "KR only (Strict)",
            "kr_fuzzy": "KR only (Fuzzy)",
        }

        self._log("=== Find Missing Translations ===", 'header')
        self._log(f"Source: {source}", 'info')
        self._log(f"Target: {target} ({len(lang_files)} language files)", 'info')
        self._log(f"Output: {output_dir}", 'info')
        self._log(f"Match Mode: {mode_labels.get(match_mode, match_mode)}", 'info')
        if match_mode.endswith("_fuzzy"):
            self._log(f"Fuzzy Threshold: {threshold:.2f}", 'info')
        if self._exclude_paths:
            self._log(f"Exclude rules: {len(self._exclude_paths)} paths", 'warning')
            for ep in self._exclude_paths:
                etype = "Folder" if not ep.lower().endswith(".xml") else "File"
                self._log(f"  [{etype}] {ep}", 'info')
        self._log("", 'info')

        export_folder = None
        if config.EXPORT_FOLDER.exists():
            export_folder = str(config.EXPORT_FOLDER)
            self._log(f"Category mapping from: {config.EXPORT_FOLDER}", 'info')

        def work():
            # For fuzzy modes, load model first
            fuzzy_model = None
            if match_mode.endswith("_fuzzy"):
                self._log("Loading Model2Vec model for fuzzy matching...", 'info')
                if not self._ensure_fuzzy_model():
                    return
                fuzzy_model = self._fuzzy_model

            def progress_cb(msg, pct):
                self._update_status(msg, progress=pct)
                self._log(msg, 'info')

            self._update_status("Finding missing translations...")

            results = find_missing_with_options(
                source_path=str(source),
                target_path=str(target),
                output_dir=output_dir,
                match_mode=match_mode,
                threshold=threshold,
                export_folder=export_folder,
                progress_cb=progress_cb,
                model=fuzzy_model,
                exclude_paths=self._exclude_paths if self._exclude_paths else None,
            )

            self._task_queue.put(('progress', 100))

            # Log summary
            self._log("", 'info')
            self._log("=== RESULTS ===", 'header')
            self._log(f"Match mode: {mode_labels.get(match_mode, match_mode)}", 'info')
            self._log(f"Total Korean entries: {results['total_korean']:,}", 'info')
            self._log(f"HITS (matched in source): {results['total_hits']:,}", 'success')
            self._log(f"MISSES (need translation): {results['total_misses']:,}",
                     'error' if results['total_misses'] > 0 else 'success')
            if results.get('total_excluded', 0) > 0:
                self._log(f"EXCLUDED (by rules): {results['total_excluded']:,}", 'warning')

            self._log("", 'info')
            self._log("=== PER-LANGUAGE BREAKDOWN ===", 'header')
            for lang in sorted(results['languages'].keys()):
                lr = results['languages'][lang]
                self._log(
                    f"  {lang}: {lr['misses']:,} missing / {lr['korean_entries']:,} Korean entries",
                    'info'
                )

            self._log("", 'info')
            self._log("=== OUTPUT FILES ===", 'header')
            self._log(f"Directory: {output_dir}", 'success')

            self._log("", 'info')
            self._log("Excel reports:", 'info')
            for fp in results['output_files']:
                self._log(f"  {Path(fp).name}", 'info')

            close_folders = results.get('close_folders', {})
            if close_folders:
                self._log("", 'info')
                self._log("Close folders (EXPORT structure):", 'info')
                for lang in sorted(close_folders.keys()):
                    self._log(f"  Close_{lang}/", 'success')

            if results.get('master_summary'):
                self._log("", 'info')
                self._log(f"Master Summary: {Path(results['master_summary']).name}", 'success')

            self._update_status(f"Done! {results['total_misses']:,} total missing translations")

            close_count = len(close_folders)
            master_note = ""
            if results.get('master_summary'):
                master_note = f"\nMaster Summary: {Path(results['master_summary']).name}\n"
            excluded_note = ""
            if results.get('total_excluded', 0) > 0:
                excluded_note = f"Excluded by rules: {results['total_excluded']:,}\n"
            self._task_queue.put(('messagebox', 'showinfo', 'Missing Translations Report',
                f"Report generated successfully!\n\n"
                f"Mode: {mode_labels.get(match_mode, match_mode)}\n"
                f"Languages scanned: {len(results['languages'])}\n"
                f"Total missing: {results['total_misses']:,}\n"
                f"{excluded_note}"
                f"Close folders: {close_count}\n"
                f"{master_note}\n"
                f"Output directory:\n{output_dir}"))

        self._run_in_thread(work)

    # === Pre-Submission Check Handlers ===

    def _get_source_for_checks(self) -> Optional[Path]:
        """Validate and return source folder for checks."""
        source_str = self.source_path.get()
        if not source_str:
            messagebox.showwarning("Warning", "Please select a Source folder.")
            return None
        source = Path(source_str)
        if not source.exists():
            messagebox.showerror("Error", f"Source folder not found:\n{source}")
            return None
        return source

    def _format_check_summary(self, summary: Dict[str, int], check_name: str) -> str:
        """Format check summary for log output."""
        total = sum(summary.values())
        langs_with_issues = {k: v for k, v in summary.items() if v > 0}
        if not langs_with_issues:
            return f"{check_name}: All clean across {len(summary)} languages"
        parts = [f"{lang}: {count}" for lang, count in sorted(langs_with_issues.items())]
        return f"{check_name}: {total} issues in {len(langs_with_issues)} languages ({', '.join(parts)})"

    def _format_pattern_summary(self, summary: Dict[str, tuple]) -> str:
        """Format pattern+bracket+broken XML+empty Str+formula+integrity check summary.

        summary values are (pattern, bracket, broken_xml, empty_str, formula_text, integrity) tuples.
        Shows categorized breakdown so users know what was wrong.
        """
        pattern_total = sum(v[0] for v in summary.values())
        bracket_total = sum(v[1] for v in summary.values())
        broken_total = sum(v[2] for v in summary.values()) if all(len(v) >= 3 for v in summary.values()) else 0
        empty_total = sum(v[3] for v in summary.values()) if all(len(v) >= 4 for v in summary.values()) else 0
        formula_total = sum(v[4] for v in summary.values()) if all(len(v) >= 5 for v in summary.values()) else 0
        integrity_total = sum(v[5] for v in summary.values()) if all(len(v) >= 6 for v in summary.values()) else 0
        total = pattern_total + bracket_total + broken_total + empty_total + formula_total + integrity_total

        if total == 0:
            return f"Pattern Check: All clean across {len(summary)} languages"

        lines = []
        # Header line
        n_langs = len([k for k, v in summary.items() if sum(v) > 0])
        lines.append(f"Pattern Check: {total} issues in {n_langs} languages")

        # CRITICAL: Formula text (show first with broken XML — garbage data)
        if formula_total > 0:
            f_langs = {k: v[4] for k, v in summary.items() if len(v) >= 5 and v[4] > 0}
            f_parts = [f"{lang}: {cnt}" for lang, cnt in sorted(f_langs.items())]
            lines.append(f"  CRITICAL — Formula/error text: {formula_total} ({', '.join(f_parts)})")
            lines.append("  (Separate files in FormulaText/ folder)")

        # CRITICAL: Text integrity issues
        if integrity_total > 0:
            i_langs = {k: v[5] for k, v in summary.items() if len(v) >= 6 and v[5] > 0}
            i_parts = [f"{lang}: {cnt}" for lang, cnt in sorted(i_langs.items())]
            lines.append(f"  CRITICAL — Text integrity: {integrity_total} ({', '.join(i_parts)})")
            lines.append("  (Separate files in TextIntegrity/ folder)")

        # CRITICAL: Broken XML
        if broken_total > 0:
            x_langs = {k: v[2] for k, v in summary.items() if len(v) >= 3 and v[2] > 0}
            x_parts = [f"{lang}: {cnt}" for lang, cnt in sorted(x_langs.items())]
            lines.append(f"  CRITICAL — Broken XML: {broken_total} ({', '.join(x_parts)})")
            lines.append("  (Separate files in BrokenXML/ folder)")

        # CRITICAL: Unbalanced brackets
        if bracket_total > 0:
            b_langs = {k: v[1] for k, v in summary.items() if len(v) >= 2 and v[1] > 0}
            b_parts = [f"{lang}: {cnt}" for lang, cnt in sorted(b_langs.items())]
            lines.append(f"  CRITICAL — Missing brackets: {bracket_total} ({', '.join(b_parts)})")
            lines.append("  (Separate files in MissingBrackets/ folder)")

        # Empty Str (has StrOrigin but no translation)
        if empty_total > 0:
            e_langs = {k: v[3] for k, v in summary.items() if len(v) >= 4 and v[3] > 0}
            e_parts = [f"{lang}: {cnt}" for lang, cnt in sorted(e_langs.items())]
            lines.append(f"  Empty Str (untranslated): {empty_total} ({', '.join(e_parts)})")
            lines.append("  (Separate files in EmptyStr/ folder)")

        # Pattern mismatches breakdown
        if pattern_total > 0:
            p_langs = {k: v[0] for k, v in summary.items() if v[0] > 0}
            p_parts = [f"{lang}: {cnt}" for lang, cnt in sorted(p_langs.items())]
            lines.append(f"  Pattern mismatches: {pattern_total} ({', '.join(p_parts)})")

        return '\n'.join(lines)

    def _on_presub_setting_changed(self):
        """Save pre-submission settings when checkbox is toggled."""
        settings = {
            "strict_non_script_only": self._strict_non_script_var.get(),
        }
        config.save_presubmission_settings(settings)
        ns_state = "ON" if settings["strict_non_script_only"] else "OFF"
        self._log(f"Strict non-script only: {ns_state} (saved)", 'info')

    def _check_korean(self):
        """Run Korean character check on Source folder."""
        source = self._get_source_for_checks()
        if not source:
            return

        self._disable_buttons()
        output_folder = config.CHECK_RESULTS_FOLDER

        def work():
            self._log("=== Korean Character Check ===", 'header')
            self._task_queue.put(('checks_status', "Checking Korean..."))

            def progress_cb(msg):
                self._task_queue.put(('checks_status', msg))

            summary = run_korean_check(source, output_folder, progress_callback=progress_cb,
                                       cancel_event=self._cancel_event)

            if not summary:
                self._log("No XML files found in Source folder.", 'warning')
                self._task_queue.put(('checks_status', "No files found"))
                return

            total = sum(summary.values())
            result_msg = self._format_check_summary(summary, "Korean Check")
            self._log(result_msg, 'success' if total == 0 else 'warning')

            if total > 0:
                self._log(f"Results written to: {output_folder / 'Korean'}", 'info')
                self._task_queue.put(('checks_status', f"Done: {total} Korean findings"))
            else:
                self._task_queue.put(('checks_status', "Done: All clean"))

            self._task_queue.put(('enable_results_btn',))

        self._run_in_thread(work)

    def _check_patterns(self):
        """Run pattern mismatch + newline + bracket + empty Str check on Source folder."""
        source = self._get_source_for_checks()
        if not source:
            return

        self._disable_buttons()
        output_folder = config.CHECK_RESULTS_FOLDER

        def work():
            self._log("=== Pattern & Newline Check ===", 'header')
            self._task_queue.put(('checks_status', "Checking patterns..."))

            def progress_cb(msg):
                self._task_queue.put(('checks_status', msg))

            summary = run_pattern_check(source, output_folder, progress_callback=progress_cb,
                                        skip_staticinfo_knowledge=False, cancel_event=self._cancel_event)

            if not summary:
                self._log("No XML or Excel files found in Source folder.", 'warning')
                self._task_queue.put(('checks_status', "No files found"))
                return

            result_msg = self._format_pattern_summary(summary)
            pattern_total = sum(v[0] for v in summary.values())
            bracket_total = sum(v[1] for v in summary.values())
            broken_total = sum(v[2] for v in summary.values()) if all(len(v) >= 3 for v in summary.values()) else 0
            empty_total = sum(v[3] for v in summary.values()) if all(len(v) >= 4 for v in summary.values()) else 0
            formula_total = sum(v[4] for v in summary.values()) if all(len(v) >= 5 for v in summary.values()) else 0
            integrity_total = sum(v[5] for v in summary.values()) if all(len(v) >= 6 for v in summary.values()) else 0
            total = pattern_total + bracket_total + broken_total + empty_total + formula_total + integrity_total

            self._log(result_msg, 'success' if total == 0 else 'warning')

            if total > 0:
                self._log(f"Results written to: {output_folder / 'PatternErrors'}", 'info')
                if formula_total > 0:
                    self._log(f"CRITICAL formula text: {output_folder / 'FormulaText'}", 'warning')
                if integrity_total > 0:
                    self._log(f"CRITICAL text integrity: {output_folder / 'TextIntegrity'}", 'warning')
                if broken_total > 0:
                    self._log(f"CRITICAL broken XML: {output_folder / 'BrokenXML'}", 'warning')
                if bracket_total > 0:
                    self._log(f"CRITICAL bracket issues: {output_folder / 'MissingBrackets'}", 'warning')
                if empty_total > 0:
                    self._log(f"Empty Str entries: {output_folder / 'EmptyStr'}", 'info')
                self._task_queue.put(('checks_status', f"Done: {total} issues ({formula_total}F + {integrity_total}I + {broken_total}X + {pattern_total}P + {bracket_total}B + {empty_total}E)"))
            else:
                self._task_queue.put(('checks_status', "Done: All clean"))

            self._task_queue.put(('enable_results_btn',))

        self._run_in_thread(work)

    def _check_quality(self):
        """Run quality check (wrong script + AI hallucination) on Source folder."""
        source = self._get_source_for_checks()
        if not source:
            return

        self._disable_buttons()
        output_folder = config.CHECK_RESULTS_FOLDER

        def work():
            self._log("=== Quality Check (Script + AI Hallucination) ===", 'header')
            self._task_queue.put(('checks_status', "Checking quality..."))

            def progress_cb(msg):
                self._task_queue.put(('checks_status', msg))

            summary = run_quality_check(source, output_folder, progress_callback=progress_cb,
                                        skip_staticinfo_knowledge=False, cancel_event=self._cancel_event)

            if not summary:
                self._log("No XML files found in Source folder.", 'warning')
                self._task_queue.put(('checks_status', "No files found"))
                return

            script_total = sum(v[0] for v in summary.values())
            halluc_total = sum(v[1] for v in summary.values())
            grand_total = script_total + halluc_total

            if grand_total == 0:
                self._log("Quality check: All clean across all languages", 'success')
                self._task_queue.put(('checks_status', "Done: All clean"))
            else:
                langs_with_issues = {k: v for k, v in summary.items() if v[0] > 0 or v[1] > 0}
                parts = [f"{lang}: {v[0]}S+{v[1]}H" for lang, v in sorted(langs_with_issues.items())]
                self._log(f"Quality check: {grand_total} issues ({script_total} script, {halluc_total} hallucination) in {len(langs_with_issues)} languages", 'warning')
                self._log(f"  {', '.join(parts)}", 'info')
                self._log(f"Results written to: {output_folder / 'QualityReport'}", 'info')
                self._task_queue.put(('checks_status', f"Done: {grand_total} issues ({script_total}S + {halluc_total}H)"))

            self._task_queue.put(('enable_results_btn',))

        self._run_in_thread(work)

    def _check_all(self):
        """Run all pre-submission checks sequentially: Korean, Pattern, Quality."""
        source = self._get_source_for_checks()
        if not source:
            return

        self._disable_buttons()
        output_folder = config.CHECK_RESULTS_FOLDER

        def work():
            self._log("=== Pre-Submission Check ALL ===", 'header')

            # Korean check (never skips — checks EVERYTHING)
            self._task_queue.put(('checks_status', "Checking Korean..."))

            def korean_cb(msg):
                self._task_queue.put(('checks_status', msg))

            korean_summary = run_korean_check(source, output_folder, progress_callback=korean_cb,
                                              cancel_event=self._cancel_event)
            if korean_summary:
                self._log(self._format_check_summary(korean_summary, "Korean Check"),
                          'success' if sum(korean_summary.values()) == 0 else 'warning')

            # Cancel gate: don't start pattern check if cancelled during korean check
            if self._cancel_event.is_set():
                raise InterruptedError("Operation cancelled by user")

            # Pattern + newline + empty Str check
            self._task_queue.put(('checks_status', "Checking patterns..."))

            def pattern_cb(msg):
                self._task_queue.put(('checks_status', msg))

            pattern_summary = run_pattern_check(source, output_folder, progress_callback=pattern_cb,
                                                skip_staticinfo_knowledge=False, cancel_event=self._cancel_event)
            if pattern_summary:
                p_total = sum(v[0] for v in pattern_summary.values())
                b_total = sum(v[1] for v in pattern_summary.values())
                x_total = sum(v[2] for v in pattern_summary.values()) if all(len(v) >= 3 for v in pattern_summary.values()) else 0
                e_total = sum(v[3] for v in pattern_summary.values()) if all(len(v) >= 4 for v in pattern_summary.values()) else 0
                f_total = sum(v[4] for v in pattern_summary.values()) if all(len(v) >= 5 for v in pattern_summary.values()) else 0
                i_total = sum(v[5] for v in pattern_summary.values()) if all(len(v) >= 6 for v in pattern_summary.values()) else 0
                self._log(self._format_pattern_summary(pattern_summary),
                          'success' if (p_total + b_total + x_total + e_total + f_total + i_total) == 0 else 'warning')
                if f_total > 0:
                    self._log(f"CRITICAL formula text: {output_folder / 'FormulaText'}", 'warning')
                if i_total > 0:
                    self._log(f"CRITICAL text integrity: {output_folder / 'TextIntegrity'}", 'warning')
                if x_total > 0:
                    self._log(f"CRITICAL broken XML: {output_folder / 'BrokenXML'}", 'warning')
                if b_total > 0:
                    self._log(f"CRITICAL bracket issues: {output_folder / 'MissingBrackets'}", 'warning')
                if e_total > 0:
                    self._log(f"Empty Str entries: {output_folder / 'EmptyStr'}", 'info')

            # Cancel gate: don't start quality check if cancelled during pattern check
            if self._cancel_event.is_set():
                raise InterruptedError("Operation cancelled by user")

            # Quality check
            self._task_queue.put(('checks_status', "Checking quality..."))

            def quality_cb(msg):
                self._task_queue.put(('checks_status', msg))

            quality_summary = run_quality_check(source, output_folder, progress_callback=quality_cb,
                                                skip_staticinfo_knowledge=False, cancel_event=self._cancel_event)
            if quality_summary:
                script_total = sum(v[0] for v in quality_summary.values())
                halluc_total = sum(v[1] for v in quality_summary.values())
                quality_total = script_total + halluc_total
                self._log(
                    f"Quality Check: {quality_total} issues ({script_total} script, {halluc_total} hallucination)",
                    'success' if quality_total == 0 else 'warning')
            else:
                quality_total = 0

            # Final summary
            korean_total = sum(korean_summary.values()) if korean_summary else 0
            check_total = 0
            bracket_total_all = 0
            broken_total_all = 0
            empty_total_all = 0
            formula_total_all = 0
            if pattern_summary:
                check_total = sum(sum(v) for v in pattern_summary.values())
                bracket_total_all = sum(v[1] for v in pattern_summary.values())
                broken_total_all = sum(v[2] for v in pattern_summary.values()) if all(len(v) >= 3 for v in pattern_summary.values()) else 0
                empty_total_all = sum(v[3] for v in pattern_summary.values()) if all(len(v) >= 4 for v in pattern_summary.values()) else 0
                formula_total_all = sum(v[4] for v in pattern_summary.values()) if all(len(v) >= 5 for v in pattern_summary.values()) else 0
            grand_total = korean_total + check_total + quality_total

            if grand_total == 0:
                self._log("All checks passed!", 'success')
                self._task_queue.put(('checks_status', "Done: All checks passed"))
            else:
                critical_parts = []
                if formula_total_all:
                    critical_parts.append(f"{formula_total_all} CRITICAL formula text")
                if broken_total_all:
                    critical_parts.append(f"{broken_total_all} CRITICAL broken XML")
                if bracket_total_all:
                    critical_parts.append(f"{bracket_total_all} CRITICAL brackets")
                if empty_total_all:
                    critical_parts.append(f"{empty_total_all} empty Str")
                critical_note = f", {', '.join(critical_parts)}" if critical_parts else ""
                self._log(f"Total issues: {grand_total} ({korean_total} Korean, {check_total} pattern/bracket/xml/empty/formula/integrity{critical_note}, {quality_total} quality)", 'warning')
                self._log(f"Results written to: {output_folder}", 'info')
                self._task_queue.put(('checks_status', f"Done: {grand_total} issues ({korean_total}K + {check_total}P + {quality_total}Q)"))

            self._task_queue.put(('enable_results_btn',))

        self._run_in_thread(work)

    def _open_check_results_folder(self):
        """Open the CheckResults folder in the system file explorer."""
        folder = config.CHECK_RESULTS_FOLDER
        if not folder.exists():
            messagebox.showinfo("Info", "No check results yet. Run a check first.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            self._log(f"Could not open folder: {e}", 'error')

    def _preprocess(self):
        """Run cleanup (postprocess) standalone on all XML/Excel files in Source folder."""
        source_str = self.source_path.get().strip()
        if not source_str:
            messagebox.showwarning("Warning", "Please select a Source folder.")
            return

        source = Path(source_str)
        if not source.is_dir():
            messagebox.showwarning("Warning", f"Source folder not found:\n{source}")
            return

        # Collect all XML and Excel files
        xml_files = sorted(source.rglob("*.xml"))
        xlsx_files = sorted(source.rglob("*.xlsx"))

        if not xml_files and not xlsx_files:
            messagebox.showinfo("Info", "No XML or Excel files found in Source folder.")
            return

        total = len(xml_files) + len(xlsx_files)
        msg = f"Pre-process {total} file(s)?\n\n"
        if xml_files:
            msg += f"  XML files: {len(xml_files)}\n"
        if xlsx_files:
            msg += f"  Excel files: {len(xlsx_files)}\n"
        msg += "\nThis will normalize linebreaks, apostrophes, invisible characters,\nhyphens, and double-escaped entities in-place."

        if not messagebox.askyesno("Pre-Process", msg):
            return

        self._clear_log()
        self._disable_buttons()
        self._log(f"Pre-processing {total} files...", 'info')

        def _work():
            from core.postprocess import run_all_postprocess, run_preprocess_excel

            total_fixes = 0
            files_fixed = 0
            errors = 0

            # Process XML files
            for i, xml_path in enumerate(xml_files):
                if self._cancel_event.is_set():
                    raise InterruptedError()
                self._task_queue.put(('status', f'XML {i + 1}/{len(xml_files)}: {xml_path.name}', None))
                result = run_all_postprocess(xml_path)
                if result.get("error"):
                    self._log(f"  ERROR {xml_path.name}: {result['error']}", 'error')
                    errors += 1
                elif result["total_fixes"] > 0:
                    files_fixed += 1
                    total_fixes += result["total_fixes"]
                    self._log(f"  {xml_path.name}: {result['total_fixes']} fixes", 'info')

            # Process Excel files
            for i, xlsx_path in enumerate(xlsx_files):
                if self._cancel_event.is_set():
                    raise InterruptedError()
                self._task_queue.put(('status', f'Excel {i + 1}/{len(xlsx_files)}: {xlsx_path.name}', None))
                result = run_preprocess_excel(xlsx_path)
                if result.get("error"):
                    self._log(f"  ERROR {xlsx_path.name}: {result['error']}", 'error')
                    errors += 1
                elif result["total_fixes"] > 0:
                    files_fixed += 1
                    total_fixes += result["total_fixes"]
                    self._log(f"  {xlsx_path.name}: {result['total_fixes']} fixes", 'info')

            summary = f"\nPre-process complete: {total_fixes} fixes in {files_fixed} file(s)."
            if errors > 0:
                summary += f"\nWARNING: {errors} file(s) had errors — check above."
                self._log(summary, 'warning')
            elif total_fixes > 0:
                self._log(summary, 'success')
            else:
                self._log("\nPre-process complete: all files are already clean.", 'success')
            self._task_queue.put(('status', 'Pre-process complete', None))

        self._run_in_thread(_work)

    def _transfer(self):
        """Transfer corrections from source to target XML files (LOC folder)."""
        source_str = self.source_path.get().strip()
        if not source_str:
            messagebox.showwarning("Warning", "Please select a Source folder.")
            return

        source = Path(source_str)

        # If columns haven't been detected (path pasted, not browsed), detect now
        cols = self._source_columns
        if not any(cols.values()) and source.is_dir():
            self._quick_detect_columns(source)
            cols = self._source_columns

        if not self._validate_columns_for_mode(cols):
            return

        target_str = self.target_path.get().strip()
        if not target_str:
            messagebox.showwarning("Warning",
                "Please set a Target folder.\n\n"
                "Target should be the LOC folder containing languagedata_*.xml files.")
            return

        target = Path(target_str)

        if not source.exists():
            messagebox.showerror("Error", f"Source not found:\n{source}")
            return

        if not target.exists():
            messagebox.showerror("Error", f"Target folder not found:\n{target}")
            return

        # Block source == target (would overwrite source files)
        try:
            if source.resolve() == target.resolve():
                messagebox.showerror(
                    "Error",
                    "Source and Target folders are the same!\n\n"
                    "Transfer writes back to the Target folder, so using the same folder "
                    "as both Source and Target would overwrite your source files."
                )
                return
        except OSError:
            pass  # resolve() can fail on broken symlinks — let transfer proceed

        # Capture StringVar values on main thread
        match_type = self.match_type.get()
        precision = self.match_precision.get()
        transfer_scope = self.transfer_scope.get()
        fuzzy_threshold = self.fuzzy_threshold.get()
        unique_only = bool(self.unique_only_strorigin.get()) if match_type == "strorigin_only" else False
        non_script_only = self._strict_non_script_var.get() if match_type in ("strict", "strorigin_descorigin") else False
        stringid_all = self._stringid_all_var.get() if match_type == "stringid_only" else False

        # StringID ALL: extra warning confirmation BEFORE the normal transfer plan
        if stringid_all:
            warn_confirm = messagebox.askyesno(
                "StringID ALL Categories — WARNING",
                "You are about to match ALL StringIDs regardless of category.\n\n"
                "This bypasses the SCRIPT-only safety filter.\n"
                "Every StringID from your source will be matched against\n"
                "the ENTIRE target XML — Dialog, Sequencer, AND game-data.\n\n"
                "This is intended for EXCEPTIONAL cases only.\n\n"
                "Are you sure?",
                icon='warning',
            )
            if not warn_confirm:
                return

        # === GENERATE FULL TRANSFER PLAN BEFORE CONFIRMATION ===
        match_str = match_type.upper()

        # Add precision info for modes that support it
        if match_type in ("strict", "strorigin_only", "strorigin_descorigin"):
            match_str = f"{match_str} ({precision.upper()})"

        scope_str = ("Only untranslated (Korean)" if transfer_scope == "untranslated"
                     else "ALL matches (overwrite)")
        if unique_only:
            scope_str += " [UNIQUE ONLY]"
        if non_script_only:
            match_str += " [NON-SCRIPT ONLY]"
        if stringid_all:
            match_str += " [ALL CATEGORIES]"

        # Scan target with flexible scanner (supports any XML/Excel with lang suffix)
        _transfer_target_scan = scan_target_for_languages(target)

        # Generate complete transfer plan with full tree table
        transfer_plan = generate_transfer_plan(source, target, target_scan=_transfer_target_scan)

        # Print FULL TREE TABLE to terminal (always show complete mapping)
        tree_table = format_transfer_plan(transfer_plan, show_all_files=True)
        logger.info(tree_table)

        # Build confirmation message with summary from transfer plan
        plan_summary = (
            f"Languages: {len(transfer_plan.languages_ready)} ready"
            + (f", {len(transfer_plan.languages_skipped)} skipped" if transfer_plan.languages_skipped else "")
            + f"\nFiles: {transfer_plan.total_ready} will transfer"
            + (f", {transfer_plan.total_skipped} skipped (no target)" if transfer_plan.total_skipped else "")
        )

        if transfer_plan.languages_ready:
            plan_summary += f"\n\nReady: {', '.join(transfer_plan.languages_ready)}"
        if transfer_plan.languages_skipped:
            plan_summary += f"\nSkipped: {', '.join(transfer_plan.languages_skipped)}"

        # Show warnings if any
        if transfer_plan.warnings:
            shown = transfer_plan.warnings[:5]
            plan_summary += f"\n\nWarnings ({len(transfer_plan.warnings)}):\n" + "\n".join(f"  - {w}" for w in shown)
            if len(transfer_plan.warnings) > 5:
                plan_summary += f"\n  ...and {len(transfer_plan.warnings) - 5} more (see Log panel)"

        confirm = messagebox.askyesno(
            "Confirm Transfer",
            f"Full tree table printed to Log panel and terminal.\n\n"
            f"Target: {target}\n\n"
            f"=== TRANSFER PLAN SUMMARY ===\n"
            f"{plan_summary}\n\n"
            f"Match Mode: {match_str}\n"
            f"Transfer Scope: {scope_str}\n\n"
            f"Are you sure you want to proceed?"
        )

        if not confirm:
            return

        self._disable_buttons()
        self.progress_value.set(0)
        self._clear_log()

        self._log("=== QuickTranslate TRANSFER ===", 'header')
        self._log(f"Match Mode: {match_str}", 'info')
        self._log(f"Transfer Scope: {scope_str}", 'info')
        if unique_only:
            self._log("Mode: UNIQUE ONLY (duplicate StrOrigin skipped, exported to Excel)", 'warning')
        if non_script_only:
            self._log("Non-Script Only: ON (Dialog/Sequencer will be skipped)", 'warning')
        if stringid_all:
            self._log("StringID ALL CATEGORIES: ON — bypassing SCRIPT-only filter!", 'warning')
        self._log(f"Source: {source}", 'info')
        self._log(f"Target: {target}", 'info')

        # Log transfer plan summary
        self._log(f"Transfer Plan: {transfer_plan.total_ready} files ready, {transfer_plan.total_skipped} skipped", 'info')
        for lang in transfer_plan.languages_ready:
            plan = transfer_plan.language_plans[lang]
            if len(plan.target_files) == 1:
                target_desc = plan.target_files[0].name
            elif len(plan.target_files) > 1:
                target_desc = f"{len(plan.target_files)} target files"
            else:
                target_desc = plan.target_file.name if plan.target_file else "N/A"
            self._log(f"  {lang}: {plan.file_count} source files → {target_desc}", 'success')
        for lang in transfer_plan.languages_skipped:
            plan = transfer_plan.language_plans[lang]
            self._log(f"  {lang}: {plan.file_count} files → SKIPPED (no target)", 'warning')

        def work():
            # Cross-match summary using flexible target scan
            if source.is_dir() and target.is_dir():
                src_scan = scan_source_for_languages(source)
                src_langs = set(src_scan.lang_files.keys())
                tgt_langs = set(_transfer_target_scan.lang_files.keys())
                matched_langs = sorted(src_langs & tgt_langs)
                src_only = sorted(src_langs - tgt_langs)
                tgt_only = sorted(tgt_langs - src_langs)
                tgt_files_total = _transfer_target_scan.total_files
                self._log(f"Cross-match: {len(matched_langs)} lang pairs, {len(src_only)} source-only, {len(tgt_only)} target-only ({tgt_files_total} target files)", 'info')

            # Load category data if needed for stringid_only or strorigin_only mode
            # StringID-Only: only processes Dialog/Sequencer (SCRIPT) strings
            # StrOrigin Only: skips Dialog/Sequencer strings (complement safeguard)
            stringid_to_category = None
            stringid_to_subfolder = None
            stringid_to_filepath = None
            if match_type in ("stringid_only", "strorigin_only", "strorigin_filename") or (match_type in ("strict", "strorigin_descorigin") and non_script_only):
                if not self._load_data_if_needed(need_sequencer=True):
                    return
                stringid_to_category = self.stringid_to_category
                stringid_to_subfolder = self.stringid_to_subfolder
                stringid_to_filepath = self.stringid_to_filepath

            # For fuzzy precision modes, extract StringIDs from source FIRST to filter index
            # NOTE: strorigin_only mode matches by StrOrigin text, NOT StringID.
            # Using stringid_filter would wrongly filter out all entries when source
            # has no StringIDs (empty set != None).  Only strict mode needs this.
            source_stringids = None
            if precision == "fuzzy" and match_type == "strict":
                self._log("Extracting StringIDs from source for filtered index build...", 'info')
                source_stringids = self._extract_stringids_from_source(source)
                self._log(f"Source has {len(source_stringids):,} unique StringIDs", 'info')
            # NOTE: strorigin_descorigin does NOT need StringID filtering (matches by StrOrigin+DescOrigin)

            only_untranslated = transfer_scope == "untranslated"

            # For strict/strorigin_only with fuzzy precision, need model + FAISS index
            if precision == "fuzzy" and match_type in ("strict", "strorigin_only", "strorigin_descorigin"):
                if not self._ensure_fuzzy_model():
                    return
                if not self._ensure_fuzzy_index(str(target), stringid_filter=source_stringids, only_untranslated=only_untranslated):
                    return
                self._log(f"{match_type} TRANSFER with FUZZY precision [Model2Vec] (threshold={fuzzy_threshold:.2f})", 'info')

            self._task_queue.put(('progress', 20))
            self._update_status("Transferring corrections...")

            # Map match_type + precision to transfer match_mode
            if match_type == "stringid_only":
                transfer_match_mode = "stringid_only"
            elif match_type == "strorigin_only":
                transfer_match_mode = "strorigin_only_fuzzy" if precision == "fuzzy" else "strorigin_only"
            elif match_type == "strorigin_descorigin":
                transfer_match_mode = "strorigin_descorigin_fuzzy" if precision == "fuzzy" else "strorigin_descorigin"
            elif match_type == "strict":
                transfer_match_mode = "strict_fuzzy" if precision == "fuzzy" else "strict"
            elif match_type == "strorigin_filename":
                transfer_match_mode = "strorigin_filename"
            else:
                transfer_match_mode = "strict"

            # Build kwargs for transfer functions
            transfer_kwargs = {
                "stringid_to_category": stringid_to_category,
                "stringid_to_subfolder": stringid_to_subfolder,
                "stringid_to_filepath": stringid_to_filepath,
                "match_mode": transfer_match_mode,
                "dry_run": False,
                "only_untranslated": only_untranslated,
            }
            if unique_only:
                transfer_kwargs["unique_only"] = True
            if non_script_only and match_type in ("strict", "strorigin_descorigin"):
                transfer_kwargs["strict_non_script_only"] = True
            if stringid_all and match_type == "stringid_only":
                transfer_kwargs["stringid_all_categories"] = True

            # Pass threshold AND pre-built fuzzy data for fuzzy modes
            # CRITICAL: Without this, transfer functions rebuild from scratch!
            if precision == "fuzzy" and match_type in ("strict", "strorigin_only", "strorigin_descorigin"):
                transfer_kwargs["threshold"] = fuzzy_threshold
                transfer_kwargs["fuzzy_model"] = self._fuzzy_model
                transfer_kwargs["fuzzy_texts"] = self._fuzzy_texts
                transfer_kwargs["fuzzy_entries"] = self._fuzzy_entries
                transfer_kwargs["source_stringids"] = source_stringids
                transfer_kwargs["fuzzy_index"] = self._fuzzy_index
                self._log(f"Passing pre-built fuzzy data: {len(self._fuzzy_entries):,} entries, FAISS index ready", 'info')

            # Perform transfer (always folder mode) — pass pre-scanned target
            transfer_kwargs["target_scan"] = _transfer_target_scan
            results = transfer_folder_to_folder(
                source,
                target,
                progress_callback=self._update_status,
                log_callback=self._log,
                **transfer_kwargs,
            )
            self._task_queue.put(('progress', 80))

            # Generate report
            report = format_transfer_report(results, mode="folder", match_mode=transfer_match_mode)

            # Log the report
            for line in report.split("\n"):
                if "SUCCESS" in line or "UPDATED" in line or "●" in line:
                    self._log(line, 'success')
                elif "ERROR" in line or "x" in line or "NOT_FOUND" in line or "○" in line:
                    self._log(line, 'error')
                elif "WARN" in line or "half" in line or "SKIPPED" in line:
                    self._log(line, 'warning')
                elif "=" in line or "|" in line or "REPORT" in line:
                    self._log(line, 'header')
                else:
                    self._log(line, 'info')

            self._task_queue.put(('progress', 90))

            # Summary
            updated = results.get("total_updated", 0)
            matched = results.get("total_matched", 0)
            not_found = results.get("total_not_found", 0)
            strorigin_mismatch = results.get("total_strorigin_mismatch", 0)
            skipped_translated = results.get("total_skipped_translated", 0)

            # === FAILURE REPORT GENERATION ===
            # Only real failures trigger report generation.
            # SKIPPED_NON_SCRIPT, SKIPPED_EXCLUDED, SKIPPED_TRANSLATED etc. are by design.
            total_failures = not_found + strorigin_mismatch
            failure_reports_msg = ""

            if total_failures > 0:
                self._log("", 'info')
                self._log("=== Generating Failure Reports ===", 'header')

                source_name = source.name if source.is_dir() else source.stem
                report_folder = config.get_failed_report_dir(source_name)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                self._log(f"Report folder: {report_folder}", 'info')

                failed_entries = extract_failed_from_folder_results(results)

                if failed_entries:
                    try:
                        xml_files = generate_failed_merge_xml_per_language(
                            failed_entries, report_folder
                        )
                        if xml_files:
                            self._log(f"XML failure reports: {len(xml_files)} language files", 'success')
                            for lang, path in xml_files.items():
                                self._log(f"  {lang}: {path.name}", 'info')
                            failure_reports_msg += f"\n\nXML Reports: {len(xml_files)} language files"
                    except Exception as e:
                        self._log(f"Failed to generate XML reports: {e}", 'error')

                # Generate "New Strings" XML for STRORIGIN_MISMATCH entries
                # These are the target's current LocStr elements where StrOrigin changed
                mismatch_entries = extract_mismatch_target_entries(results)
                if mismatch_entries:
                    try:
                        mismatch_folder = report_folder / "NewStrOrigin"
                        mismatch_folder.mkdir(parents=True, exist_ok=True)
                        mismatch_xml_files = generate_failed_merge_xml_per_language(
                            mismatch_entries, mismatch_folder,
                            preserve_all_attribs=True,
                        )
                        if mismatch_xml_files:
                            self._log(f"New StrOrigin XML: {len(mismatch_xml_files)} files ({len(mismatch_entries)} strings)", 'success')
                            for lang, path in mismatch_xml_files.items():
                                self._log(f"  {lang}: {path.name}", 'info')
                            failure_reports_msg += f"\nNew StrOrigin: {len(mismatch_entries)} strings in {len(mismatch_xml_files)} files"
                    except Exception as e:
                        self._log(f"Failed to generate New StrOrigin XML: {e}", 'error')

                if check_xlsxwriter_available():
                    excel_report_path = report_folder / f"FailureReport_{timestamp}.xlsx"
                    try:
                        success, msg = generate_failure_report_excel(
                            results,
                            excel_report_path,
                            mode="folder",
                            source_name=str(source.name),
                            target_name=str(target.name)
                        )
                        if success:
                            self._log(f"Excel failure report: {excel_report_path.name}", 'success')
                            failure_reports_msg += f"\nExcel Report: {excel_report_path.name}"
                        else:
                            self._log(f"Excel report failed: {msg}", 'error')
                    except Exception as e:
                        self._log(f"Failed to generate Excel report: {e}", 'error')
                else:
                    self._log("Excel report skipped (xlsxwriter not installed)", 'warning')

                self._log(f"Reports saved to: {report_folder}", 'info')

            # === DUPLICATE STRORIGIN REPORT (Unique-Only mode) ===
            if unique_only:
                # Duplicate details are collected globally by transfer_folder_to_folder
                # (not per-file), so retrieve from the top-level results key.
                dup_entries = results.get("_duplicate_strorigin_details", [])

                if dup_entries:
                    from core.failure_report import generate_duplicate_strorigin_excel
                    source_name = source.name if source.is_dir() else source.stem
                    dup_report_folder = config.get_failed_report_dir(source_name)
                    dup_paths = generate_duplicate_strorigin_excel(dup_entries, dup_report_folder)
                    if dup_paths:
                        self._log("", 'info')
                        self._log("=== Duplicate StrOrigin Report ===", 'header')
                        for dup_path in dup_paths:
                            self._log(f"  {dup_path.name}", 'warning')
                        self._log(f"  Total: {len(dup_entries)} entries across {len(dup_paths)} language(s)", 'warning')
                        self._log(f"  Location: {dup_report_folder}", 'info')
                        self._log("  Delete unwanted rows, keep desired corrections, re-submit via TRANSFER", 'info')
                        dup_names = ", ".join(p.name for p in dup_paths)
                        failure_reports_msg += f"\nDuplicate strings: {dup_names} ({len(dup_entries)} entries)"

            # === FUZZY MATCH REPORT ===
            fuzzy_matched_data = results.get("_fuzzy_matched")
            if fuzzy_matched_data:
                try:
                    source_name = source.name if source.is_dir() else source.stem
                    fuzzy_report_folder = config.get_failed_report_dir(source_name)
                    fuzzy_timestamp = datetime.now().strftime("%y%m%d_%H%M")
                    fuzzy_report_path = fuzzy_report_folder / f"FuzzyReport_{fuzzy_timestamp}.xlsx"

                    # Enrich stats with transfer-level context for the report
                    fuzzy_stats_data = dict(results.get("_fuzzy_stats") or {})
                    fuzzy_stats_data["transfer_total_corrections"] = results.get("total_corrections", 0)
                    fuzzy_stats_data["transfer_total_matched"] = results.get("total_matched", 0)
                    fuzzy_stats_data["transfer_total_updated"] = results.get("total_updated", 0)

                    generate_fuzzy_report_excel(
                        fuzzy_matched_data,
                        results.get("_fuzzy_unmatched", []),
                        fuzzy_stats_data,
                        fuzzy_report_path,
                    )
                    self._log("", 'info')
                    self._log("=== Fuzzy Match Report ===", 'header')
                    self._log(f"Fuzzy report: {fuzzy_report_path.name}", 'success')
                    fuzzy_unmatched_count = len(results.get('_fuzzy_unmatched', []))
                    fuzzy_sent_to_faiss = len(fuzzy_matched_data) + fuzzy_unmatched_count
                    self._log(
                        f"  Fuzzy recovered {len(fuzzy_matched_data)} of {fuzzy_sent_to_faiss} "
                        f"unmatched ({fuzzy_stats_data.get('avg_score', 0):.3f} avg score)",
                        'info',
                    )
                    failure_reports_msg += f"\nFuzzy Report: {fuzzy_report_path.name}"
                except Exception as e:
                    self._log(f"Failed to generate fuzzy report: {e}", 'error')

            # EventName resolution stats (if any EventNames were in source)
            eventname_msg = ""
            missing_en_count = results.get("missing_eventnames_count", 0)
            missing_en_report = results.get("missing_eventname_report", "")
            if missing_en_count > 0 or missing_en_report:
                self._log("", 'info')
                self._log("=== EventName Resolution ===", 'header')
                if missing_en_count > 0:
                    self._log(f"Unresolved EventNames: {missing_en_count}", 'warning')
                if missing_en_report:
                    self._log(f"Missing EventName report: {missing_en_report}", 'info')
                    eventname_msg = f"\n\nMissing EventNames: {missing_en_count}"
                    eventname_msg += f"\nReport: {Path(missing_en_report).name}"

            self._task_queue.put(('progress', 100))
            unchanged = max(0, matched - updated - skipped_translated)
            self._update_status(f"Transfer complete: {updated:,} updated, {unchanged:,} already correct")

            # Build clear summary where all numbers add up
            desc_updated = results.get("total_desc_updated", 0)
            summary_lines = [
                f"Transfer completed!\n",
                f"Total Corrections: {results.get('total_corrections', 0):,}\n",
                f"  Updated:          {updated:,}  (value changed)",
            ]
            if desc_updated > 0:
                summary_lines.append(f"  Desc Updated:     {desc_updated:,}  (voice directions)")
            summary_lines.append(f"  Already Correct:  {unchanged:,}  (target already had correct value)")
            if not_found > 0:
                nf_label = "(StrOrigin not found)" if transfer_match_mode.startswith("strorigin_only") or transfer_match_mode.startswith("strorigin_descorigin") else "(StringID missing)"
                summary_lines.append(f"  Not Found:        {not_found:,}  {nf_label}")
            if strorigin_mismatch > 0:
                summary_lines.append(f"  Origin Mismatch:  {strorigin_mismatch:,}  (StrOrigin differs)")
            if skipped_translated > 0:
                summary_lines.append(f"  Skipped:          {skipped_translated:,}  (already translated)")
            skipped_dup_strorigin = results.get("total_skipped_duplicate_strorigin", 0)
            if skipped_dup_strorigin > 0:
                summary_lines.append(f"  Dup. StrOrigin:   {skipped_dup_strorigin:,}  (see duplicate report)")
            skipped_script = results.get("total_skipped_script", 0)
            if skipped_script > 0:
                summary_lines.append(f"  Script Skipped:   {skipped_script:,}  (Non-Script filter)")
            summary_lines.append(f"\nTarget: {target}")

            # Split transfer integrity warnings into critical vs secondary
            fw = results.get("formula_warnings", [])
            iw = results.get("integrity_warnings", [])
            critical_iw = [w for w in iw if w[3].startswith('Broken') or w[3].startswith('Truncated')]
            secondary_iw = [w for w in iw if not (w[3].startswith('Broken') or w[3].startswith('Truncated'))]

            # End-of-log CRITICAL warning summary (formulas + broken linebreaks)
            if fw or critical_iw:
                critical_total = len(fw) + len(critical_iw)
                self._log("", 'info')
                self._log(f"=== CRITICAL WARNING ({critical_total} entries skipped) ===", 'error')
                shown = 0
                if fw:
                    self._log("  Formula/error text:", 'error')
                    for fname, sid, col, reason in fw[:20]:
                        self._log(f"    {fname} | [{col}] StringID={sid or '(empty)'} | {reason}", 'error')
                    if len(fw) > 20:
                        self._log(f"    ...and {len(fw) - 20} more.", 'error')
                    shown = min(len(fw), 20)
                if critical_iw:
                    self._log("  Broken linebreak tags:", 'error')
                    remaining = max(20 - shown, 5)
                    for fname, sid, col, reason in critical_iw[:remaining]:
                        self._log(f"    {fname} | [{col}] StringID={sid or '(empty)'} | {reason}", 'error')
                    if len(critical_iw) > remaining:
                        self._log(f"    ...and {len(critical_iw) - remaining} more.", 'error')
                self._log("Fix: re-save Excel with Paste Values (Ctrl+Shift+V) or fix broken <br/> tags in the source.", 'error')
                summary_lines.append(f"\nWARNING: {critical_total} entries skipped (critical: formula/broken linebreak)")

            # End-of-log SECONDARY warning summary (encoding/invisible/control)
            if secondary_iw:
                self._log("", 'info')
                self._log(f"=== SECONDARY WARNING ({len(secondary_iw)} entries skipped) ===", 'error')
                self._log("Encoding artifacts or invisible characters:", 'error')
                for fname, sid, col, reason in secondary_iw[:20]:
                    self._log(f"  {fname} | [{col}] StringID={sid or '(empty)'} | {reason}", 'error')
                if len(secondary_iw) > 20:
                    self._log(f"  ...and {len(secondary_iw) - 20} more.", 'error')
                self._log("Fix: correct the broken text in the source file before re-transferring.", 'error')
                summary_lines.append(f"\nWARNING: {len(secondary_iw)} entries skipped (secondary: encoding/invisible chars)")

            # End-of-log OTHER WARNINGS ("no translation" skips)
            no_trans_warnings = results.get("no_translation_warnings", [])
            if no_trans_warnings:
                self._log("", 'info')
                self._log(f"=== OTHER WARNINGS ({len(no_trans_warnings)} entries skipped) ===", 'warning')
                self._log("Source entries with 'no translation' were skipped to preserve existing translations:", 'warning')
                for fname, sid in no_trans_warnings[:20]:
                    self._log(f"  {fname} | StringID={sid or '(empty)'}", 'warning')
                if len(no_trans_warnings) > 20:
                    self._log(f"  ...and {len(no_trans_warnings) - 20} more.", 'warning')
                summary_lines.append(f"\nOTHER: {len(no_trans_warnings)} 'no translation' entries skipped (existing translations preserved)")

            # End-of-log POST-PROCESSING report (automatic cleanup stats)
            pp_stats = results.get("postprocess_stats", {})
            pp_total = sum(pp_stats.get(k, 0) for k in ("newlines_fixed", "empty_strorigin_cleaned", "no_translation_replaced", "apostrophes_normalized", "hyphens_normalized", "ellipsis_normalized", "entities_decoded", "spaces_normalized", "invisibles_removed"))
            if pp_total > 0:
                self._log("", 'info')
                self._log(f"=== POST-PROCESSING ({pp_total} automatic fixes) ===", 'info')
                if pp_stats.get("newlines_fixed", 0) > 0:
                    self._log(f"  Newlines normalized:           {pp_stats['newlines_fixed']:,}", 'info')
                if pp_stats.get("empty_strorigin_cleaned", 0) > 0:
                    self._log(f"  Empty StrOrigin cleared:       {pp_stats['empty_strorigin_cleaned']:,}", 'info')
                if pp_stats.get("no_translation_replaced", 0) > 0:
                    self._log(f"  'No translation' → StrOrigin:  {pp_stats['no_translation_replaced']:,}", 'info')
                if pp_stats.get("apostrophes_normalized", 0) > 0:
                    self._log(f"  Apostrophes normalized:        {pp_stats['apostrophes_normalized']:,}", 'info')
                if pp_stats.get("hyphens_normalized", 0) > 0:
                    self._log(f"  Hyphens normalized:            {pp_stats['hyphens_normalized']:,}", 'info')
                if pp_stats.get("ellipsis_normalized", 0) > 0:
                    self._log(f"  Ellipsis normalized (… → ...): {pp_stats['ellipsis_normalized']:,}", 'info')
                if pp_stats.get("entities_decoded", 0) > 0:
                    self._log(f"  Double-escaped entities fixed:  {pp_stats['entities_decoded']:,}", 'info')
                if pp_stats.get("spaces_normalized", 0) > 0:
                    self._log(f"  Spaces normalized (NBSP etc.): {pp_stats['spaces_normalized']:,}", 'info')
                if pp_stats.get("invisibles_removed", 0) > 0:
                    self._log(f"  Invisible chars removed:       {pp_stats['invisibles_removed']:,}", 'info')
                # Per-type detail breakdown
                invisible_detail = pp_stats.get("invisible_detail", {})
                if invisible_detail:
                    self._log("  Invisible Character Details:", 'info')
                    for name, cnt in sorted(invisible_detail.items(), key=lambda x: -x[1]):
                        self._log(f"    {name}: {cnt:,}", 'info')
                summary_lines.append(f"\nPost-processing: {pp_total} automatic fixes applied")

            # Grey zone warning (outside pp_total check — show even if zero fixes)
            grey_zone = pp_stats.get("grey_zone_detected", {})
            if grey_zone:
                grey_total = sum(grey_zone.values())
                names = ", ".join(f"{n} ({c})" for n, c in sorted(grey_zone.items(), key=lambda x: -x[1]))
                if pp_total == 0:
                    self._log("", 'info')
                self._log(f"  ⚠ Grey zone chars detected (not modified): {grey_total} — {names}", 'warning')

            self._task_queue.put(('messagebox', 'showinfo', 'Transfer Complete',
                "\n".join(summary_lines)
                + failure_reports_msg
                + eventname_msg))

        self._run_in_thread(work)


def run_app():
    """Create and run the application."""
    root = tk.Tk()
    app = QuickTranslateApp(root)
    root.mainloop()
