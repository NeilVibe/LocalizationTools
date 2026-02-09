"""
QuickTranslate GUI Application.

Tkinter-based GUI with folder-only source mode (auto-detects XML + Excel):
- Match Type Selection: Substring / StringID-only / Strict / Quadruple Fallback
- Enhanced source validation (dry-run parse with per-file reporting)
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

import config

logger = logging.getLogger(__name__)
from core import (
    build_sequencer_strorigin_index,
    scan_folder_for_strings,
    discover_language_files,
    build_translation_lookup,
    build_reverse_lookup,
    find_matches,
    find_matches_with_stats,
    find_matches_stringid_only,
    find_matches_strict,
    find_matches_special_key,
    find_matches_quadruple_fallback,
    find_stringid_from_text,
    format_multiple_matches,
    read_corrections_from_excel,
    get_ordered_languages,
    write_output_excel,
    write_stringid_lookup_excel,
    write_folder_translation_excel,
    write_reverse_lookup_excel,
    parse_corrections_from_xml,
    parse_folder_xml_files,
    # TRANSFER functions
    transfer_folder_to_folder,
    format_transfer_report,
    # Source scanner (auto-recursive language detection)
    scan_source_for_languages,
    validate_source_structure,
    format_scan_result,
    # Transfer plan (full tree table)
    generate_transfer_plan,
    format_transfer_plan,
    # Failure reports (XML + Excel)
    generate_failed_merge_xml_per_language,
    extract_failed_from_folder_results,
    generate_failure_report_excel,
    check_xlsxwriter_available,
    # Missing translation finder
    find_missing_translations_per_language,
    format_report_summary,
)
from core.missing_translation_finder import find_missing_with_options
from gui.missing_params_dialog import MissingParamsDialog
from gui.exclude_dialog import ExcludeDialog
from core.indexing import scan_folder_for_entries, scan_folder_for_entries_with_context
from core.fuzzy_matching import (
    check_model_available,
    load_model,
    build_faiss_index,
    search_fuzzy,
    build_index_from_folder,
    get_cached_index_info,
    clear_cache as clear_fuzzy_cache,
)
from core.matching import find_matches_strict_fuzzy
from core.language_loader import build_stringid_to_category, build_stringid_to_subfolder
from utils import read_text_file_lines


class QuickTranslateApp:
    """Main GUI application for QuickTranslate."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QuickTranslate")
        self.root.geometry("950x1050")
        self.root.resizable(True, True)
        self.root.minsize(850, 800)
        self.root.configure(bg='#f0f0f0')

        # Variables
        self.match_type = tk.StringVar(value="substring")  # substring, stringid_only, strict, strorigin_only

        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.string_id_input = tk.StringVar()
        self.reverse_file_path = tk.StringVar()

        # Fuzzy matching variables
        self.fuzzy_threshold = tk.DoubleVar(value=config.FUZZY_THRESHOLD_DEFAULT)
        self.fuzzy_model_status = tk.StringVar(value="Not loaded")

        # Shared match precision: "perfect" (exact) or "fuzzy" (SBERT)
        # Used by both Strict and Quadruple Fallback modes
        self.match_precision = tk.StringVar(value="perfect")

        # Transfer scope: "all" = overwrite always, "untranslated" = only if target has Korean
        self.transfer_scope = tk.StringVar(value="all")

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
        self.available_langs: Optional[List[str]] = None
        self.cached_paths: Optional[tuple] = None  # (loc_path, export_path)

        # Fuzzy matching cache
        self._fuzzy_model = None
        self._fuzzy_index = None
        self._fuzzy_index_path = None  # Track which target folder was indexed
        self._fuzzy_texts = None
        self._fuzzy_entries = None

        # Exclude rules for Missing Translations
        self._exclude_paths: List[str] = config.load_exclude_rules()

        # Threading infrastructure
        self._task_queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._worker_thread = None

        # Load current settings into variables
        self._load_settings_to_vars()

        # Ensure default Source folder exists and pre-populate if empty
        config.ensure_source_folder()
        if not self.source_path.get():
            self.source_path.set(str(config.SOURCE_FOLDER))

        self._create_ui()

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

        tk.Button(btn_container, text="Exit", command=self.root.quit,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=15, pady=4, cursor='hand2').pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(btn_container, text="Clear All", command=self._clear_fields,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=12, pady=4, cursor='hand2').pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(btn_container, text="Clear Log", command=self._clear_log,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=12, pady=4, cursor='hand2').pack(side=tk.RIGHT, padx=(5, 0))

        self.transfer_btn = tk.Button(btn_container, text="TRANSFER", command=self._transfer,
                                      font=('Segoe UI', 11, 'bold'), bg='#d9534f', fg='white',
                                      relief='flat', padx=20, pady=4, cursor='hand2')
        self.transfer_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.generate_btn = tk.Button(btn_container, text="Generate", command=self._generate,
                                      font=('Segoe UI', 11, 'bold'), bg='#4a90d9', fg='white',
                                      relief='flat', padx=20, pady=4, cursor='hand2')
        self.generate_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Transfer note (shown when TRANSFER disabled for substring mode)
        transfer_note_frame = tk.Frame(main, bg='#f0f0f0')
        transfer_note_frame.pack(fill=tk.X, pady=(0, 8))
        self.transfer_note_label = tk.Label(transfer_note_frame, text="",
                                            font=('Segoe UI', 8), bg='#f0f0f0', fg='#d9534f')
        self.transfer_note_label.pack(side=tk.RIGHT)

        # === Match Type Selection ===
        match_frame = tk.LabelFrame(main, text="Match Type", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=8)
        match_frame.pack(fill=tk.X, pady=(0, 8))

        match_types = [
            ("substring", "Substring Match (Lookup only)", "Find Korean text in StrOrigin"),
            ("stringid_only", "StringID-Only (SCRIPT)", "SCRIPT categories only - match by StringID"),
            ("strict", "StringID + StrOrigin (STRICT)", "Requires BOTH to match exactly"),
            ("strorigin_only", "StrOrigin Only", "Match by StrOrigin text only - fills ALL duplicates"),
        ]

        for value, label, desc in match_types:
            row = tk.Frame(match_frame, bg='#f0f0f0')
            row.pack(fill=tk.X, pady=2)
            tk.Radiobutton(row, text=label, variable=self.match_type, value=value,
                          font=('Segoe UI', 10), bg='#f0f0f0', activebackground='#f0f0f0',
                          cursor='hand2', width=35, anchor='w',
                          command=self._on_match_type_changed).pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=('Segoe UI', 9), bg='#f0f0f0', fg='#888').pack(side=tk.LEFT)

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
        tk.Radiobutton(precision_row, text="Perfect Match (exact StrOrigin comparison)",
                       variable=self.match_precision, value="perfect",
                       font=('Segoe UI', 9), bg='#e8f4e8', activebackground='#e8f4e8',
                       cursor='hand2', command=self._on_precision_changed).pack(
                       side=tk.LEFT, padx=(10, 0))

        precision_row2 = tk.Frame(self.precision_options_frame, bg='#e8f4e8')
        precision_row2.pack(fill=tk.X, pady=(0, 4))
        tk.Radiobutton(precision_row2, text="Fuzzy Match (SBERT similarity for StrOrigin)",
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

        # === Files Section ===
        files_frame = tk.LabelFrame(main, text="Files", font=('Segoe UI', 10, 'bold'),
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

        # === Quick Actions Section ===
        quick_frame = tk.LabelFrame(main, text="Quick Actions", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=8)
        quick_frame.pack(fill=tk.X, pady=(0, 8))

        # StringID Lookup
        stringid_row = tk.Frame(quick_frame, bg='#f0f0f0')
        stringid_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(stringid_row, text="StringID:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.stringid_entry = tk.Entry(stringid_row, textvariable=self.string_id_input,
                                       font=('Segoe UI', 9), relief='solid', bd=1)
        self.stringid_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        self.lookup_btn = tk.Button(stringid_row, text="Lookup", command=self._lookup_stringid,
                 font=('Segoe UI', 9, 'bold'), bg='#5cb85c', fg='white',
                 relief='flat', padx=14, cursor='hand2')
        self.lookup_btn.pack(side=tk.LEFT)

        # Reverse Lookup
        reverse_row = tk.Frame(quick_frame, bg='#f0f0f0')
        reverse_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(reverse_row, text="Reverse:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.reverse_entry = tk.Entry(reverse_row, textvariable=self.reverse_file_path,
                                      font=('Segoe UI', 9), relief='solid', bd=1)
        self.reverse_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(reverse_row, text="Browse", command=self._browse_reverse_file,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT, padx=(0, 8))
        self.reverse_btn = tk.Button(reverse_row, text="Find All", command=self._reverse_lookup,
                 font=('Segoe UI', 9, 'bold'), bg='#d9534f', fg='white',
                 relief='flat', padx=10, cursor='hand2')
        self.reverse_btn.pack(side=tk.LEFT)

        # Missing Translations - Find Korean in Target MISSING from Source (by StrOrigin+StringId key)
        missing_trans_row = tk.Frame(quick_frame, bg='#f0f0f0')
        missing_trans_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(missing_trans_row, text="", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        tk.Label(missing_trans_row, text="Korean in Target MISSING from Source by (StrOrigin, StringId) - per-language XML + Excel report",
                font=('Segoe UI', 8), bg='#f0f0f0', fg='#888').pack(side=tk.LEFT, padx=(0, 8))
        self.missing_trans_btn = tk.Button(missing_trans_row, text="Find Missing Translations",
                 command=self._find_missing_translations,
                 font=('Segoe UI', 9, 'bold'), bg='#9b59b6', fg='white',
                 relief='flat', padx=10, cursor='hand2')
        self.missing_trans_btn.pack(side=tk.RIGHT)

        self._exclude_count_label = tk.Label(missing_trans_row, text="",
                 font=('Segoe UI', 8, 'bold'), bg='#f0f0f0', fg='#e67e22')
        self._exclude_count_label.pack(side=tk.RIGHT, padx=(0, 6))

        self.exclude_btn = tk.Button(missing_trans_row, text="Exclude...",
                 command=self._open_exclude_dialog,
                 font=('Segoe UI', 9, 'bold'), bg='#e67e22', fg='white',
                 relief='flat', padx=10, cursor='hand2')
        self.exclude_btn.pack(side=tk.RIGHT, padx=(0, 4))

        self._update_exclude_count_label()

        # === Settings Section ===
        settings_frame = tk.LabelFrame(main, text="Settings", font=('Segoe UI', 10, 'bold'),
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

        # === Log Section ===
        log_frame = tk.LabelFrame(main, text="Log", font=('Segoe UI', 10, 'bold'),
                                  bg='#f0f0f0', fg='#555', padx=10, pady=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.log_area = scrolledtext.ScrolledText(
            log_frame, height=6, font=('Consolas', 9), relief='solid', bd=1,
            wrap=tk.WORD, state='disabled'
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Configure log tags for colors
        self.log_area.tag_config('info', foreground='#333')
        self.log_area.tag_config('success', foreground='#008000')
        self.log_area.tag_config('warning', foreground='#FF8C00')
        self.log_area.tag_config('error', foreground='#FF0000')
        self.log_area.tag_config('header', foreground='#4a90d9', font=('Consolas', 9, 'bold'))

        # === Progress Section ===
        progress_frame = tk.Frame(main, bg='#f0f0f0')
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

        # Apply initial match type state (disable TRANSFER for substring)
        self._on_match_type_changed()

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

    def _log_on_main(self, timestamp: str, message: str, tag: str):
        """Insert log message into widget (must run on main thread)."""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

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
            logger.warning("  No languagedata_*.xml files found!")

        if non_lang_xml:
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

        # === Smart Auto-Recursive Source Scanner (for SOURCE folders) ===
        # Scan once and reuse result (avoid duplicate scanning)
        scan_result = None
        if role == "SOURCE":
            scan_result = scan_source_for_languages(folder)
            if scan_result.lang_files:
                logger.info("\n  SMART LANGUAGE DETECTION (Auto-Recursive):")
                logger.info("  %-10s %-8s %s", "Language", "Files", "Source")
                logger.info("  %s %s %s", "-"*10, "-"*8, "-"*30)
                for lang in scan_result.get_languages():
                    files = scan_result.lang_files[lang]
                    if len(files) <= 2:
                        sources = ", ".join(f.name for f in files)
                    else:
                        sources = f"{files[0].name}, ... ({len(files)} total)"
                    logger.info("  %-10s %-8d %s", lang, len(files), sources)
                logger.info("\n  Total: %d files in %d languages (auto-detected)",
                            scan_result.total_files, scan_result.language_count)

                if scan_result.unrecognized:
                    logger.info("\n  UNRECOGNIZED ITEMS (%d):", len(scan_result.unrecognized))
                    for item in scan_result.unrecognized[:5]:
                        item_type = "folder" if item.is_dir() else "file"
                        logger.info("    - %s (%s)", item.name, item_type)
                    if len(scan_result.unrecognized) > 5:
                        logger.info("    ... and %d more", len(scan_result.unrecognized) - 5)

                # Log to GUI
                self._log(f"Smart scan: {scan_result.total_files} files in {scan_result.language_count} languages", 'success')
                self._log(f"  Languages: {', '.join(scan_result.get_languages())}", 'info')

        # Validation - show WORKING FOR / NOT WORKING FOR
        logger.info("\n  VALIDATION:")
        is_eligible = len(lang_files) > 0
        lang_codes = sorted([lc for _, lc, _ in lang_files]) if lang_files else []

        # Check for smart scan results (non-standard naming)
        has_smart_scan = role == "SOURCE" and scan_result and scan_result.lang_files
        if has_smart_scan and not is_eligible:
            is_eligible = True

        # Determine what features work with this structure
        working_for = []
        not_working_for = []

        if is_eligible:
            working_for.append(f"TRANSFER ({len(lang_files) if lang_files else scan_result.language_count} language files)")
            working_for.append("Find Missing Translations")
            working_for.append("Reverse Lookup")
            if lang_codes:
                working_for.append(f"Languages: {', '.join(lang_codes)}")
        else:
            not_working_for.append("TRANSFER - no languagedata_*.xml files found")
            not_working_for.append("Find Missing Translations - needs LOC folder structure")

        # StringID Lookup depends on LOC folder in Settings
        loc_folder_set = bool(config.LOC_FOLDER and config.LOC_FOLDER.exists())
        if loc_folder_set:
            working_for.append("StringID Lookup (LOC folder configured)")
        else:
            not_working_for.append("StringID Lookup - set LOC folder in Settings first")

        if working_for:
            logger.info("  WORKING FOR:")
            for item in working_for:
                logger.info("    + %s", item)

        if not_working_for:
            logger.info("  NOT WORKING FOR:")
            for item in not_working_for:
                logger.info("    x %s", item)

        if non_lang_xml:
            logger.info("  [!!] %d non-languagedata XML files will be IGNORED", len(non_lang_xml))
        if subdirs and role == "TARGET":
            logger.info("  [!!] %d subdirectories will be IGNORED (flat scan only)", len(subdirs))

        logger.info("%s\n", separator)

        # Log to GUI
        if is_eligible:
            self._log(f"{role}: ELIGIBLE for TRANSFER + Find Missing Translations", 'success')
            if lang_codes:
                self._log(f"  Languages: {', '.join(lang_codes)}", 'info')
        else:
            self._log(f"{role}: Limited features available (no languagedata files)", 'warning')

        # Run enhanced source validation (dry-run parse)
        if role == "SOURCE" and scan_result:
            self._validate_source_files(folder, scan_result)

    def _validate_source_files(self, folder: Path, scan_result) -> None:
        """Dry-run parse every source file and report results.

        Attempts to parse each XML and Excel file found by the source scanner,
        reporting per-file success/failure and per-language entry counts.

        Args:
            folder: Source folder path
            scan_result: Result from scan_source_for_languages()
        """
        # Collect all files to validate
        files_to_check = []
        for lang, file_list in scan_result.lang_files.items():
            for f in file_list:
                files_to_check.append((f, lang))

        # Also check unrecognized files that might be parseable
        for item in scan_result.unrecognized:
            if item.is_file() and item.suffix.lower() in (".xml", ".xlsx", ".xls"):
                files_to_check.append((item, "???"))

        if not files_to_check:
            logger.info("  No source files to validate.")
            return

        # Parse each file and collect results
        results = []  # (filename, file_type, lang, entry_count, status, error_msg)
        for filepath, lang in files_to_check:
            suffix = filepath.suffix.lower()
            file_type = "XML" if suffix == ".xml" else "Excel"
            try:
                if suffix == ".xml":
                    entries = parse_corrections_from_xml(filepath)
                elif suffix in (".xlsx", ".xls"):
                    entries = read_corrections_from_excel(filepath)
                else:
                    results.append((filepath.name, file_type, lang, 0, "SKIPPED", "Unsupported format"))
                    continue

                count = len(entries) if entries else 0
                if count > 0:
                    results.append((filepath.name, file_type, lang, count, "OK", ""))
                else:
                    results.append((filepath.name, file_type, lang, 0, "EMPTY", "No entries parsed"))
            except Exception as e:
                results.append((filepath.name, file_type, lang, 0, "FAILED", str(e)))

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
            logger.info("  %-4d %-30s %-6s %-8s %8s  %s", idx, fname[:30], ftype, lang, count_str, status_str)

        # Compute summary stats
        xml_good = sum(1 for r in results if r[1] == "XML" and r[4] == "OK")
        excel_good = sum(1 for r in results if r[1] == "Excel" and r[4] == "OK")
        xml_fail = sum(1 for r in results if r[1] == "XML" and r[4] in ("FAILED", "EMPTY"))
        excel_fail = sum(1 for r in results if r[1] == "Excel" and r[4] in ("FAILED", "EMPTY"))
        total_entries = sum(r[3] for r in results)
        errors = [(r[0], r[5]) for r in results if r[4] == "FAILED"]

        # Per-language breakdown
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
            lang_str = "  ".join(f"{lang}: {count:,}" for lang, count in sorted(lang_entries.items()))
            logger.info("  Per-language: %s", lang_str)

        if errors:
            logger.warning("  PARSE ERRORS (%d):", len(errors))
            for fname, err_msg in errors:
                logger.warning("    %s: %s", fname, err_msg)

        logger.info("%s", separator)

        # Log summary to GUI
        if errors:
            gui_summary = ", ".join(summary_parts) if summary_parts else "No files"
            self._log(f"Source validation: {gui_summary}", 'warning')
            for fname, err_msg in errors:
                self._log(f"  PARSE ERROR: {fname}: {err_msg}", 'error')
        else:
            self._log(f"Source validation: {', '.join(summary_parts)}, {total_entries:,} entries total", 'success')

        if lang_entries:
            lang_str = ", ".join(f"{lang}:{count:,}" for lang, count in sorted(lang_entries.items()))
            self._log(f"  Per-language: {lang_str}", 'info')

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

    def _browse_reverse_file(self):
        """Browse for reverse lookup text file."""
        path = filedialog.askopenfilename(
            title="Select Text File with List",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.reverse_file_path.set(path)

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

        if match_type in ("strict", "strorigin_only"):
            self.precision_options_frame.pack(fill=tk.X, pady=(4, 0))
            # Show/hide the fuzzy sub-frame based on current precision
            self._on_precision_changed()
            # Enable TRANSFER button + show transfer scope toggle
            self.transfer_btn.config(state='normal')
            self.transfer_note_label.config(text="")
            self.transfer_scope_frame.pack(fill=tk.X, pady=(4, 0))
            # SAFETY: StrOrigin Only defaults to untranslated-only (no StringID verification)
            if match_type == "strorigin_only":
                self.transfer_scope.set("untranslated")
        elif match_type == "substring":
            self.precision_options_frame.pack_forget()
            # Disable TRANSFER button for substring (lookup only)
            self.transfer_btn.config(state='disabled')
            self.transfer_note_label.config(text="(Lookup only - TRANSFER not available)")
            self.transfer_scope_frame.pack_forget()
        else:
            # stringid_only
            self.precision_options_frame.pack_forget()
            # Enable TRANSFER button + show transfer scope toggle
            self.transfer_btn.config(state='normal')
            self.transfer_scope_frame.pack(fill=tk.X, pady=(4, 0))
            self.transfer_note_label.config(text="")

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
                    self.fuzzy_model_status.set(f"Ready ({info['ntotal']} vectors)")
                else:
                    self.fuzzy_model_status.set("Model loaded, no index yet")
            else:
                self.fuzzy_model_status.set("Not loaded (will load on first use)")
        else:
            self.fuzzy_model_status.set("Not available - model folder missing")

    def _on_precision_changed(self):
        """Show/hide fuzzy threshold slider within precision options."""
        if self.match_precision.get() == "fuzzy":
            self.fuzzy_sub_frame.pack(fill=tk.X, pady=(4, 0))
            self._update_fuzzy_model_status()
        else:
            self.fuzzy_sub_frame.pack_forget()

    def _on_threshold_changed(self, value):
        """Update threshold display labels when slider moves."""
        # Round to nearest step
        val = round(float(value) / config.FUZZY_THRESHOLD_STEP) * config.FUZZY_THRESHOLD_STEP
        self.fuzzy_threshold.set(val)
        self.threshold_label.config(text=f"{val:.2f}")

    def _ensure_fuzzy_model(self) -> bool:
        """Load fuzzy model if needed. Returns True if model is ready.

        Thread-safe: uses queue for UI updates instead of direct widget access.
        """
        if self._fuzzy_model is not None:
            return True

        available, msg = check_model_available()
        if not available:
            self._task_queue.put(('messagebox', 'showerror', 'KR-SBERT Model Not Found', msg))
            return False

        try:
            self._task_queue.put(('fuzzy_status', 'Loading...'))
            self._fuzzy_model = load_model(self._update_status)
            self._task_queue.put(('fuzzy_status', 'Model loaded'))
            self._log("KR-SBERT model loaded successfully", 'success')
            return True
        except Exception as e:
            self._task_queue.put(('fuzzy_status', 'Load failed'))
            self._task_queue.put(('messagebox', 'showerror', 'Model Load Error', f'Failed to load KR-SBERT model:\n{e}'))
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
            self._fuzzy_texts = texts
            self._fuzzy_entries = entries
            # Leave _fuzzy_index as None - not needed for strict_fuzzy

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
        # Only reuse cache if no filter specified (filter changes what we need)
        if (self._fuzzy_index is not None
                and self._fuzzy_index_path == target_path
                and self._fuzzy_texts
                and stringid_filter is None):
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
        from core.indexing import (
            _get_attribute_case_insensitive,
            _iter_locstr_case_insensitive,
        )
        from core.xml_parser import parse_xml_file
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

        # Extract from XML files
        for xml_file in xml_files:
            try:
                root = parse_xml_file(xml_file)
                for elem in _iter_locstr_case_insensitive(root):
                    sid = (_get_attribute_case_insensitive(
                        elem, ['StringId', 'StringID', 'stringid', 'STRINGID']
                    ) or '').strip()
                    if sid:
                        stringids.add(sid)
            except Exception:
                continue

        # Extract from Excel files
        for excel_file in excel_files:
            try:
                corrections = read_corrections_from_excel(excel_file)
                for c in corrections:
                    sid = c.get("string_id", "")
                    if sid:
                        stringids.add(sid)
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

        # Clear fuzzy cache too
        self._fuzzy_index = None
        self._fuzzy_index_path = None
        self._fuzzy_texts = None
        self._fuzzy_entries = None
        clear_fuzzy_cache()

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

    def _poll_queue(self):
        """Drain the task queue on the main thread. Scheduled via root.after."""
        try:
            while True:
                msg = self._task_queue.get_nowait()
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
                elif kind == 'done':
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
                    elif kind == 'done':
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
        """
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
                import traceback
                traceback.print_exc()
            finally:
                self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=_wrapper, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)

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
        self.string_id_input.set("")
        self.reverse_file_path.set("")
        self.progress_value.set(0)
        self.status_text.set("Ready")
        self._clear_log()

    def _disable_buttons(self):
        """Disable all action buttons during processing."""
        self._cancel_event.clear()
        self.generate_btn.config(state='disabled')
        self.transfer_btn.config(state='disabled')
        self.missing_trans_btn.config(state='disabled')
        self.exclude_btn.config(state='disabled')
        self.lookup_btn.config(state='disabled')
        self.reverse_btn.config(state='disabled')
        self.cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

    def _enable_buttons(self):
        """Re-enable all action buttons (respects match type for TRANSFER)."""
        self.generate_btn.config(state='normal')
        # Respect match type: substring disables TRANSFER
        if self.match_type.get() == "substring":
            self.transfer_btn.config(state='disabled')
        else:
            self.transfer_btn.config(state='normal')
        self.missing_trans_btn.config(state='normal')
        self.exclude_btn.config(state='normal')
        self.lookup_btn.config(state='normal')
        self.reverse_btn.config(state='normal')
        self.cancel_btn.pack_forget()
        self._worker_thread = None

    def _generate(self):
        """Main generate action based on current mode."""
        if not self.source_path.get():
            messagebox.showwarning("Warning", "Please select a source folder.")
            return

        source = Path(self.source_path.get())
        if not source.exists():
            messagebox.showerror("Error", f"Source not found:\n{source}")
            return

        # Capture StringVar values on main thread before entering worker
        match_type = self.match_type.get()
        target_path = self.target_path.get()
        precision = self.match_precision.get()
        transfer_scope = self.transfer_scope.get()
        fuzzy_threshold = self.fuzzy_threshold.get()
        source_path_str = self.source_path.get()

        self._disable_buttons()
        self.progress_value.set(0)
        self._clear_log()

        self._log(f"=== QuickTranslate Generation ===", 'header')
        self._log(f"Match Type: {match_type.upper()}", 'info')

        def work():
            # Load data
            if not self._load_data_if_needed(need_sequencer=True):
                return

            self._task_queue.put(('progress', 20))

            # Read input - always folder mode, auto-detect XML + Excel
            corrections = []
            korean_inputs = []

            xml_files = list(source.rglob("*.xml"))
            excel_files = list(source.rglob("*.xlsx")) + list(source.rglob("*.xls"))

            if xml_files:
                xml_corrections = parse_folder_xml_files(source, self._update_status)
                corrections.extend(xml_corrections)
                self._log(f"Loaded {len(xml_corrections)} corrections from {len(xml_files)} XML files", 'info')

            if excel_files:
                for excel_file in excel_files:
                    excel_corrections = read_corrections_from_excel(excel_file)
                    corrections.extend(excel_corrections)
                self._log(f"Loaded {len(excel_files)} Excel files", 'info')

            korean_inputs = [c.get("str_origin", "") for c in corrections if c.get("str_origin")]
            if not korean_inputs:
                korean_inputs = [c.get("string_id", "") for c in corrections if c.get("string_id")]

            if not korean_inputs and not corrections:
                self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'No input data found.'))
                self._log("No input data found!", 'error')
                return

            self._task_queue.put(('progress', 40))

            # Find matches based on match type
            self._update_status("Finding matches...")
            self._log(f"Finding matches using {match_type} mode...", 'info')

            matches_per_input = []
            stats = {"total": len(korean_inputs), "matched": 0, "no_match": 0, "multi_match": 0, "skipped": 0, "total_matches": 0}

            if match_type == "substring":
                # Use new stats-tracking function
                matches_per_input, stats = find_matches_with_stats(korean_inputs, self.strorigin_index)
                self._log(f"Substring search complete:", 'info')
                self._log(f"  - Total inputs: {stats['total']}", 'info')
                self._log(f"  - Matched (1): {stats['matched']}", 'success')
                self._log(f"  - Multi-match: {stats['multi_match']}", 'warning')
                self._log(f"  - Not found: {stats['no_match']}", 'error')

            elif match_type == "stringid_only":
                # StringID-only (SCRIPT): Filter to SCRIPT categories
                if not self.stringid_to_category:
                    self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'Category index not loaded.'))
                    return

                if corrections:
                    script_corrections, skipped = find_matches_stringid_only(
                        corrections, self.stringid_to_category,
                        self.stringid_to_subfolder,
                    )
                    korean_inputs = [c.get("str_origin", "") for c in script_corrections]
                    for c in script_corrections:
                        matches_per_input.append([c.get("string_id")])
                    stats["total"] = len(corrections)
                    stats["matched"] = len(script_corrections)
                    stats["skipped"] = skipped
                    stats["total_matches"] = len(script_corrections)
                    self._log(f"SCRIPT filter results:", 'info')
                    self._log(f"  - Total corrections: {stats['total']}", 'info')
                    self._log(f"  - SCRIPT strings kept: {stats['matched']}", 'success')
                    self._log(f"  - Non-SCRIPT skipped: {stats['skipped']}", 'warning')
                else:
                    # Excel mode with StringIDs in column A
                    exclude_lower = {s.lower() for s in config.SCRIPT_EXCLUDE_SUBFOLDERS}
                    for text in korean_inputs:
                        sid = text.strip()
                        category = self.stringid_to_category.get(sid, "")
                        if category in config.SCRIPT_CATEGORIES:
                            # Check subfolder exclusion (case-insensitive)
                            subfolder = self.stringid_to_subfolder.get(sid, "") if self.stringid_to_subfolder else ""
                            if subfolder.lower() in exclude_lower:
                                matches_per_input.append([])
                                stats["skipped"] += 1
                                continue
                            matches_per_input.append([sid])
                            stats["matched"] += 1
                        else:
                            matches_per_input.append([])
                            stats["skipped"] += 1
                    stats["total_matches"] = stats["matched"]

            elif match_type == "strict":
                # Strict mode: Match by StringID + StrOrigin tuple
                if not corrections:
                    self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'Strict mode requires XML input or corrections data.'))
                    return

                if not target_path:
                    self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'Strict mode requires a Target folder for matching.'))
                    return

                self._log(f"Scanning target folder: {target_path}", 'info')
                xml_entries = scan_folder_for_entries(Path(target_path), self._update_status)
                self._log(f"Found {len(xml_entries)} entries in target", 'info')

                if precision == "fuzzy":
                    # Fuzzy precision: use SBERT similarity for StrOrigin comparison
                    if not self._ensure_fuzzy_model():
                        return

                    # Extract StringIDs from corrections FIRST - this is the filter!
                    correction_stringids = {c.get("string_id", "") for c in corrections if c.get("string_id")}
                    self._log(f"Corrections have {len(correction_stringids):,} unique StringIDs", 'info')

                    only_untranslated = transfer_scope == "untranslated"

                    # Load ONLY entries matching our correction StringIDs
                    if not self._ensure_fuzzy_entries(
                        target_path,
                        stringid_filter=correction_stringids,
                        only_untranslated=only_untranslated,
                    ):
                        return

                    self._log(f"Strict mode with FUZZY precision (threshold: {fuzzy_threshold:.2f})", 'info')

                    matched, not_found = find_matches_strict_fuzzy(
                        corrections, xml_entries, self._fuzzy_model, self._fuzzy_index,
                        self._fuzzy_texts, self._fuzzy_entries, fuzzy_threshold,
                        only_untranslated=only_untranslated,
                        progress_callback=self._progress_log_callback
                    )
                else:
                    self._log("Strict mode with PERFECT precision", 'info')
                    matched, not_found = find_matches_strict(corrections, xml_entries)

                korean_inputs = [c.get("str_origin", "") for c in matched]
                for c in matched:
                    matches_per_input.append([c.get("string_id")])
                stats["total"] = len(corrections)
                stats["matched"] = len(matched)
                stats["no_match"] = not_found
                stats["total_matches"] = len(matched)

                precision_label = "FUZZY" if precision == "fuzzy" else "PERFECT"
                self._log(f"Strict match results ({precision_label}):", 'info')
                self._log(f"  - Total corrections: {stats['total']}", 'info')
                self._log(f"  - Matched (ID+Origin): {stats['matched']}", 'success')
                self._log(f"  - Not found: {stats['no_match']}", 'error')

            elif match_type == "quadruple_fallback":
                # Quadruple Fallback: StrOrigin + filename + adjacency cascade
                if not corrections:
                    self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'Quadruple Fallback mode requires corrections data (XML or structured Excel).'))
                    return

                if not target_path:
                    self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'Quadruple Fallback mode requires a Target folder.'))
                    return

                # Scan TARGET with context to build 4-level indexes
                self._log(f"Scanning target with context: {target_path}", 'info')
                all_entries, level1_idx, level2a_idx, level2b_idx, level3_idx = scan_folder_for_entries_with_context(
                    Path(target_path), self._update_status
                )
                self._log(f"Found {len(all_entries)} entries with context in target", 'info')

                # Enrich SOURCE corrections with file/adjacency context if XML source
                source_has_context = any(c.get("file_relpath") for c in corrections)
                if not source_has_context:
                    source_path_obj = Path(source_path_str)
                    scan_source = source_path_obj if source_path_obj.is_dir() else source_path_obj.parent
                    self._log(f"Enriching source corrections with context from: {scan_source}", 'info')
                    src_entries, _, _, _, _ = scan_folder_for_entries_with_context(
                        scan_source, self._update_status
                    )
                    if src_entries:
                        from core.text_utils import normalize_for_matching
                        src_lookup = {}
                        for se in src_entries:
                            norm_o = normalize_for_matching(se.get("str_origin", ""))
                            if norm_o not in src_lookup:
                                src_lookup[norm_o] = se
                        enriched_count = 0
                        for c in corrections:
                            c_origin = c.get("str_origin", "").strip()
                            if not c_origin:
                                continue
                            norm_c = normalize_for_matching(c_origin)
                            src_entry = src_lookup.get(norm_c)
                            if src_entry:
                                c["file_relpath"] = src_entry.get("file_relpath", "")
                                c["adjacent_before"] = src_entry.get("adjacent_before", "")
                                c["adjacent_after"] = src_entry.get("adjacent_after", "")
                                c["adjacency_hash"] = src_entry.get("adjacency_hash", "")
                                enriched_count += 1
                        source_has_context = enriched_count > 0
                        self._log(f"Enriched {enriched_count}/{len(corrections)} corrections with source context", 'info')

                if not source_has_context:
                    self._log("Source lacks file context - using L3 (StrOrigin only) fallback", 'warning')

                if precision == "fuzzy":
                    if not self._ensure_fuzzy_model():
                        return

                    correction_stringids = {c.get("string_id", "") for c in corrections if c.get("string_id")}
                    self._log(f"Corrections have {len(correction_stringids):,} unique StringIDs for filtering", 'info')

                    only_untranslated = transfer_scope == "untranslated"
                    if not self._ensure_fuzzy_index(target_path, stringid_filter=correction_stringids, only_untranslated=only_untranslated):
                        return
                    self._log(f"Quadruple Fallback with FUZZY precision (threshold: {fuzzy_threshold:.2f})", 'info')

                    matched_corrections, not_found, level_counts = find_matches_quadruple_fallback(
                        corrections, level1_idx, level2a_idx, level2b_idx, level3_idx,
                        source_has_context,
                        use_fuzzy=True,
                        fuzzy_model=self._fuzzy_model,
                        fuzzy_threshold=fuzzy_threshold,
                        fuzzy_texts=self._fuzzy_texts,
                        fuzzy_entries=self._fuzzy_entries,
                        fuzzy_index=self._fuzzy_index,
                    )
                else:
                    self._log("Quadruple Fallback with PERFECT precision", 'info')

                    matched_corrections, not_found, level_counts = find_matches_quadruple_fallback(
                        corrections, level1_idx, level2a_idx, level2b_idx, level3_idx,
                        source_has_context,
                    )

                korean_inputs = [c.get("str_origin", "") for c in matched_corrections]
                for c in matched_corrections:
                    matches_per_input.append([c.get("matched_string_id")])
                stats["total"] = len(corrections)
                stats["matched"] = len(matched_corrections)
                stats["no_match"] = not_found
                stats["total_matches"] = len(matched_corrections)

                precision_label = "FUZZY" if precision == "fuzzy" else "PERFECT"
                self._log(f"Quadruple Fallback results ({precision_label}):", 'info')
                self._log(f"  - Total corrections: {stats['total']}", 'info')
                self._log(f"  - Matched total: {stats['matched']}", 'success')
                self._log(f"    L1  (Quadruple: Origin+File+Adjacent): {level_counts['L1']}", 'success')
                self._log(f"    L2A (Double: Origin+File):          {level_counts['L2A']}", 'info')
                self._log(f"    L2B (Double: Origin+Adjacent):      {level_counts['L2B']}", 'info')
                self._log(f"    L3  (Single: Origin only):          {level_counts['L3']}", 'warning')
                self._log(f"  - Not found: {stats['no_match']}", 'error')

            self._task_queue.put(('progress', 70))

            # Write output
            self._update_status("Writing output...")
            self._log("Writing output Excel...", 'info')
            config.ensure_output_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.OUTPUT_FOLDER / f"QuickTranslate_{timestamp}.xlsx"

            write_output_excel(
                output_path,
                korean_inputs,
                matches_per_input,
                self.translation_lookup,
                self.available_langs,
                config.LANGUAGE_NAMES,
                stats=stats,
                match_type=match_type,
            )

            self._task_queue.put(('progress', 100))
            self._update_status(f"Done! {stats['total']} inputs processed")
            self._log(f"=== Generation Complete ===", 'header')
            self._log(f"Output: {output_path}", 'success')
            self._log(f"Summary: {stats['matched']} matched, {stats.get('no_match', 0)} not found, {stats.get('skipped', 0)} skipped", 'info')

            self._task_queue.put(('messagebox', 'showinfo', 'Success',
                f"Output saved to:\n{output_path}\n\n"
                f"Total: {stats['total']}\n"
                f"Matched: {stats['matched']}\n"
                f"Not Found: {stats.get('no_match', 0)}\n"
                f"Skipped: {stats.get('skipped', 0)}"))

        self._run_in_thread(work)

    def _lookup_stringid(self):
        """Look up a single StringID."""
        string_id = self.string_id_input.get().strip()

        if not string_id:
            messagebox.showwarning("Warning", "Please enter a StringID.")
            return

        self._disable_buttons()
        self._log(f"Looking up StringID: {string_id}", 'info')

        def work():
            if not self._load_data_if_needed(need_sequencer=False):
                return

            # Check if StringID exists
            found = False
            for lang_code, lookup in self.translation_lookup.items():
                if string_id in lookup:
                    found = True
                    break

            if not found:
                self._task_queue.put(('messagebox', 'showwarning', 'Warning', f'StringID not found: {string_id}'))
                self._log(f"StringID not found: {string_id}", 'error')
                self._update_status(f"StringID not found: {string_id}")
                return

            # Write output
            self._update_status("Writing output...")
            config.ensure_output_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.OUTPUT_FOLDER / f"StringID_{string_id}_{timestamp}.xlsx"

            write_stringid_lookup_excel(
                output_path,
                string_id,
                self.translation_lookup,
                self.available_langs,
                config.LANGUAGE_NAMES,
            )

            self._update_status(f"Done! Lookup for {string_id}")
            self._log(f"Output saved: {output_path}", 'success')
            self._task_queue.put(('messagebox', 'showinfo', 'Success', f'Output saved to:\n{output_path}'))

        self._run_in_thread(work)

    def _reverse_lookup(self):
        """Perform reverse lookup from any language to all languages."""
        if not self.reverse_file_path.get():
            messagebox.showwarning("Warning", "Please select a text file with list of strings.")
            return

        file_path = Path(self.reverse_file_path.get())
        if not file_path.exists():
            messagebox.showerror("Error", f"File not found:\n{file_path}")
            return

        self._disable_buttons()
        self._log(f"Reverse lookup from: {file_path}", 'info')

        def work():
            if not self._load_data_if_needed(need_sequencer=False):
                return

            # Read input file
            self._update_status("Reading input file...")
            input_texts = read_text_file_lines(file_path)

            if not input_texts:
                self._task_queue.put(('messagebox', 'showwarning', 'Warning', 'No text found in input file.'))
                return

            self._log(f"Read {len(input_texts)} texts from file", 'info')

            # Build reverse lookup
            self._update_status("Building reverse lookup...")
            reverse_lookup = build_reverse_lookup(self.translation_lookup)

            # Find StringID for each input text
            self._update_status("Finding StringIDs...")
            stringid_map = {}
            not_found_list = []
            detected_langs = set()

            for text in input_texts:
                result = find_stringid_from_text(text, reverse_lookup)
                if result:
                    string_id, lang = result
                    stringid_map[text] = string_id
                    detected_langs.add(lang)
                else:
                    not_found_list.append(text)

            self._log(f"Found: {len(stringid_map)}, Not found: {len(not_found_list)}", 'info')
            if detected_langs:
                self._log(f"Detected languages: {', '.join(sorted(detected_langs))}", 'info')

            # Write output
            self._update_status("Writing output...")
            config.ensure_output_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.OUTPUT_FOLDER / f"ReverseLookup_{timestamp}.xlsx"

            write_reverse_lookup_excel(
                output_path,
                input_texts,
                stringid_map,
                self.translation_lookup,
                self.available_langs,
                config.LANGUAGE_NAMES,
            )

            found_count = len(stringid_map)
            total_count = len(input_texts)
            detected_str = ", ".join(sorted(detected_langs)) if detected_langs else "N/A"

            self._update_status(f"Done! {found_count}/{total_count} found")
            self._log(f"Output saved: {output_path}", 'success')
            self._task_queue.put(('messagebox', 'showinfo', 'Success',
                f"Output saved to:\n{output_path}\n\n"
                f"Found: {found_count}/{total_count}\n"
                f"Detected languages: {detected_str}"))

        self._run_in_thread(work)

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
            target_path_str = str(config.LOC_FOLDER)
            self.target_path.set(target_path_str)

        target = Path(target_path_str)
        if not target.exists():
            messagebox.showerror("Error", f"Target not found:\n{target}")
            return

        if not target.is_dir():
            messagebox.showwarning("Warning",
                "Target must be a folder containing languagedata_*.xml files.\n\n"
                "Example: LOC folder with languagedata_FRE.xml, languagedata_GER.xml, etc.")
            return

        lang_files = list(target.glob("languagedata_*.xml"))
        if not lang_files:
            messagebox.showwarning("Warning",
                f"No languagedata_*.xml files found in:\n{target}\n\n"
                "Please select a folder with languagedata_FRE.xml, languagedata_GER.xml, etc.")
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
                self._log("Loading KR-SBERT model for fuzzy matching...", 'info')
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

    def _transfer(self):
        """Transfer corrections from source to target XML files (LOC folder)."""
        # Block transfer for substring mode (lookup only)
        if self.match_type.get() == "substring":
            messagebox.showwarning("Warning", "Substring mode is lookup-only. TRANSFER is not available.\n\n"
                                   "Please select StringID-Only, Strict, or Quadruple Fallback mode.")
            return

        if not self.source_path.get():
            messagebox.showwarning("Warning", "Please select a Source folder with corrections.")
            return

        if not self.target_path.get():
            # Default to LOC folder from config
            self.target_path.set(str(config.LOC_FOLDER))

        source = Path(self.source_path.get())
        target = Path(self.target_path.get())

        if not source.exists():
            messagebox.showerror("Error", f"Source not found:\n{source}")
            return

        if not target.exists():
            messagebox.showerror("Error", f"Target folder not found:\n{target}")
            return

        # Capture StringVar values on main thread
        match_type = self.match_type.get()
        precision = self.match_precision.get()
        transfer_scope = self.transfer_scope.get()
        fuzzy_threshold = self.fuzzy_threshold.get()

        # === GENERATE FULL TRANSFER PLAN BEFORE CONFIRMATION ===
        match_str = match_type.upper()

        # Add precision info for modes that support it
        if match_type in ("strict", "strorigin_only"):
            match_str = f"{match_str} ({precision.upper()})"

        scope_str = ("Only untranslated (Korean)" if transfer_scope == "untranslated"
                     else "ALL matches (overwrite)")

        # Generate complete transfer plan with full tree table
        transfer_plan = generate_transfer_plan(source, target)

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
            plan_summary += f"\n\nWarnings:\n" + "\n".join(f"  - {w}" for w in transfer_plan.warnings[:3])

        confirm = messagebox.askyesno(
            "Confirm Transfer - Review Tree in Terminal",
            f"FULL TREE TABLE printed to terminal - review before confirming!\n\n"
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
        self._log(f"Source: {source}", 'info')
        self._log(f"Target: {target}", 'info')

        # Log transfer plan summary
        self._log(f"Transfer Plan: {transfer_plan.total_ready} files ready, {transfer_plan.total_skipped} skipped", 'info')
        for lang in transfer_plan.languages_ready:
            plan = transfer_plan.language_plans[lang]
            self._log(f"  {lang}: {plan.file_count} files → {plan.target_file.name if plan.target_file else 'N/A'}", 'success')
        for lang in transfer_plan.languages_skipped:
            plan = transfer_plan.language_plans[lang]
            self._log(f"  {lang}: {plan.file_count} files → SKIPPED (no target)", 'warning')

        def work():
            # Cross-match summary - main analysis already in transfer plan
            if source.is_dir() and target.is_dir():
                src_xmls = {f.stem.lower()[13:]: f.name for f in source.glob("*.xml") if f.stem.lower().startswith("languagedata_")}
                tgt_xmls = {f.stem.lower()[13:]: f.name for f in target.glob("*.xml") if f.stem.lower().startswith("languagedata_")}
                matched_langs = sorted(set(src_xmls.keys()) & set(tgt_xmls.keys()))
                src_only = sorted(set(src_xmls.keys()) - set(tgt_xmls.keys()))
                tgt_only = sorted(set(tgt_xmls.keys()) - set(src_xmls.keys()))
                self._log(f"Cross-match: {len(matched_langs)} pairs, {len(src_only)} source-only, {len(tgt_only)} target-only", 'info')

            # Load category data if needed for stringid_only mode
            stringid_to_category = None
            stringid_to_subfolder = None
            if match_type == "stringid_only":
                if not self._load_data_if_needed(need_sequencer=True):
                    return
                stringid_to_category = self.stringid_to_category
                stringid_to_subfolder = self.stringid_to_subfolder

            # For fuzzy precision modes, extract StringIDs from source FIRST to filter index
            source_stringids = None
            if precision == "fuzzy" and match_type in ("strict", "strorigin_only"):
                self._log("Extracting StringIDs from source for filtered index build...", 'info')
                source_stringids = self._extract_stringids_from_source(source)
                self._log(f"Source has {len(source_stringids):,} unique StringIDs", 'info')

            only_untranslated = transfer_scope == "untranslated"

            # For strict/strorigin_only with fuzzy precision, need model + FAISS index
            if precision == "fuzzy" and match_type in ("strict", "strorigin_only"):
                if not self._ensure_fuzzy_model():
                    return
                if not self._ensure_fuzzy_index(str(target), stringid_filter=source_stringids, only_untranslated=only_untranslated):
                    return
                self._log(f"{match_type} TRANSFER with FUZZY precision (threshold={fuzzy_threshold:.2f})", 'info')

            self._task_queue.put(('progress', 20))
            self._update_status("Transferring corrections...")

            # Map match_type + precision to transfer match_mode
            if match_type == "stringid_only":
                transfer_match_mode = "stringid_only"
            elif match_type == "strorigin_only":
                transfer_match_mode = "strorigin_only_fuzzy" if precision == "fuzzy" else "strorigin_only"
            elif match_type == "strict":
                transfer_match_mode = "strict_fuzzy" if precision == "fuzzy" else "strict"
            else:
                transfer_match_mode = "strict"

            # Build kwargs for transfer functions
            transfer_kwargs = {
                "stringid_to_category": stringid_to_category,
                "stringid_to_subfolder": stringid_to_subfolder,
                "match_mode": transfer_match_mode,
                "dry_run": False,
                "only_untranslated": only_untranslated,
            }

            # Pass threshold AND pre-built fuzzy data for fuzzy modes
            # CRITICAL: Without this, transfer functions rebuild from scratch!
            if precision == "fuzzy" and match_type in ("strict", "strorigin_only"):
                transfer_kwargs["threshold"] = fuzzy_threshold
                transfer_kwargs["fuzzy_model"] = self._fuzzy_model
                transfer_kwargs["fuzzy_texts"] = self._fuzzy_texts
                transfer_kwargs["fuzzy_entries"] = self._fuzzy_entries
                transfer_kwargs["source_stringids"] = source_stringids
                transfer_kwargs["fuzzy_index"] = self._fuzzy_index
                self._log(f"Passing pre-built fuzzy data: {len(self._fuzzy_entries):,} entries, FAISS index ready", 'info')

            if match_type == "quadruple_fallback" and precision == "fuzzy":
                transfer_kwargs["use_fuzzy_precision"] = True

            # Perform transfer (always folder mode)
            results = transfer_folder_to_folder(
                source,
                target,
                progress_callback=self._update_status,
                **transfer_kwargs,
            )
            self._task_queue.put(('progress', 80))

            # Generate report
            report = format_transfer_report(results, mode="folder")

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
            skipped = results.get("total_skipped", 0)
            skipped_excluded = results.get("total_skipped_excluded", 0)
            total_failures = not_found + strorigin_mismatch + skipped_translated + skipped + skipped_excluded
            failure_reports_msg = ""

            if total_failures > 0:
                self._log("", 'info')
                self._log("=== Generating Failure Reports ===", 'header')

                report_folder = source if source.is_dir() else source.parent
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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

            self._task_queue.put(('progress', 100))
            self._update_status(f"Transfer complete: {updated} updated")

            self._task_queue.put(('messagebox', 'showinfo', 'Transfer Complete',
                f"Transfer completed!\n\n"
                f"Matched: {matched}\n"
                f"Updated: {updated}\n"
                f"Not Found: {not_found}\n"
                + (f"Skipped (translated): {skipped_translated}\n" if skipped_translated > 0 else "")
                + f"\nTarget: {target}"
                + failure_reports_msg))

        self._run_in_thread(work)


def run_app():
    """Create and run the application."""
    root = tk.Tk()
    app = QuickTranslateApp(root)
    root.mainloop()
